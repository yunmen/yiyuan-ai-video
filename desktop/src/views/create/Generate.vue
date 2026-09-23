<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '@/api'

const router = useRouter()
const route = useRoute()

const detail = ref(null)
const timer = ref(null)
const downloading = ref(false)

// 局部重跑(改一句台词重生成):弹窗收集分段下标与新台词
const showSeg = ref(false)
const segIndex = ref(0)
const segText = ref('')
// 可用分段来自成片脚本时间轴,后端据此替换对应时间窗;无则回退手动输入下标
const segOptions = computed(() => {
  const segs = detail.value?.params?.script?.segments || []
  return segs.map((s, i) => ({
    index: i,
    label: `第${i + 1}段 · ${(s.text || '').slice(0, 12)}${(s.text || '').length > 12 ? '…' : ''}`,
  }))
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
    if (res.code !== 1) return
    detail.value = res.data
    if (res.data.status === 'processing') {
      if (!timer.value) timer.value = setInterval(fetchDetail, 2000)
    } else {
      stopPolling()
    }
  } catch (e) { /* 拦截器已提示 */ }
}

function stopPolling() {
  if (timer.value) { clearInterval(timer.value); timer.value = null }
}

function formatRemain(sec) {
  if (sec == null || sec <= 0) return '即将完成'
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return m > 0 ? `约 ${m} 分 ${s} 秒` : `约 ${s} 秒`
}

// 时长格式化(不带"约"):用于"已用时 3 分 12 秒"这类确定值
function formatSpan(sec) {
  const n = Math.max(0, Number(sec) || 0)
  const m = Math.floor(n / 60)
  const s = n % 60
  return m > 0 ? `${m} 分 ${s} 秒` : `${s} 秒`
}

// 预计总耗时 = 已用时 + 预计剩余(两者都来自后端 _to_detail):
// 此前底部写死"生成大约需要 2 分钟",与后端 TASK_PROFILES(300 秒)自相矛盾。
const totalEstText = computed(() => {
  const total = (detail.value?.elapsed_seconds || 0) + (detail.value?.remain_seconds || 0)
  return total > 0 ? `预计 ${formatRemain(total)}` : '生成需要几分钟'
})

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
    }
  } catch (e) { /* 拦截器已提示 */ }
}

onMounted(() => {
  fetchDetail()
  timer.value = setInterval(fetchDetail, 2000)
})
onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="gen-page">
    <!-- 生成中 -->
    <template v-if="!detail || detail.status === 'processing'">
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
            <div class="btn-outline" @click="openSeg" v-if="mediaKind === 'video' && detail.result_video">改一句台词重生成</div>
            <div class="share" @click="onShare">{{ mediaKind === 'text' ? '复制全文' : '分享给好友' }}</div>
          </div>
          <div class="info">
            <b>{{ workTitle }} · 我的成品</b>
            <span class="muted">{{ detail.create_time }} 生成</span>
            <span v-if="mediaKind === 'video'" class="meta">{{ detail.gen_duration }} 秒 · {{ detail.gen_resolution }} 竖版 {{ detail.gen_ratio }}，适合发抖音</span>
            <span class="muted">任务编号：{{ detail.task_no }}</span>
            <span v-if="detail.deidentify_note" class="deid-note">已自动人脸打码：{{ detail.deidentify_note }}</span>
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
    		</div>
    		<div class="seg-actions">
    			<div class="btn-outline" @click="showSeg = false">取消</div>
    			<div class="btn-primary" @click="onRegenerateSegment">提交重跑</div>
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
.info { padding: 16px 0 0; display: flex; flex-direction: column; gap: 6px; }
.info b { font-size: 15px; }
.info .meta { font-size: 12px; color: var(--body-c); }
.info .deid-note { font-size: 12px; color: var(--brand); background: var(--brand-bg); padding: 4px 8px; border-radius: 6px; align-self: flex-start; }
/* 降级提示用警示色:成片"看起来成功"却没做替换,不能和普通提示一样弱 */
.info .degrade-note { color: #d03050; background: #FFF0F0; }

@media (min-width: 768px) {
  .rcols { display: grid; grid-template-columns: 1.2fr 1fr; gap: 24px; align-items: start; padding: 4px 20px 0; }
  .rcol-video { padding: 20px 0; }
  .rcol-ops { padding: 20px 0; }
}
</style>
