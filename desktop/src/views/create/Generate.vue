<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '@/api'
import { formatDuration } from '@/utils/format'

const router = useRouter()
const route = useRoute()

const detail = ref(null)
const timer = ref(null)
// 终态错误:轮询被拒(未登录/鉴权过期/无权限/任务不存在)时停止轮询并提示,
// 否则前端会卡在"生成中"永久转圈(视频生成耗时长,期间登录态过期最常见,详见下方 fetchDetail)
const fatal = ref('')
const downloading = ref(false)

// 局部重跑(改一句台词重生成):弹窗收集分段下标与新台词
const showSeg = ref(false)
const segIndex = ref(0)
const segText = ref('')
// 局部重跑提交中禁用:避免连点重复派发,触发后端「任务正在生成中」守卫
const segSubmitting = ref(false)

// 分镜镜头编辑(覆盖提示词,供后续局部重跑):按镜头 index 编辑,持久化到后端分镜表
const editingShot = ref(null)
const shotEditPrompt = ref('')
// 镜头提示词保存中禁用:避免重复提交
const shotSaving = ref(false)
function openShotEdit(shot) {
  editingShot.value = shot.index
  shotEditPrompt.value = shot.prompt || ''
}
async function saveShotEdit() {
  if (editingShot.value === null || shotSaving.value) return
  shotSaving.value = true
  try {
    const res = await api.storyboard.shotUpdate.post({
      task_id: Number(route.params.id),
      index: editingShot.value,
      prompt: shotEditPrompt.value,
    })
    // 只有确实写回镜头(data 非空)才算成功:避免后端「镜头不存在」时误报已更新
    if (res.code === 1 && res.data) {
      // 同步回本地展示:更新 usage.shot_prompts 中对应序号的提示词,触发分镜列表重算
      const usage = (detail.value.usage = detail.value.usage || {})
      const prompts = Array.isArray(usage.shot_prompts) ? usage.shot_prompts : []
      const hit = prompts.find((it) => it.index === editingShot.value)
      if (hit) hit.prompt = shotEditPrompt.value
      else prompts.push({ index: editingShot.value, prompt: shotEditPrompt.value })
      usage.shot_prompts = prompts
      window.$message?.success('镜头提示词已更新')
    } else {
      window.$message?.warning(res.message || '更新失败')
    }
  } catch (e) { /* 拦截器已提示 */ } finally {
    shotSaving.value = false
    editingShot.value = null
  }
}
// 可用分段来自成片脚本时间轴,后端据此替换对应时间窗;无则回退手动输入下标
const segOptions = computed(() => {
  const segs = detail.value?.params?.script?.segments || []
  return segs.map((s, i) => ({
    index: i,
    label: `第${i + 1}段 · ${(s.text || '').slice(0, 12)}${(s.text || '').length > 12 ? '…' : ''}`,
  }))
})
// 当前选中分段是否已编辑过镜头描述:有则局部重跑会采用该描述生成画面(后端已从 usage.shot_prompts 取用)
const segEditedPrompt = computed(() => {
  const prompts = Array.isArray(detail.value?.usage?.shot_prompts) ? detail.value.usage.shot_prompts : []
  const hit = prompts.find((it) => it.index === Number(segIndex.value))
  return hit?.prompt || ''
})

// 原片分镜表:worker 解析参考视频后随 usage 回写落库(仅多段复刻任务才有)。
// 它是「复刻拆解」唯一可见的产物 —— 用户据此判断成片是否按原片镜头数拍,
// 也能核对模型把哪一镜理解错了(逐镜头逆推描述按镜头序号并入)。
// 逐镜头质检结果(usage.shot_qc)同样按序号并入:只标记不自动重跑,重跑由用户决定。
const showShots = ref(false)
const shotList = computed(() => {
  const usage = detail.value?.usage || {}
  const shots = Array.isArray(usage.shots) ? usage.shots : []
  const prompts = new Map(
    (Array.isArray(usage.shot_prompts) ? usage.shot_prompts : []).map((it) => [it.index, it.prompt])
  )
  const scores = new Map(
    (Array.isArray(usage.shot_qc) ? usage.shot_qc : []).map((it) => [it.index, it])
  )
  return shots.map((shot) => {
    const qc = scores.get(shot.index)
    return {
      ...shot,
      prompt: prompts.get(shot.index) || '',
      score: qc && typeof qc.score === 'number' ? qc.score : null,
      // low 由 worker 判定(低分线只在 worker 一处定义),前端不重复写阈值
      low: !!qc?.low,
      issue: qc?.issue || '',
    }
  })
})
// 已参与质检的镜头均分:给一个"这条到底复刻得像不像"的总观感
const shotQcAvg = computed(() => {
  const scored = shotList.value.filter((shot) => shot.score !== null)
  if (!scored.length) return null
  return Math.round(scored.reduce((sum, shot) => sum + shot.score, 0) / scored.length)
})

// 生成决策日志 / 成本快照:worker 仅在「提交成功」时记录实际选用的网关,失败任务不计入。
// 默认路径仍「只标记不阻断」(自动重跑默认关闭),这里仅做透明展示,不改变任何付费语义。
const showDecision = ref(false)
const decisionLog = computed(() =>
  Array.isArray(detail.value?.usage?.decision_log) ? detail.value.usage.decision_log : []
)
const costSnapshot = computed(() => detail.value?.usage?.cost_snapshot || null)

// 本次实际注入的提示词资产(backend 在建单时写入 params.injected_assets 并随详情透出)。
// 为什么必须让用户看到正文:页面上能操作的只有"形态/创意档位"这类业务旋钮,
// 当成片不符预期时需要确认模型到底收到了什么 —— 否则"换了档位却没变化"只能靠猜。
// 与注入行为严格对齐:没注入的资产不会出现在这里,不做二次推断,免得预览与实际不一致。
const showAssets = ref(false)
const ASSET_LABELS = {
  format: '复刻目标形态',
  creative: '创作要求(档位/钩子/自定义)',
}
const injectedAssets = computed(() => {
  const assets = detail.value?.params?.injected_assets
  if (!assets || typeof assets !== 'object') return []
  return Object.keys(assets)
    .filter((key) => String(assets[key] || '').trim())
    .map((key) => ({ key, label: ASSET_LABELS[key] || key, body: String(assets[key]) }))
})

// 生成阶段(与后端 TASK_PROFILES 对齐,按任务类型展示)
const STAGES = {
  video: ['解析模板结构', 'AI改写视频脚本', '提交生成任务', '模型生成视频', '回传成片'],
  digital: ['解析口播文案', '合成口播音频', '提交数字人任务', '口型驱动合成', '回传成片'],
  // AI 创作(图片/音频/文本):此前没有对应页面,阶段文案会回落到视频的,与真实过程不符
  image: ['解析提示词', 'AI绘制画面', '优化输出'],
  audio: ['解析文本', '合成音频', '优化输出'],
  text: ['解析提示词', '生成文本', '润色输出']
}
const stages = computed(() => STAGES[detail.value?.type] || STAGES.video)
// 各类型的进行中文案:图片/音频/文本此前都会显示"正在为你生成爆款视频"
const TYPE_TITLES = {
  video: '正在为你生成爆款视频...',
  digital: '正在为你生成数字人口播视频...',
  image: '正在为你绘制图片...',
  audio: '正在为你合成音频...',
  text: '正在为你生成文案...'
}
const genTitle = computed(() => TYPE_TITLES[detail.value?.type] || TYPE_TITLES.video)

// 结果形态:worker 对 image/audio 同样回写 result_video(媒体地址),文本回写 result_text
const mediaKind = computed(() => {
  const t = detail.value?.type
  if (t === 'image' || t === 'audio' || t === 'text') return t
  return 'video'
})
// 作品标题:视频任务取模板标题,数字人任务取数字人名称,其余按类型给通用名
const TYPE_WORK_NAMES = {
  video: '我的成品',
  digital: '数字人口播',
  image: 'AI 图片',
  audio: 'AI 音频',
  text: 'AI 文案'
}
const workTitle = computed(
  () => detail.value?.template_title || detail.value?.params?.digital_name
    || TYPE_WORK_NAMES[detail.value?.type] || '我的成品'
)

// 用户设定的「一句话目标」(选填,随建单下发):结果页回显,让用户确认"我想要的正是这个",
// 也便于复盘"为什么成片与预期有出入"。不展示则跳过(选填项,留空也能出片)。
const goalText = computed(() => {
  const g = detail.value?.params?.goal
  return typeof g === 'string' && g.trim() ? g.trim() : ''
})
// 本次成片采用的效果口径:从建单参数回显,让用户看懂"这个版本是怎么生成的"。
// 若不展示,用户点「换个效果」会以为"换了档却没反应"(实际是同一个档);回显后点击才有对照依据。
// 各取值与后端白名单(VALID_CREATIVE_LEVELS / VALID_HOOK_BOOSTS / REPLICATE_FORMATS)同源,只做展示不做校验。
const styleSummary = computed(() => {
  const p = detail.value?.params || {}
  const labels = []
  const fmtMap = {
    talking_head: '口播', short_drama: '短剧', presenter_led_explainer: '主讲人讲解',
    street_interview: '街采', two_person_podcast: '双人播客', ranking_listicle: '榜单盘点',
    narration_led_demo: '旁白演示',
  }
  if (p.format) labels.push(`形态:${fmtMap[p.format] || p.format}`)
  const clMap = { faithful: '忠实复刻', creative: '适度改造', viral: '爆款改造' }
  if (p.creative_level) labels.push(clMap[p.creative_level] || p.creative_level)
  const hbMap = { normal: '正常开头', strong: '强化开头', off: '关闭开头处理' }
  if (p.hook_boost) labels.push(hbMap[p.hook_boost] || p.hook_boost)
  return labels.join(' · ')
})

// 失败原因展示前做兜底过滤:worker 已改为只回写"说人话"的 fail_reason,
// 但历史任务落库的仍可能是原始报错(Error code/网关返回体/URL 等技术细节),
// 这些不该给用户看 —— 检出技术载荷就换通用话术,完整原因始终在后端日志/管理端排查。
const RAW_ERR_RE = /Error code:?\s*\d|\{\s*['"]|https?:\/\/|Traceback|HTTP\s*\/?\s*\d/i
const failMsg = computed(() => {
  const raw = detail.value?.fail_reason
  if (raw && !RAW_ERR_RE.test(raw)) return raw
  return '抱歉，生成过程中出现异常，已为你安全保存进度，可重试一次；若多次失败请联系客服。'
})

async function fetchDetail() {
  try {
    const res = await api.task.detail.post({ id: Number(route.params.id) })
    if (res.code !== 1) {
      // 查询被拒(未登录/鉴权过期/无权限/任务不存在):这类问题重试也不会恢复,
      // 必须停止轮询并明确提示,否则页面会卡在"生成中"永久转圈
      // (视频生成耗时长,期间 JWT 过期是最典型触发场景)
      stopPolling()
      fatal.value = res.message || res.msg || '无法获取该任务状态,请刷新页面或重新登录'
      return
    }
    detail.value = res.data
    if (res.data.status === 'processing') {
      if (!timer.value) timer.value = setInterval(fetchDetail, 2000)
    } else {
      stopPolling()
    }
  } catch (e) { /* 网络瞬断:保持轮询,下次再来 */ }
}

// 终态错误后由用户主动重试:清空错误态重新拉取并重启轮询
function onRefresh() {
  fatal.value = ''
  detail.value = null
  fetchDetail()
  if (!timer.value) timer.value = setInterval(fetchDetail, 2000)
}

function stopPolling() {
  if (timer.value) { clearInterval(timer.value); timer.value = null }
}

// 剩余时间格式化:复用统一工具,无有效值时提示"即将完成"
function formatRemain(sec) {
  return sec == null || sec <= 0 ? '即将完成' : formatDuration(sec, { approx: true })
}

// 时长格式化(不带"约"):用于"已用时 3 分 12 秒"这类确定值
function formatSpan(sec) {
  return formatDuration(sec)
}

// 预计总耗时 = 已用时 + 预计剩余(两者都来自后端 _to_detail):
// 此前底部写死"生成大约需要 2 分钟",与后端 TASK_PROFILES(300 秒)自相矛盾。
const totalEstText = computed(() => {
  const total = (detail.value?.elapsed_seconds || 0) + (detail.value?.remain_seconds || 0)
  return total > 0 ? `预计 ${formatRemain(total)}` : '生成需要几分钟'
})

// 失败码 → 可执行动作:用户看到的不该只是一句"失败了",而是下一步该做什么。
// 与 worker 的 _fail(..., error_type) 同源;未命中映射时回退到"重试"。
const FAIL_ACTIONS = {
  real_person_blocked: { text: '用数字人出镜', action: 'digital', tip: '换成平台数字人形象,或改用不含真人的素材图' },
  edit_failed: { text: '换素材重做', action: 'recreate', tip: '这段素材无法被编辑模型处理,换一段原片或去掉替换意图' },
  config_error: { text: '联系客服', action: 'support', tip: '平台能力未配置完整,需要管理员处理' },
  timeout: { text: '重试一次', action: 'retry', tip: '模型这次没返回结果,重试通常能过' },
}
const failAction = computed(() => {
  const code = String(detail.value?.usage?.fail_code || '')
  return FAIL_ACTIONS[code] || { text: '重试一次', action: 'retry', tip: '可以先重试,额度不会重复扣' }
})
function onFailAction() {
  const a = failAction.value.action
  if (a === 'digital') router.push('/digital')
  else if (a === 'recreate') router.push('/studio')
  else if (a === 'support') router.push('/support')
  else onResume()
}

// 返回首页等(后台继续生成)
function leaveGen() {
  stopPolling()
  window.$message?.success('已返回首页，生成完成后会通知你')
  router.push('/home')
}

// 下载扩展名按结果形态推导:图片/音频此前会被写成 .mp4,下载后打不开
const EXT_BY_KIND = { video: 'mp4', image: 'png', audio: 'mp3' }

async function onDownload() {
  if (!detail.value?.result_video) return
  downloading.value = true
  try {
    const mediaUrl = detail.value.result_video
    const link = document.createElement('a')
    link.href = mediaUrl
    link.download = `${workTitle.value || '作品'}_${Date.now()}.${EXT_BY_KIND[mediaKind.value] || 'mp4'}`
    link.target = '_blank'
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.$message?.success('已开始下载 · 无水印高清版')
  } catch (e) {
    window.$message?.error('下载失败，请重试')
  } finally {
    downloading.value = false
  }
}

async function onShare() {
  // 文案类任务复制的是**文案本身**(用户要拿去粘贴使用),其它类型复制成片链接
  const isText = mediaKind.value === 'text'
  const payload = isText
    ? (detail.value?.result_text || '')
    : (detail.value?.result_video || window.location.href)
  const tip = isText ? '文案已复制' : '链接已复制，去发给好友吧'
  try {
    await navigator.clipboard.writeText(payload)
    window.$message?.success(tip)
  } catch (e) {
    window.$message?.success(tip)
  }
}

async function onRegenerate() {
  try {
    const res = await api.task.regenerate.post({ id: Number(route.params.id) })
    if (res.code === 1) {
      window.$message?.success('已重新生成')
      detail.value = null
      fetchDetail()
      if (!timer.value) timer.value = setInterval(fetchDetail, 2000)
    }
  } catch (e) { /* 拦截器已提示 */ }
}

// 「换个效果」:小白不需要理解"创意档位",只需要在几个效果之间轮换看哪个顺眼。
// 每次点击换到下一档(适度改造 → 爆款改造 → 忠实复刻),只覆盖效果旋钮,素材口径不变。
const STYLE_CYCLE = ['creative', 'viral', 'faithful']
const STYLE_LABEL = { creative: '自然一点', viral: '更有爆款感', faithful: '更贴近原片' }
let styleCursor = 0
async function onRestyle() {
  const level = STYLE_CYCLE[styleCursor % STYLE_CYCLE.length]
  styleCursor += 1
  try {
    const res = await api.task.regenerate.post({
      id: Number(route.params.id),
      creative_level: level,
      hook_boost: 'strong',
    })
    if (res.code === 1) {
      window.$message?.success(`已换效果:${STYLE_LABEL[level]},正在重新生成`)
      detail.value = null
      fetchDetail()
      if (!timer.value) timer.value = setInterval(fetchDetail, 2000)
    }
  } catch (e) { /* 拦截器已提示 */ }
}

async function onResume() {
  try {
    const res = await api.task.resume.post({ id: Number(route.params.id) })
    if (res.code === 1) {
      window.$message?.success('已继续生成，将从上次中断处接着完成')
      detail.value = null
      fetchDetail()
      if (!timer.value) timer.value = setInterval(fetchDetail, 2000)
    }
  } catch (e) { /* 拦截器已提示 */ }
}

function openSeg() {
  segIndex.value = 0
  segText.value = ''
  showSeg.value = true
}

async function onRegenerateSegment() {
  if (segSubmitting.value) return
  segSubmitting.value = true
  try {
    const res = await api.task.regenerateSegment.post({
      id: Number(route.params.id),
      segment_index: Number(segIndex.value),
      new_text: segText.value,
    })
    if (res.code === 1) {
      window.$message?.success('已提交局部重跑，将改一句台词后拼回原片')
      showSeg.value = false
      detail.value = null
      fetchDetail()
      if (!timer.value) timer.value = setInterval(fetchDetail, 2000)
    } else {
      window.$message?.warning(res.message || '提交失败，请稍后重试')
    }
  } catch (e) { /* 拦截器已提示 */ } finally {
    segSubmitting.value = false
  }
}

onMounted(() => {
  fetchDetail()
  timer.value = setInterval(fetchDetail, 2000)
})
onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="gen-page">
    <!-- 查询被拒(鉴权过期/无权限等):明确提示,不再无限转圈 -->
    <template v-if="fatal">
      <div class="center">
        <svg width="96" height="96" viewBox="0 0 96 96">
          <circle cx="48" cy="48" r="44" fill="#FFF0EA"/>
          <path d="M48 26v24" stroke="#FF4D1C" stroke-width="6" stroke-linecap="round"/>
          <circle cx="48" cy="66" r="4" fill="#FF4D1C"/>
        </svg>
        <div class="gen-title">暂时无法显示进度</div>
        <p class="fail-msg">{{ fatal }}</p>
        <div class="linkbtn" @click="onRefresh">刷新重试</div>
        <div class="linkbtn" @click="leaveGen">返回首页</div>
      </div>
    </template>

    <!-- 生成中 -->
    <template v-else-if="!detail || detail.status === 'processing'">
      <div class="center">
        <svg class="spin" width="96" height="96" viewBox="0 0 96 96">
          <circle cx="48" cy="48" r="44" fill="none" stroke="#FFE3D9" stroke-width="6"/>
          <path d="M48 4C72.3 4 92 23.7 92 48" fill="none" stroke="#FF4D1C" stroke-width="6" stroke-linecap="round"/>
          <rect x="30" y="34" width="36" height="28" rx="8" fill="#FFF0EA"/>
          <path d="M43 42L54 48L43 54V42Z" fill="#FF4D1C"/>
        </svg>
        <div class="gen-title">{{ genTitle }}</div>
        <div class="prog-wrap">
          <div class="prog-row">
            <span class="stage-now">{{ detail?.stage || '排队等待' }}</span>
            <span class="pct">{{ detail?.progress || 0 }}%</span>
          </div>
          <div class="pbar"><i :style="{ width: (detail?.progress || 0) + '%' }"></i></div>
          <div class="stepsrow">
            <template v-for="(s, i) in stages" :key="s">
              <span :class="detail && stages.indexOf(detail.stage) >= i ? 'done' : 'todo'">{{ s }}</span>
              <span v-if="i < stages.length - 1" class="todo sep"> → </span>
            </template>
          </div>
          <div v-if="detail" class="remain muted">
            <span v-if="detail.elapsed_seconds">已用时 {{ formatSpan(detail.elapsed_seconds) }} · </span>预计剩余 {{ formatRemain(detail.remain_seconds) }}
          </div>
        </div>
      </div>
      <div class="bottom-tip">
        <p class="muted">{{ totalEstText }}，你可以先去做别的事</p>
        <p class="muted">生成完成后会在「我的作品」里找到</p>
        <div class="linkbtn" @click="leaveGen">返回首页等</div>
      </div>
    </template>

    <!-- 生成成功:结果预览 -->
    <template v-else-if="detail.status === 'success'">
      <div class="wrap rcols">
        <div class="rcol-video">
          <!-- 视频 / 数字人 -->
          <div v-if="mediaKind === 'video'" class="vframe" :class="{ fit: detail.result_video }">
            <video
              v-if="detail.result_video"
              :src="detail.result_video"
              :poster="detail.template_cover"
              controls
              playsinline
              class="vframe-video"
            ></video>
            <div v-else class="play">
              <svg width="24" height="24" viewBox="0 0 24 24"><path d="M9 6L18 12L9 18V6Z" fill="#fff"/></svg>
            </div>
            <div class="re" @click="onRegenerate">重新生成</div>
          </div>
          <!-- 图片 -->
          <div v-else-if="mediaKind === 'image'" class="vframe fit img-frame">
            <img v-if="detail.result_video" :src="detail.result_video" :alt="workTitle" class="vframe-img" />
            <div v-else class="play">
              <svg width="24" height="24" viewBox="0 0 24 24"><path d="M9 6L18 12L9 18V6Z" fill="#fff"/></svg>
            </div>
            <div class="re" @click="onRegenerate">重新生成</div>
          </div>
          <!-- 音频 -->
          <div v-else-if="mediaKind === 'audio'" class="aframe">
            <div class="aframe-title">{{ workTitle }}</div>
            <audio v-if="detail.result_video" :src="detail.result_video" controls class="aframe-audio"></audio>
            <div v-else class="muted">音频结果缺失</div>
            <div class="re" @click="onRegenerate">重新生成</div>
          </div>
          <!-- 文案 -->
          <div v-else class="tframe">
            <pre class="tframe-text">{{ detail.result_text || '（无文本结果）' }}</pre>
            <div class="re" @click="onRegenerate">重新生成</div>
          </div>
        </div>
        <div class="rcol-ops">
          <div class="ops">
            <div
              class="btn-primary"
              :class="{ disabled: downloading }"
              @click="mediaKind === 'text' ? onShare() : onDownload()"
            >
              {{ mediaKind === 'text' ? '复制文案' : (downloading ? '下载中...' : '下载') }}
            </div>
            <div class="muted" style="text-align:center">{{ mediaKind === 'text' ? '可直接粘贴使用' : '无水印高清版' }}</div>
            <div class="btn-outline" @click="router.push(mediaKind === 'video' ? '/templates' : '/creator')">再做一个</div>
            <div class="btn-outline" @click="onRestyle" v-if="mediaKind === 'video' && detail.result_video">换个效果</div>
            <div class="muted" v-if="mediaKind === 'video' && detail.result_video" style="text-align:center;font-size:12px">「换个效果」会轮换“自然 / 爆款 / 贴近原片”三种风格，素材不变</div>
            <div class="btn-outline" @click="openSeg" v-if="mediaKind === 'video' && detail.result_video">改一句台词重生成</div>
            <div class="share" @click="onShare">{{ mediaKind === 'text' ? '复制全文' : '分享给好友' }}</div>
          </div>
          <div class="info">
            <b>{{ workTitle }} · 我的成品</b>
            <span class="muted">{{ detail.create_time }} 生成</span>
            <span v-if="goalText" class="meta">你的目标：{{ goalText }}</span>
            <span v-if="styleSummary" class="meta">本次风格：{{ styleSummary }}</span>
            <span v-if="mediaKind === 'video'" class="meta">{{ detail.gen_duration }} 秒 · {{ detail.gen_resolution }} 竖版 {{ detail.gen_ratio }}，适合发抖音</span>
            <span class="muted">任务编号：{{ detail.task_no }}</span>
            <span v-if="detail.deidentify_note" class="deid-note">已自动人脸打码：{{ detail.deidentify_note }}</span>
            <!-- 参考图含真人时已被本地处理(丢弃改按文字描述/拟态化),后端给出完整话术,直接展示 -->
            <span v-if="detail.image_note" class="deid-note">{{ detail.image_note }}</span>
            <!-- 降级提示:视频编辑失败后会降级成图片生成,成片并未替换原视频元素。
                 后端已给出"结论 + 可执行动作"的完整话术,这里直接展示,避免重复前缀。 -->
            <span v-if="detail.degrade_note" class="deid-note degrade-note">{{ detail.degrade_note }}</span>
            <!-- 成片自检:成片画幅/时长与参考视频明显不符,基本等价于没复刻上原片。
                 用户看结论;具体探测值(画幅/时长)放 title,供排查时查看 -->
            <span
              v-if="detail.output_note"
              class="deid-note degrade-note"
              :title="detail.output_detail || ''"
            >{{ detail.output_note }}</span>
            <!-- 原片分镜表:复刻时把原片拆成了哪几个镜头、每镜多长、原片说了什么,
                 以及模型对该镜的复刻描述。默认收起,避免结果页被长列表淹没 -->
            <div v-if="shotList.length" class="shot-panel">
              <div class="shot-head" @click="showShots = !showShots">
                <span>
                  原片分镜（{{ shotList.length }} 个镜头）
                  <em v-if="shotQcAvg !== null" class="shot-avg">复刻比对平均 {{ shotQcAvg }} 分</em>
                </span>
                <span class="muted">{{ showShots ? '收起' : '展开查看' }}</span>
              </div>
              <ul v-if="showShots" class="shot-list">
                <li v-for="shot in shotList" :key="shot.index">
                  <span class="shot-title">第 {{ shot.index + 1 }} 镜 · {{ shot.duration }} 秒</span>
                  <span v-if="shot.narration" class="shot-line">原片台词：{{ shot.narration }}</span>
                  <span v-if="shot.prompt" class="shot-line">复刻描述：{{ shot.prompt }}</span>
                  <!-- 质检只给结论:分数偏低时把"差在哪"一并说清,是否需要重新生成由用户决定 -->
                  <span
                    v-if="shot.score !== null"
                    class="shot-line"
                    :class="{ 'shot-issue': shot.low }"
                  >复刻比对：{{ shot.score }} 分{{ shot.issue ? ' · ' + shot.issue : '' }}</span>
                  <!-- 分镜镜头编辑:覆盖该镜提示词,供后续局部重跑使用(仅多段复刻任务有分镜) -->
                  <button
                    v-if="detail.type === 'video'"
                    class="shot-edit-btn"
                    @click="openShotEdit(shot)"
                  >改提示词</button>
                  <div v-if="editingShot === shot.index" class="shot-edit">
                    <textarea v-model="shotEditPrompt" rows="3" placeholder="输入该镜头的复刻提示词"></textarea>
                    <div class="shot-edit-actions">
                      <button class="shot-edit-save" :disabled="shotSaving" @click="saveShotEdit">{{ shotSaving ? '保存中...' : '保存' }}</button>
                      <button class="shot-edit-cancel" @click="editingShot = null">取消</button>
                    </div>
                  </div>
                </li>
              </ul>
            </div>
            <!-- 生成决策 / 成本快照:透明展示本次实际选用的网关与预估模型时长。
                 自动重跑默认关闭,这里只做展示,不改变任何付费语义 -->
            <div v-if="decisionLog.length || costSnapshot" class="shot-panel">
              <div class="shot-head" @click="showDecision = !showDecision">
                <span>
                  生成决策（{{ decisionLog.length }} 次模型提交）
                  <em v-if="costSnapshot" class="shot-avg">预估模型时长 {{ costSnapshot.total_seconds }} 秒</em>
                </span>
                <span class="muted">{{ showDecision ? '收起' : '展开查看' }}</span>
              </div>
              <ul v-if="showDecision" class="shot-list">
                <li v-for="(d, i) in decisionLog" :key="i">
                  <span class="shot-title">{{ d.route }} · {{ d.model || '默认模型' }}</span>
                  <span class="shot-line">{{ d.resolution || '—' }} · {{ d.ratio || '—' }} · {{ d.duration }} 秒</span>
                  <span v-if="d.gateway_name" class="shot-line">实际网关：{{ d.gateway_name }}</span>
                </li>
              </ul>
              <div v-if="costSnapshot" class="shot-line" style="padding:6px 0 0">
                提交次数 {{ costSnapshot.actions }} 次
                <span v-if="costSnapshot.by_model && costSnapshot.by_model.length">
                  （{{ costSnapshot.by_model.map((m) => m.model + ' ' + m.seconds + 's').join('，') }}）
                </span>
              </div>
            </div>
            <!-- 本次实际注入的提示词资产(专家模式只读):用户操作的是"形态/创意档位"这类旋钮,
                 这里给出正文,便于"换了档位却感觉没变化"时自查模型到底收到了什么 -->
            <div v-if="injectedAssets.length" class="shot-panel">
              <div class="shot-head" @click="showAssets = !showAssets">
                <span>
                  本次注入的提示词（{{ injectedAssets.length }} 段）
                  <em class="shot-avg">只读,用于自查效果差异</em>
                </span>
                <span class="muted">{{ showAssets ? '收起' : '展开查看' }}</span>
              </div>
              <ul v-if="showAssets" class="shot-list">
                <li v-for="asset in injectedAssets" :key="asset.key">
                  <span class="shot-title">{{ asset.label }}</span>
                  <pre class="asset-body">{{ asset.body }}</pre>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 生成失败 -->
    <template v-else>
      <div class="center">
        <svg width="96" height="96" viewBox="0 0 96 96">
          <circle cx="48" cy="48" r="44" fill="#FFF0EA"/>
          <path d="M34 34L62 62M62 34L34 62" stroke="#FF4D1C" stroke-width="5" stroke-linecap="round"/>
        </svg>
        <div class="gen-title">生成中断了</div>
        <!-- 失败原因以 worker 回写的为准:不同失败的可执行结论不同(如"替换商品失败:输入视频含真人"),
             写死"网络波动"会让用户以为重试就行,反复白跑;技术载荷经 failMsg 兜底过滤不外泄 -->
        <p class="fail-msg">{{ failMsg }}</p>
        <!-- 按 worker 回写的失败码给出可执行的一步,而不是让用户从文案里猜 -->
        <div style="display:flex; gap:12px; margin-top:12px">
          <div class="btn-primary" style="width:200px" @click="onFailAction">{{ failAction.text }}</div>
        </div>
        <p class="muted" style="margin-top:6px">{{ failAction.tip }}</p>
        <div class="prog-wrap" style="max-width: 360px">
          <div class="prog-row">
            <span class="stage-now">中断时进度</span>
            <span class="pct">{{ detail?.progress || 0 }}%</span>
          </div>
          <div class="pbar"><i :style="{ width: (detail?.progress || 0) + '%' }"></i></div>
        </div>
        <div style="display:flex; gap:12px">
          <!-- 只有"外部任务已提交"才算有断点可续;否则按钮就叫"重试",避免用户以为是接着上次跑 -->
          <div class="btn-primary" style="width:160px" @click="onResume">{{ detail.resumable ? '继续生成' : '重试一次' }}</div>
          <div class="btn-outline" style="width:160px" @click="onRegenerate">重新生成</div>
          <div class="btn-outline" style="width:160px" @click="router.push('/templates')">返回模板库</div>
        </div>
        <p class="muted" style="margin-top:4px">
          {{ detail.resumable
            ? '继续生成将从上次中断处接着完成，不重复扣额度。'
            : '上次在提交阶段就失败了，重试不会重复扣额度；若重试仍报同样原因（如原片含真人），请更换素材后再重新生成。' }}
        </p>
      </div>
    </template>

    <!-- 局部重跑:改一句台词重生成 -->
    <div v-if="showSeg" class="seg-mask" @click.self="showSeg = false">
    	<div class="seg-modal">
    		<div class="seg-title">改一句台词重生成</div>
    		<p class="seg-tip muted">只重生成某一分段的口播并拼回原片，省额度也更快。分段下标从 0 开始。</p>
    		<div class="seg-field">
    			<label>目标分段</label>
    			<select v-if="segOptions.length" v-model="segIndex" class="seg-input">
    				<option v-for="o in segOptions" :key="o.index" :value="o.index">{{ o.label }}</option>
    			</select>
    			<input v-else type="number" min="0" v-model="segIndex" class="seg-input" />
    		</div>
    		<div class="seg-field">
    			<label>新口播文案</label>
    			<textarea v-model="segText" class="seg-input seg-text" rows="3" placeholder="留空则沿用原台词"></textarea>
    			<div v-if="segEditedPrompt" class="seg-edit-hint">
    				该段已编辑过分镜描述，局部重跑将以此为画面提示词生成：
    				<div class="muted seg-edit-text">{{ segEditedPrompt }}</div>
    			</div>
    		</div>
    		<div class="seg-actions">
    			<div class="btn-outline" @click="showSeg = false">取消</div>
    			<div class="btn-primary" :class="{ disabled: segSubmitting }" @click="onRegenerateSegment">{{ segSubmitting ? '提交中...' : '提交重跑' }}</div>
    		</div>
    	</div>
    </div>
    </div>
    </template>

<style scoped>
.gen-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); display: flex; flex-direction: column; }
.wrap { max-width: var(--page-max); margin: 0 auto; width: 100%; }
.muted { font-size: 12px; color: var(--weak); }

/* 生成中 */
.center {
  flex: 1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 20px; gap: 26px; text-align: center;
}
.spin { animation: spin 2.4s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.gen-title { font-size: 16px; font-weight: 700; }
.fail-msg { font-size: 13px; color: var(--weak); margin: 0; max-width: 320px; line-height: 1.6; }
.prog-wrap { width: 100%; max-width: 420px; display: flex; flex-direction: column; gap: 10px; }
.prog-row { display: flex; justify-content: space-between; font-size: 12px; }
.stage-now { color: var(--body-c); }
.pct { color: var(--brand); font-weight: 700; }
.pbar { height: 8px; border-radius: 4px; background: #F0F1F3; width: 100%; overflow: hidden; }
.pbar i { display: block; height: 100%; width: 0; border-radius: 4px; background: var(--brand); transition: width 0.3s linear; }
.stepsrow { font-size: 12px; }
.stepsrow .done { color: var(--brand); font-weight: 700; }
.stepsrow .todo { color: #C9CCD1; }
.remain { text-align: left; }
.bottom-tip {
  padding: 0 20px 28px;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
}
.bottom-tip p { margin: 0; text-align: center; }
.linkbtn { font-size: 14px; color: var(--brand); font-weight: 500; cursor: pointer; }

/* 结果页 */
.rcol-video { padding: 20px; }
.vframe {
  height: 300px; border-radius: var(--radius); position: relative;
  background: linear-gradient(90deg, #FA8C4D, #DB331F);
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}
/* 有视频时:容器尺寸跟随视频自身比例 —— 竖屏 9:16 若塞进固定高度的宽框,
   object-fit: contain 会在左右留下大片黑边(成片本身没有黑边,是播放器框的问题) */
.vframe.fit { height: auto; width: fit-content; max-width: 100%; margin: 0 auto; background: #000; }
.vframe-video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; background: #000; }
/* fit 态下让视频参与布局撑开容器,max-height 防止竖屏视频高过一屏 */
.vframe.fit .vframe-video {
  position: static; display: block; width: auto; height: auto;
  max-width: 100%; max-height: 62vh;
}
/* 图片结果:按原始比例展示,不裁剪、不套黑边播放器 */
.vframe-img { position: static; display: block; width: auto; height: auto; max-width: 100%; max-height: 62vh; margin: 0 auto; }
/* 音频结果:播放器居中,套视频框会显得空荡 */
.aframe {
  position: relative; background: #fff; border: 1px solid var(--line); border-radius: var(--radius);
  padding: 24px 20px; display: flex; flex-direction: column; align-items: center; gap: 14px;
}
.aframe-title { font-size: 15px; font-weight: 700; color: #1a1a1a; }
.aframe-audio { width: 100%; max-width: 420px; }
/* 文案结果:保留换行、可滚动 */
.tframe {
  position: relative; background: #fff; border: 1px solid var(--line); border-radius: var(--radius);
  padding: 20px; max-height: 62vh; overflow: auto;
}
.tframe-text {
  margin: 0; white-space: pre-wrap; word-break: break-word;
  font-size: 14px; line-height: 1.8; color: var(--body-c); font-family: inherit;
}
.play {
  width: 56px; height: 56px; border-radius: 50%;
  background: rgba(0, 0, 0, 0.32);
  display: flex; align-items: center; justify-content: center;
}
.re {
  position: absolute; top: 12px; right: 12px; z-index: 2;
  background: rgba(0, 0, 0, 0.42); color: #fff;
  font-size: 11px; padding: 6px 10px; border-radius: 14px; cursor: pointer;
}
.rcol-ops { padding: 0 20px 20px; }
.ops { display: flex; flex-direction: column; align-items: stretch; gap: 12px; }
.btn-primary {
  height: 48px; border-radius: 24px; background: var(--brand); color: #fff;
  font-size: 16px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.btn-primary.disabled { opacity: 0.6; pointer-events: none; }
.btn-outline {
  height: 48px; border-radius: 24px; background: #fff; color: var(--brand);
  font-size: 16px; font-weight: 500; border: 1.5px solid var(--brand);
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.share { font-size: 14px; color: var(--body-c); cursor: pointer; text-align: center; }
/* 局部重跑弹窗 */
.seg-mask { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; z-index: 50; }
.seg-modal { width: 360px; max-width: 90vw; background: #fff; border-radius: var(--radius); padding: 20px; box-sizing: border-box; }
.seg-title { font-size: 16px; font-weight: 700; }
.seg-tip { margin: 6px 0 14px; }
.seg-field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.seg-field label { font-size: 13px; color: var(--body-c); }
.seg-input { border: 1.5px solid #e6e8eb; border-radius: 10px; padding: 10px 12px; font-size: 14px; outline: none; font-family: inherit; box-sizing: border-box; width: 100%; }
.seg-text { resize: vertical; }
.seg-actions { display: flex; gap: 12px; }
.seg-actions .btn-primary, .seg-actions .btn-outline { flex: 1; }
.seg-edit-hint { margin-top: 10px; font-size: 12px; color: #18a058; background: rgba(24,160,88,.08); border-radius: 8px; padding: 8px 10px; line-height: 1.5; }
.seg-edit-text { margin-top: 4px; color: var(--weak); word-break: break-all; }
.info { padding: 16px 0 0; display: flex; flex-direction: column; gap: 6px; }
.info b { font-size: 15px; }
.info .meta { font-size: 12px; color: var(--body-c); }
.info .deid-note { font-size: 12px; color: var(--brand); background: var(--brand-bg); padding: 4px 8px; border-radius: 6px; align-self: flex-start; }
/* 降级提示用警示色:成片"看起来成功"却没做替换,不能和普通提示一样弱 */
.info .degrade-note { color: #d03050; background: #FFF0F0; }
/* 原片分镜表:复刻拆解的可视化产物,默认收起 */
.shot-panel { margin-top: 10px; border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 10px 12px; }
.shot-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; cursor: pointer; font-size: 13px; font-weight: 600; }
.shot-list { list-style: none; margin: 10px 0 0; padding: 0; display: flex; flex-direction: column; }
.shot-list li { display: flex; flex-direction: column; gap: 2px; padding: 8px 0 0; margin-top: 8px; border-top: 1px solid var(--line); }
.shot-list li:first-child { padding-top: 0; margin-top: 0; border-top: none; }
.shot-title { font-size: 12px; color: var(--ink); }
.shot-line { font-size: 12px; color: var(--body-c); line-height: 1.5; }
/* 注入资产的正文:保留换行与缩进(提示词是分段的散文,折叠空白会读不出结构) */
.asset-body { margin: 6px 0 0; padding: 8px 10px; background: var(--bg); border-radius: 6px; font-size: 12px; line-height: 1.6; color: var(--body-c); white-space: pre-wrap; word-break: break-word; max-height: 260px; overflow: auto; font-family: inherit; }
/* 均分与低分提示:均分用品牌色(正向信息),低分用警示色(与降级提示同一语义色) */
.shot-avg { margin-left: 8px; font-style: normal; font-weight: 400; font-size: 12px; color: var(--brand); }
.shot-issue { color: #d03050; }

@media (min-width: 768px) {
  .rcols { display: grid; grid-template-columns: 1.2fr 1fr; gap: 24px; align-items: start; padding: 4px 20px 0; }
  .rcol-video { padding: 20px 0; }
  .rcol-ops { padding: 20px 0; }
}
</style>
