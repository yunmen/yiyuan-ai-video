<script setup>
// 带货视频复刻页:对标视频 + 产品图 → 拆解分镜(可视化可编辑) → 生成复刻视频。
// 与 douyin-video-replication 的「复刻链路」一致:先「看懂原片」(拆解),再替换出片。
// 拆解与生成分别复用既有后端契约:/v1/task/deconstruct(只分析、不扣额度)与 /v1/task/create。
import { ref, reactive, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { uploadFile } from '@/api/model/common'
import { useUserStore } from '@/store/modules/user'
import { useTaskEstimate } from '@/composables/useTaskEstimate'
import { useTaskCreate } from '@/composables/useTaskCreate'
import QRCode from 'qrcode'

const router = useRouter()
const userStore = useUserStore()
const { estText, refresh: estRefresh } = useTaskEstimate()
const { createAndNavigate } = useTaskCreate()

// 对标视频最小时长(秒):过短的视频无法稳定拆解镜头/编辑成片,提前拦截避免浪费额度。
// 与 worker 视频编辑下限保持一致;如需调整请同步 worker 侧约束。
const MIN_REF_VIDEO_SECONDS = 5

// 替换意图选项:由后端 /gen-config 的 replicate_intents **单一来源下发**,
// 前端不再各存一份数组 —— 新增/改名意图只改后端,避免"前端能选、后端校验不过"的漂移。
// 每个意图附带一句人话说明,避免用户看不懂“换产品/换人物/换场景”到底改什么。
const intents = ref([])
// 默认【不预选任何意图】:意图必须由用户显式勾选,否则会随上传图角色(image_roles)自动推断。
// 此前默认 ['product'] 且与 toggleIntent 的“只增不减”叠加,导致用户点“换人物”后 intent 实际是
// ['product','person'],产品替换始终生效 —— 表现出来就是“不管选啥都生成产品广告”。
const intent = ref([])
// 已选意图的人话说明:未选则提示会完整仿照原片,选中则列出各自作用
const intentHint = computed(() => {
  const picked = intents.value.filter((i) => intent.value.includes(i.key))
  if (!picked.length) return '未手动选择替换意图:将按你上传素材标注的类型(产品/人物/场景)自动替换对应元素'
  return '已选「' + picked.map((i) => i.label).join('、') + '」——' + picked.map((i) => i.desc).join(';')
})

// 复刻目标形态:由后端 /gen-config 的 replicate_formats **单一来源下发**,
// 前端不再另存一份白名单副本 —— 新增形态只改后端,本页自动跟着变,消除两份漂移。
// 决定成片的**内容结构**:不选则沿用原片结构,选了则按该形态重塑(短剧/口播/街采等)。
// 后端未升级时列表为空 → 形态选择区自动隐藏,链路与升级前完全一致。
const formats = ref([])
// 单选;默认【不选中】—— 未指定形态时链路与现状完全一致(沿用原片结构),预选会让用户误以为必填
const replicateFormat = ref('')
// 已选形态的人话说明:未选则提示沿用原片结构
const formatHint = computed(() => {
  const picked = formats.value.find((f) => f.key === replicateFormat.value)
  return picked
    ? `已选「${picked.label}」——${picked.desc}`
    : '未指定形态:将完整沿用原片的结构与节奏'
})
// 形态单选:再点一次即取消
function toggleFormat(key) {
  replicateFormat.value = replicateFormat.value === key ? '' : key
}

// —— 主角表现(仅“换人物”时生效) ——
// 由后端 /gen-config 的 lead_acts **单一来源下发**:决定新主角以什么方式表演。
// 为什么要有它:只做“换脸式替换”时,成片容易退化成原片的平淡翻拍;
// 用户真正要的是“主角换成我的人,并且他有反应(跳舞/推广)”。
// 后端未升级时列表为空 → 选择区自动隐藏,链路与升级前完全一致。
const leadActs = ref([])
// 单选;默认【不选中】= 跟随原片(行为与改造前一致)
const leadAct = ref('')
// 已选主角表现的人话说明:未选则说明会完整复演原片动作
const leadActHint = computed(() => {
  const picked = leadActs.value.find((a) => a.key === leadAct.value)
  return picked
    ? `已选「${picked.label}」——${picked.desc}`
    : '未指定:新主角将完整复演原片人物的动作与反应(原片的情节与镜头都会保留)'
})
// 主角表现单选:再点一次即取消(回到“跟随原片”)
function toggleLeadAct(key) {
  leadAct.value = leadAct.value === key ? '' : key
}

// —— 创意档位(决定在原片骨架上“改写多少”) ——
// 由后端 /gen-config 的 replicate_creative_levels **单一来源下发**:前端不再各存一份,
// 新增档位只改后端。后端未升级时列表为空 → 选择区自动隐藏,链路与升级前完全一致。
// 注意:方法论散文(改造透镜等)始终留在后端,前端只拿 label/desc ——
// 用户调的是“改多少”这个业务旋钮,不是直接编辑提示词。
const creativeLevels = ref([])
// 单选;默认【不选中】= 不指定,沿用改造前的全量方法论注入
const creativeLevel = ref('')
const creativeHint = computed(() => {
  const picked = creativeLevels.value.find((c) => c.key === creativeLevel.value)
  return picked
    ? `已选「${picked.label}」——${picked.desc}`
    : '未指定:保留原片的镜头结构与节奏,只替换你指定的元素'
})
function toggleCreative(key) {
  creativeLevel.value = creativeLevel.value === key ? '' : key
}

// —— 开头钩子强化(只改前 3 秒) ——
// 单独成档的原因:前 3 秒决定留存,但部分用户的目标就是“完整照搬原片”,不能默认动开头。
const hookBoosts = ref([])
const hookBoost = ref('')
const hookHint = computed(() => {
  const picked = hookBoosts.value.find((h) => h.key === hookBoost.value)
  return picked
    ? `已选「${picked.label}」——${picked.desc}`
    : '未指定:开头与其余镜头保持一致'
})
function toggleHookBoost(key) {
  hookBoost.value = hookBoost.value === key ? '' : key
}

// —— 专家模式 ——
// showExpert:折叠区开关,默认关闭(普通用户不需要看到提示词资产)
const showExpert = ref(false)
// 用户为本次任务追加的创作要求(≤500 字,后端 Schema 收口)。
// 位置即优先级:它排在档位资产之后,是“用户本人的最后定性要求”。
// 实际注入了什么在结果页(/generate/:id)只读展示 —— 那里才有任务的真实 params。
const assetOverride = ref('')
const ASSET_OVERRIDE_MAX = 500

// —— 上传 ——
const refVideo = ref('')          // 对标视频地址
const refVideoName = ref('')
const refVideoDuration = ref(0)   // 对标视频真实时长(秒),用于最小时长校验与提示
const productImages = ref([])     // 替换素材图(可多张,作为替换素材)
// 每张上传图的角色标注:URL → product/person/scene。随建单下发 image_roles,
// 后端据此给视觉模型“这张是人物图/产品图/场景图”的强提示,避免把人物/场景误判成产品
// (实测:无角色提示时庭院里的狗照会被判成场景、人物图可能被错叫商品,导致换人/换场景失效)。
const imageRoles = reactive({})

// —— 拆解分镜 ——
const deconstructId = ref(null)
// deconstructing:仅表示“建单请求”进行中(很快结束);
// deconstructPending:表示拆解任务已提交、正在后台执行(轮询中)。
// 二者必须分开:此前建单返回即把 deconstructing 复位,而轮询期间页面无任何加载态,
// 用户会以为点击无效/任务没在跑。轮询期间要持续展示加载卡片与已耗时。
const deconstructing = ref(false)
const deconstructPending = ref(false)
const deconstructElapsed = ref(0) // 拆解已进行秒数,给用户“任务确实在跑”的直观反馈
const loadingCardRef = ref(null)  // “步骤 2”加载卡片 DOM,提交拆解后滚动到可视区
const deconstructError = ref('')  // 拆解空结果/失败的持久提示:此前只弹 2 秒 toast,卡片直接消失,用户以为没反应
// deconstructNote:「不是失败但需要用户知道」的提示(如部分镜头没逆推出描述)。
// 与 deconstructError 分开:失败要阻断并引导重试,提示只说明可继续但要人工补。
const deconstructNote = ref('')
const shots = ref([])             // [{index,start,end,duration,narration,description}]
let pollTimer = null
let elapsedTimer = null

// worker 空分镜 reason → 用户能看懂的提示(拆解是“只分析不失败”的增强能力,空结果也带原因回写)
const EMPTY_REASON_TIPS = {
  missing_reference: '缺少对标视频地址,请重新上传视频后再试',
  ffmpeg_unavailable: '服务器缺少 ffmpeg,暂时无法分析视频,请联系管理员',
  download_failed: '对标视频下载失败,请确认视频可访问后重试',
  unknown_duration: '无法读取视频时长,请换一个标准编码的视频重试',
  no_shots: '未检测到镜头边界,可换一段剪辑更清晰的视频重试',
  no_targets: '未找到可分析的目标镜头,请重试',
  frame_extract_failed: '视频抽帧失败,请换一个编码更通用的视频(H.264)重试',
  exception: '拆解过程出现异常,请重试;若持续失败请联系管理员',
}

// 对标视频元素引用:镜头卡片上点时间码即可跳转到该镜头起点,便于逐镜核对原片画面。
// 用原生 video seek 而不是"抽帧缩略图":worker 的抽帧是本地临时文件(不上传 OSS),
// 前端自取会引入跨域与额外流量;直接把用户已上传的原片当预览器零成本且更直观。
const refVideoEl = ref(null)

function seekToShot(shot) {
  const el = refVideoEl.value
  const start = Number(shot?.start)
  if (!el || !Number.isFinite(start)) return
  try {
    el.currentTime = Math.max(0, start)
    el.play?.()
  } catch (e) {
    // 元数据尚未加载完成时忽略:用户可手动拖动进度条,不因此报错打断编辑
  }
}

// 调整镜头时长(秒):只改结束时间,起点不动 —— 起点一动会与相邻镜头重叠或留空。
// 这里编辑的是本地分镜表,最终随「生成复刻视频」一并下发;已落库的任务可在结果页继续微调。
function setShotDuration(shot, seconds) {
  const dur = Number(seconds)
  if (!Number.isFinite(dur) || dur <= 0) return
  shot.duration = Math.round(dur * 10) / 10
  shot.end = Math.round((Number(shot.start) + shot.duration) * 10) / 10
}

// —— 生成 ——
// 复刻链路不依赖平台模板:成片直接以用户上传的对标视频为蓝本编辑(后端 template_id 已放开为可选)。
const submitting = ref(false)
// 定价(来自后端业务配置,可在管理端修改);无额度用户走单次支付时使用
const price = ref('9.90')
// 收银台状态:无额度用户生成时创建支付订单,支付成功后由后端自动建单
const payVisible = ref(false)
const payOrder = ref(null)        // { order_no, amount, gateway, code_url, mock }
const qrDataUrl = ref('')
const paying = ref(false)
let payTimer = null
// 额度优先:登录且剩余额度>0 时直接扣额度生成,额度为 0 才走单次支付
const hasCredit = computed(() => userStore.isLoggedIn && (userStore.creditTotal ?? 0) > 0)

// 拆解可点击条件:有视频,且当前没有建单请求、也没有拆解任务在后台执行
const canDeconstruct = computed(
  () => !!refVideo.value && !deconstructing.value && !deconstructPending.value,
)
// 复刻不再让用户选择模板(成片直接以对标视频为蓝本编辑,时长跟随原片);
// 仅需拆解结果与替换素材齐全即可生成。
const canGenerate = computed(
  () => !!shots.value.length && productImages.value.length > 0 && !submitting.value,
)

const device = () => (window.innerWidth <= 768 ? 'mobile' : 'desktop')

// 探测远程视频时长:用临时 video 元素加载元数据,返回秒数;加载失败/超时返回 null。
// 仅用于前端最小时长拦截,不影响真实上传与生成。
function probeVideoDuration(url) {
  return new Promise((resolve) => {
    const v = document.createElement('video')
    v.preload = 'metadata'
    v.muted = true
    v.onloadedmetadata = () => resolve(Number.isFinite(v.duration) ? v.duration : null)
    v.onerror = () => resolve(null)
    v.src = url
    // 8s 内拿不到元数据视为探测失败,不阻塞上传(交由后端处理)
    setTimeout(() => resolve(null), 8000)
  })
}

// 上传对标视频:上传成功后清空上一轮拆解结果,避免新旧素材混用;
// 并校验最小时长,过短则拒绝接受,引导用户换更完整的视频。
async function uploadRefVideo({ file, onFinish, onError, onProgress }) {
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    const dur = await probeVideoDuration(url)
    if (dur && dur < MIN_REF_VIDEO_SECONDS) {
      window.$message?.error(`对标视频时长过短(需≥${MIN_REF_VIDEO_SECONDS}秒),请上传更完整的视频`)
      onError()
      return
    }
    refVideo.value = url
    refVideoName.value = file.file.name || '对标视频'
    refVideoDuration.value = dur || 0
    shots.value = []
    deconstructId.value = null
    deconstructError.value = ''
    deconstructNote.value = ''
    // 换视频时终止上一轮拆解轮询,避免旧任务状态污染新素材的展示
    stopPolling()
    onFinish()
    window.$message?.success('对标视频已上传,可开始拆解分镜')
  } catch (e) {
    onError()
  }
}

// 上传产品图(最多 9 张,作为替换素材)
async function uploadProduct({ file, onFinish, onError, onProgress }) {
  if (productImages.value.length >= 9) {
    window.$message?.warning('产品图最多 9 张')
    onError(); return
  }
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    productImages.value = [...productImages.value, url]
    if (!(url in imageRoles)) imageRoles[url] = 'product'
    onFinish()
  } catch (e) {
    onError()
  }
}
function removeProduct(url) {
  productImages.value = productImages.value.filter((u) => u !== url)
  delete imageRoles[url]
}

function toggleIntent(key) {
  intent.value = intent.value.includes(key)
    ? intent.value.filter((k) => k !== key)
    : [...intent.value, key]
}

// 未登录先引导:拆解/生成都要归属到用户
function requireLogin() {
  if (userStore.isLoggedIn) return true
  window.$message?.warning('请先登录后再复刻')
  userStore.openLogin()
  return false
}

// 拆解分镜:建单(type=deconstruct)后轮询 detail,直到 worker 回写 result_text(分镜 JSON)
async function startDeconstruct() {
  if (!canDeconstruct.value) return
  if (!requireLogin()) return
  deconstructing.value = true
  shots.value = []
  deconstructError.value = ''
  deconstructNote.value = ''
  try {
    const res = await api.task.deconstruct.post({
      reference_video: refVideo.value,
      intent: intent.value,
      // 与生成建单传同一个形态:保证"理解原片"与"重塑出片"一致
      format: replicateFormat.value,
      // 创意档位/钩子同样必须与生成侧一致:拆解按"忠实复刻"理解原片、却按"爆款改造"出片时,
      // 用户看到的分镜描述就不再是成片的依据
      creative_level: creativeLevel.value || undefined,
      hook_boost: hookBoost.value || undefined,
      device: device(),
    })
    if (res.code === 1 && res.data?.id) {
      deconstructId.value = res.data.id
      // 建单成功 → 进入“任务执行中”状态:轮询期间页面持续展示加载卡片
      deconstructPending.value = true
      window.$message?.success('已提交拆解,正在解析对标视频…')
      startPolling()
      // 把“步骤 2”加载卡片滚动到可视区,确保用户第一时间看到任务正在执行
      await nextTick()
      loadingCardRef.value?.$el?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
        ?? loadingCardRef.value?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
    } else {
      // 建单被业务拒绝(非 code=0 场景拦截器不提示):把原因持久写入失败卡片,
      // 否则加载卡片随 deconstructing 复位直接消失,用户只会看到“闪一下”
      deconstructError.value = res.message || res.msg || '拆解提交失败,请稍后重试'
      window.$message?.error(deconstructError.value)
    }
  } catch (e) {
    // 建单请求本身异常(网络/网关/超时/422/500):拦截器已弹通用通知,这里把原因持久写入失败卡片,
    // 附带 HTTP 状态与后端 message 便于定位根因,避免“点了按钮 → 请求失败 → 卡片直接消失”
    const status = e?.status || e?.response?.status
    const srvMsg = e?.data?.message || e?.data?.msg || e?.message
    deconstructError.value =
      '提交拆解请求失败' + (status ? `(HTTP ${status})` : '') + (srvMsg ? `:${srvMsg}` : '') + ',请检查网络后重试'
    window.$message?.error(deconstructError.value)
  }
  finally { deconstructing.value = false }
}

// 开始轮询拆解任务状态,并同步启动已耗时计时,给用户任务在跑的直观感知
function startPolling() {
  stopPolling()
  deconstructElapsed.value = 0
  pollTimer = setInterval(fetchDeconstruct, 2000)
  elapsedTimer = setInterval(() => { deconstructElapsed.value += 1 }, 1000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null }
  deconstructPending.value = false
}

// 轮询拆解任务详情:成功则解析 result_text(分镜 JSON),失败则停止并提示
async function fetchDeconstruct() {
  if (!deconstructId.value) return
  try {
    const res = await api.task.detail.post({ id: Number(deconstructId.value) })
    if (res.code !== 1 || !res.data) {
      // 轮询被拒(未登录/鉴权过期/无权限/任务不存在):不再重试也不会恢复,
      // 停止轮询并持久提示,否则后台每 2s 打一次被拒请求且界面一直卡在"拆解中…"
      stopPolling()
      deconstructError.value = res.message || res.msg || '无法获取拆解进度,请刷新或重新登录后重试'
      return
    }
    const detail = res.data
    if (detail.status === 'success') {
      stopPolling()
      const sb = parseStoryboard(detail.result_text)
      // 优先取「已落库的分镜」:它是 backend 把本次拆解沉淀进 tb_episode/tb_shot 的权威副本;
      // 落库属增强能力(异常时不落),读不到才回退 result_text —— 二者都不可用时保持空分镜提示。
      const persisted = await loadPersistedShots(deconstructId.value)
      shots.value = persisted || sb.shots
      // 部分镜头未逆推出描述(逆推是逐镜头增强,允许部分成功):提示但不阻断,
      // 用户可以自行补描述后照样出片 —— 与"完全失败"的处理必须区分开。
      deconstructNote.value = String(detail.usage?.deconstruct_note || '')
      if (!shots.value.length) {
        // 空分镜(拆解“只分析不失败”:工具层异常/缺 ffmpeg 等都以 success+reason 回写):
        // 把原因持久展示在卡片里,而不是只弹一条 2 秒 toast 后整卡消失
        const reason = resolveDeconstructReason(detail, sb)
        deconstructError.value = EMPTY_REASON_TIPS[reason] || '未分析出有效镜头,可换一段视频重试'
        window.$message?.warning(deconstructError.value)
      } else {
        deconstructError.value = ''
        if (deconstructNote.value) window.$message?.warning(deconstructNote.value)
        else window.$message?.success(`拆解完成,共 ${shots.value.length} 个镜头,可编辑后生成`)
      }
      refreshEstimate()
    } else if (detail.status === 'failed') {
      stopPolling()
      // 失败同样持久展示,避免 toast 一闪而过用户毫无感知
      deconstructError.value = detail.fail_reason || '拆解失败,请稍后重试'
      window.$message?.error(deconstructError.value)
    }
  } catch (e) { /* 拦截器已提示 */ }
}

// 分镜字段规范化:worker 正常回写时字段齐全,但工具层部分降级(逆推缺失/时长探测回退)
// 时可能缺 duration 等。前端若拿到 undefined,编辑与拼接备注会输出 "NaN" 或空镜头 ——
// 统一在解析入口收口为可安全编辑的数字/字符串。
function normalizeShots(list) {
  return (Array.isArray(list) ? list : []).map((s, i) => {
    const start = Number(s?.start) || 0
    const end = Number(s?.end) || 0
    const duration = Number(s?.duration) || Math.max(0, end - start)
    const idx = Number(s?.index)
    return {
      index: Number.isFinite(idx) ? idx : i,
      start,
      end,
      duration,
      narration: String(s?.narration || ''),
      description: String(s?.description || ''),
    }
  })
}

// 解析拆解结果(worker 以 result_text 回写 JSON 字符串):分镜数组 + 空结果原因
function parseStoryboard(text) {
  if (!text) return { shots: [], reason: '' }
  try {
    const data = typeof text === 'string' ? JSON.parse(text) : text
    return {
      shots: normalizeShots(data?.shots),
      reason: String(data?.reason || ''),
    }
  } catch (e) {
    return { shots: [], reason: '' }
  }
}

// 取拆解失败原因:优先读 worker 结构化回写的 usage.deconstruct_reason,
// 再回退 result_text 里的 reason —— usage 字段不经 JSON 文本解析,不受模型输出格式影响,
// 也让后端能按字段统计失败率(此前原因只存在于一段文本里,无法统计)。
function resolveDeconstructReason(detail, sb) {
  const fromUsage = detail?.usage?.deconstruct_reason
  if (typeof fromUsage === 'string' && fromUsage.trim()) return fromUsage.trim()
  return sb.reason || ''
}

// 读取「已落库的分镜」:backend 在拆解回调时把 usage.shots 沉淀为 tb_episode/tb_shot,
// 它才是可编辑、可复跑、刷新不丢的权威副本;落库是增强能力(异常/资产缺失时不落),
// 因此读不到(或无镜头)时返回 null,由调用方回退 result_text 的 JSON —— 不能让落库失败导致分镜页空白。
async function loadPersistedShots(taskId) {
  if (!taskId) return null
  try {
    const res = await api.storyboard.list.post({ task_id: Number(taskId) })
    const list = res?.data?.shots
    if (res?.code !== 1 || !Array.isArray(list) || !list.length) return null
    return normalizeShots(list.map((s) => ({
      index: s.index,
      start: (Number(s.start_ms) || 0) / 1000,
      end: (Number(s.end_ms) || 0) / 1000,
      duration: (Number(s.duration_ms) || 0) / 1000,
      narration: s.narration,
      // 落库字段名是 prompt(逐镜头逆推描述),前端沿用 description 作为可编辑字段名
      description: s.prompt,
    })))
  } catch (e) {
    // 落库副本读取失败不影响主流程:回退 result_text 即可(接口异常拦截器已提示)
    return null
  }
}

// 预估花费:复刻复用既有 create 链路,但无需模板 —— 直接按"带参考视频"预估即可
// (后端 estimate 在 template_id 为空时已按系统默认规格估算)。
// 带上探测到的对标视频真实时长,让预估额度贴近实际成片长度,而不是写死的默认值。
async function refreshEstimate() {
  const dur = refVideoDuration.value ? Math.min(60, Math.round(refVideoDuration.value)) : undefined
  await estRefresh('video', { has_reference_video: true, duration: dur })
}

// 生成复刻视频:把对标视频与产品图一起作为素材提交(后端 split_materials 会分离参考视频走编辑链路),
// 分镜描述作为备注下发给 worker,让改写继承拆解结果。
// 不复用平台模板:template_id 不传,后端按"用户自传对标视频"的复刻链路处理,
// 成片时长与节奏跟随原片,画幅/清晰度回退系统默认。
async function generate() {
  if (!canGenerate.value) return
  if (!requireLogin()) return
  // 生成前刷新额度,确保「扣额度 / 支付」分支判断准确
  await refreshCredits()
  submitting.value = true
  try {
    const remark = shots.value
      .map((s) => `镜头${s.index + 1}(${s.start}-${s.end}s): ${s.description || s.narration || '参考原片'}`)
      .join('\n')
    const materials = [...productImages.value, refVideo.value]
    const dur = refVideoDuration.value ? Math.min(60, Math.round(refVideoDuration.value)) : undefined
    // 逐图角色 → image_roles 下发:后端据此给视觉模型强提示,确保人物/场景图不被误判成产品
    const image_roles = {}
    for (const u of productImages.value) {
      if (imageRoles[u]) image_roles[u] = imageRoles[u]
    }
    const payload = {
      materials,
      intent: intent.value,
      // 复刻目标形态(可选):后端按白名单校验后注入形态提示词,不指定则沿用原片结构
      format: replicateFormat.value || undefined,
      // 主角表现(可选,仅“换人物”时生效):跳舞/推广等创意增强;不传=跟随原片
      lead_act: (intent.value.includes('person') && leadAct.value) ? leadAct.value : undefined,
      // 创意档位/开头钩子(可选):决定在原片骨架上改多少、是否重写前 3 秒;
      // 与拆解时传的值同源,保证"看懂原片"与"重塑出片"用的是同一档
      creative_level: creativeLevel.value || undefined,
      hook_boost: hookBoost.value || undefined,
      // 专家模式(可选):本次任务追加的创作要求,拼在创作要求段末尾(位置即优先级)
      asset_override: assetOverride.value.trim() || undefined,
      image_roles: Object.keys(image_roles).length ? image_roles : undefined,
      remark: remark || undefined,
      duration: dur,
      device: device(),
    }
    // 有额度:直接扣额度创建生成任务并跳转(与额度生成链路一致)
    if (hasCredit.value) {
      await createAndNavigate(
        () => api.task.create.post(payload),
        { message: '已提交复刻生成,正在出片' },
      )
      refreshCredits()
      return
    }
    // 无额度:创建支付订单,支付成功后由后端自动创建生成任务
    const res = await api.payment.orderCreate.post(payload)
    if (res.code === 1 && res.data) {
      payOrder.value = res.data
      payVisible.value = true
      if (res.data.code_url && !res.data.mock) {
        qrDataUrl.value = await QRCode.toDataURL(res.data.code_url, { width: 220, margin: 1 })
      }
      startPayPolling(res.data.order_no)
    }
  } catch (e) { /* 拦截器已提示 */ }
  finally { submitting.value = false }
}

// 额度优先:登录用户拉取最新剩余额度,决定走「扣额度」还是「支付」
async function refreshCredits() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await api.account.credits.post()
    if (res.code === 1) userStore.setCreditTotal(res.data.total)
  } catch (e) { /* 静默,以下单时后端校验为准 */ }
}

// 加载视频生成单价(管理端可改)与复刻目标形态选项(后端单一来源下发)
async function loadPrice() {
  try {
    const res = await api.payment.genConfig.post()
    if (res.code === 1 && res.data?.['gen.video_price']) price.value = res.data['gen.video_price']
    // 形态与意图选项均取自后端(单一来源):取不到则保持空列表(选择区自动隐藏),
    // 不阻断复刻主流程 —— 后端未升级时页面退化为"不指定形态/不指定意图",与升级前一致。
    if (res.code === 1 && Array.isArray(res.data?.replicate_formats)) {
      formats.value = res.data.replicate_formats
    }
    if (res.code === 1 && Array.isArray(res.data?.replicate_intents)) {
      intents.value = res.data.replicate_intents
    }
    // 主角表现档位同样是后端单一来源;取不到则保持空列表(仅“换人物”时才展示)
    if (res.code === 1 && Array.isArray(res.data?.lead_acts)) {
      leadActs.value = res.data.lead_acts
    }
    // 创意档位与开头钩子强化:同样后端单一来源(方法论散文留在后端,前端只渲染 label/desc)
    if (res.code === 1 && Array.isArray(res.data?.replicate_creative_levels)) {
      creativeLevels.value = res.data.replicate_creative_levels
    }
    if (res.code === 1 && Array.isArray(res.data?.replicate_hook_boosts)) {
      hookBoosts.value = res.data.replicate_hook_boosts
    }
  } catch (e) { /* 用默认定价 */ }
}

// 轮询支付订单状态:交付成功(status=3 且带回 task_id)后跳生成页
function startPayPolling(orderNo) {
  stopPayPolling()
  payTimer = setInterval(async () => {
    try {
      const res = await api.payment.orderStatus.post({ order_no: orderNo })
      if (res.code === 1 && res.data) {
        if (res.data.status === 3 && res.data.task_id) {
          stopPayPolling()
          payVisible.value = false
          window.$message?.success('支付成功,开始生成')
          router.replace(`/generate/${res.data.task_id}`)
        } else if (res.data.status === 4) {
          stopPayPolling()
          payVisible.value = false
          window.$message?.warning('订单已超时取消,请重新下单')
        }
      }
    } catch (e) { /* 轮询失败静默重试 */ }
  }, 2000)
}
function stopPayPolling() {
  if (payTimer) { clearInterval(payTimer); payTimer = null }
}

// 开发环境模拟支付
async function mockPay() {
  if (!payOrder.value) return
  paying.value = true
  try {
    const res = await api.payment.mockConfirm.post({ order_no: payOrder.value.order_no })
    if (res.code !== 1) paying.value = false
  } catch (e) { paying.value = false }
}

function closePay() {
  stopPayPolling()
  payVisible.value = false
}

onMounted(() => {
  // 复刻无需加载平台模板列表;拉取额度与单价,决定走「扣额度」还是「支付」
  refreshCredits()
  loadPrice()
})
onBeforeUnmount(() => { stopPolling(); stopPayPolling() })
</script>

<template>
  <div class="replicate-page">
    <div class="wrap">
      <div class="hero">
        <h1>视频复刻</h1>
        <p>拿爆款视频当“对标”,把里面的产品/人物/场景换成你的,生成结构相似的新视频。共三步。</p>
        <!-- 三步流程引导:让用户一眼看懂先做什么后做什么 -->
        <div class="guide">
          <span class="g"><b>1</b> 上传素材</span>
          <span class="arrow">→</span>
          <span class="g"><b>2</b> 拆解分镜</span>
          <span class="arrow">→</span>
          <span class="g"><b>3</b> 生成复刻视频</span>
        </div>
      </div>

      <!-- 步骤 1:素材 -->
      <section class="card">
        <div class="step"><b>1</b> 上传素材</div>

        <div class="field">
          <div class="lbl">对标视频 <i class="req">*</i></div>
          <div class="row">
            <!-- 不设 :max="1":Naive UI 在文件数达到 max 后会禁用触发区,导致“重新上传”点击无效;
                 替换逻辑由 custom-request 内覆盖 refVideo 完成 -->
            <n-upload
              accept="video/*"
              :show-file-list="false"
              :custom-request="uploadRefVideo"
            >
              <n-button secondary>{{ refVideo ? '重新上传对标视频' : '上传对标视频' }}</n-button>
            </n-upload>
            <span v-if="refVideo" class="name">{{ refVideoName }}</span>
          </div>
          <!-- 已上传视频预览:上传成功即可播放,确认内容与画幅后再开始拆解 -->
          <video
            v-if="refVideo"
            ref="refVideoEl"
            class="video-preview"
            :src="refVideo"
            controls
            preload="metadata"
          />
          <div class="sub">请仅上传你拥有版权的素材;系统只做分析,不会保存或传播原片</div>
          <div class="note">
            对标视频含真人出镜时，系统会尝试本地人脸打码；打码不保留可识别身份，处理失败也可能无法出片。
          </div>
        </div>

        <div class="field">
          <div class="lbl">替换素材（图片，请标注类型） <i class="req">*</i>(将替换进成片,最多 9 张)</div>
          <div class="thumbs">
            <div v-for="(u, i) in productImages" :key="u" class="thumb">
              <img :src="u" alt="替换素材" />
              <span class="del" @click="removeProduct(u)">×</span>
              <div class="role-sel">
                <span :class="['r', { on: imageRoles[u] === 'product' }]" @click="imageRoles[u] = 'product'">产品</span>
                <span :class="['r', { on: imageRoles[u] === 'person' }]" @click="imageRoles[u] = 'person'">人物</span>
                <span :class="['r', { on: imageRoles[u] === 'scene' }]" @click="imageRoles[u] = 'scene'">场景</span>
              </div>
            </div>
            <n-upload
              v-if="productImages.length < 9"
              accept="image/*"
              :show-file-list="false"
              :custom-request="uploadProduct"
            >
              <div class="add">+ 添加</div>
            </n-upload>
          </div>
          <div class="sub">请为每张图标注类型(产品/人物/场景)，系统据此决定替换原片的哪个元素；不标注则按视觉识别推断。</div>
          <div class="note">
            当前视频供应商不接受真人照片作为成片素材。选择“换人物”并上传本人照片，照片可能被移除，最终只按文字描述生成非本人角色，无法实现本人替换。
            可改用插画/虚拟形象图、用文字描述角色，或选择换产品/换场景；如需真人口播，可使用
            <router-link to="/digital">平台数字人形象</router-link>（不是本人克隆）。
          </div>
        </div>

        <div v-if="intents.length" class="field">
          <div class="lbl">替换意图</div>
          <div class="chips">
            <span
              v-for="it in intents"
              :key="it.key"
              :title="it.desc"
              :class="['chip', { on: intent.includes(it.key) }]"
              @click="toggleIntent(it.key)"
            >{{ it.label }}</span>
          </div>
          <!-- 选中意图的动态人话说明,鼠标悬浮单个标签也会显示 -->
          <div class="intent-hint">{{ intentHint }}</div>
        </div>

        <!-- 主角表现(创意增强):仅“换人物”时出现 —— 决定新主角怎么演(跟随原片/跳舞/推广)。
             原片的情节、动作与镜头始终保留,这里只追加主角的表演方式。
             选项由后端下发(单一来源),后端未升级时列表为空则整块隐藏。 -->
        <div v-if="intent.includes('person') && leadActs.length" class="field">
          <div class="lbl">主角怎么演</div>
          <div class="chips">
            <span
              v-for="la in leadActs"
              :key="la.key"
              :title="la.desc"
              :class="['chip', { on: leadAct === la.key }]"
              @click="toggleLeadAct(la.key)"
            >{{ la.label }}</span>
          </div>
          <div class="intent-hint">{{ leadActHint }}</div>
        </div>

        <!-- 复刻目标形态:决定成片的内容结构;不指定则沿用原片结构。
             选项由后端下发(单一来源),后端未升级时列表为空则整块隐藏。 -->
        <div v-if="formats.length" class="field">
          <div class="lbl">复刻成什么形态</div>
          <div class="chips">
            <span
              v-for="fm in formats"
              :key="fm.key"
              :title="fm.desc"
              :class="['chip', { on: replicateFormat === fm.key }]"
              @click="toggleFormat(fm.key)"
            >{{ fm.label }}</span>
          </div>
          <div class="intent-hint">{{ formatHint }}</div>
        </div>

        <!-- 创意档位:决定在原片骨架上“改写多少”(忠实复刻/轻度改写/爆款改造)。
             方法论散文全部留在后端,这里只渲染后端下发的 label/desc —— 用户调的是业务旋钮,
             不是直接编辑提示词。后端未升级时列表为空则整块隐藏。 -->
        <div v-if="creativeLevels.length" class="field">
          <div class="lbl">改写幅度</div>
          <div class="chips">
            <span
              v-for="cl in creativeLevels"
              :key="cl.key"
              :title="cl.desc"
              :class="['chip', { on: creativeLevel === cl.key }]"
              @click="toggleCreative(cl.key)"
            >{{ cl.label }}</span>
          </div>
          <div class="intent-hint">{{ creativeHint }}</div>
        </div>

        <!-- 开头钩子强化:只重写前 3 秒,其余镜头按所选档位处理。
             单独成档是因为"完整照搬原片"的目标也很常见,不能默认动开头。 -->
        <div v-if="hookBoosts.length" class="field">
          <div class="lbl">开头钩子</div>
          <div class="chips">
            <span
              v-for="hb in hookBoosts"
              :key="hb.key"
              :title="hb.desc"
              :class="['chip', { on: hookBoost === hb.key }]"
              @click="toggleHookBoost(hb.key)"
            >{{ hb.label }}</span>
          </div>
          <div class="intent-hint">{{ hookHint }}</div>
        </div>

        <!-- 专家模式:为高级用户提供“追加一条本次任务的创作要求”的入口。
             不做成直接编辑提示词资产 —— 资产是全局共享的方法论,按任务改写会污染其它任务;
             这里给的是**叠加**在档位资产之后的补充要求(位置即优先级)。
             实际注入了什么,在结果页只读展示,便于“换了档位却没变化”时自查。 -->
        <div class="field">
          <div class="expert-head" @click="showExpert = !showExpert">
            <span class="lbl-inline">专家模式(可选)</span>
            <span class="caret">{{ showExpert ? '收起' : '展开' }}</span>
          </div>
          <div v-if="showExpert" class="expert-body">
            <div class="sub">追加一条只作用于本次任务的要求(例如“全程不要出现英文字幕”)。它会排在档位要求之后,优先级更高;留空则只按上面的档位执行。</div>
            <n-input
              v-model:value="assetOverride"
              type="textarea"
              :rows="3"
              :maxlength="ASSET_OVERRIDE_MAX"
              show-count
              placeholder="只作用于本次任务的要求(选填)"
            />
          </div>
        </div>

        <div class="actions">
          <n-button type="primary" :disabled="!canDeconstruct" :loading="deconstructing" @click="startDeconstruct">
            {{ deconstructPending ? '拆解中…' : (shots.length ? '重新拆解' : '开始拆解分镜') }}
          </n-button>
          <span class="btn-tip">上传对标视频后点击,AI 将分析原片并切分为镜头</span>
        </div>
      </section>

      <!-- 步骤 2:分镜(可编辑);建单请求中、拆解执行中、空结果/失败提示都持续展示,避免“转一下就消失” -->
      <section v-if="deconstructing || deconstructPending || shots.length || deconstructError" class="card">
        <div class="step"><b>2</b> 拆解分镜(可编辑描述后生成)</div>
        <div v-if="deconstructing || deconstructPending" ref="loadingCardRef" class="loading">
          <n-spin size="small" />
          <span>正在解析对标视频的镜头与文案…</span>
          <!-- 已耗时提示:拆解通常需要几十秒,让用户明确知道后台任务在跑 -->
          <span class="elapsed">已进行 {{ deconstructElapsed }} 秒,请勿关闭页面</span>
        </div>
        <!-- 空结果/失败:持久展示原因与重试引导,不再只靠一闪而过的 toast -->
        <div v-else-if="deconstructError" class="deconstruct-error">
          <span>{{ deconstructError }}</span>
          <n-button size="small" secondary type="primary" @click="startDeconstruct">重新拆解</n-button>
        </div>
        <div v-else class="shots">
          <!-- 部分镜头未逆推成功:黄条提示(可继续出片,但要人工补描述),与"完全失败"的红框区分开 -->
          <div v-if="deconstructNote" class="deconstruct-note">{{ deconstructNote }}</div>
          <!-- 若 AI 未识别出任何镜头描述,给出引导而不是空红框 -->
          <div v-if="!shots.some((s) => s.description || s.narration)" class="shot-tip">
            AI 未识别出镜头画面描述(多为未配置视觉模型或视频过短),可手动填写每个镜头的画面/运镜描述,生成时才会更贴近你的预期。
          </div>
          <div v-for="s in shots" :key="s.index" class="shot">
            <div class="shot-head">
              <span class="idx">镜头 {{ s.index + 1 }}</span>
              <!-- 时间码可点击:跳转到原片该镜头起点,逐镜核对时不必手动拖进度条 -->
              <span class="time time-link" title="点击跳转到原片该镜头起点" @click="seekToShot(s)">
                {{ s.start }}s - {{ s.end }}s
              </span>
              <!-- 时长微调:只改结束时间(起点不动),用于控制成片节奏 -->
              <span class="dur">
                时长
                <n-input-number
                  :value="s.duration"
                  size="tiny"
                  :min="0.5"
                  :max="30"
                  :step="0.5"
                  :show-button="false"
                  @update:value="(v) => setShotDuration(s, v)"
                />
                <span class="unit">秒</span>
              </span>
            </div>
            <div v-if="s.narration" class="narration">原片口播:{{ s.narration }}</div>
            <n-input
              v-model:value="s.description"
              type="textarea"
              :rows="2"
              :placeholder="s.description ? '画面/运镜描述(可修改,将作为复刻参考下发给模型)' : '此镜头没有逆推描述,建议补上画面与运镜;留空则按原片结构复刻'"
            />
          </div>
        </div>
      </section>

      <!-- 步骤 3:生成(复刻直接以对标视频为蓝本,无需选择模板) -->
      <section v-if="shots.length" class="card">
        <div class="step"><b>3</b> 生成复刻视频</div>
        <div class="sub">将直接以你的对标视频为蓝本进行编辑生成,无需选择模板;成片时长与节奏跟随原片,请确认已上传清晰度足够、时长≥{{ MIN_REF_VIDEO_SECONDS }}秒的视频。</div>
        <div class="actions">
          <div class="est">
            {{ estText }}
            <span v-if="!hasCredit" class="pay-tip">无额度 · 单次生成 ¥{{ price }}</span>
          </div>
          <n-button type="primary" :disabled="!canGenerate" :loading="submitting" @click="generate">
            {{ submitting ? '提交中...' : (hasCredit ? '生成复刻视频' : `去支付 ¥${price} 生成`) }}
          </n-button>
        </div>
      </section>

      <!-- 收银台(无额度用户单次支付) -->
      <n-modal :show="payVisible" :mask-closable="false" :closable="false">
        <div class="pay">
          <h3>微信支付</h3>
          <div class="pay-amount">¥{{ payOrder?.amount || price }}</div>
          <p class="sub" style="text-align:center">{{ payOrder?.mock ? '开发环境模拟支付' : '请使用微信扫码完成支付' }}</p>
          <img v-if="qrDataUrl" :src="qrDataUrl" class="pay-qr" alt="支付二维码" />
          <button v-if="payOrder?.mock" class="pay-mock-btn" :disabled="paying" @click="mockPay">
            {{ paying ? '支付中...' : '模拟支付(仅开发环境)' }}
          </button>
          <div class="pay-close" @click="closePay">取消支付</div>
        </div>
      </n-modal>
    </div>
  </div>
</template>

<style scoped>
.replicate-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); padding: 24px 16px 48px; }
.wrap { max-width: 720px; margin: 0 auto; }
.hero { text-align: center; margin-bottom: 20px; }
.hero h1 { font-size: 22px; font-weight: 700; margin: 0 0 8px; color: #1a1a1a; }
.hero p { font-size: 13px; color: var(--weak); margin: 0; }
/* 三步流程引导条:让用户一眼看懂操作顺序 */
.guide { display: flex; align-items: center; justify-content: center; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
.guide .g { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: var(--body-c); background: var(--bg); border: 1px solid var(--line); border-radius: 18px; padding: 5px 12px; }
.guide .g b { display: inline-flex; width: 18px; height: 18px; border-radius: 50%; background: var(--brand); color: #fff; align-items: center; justify-content: center; font-size: 12px; }
.guide .arrow { color: var(--weak); font-size: 14px; }
/* 意图动态说明、按钮引导、拆解空描述引导 */
.intent-hint { font-size: 12px; color: var(--weak); margin-top: 8px; line-height: 1.5; }
.btn-tip { font-size: 12px; color: var(--weak); }
.shot-tip { font-size: 12px; color: #b26a00; background: #fff8e6; border: 1px solid #ffe2a8; border-radius: 8px; padding: 8px 10px; line-height: 1.5; margin-bottom: 14px; }
/* 部分镜头未逆推成功:与 .shot-tip 同色系(可继续但要人工补),区别于失败的红色 .deconstruct-error */
.deconstruct-note { font-size: 12px; color: #b26a00; background: #fff8e6; border: 1px solid #ffe2a8; border-radius: 8px; padding: 8px 10px; line-height: 1.5; margin-bottom: 12px; }
.card { background: #fff; border-radius: var(--radius); padding: 20px; margin-bottom: 16px; }
.step { font-size: 15px; font-weight: 600; color: #1a1a1a; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.step b { display: inline-flex; width: 22px; height: 22px; border-radius: 50%; background: var(--brand); color: #fff; align-items: center; justify-content: center; font-size: 13px; }
.field { margin-bottom: 18px; }
.lbl { font-size: 14px; font-weight: 500; margin-bottom: 8px; color: #1a1a1a; }
.req { color: #d03050; font-style: normal; }
.sub { font-size: 12px; color: var(--weak); margin-top: 8px; }
.note { font-size: 12px; color: #b26a00; background: #fff8e6; border: 1px solid #ffe2a8; border-radius: 8px; padding: 8px 10px; margin-top: 8px; line-height: 1.5; }
.row { display: flex; align-items: center; gap: 12px; }
.name { font-size: 13px; color: var(--body-c); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* 对标视频预览:上传成功即可播放,确认内容与画幅后再拆解 */
.video-preview { width: 100%; max-height: 320px; display: block; margin-top: 10px; border-radius: 10px; border: 1px solid var(--line); background: #000; object-fit: contain; }
.thumbs { display: flex; flex-wrap: wrap; gap: 10px; }
.thumb { position: relative; width: 72px; height: 72px; border-radius: 8px; overflow: hidden; border: 1px solid var(--line); }
.thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.thumb .del { position: absolute; top: 2px; right: 4px; color: #fff; background: rgba(0,0,0,.5); border-radius: 50%; width: 16px; height: 16px; line-height: 16px; text-align: center; font-size: 12px; cursor: pointer; }
.thumb .role-sel { position: absolute; left: 0; right: 0; bottom: 0; display: flex; gap: 2px; padding: 2px; background: rgba(0, 0, 0, 0.55); }
.thumb .role-sel .r { flex: 1; text-align: center; font-size: 10px; line-height: 15px; color: #cbd5e1; cursor: pointer; border-radius: 3px; user-select: none; }
.thumb .role-sel .r:hover { color: #fff; }
.thumb .role-sel .r.on { background: #4f7cff; color: #fff; }
.add { width: 72px; height: 72px; border: 1.5px dashed #d6d9de; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: var(--weak); font-size: 13px; cursor: pointer; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip { padding: 7px 16px; border-radius: 18px; background: var(--bg); font-size: 13px; color: var(--body-c); cursor: pointer; border: 1.5px solid transparent; user-select: none; }
.chip.on { background: var(--brand-bg); color: var(--brand); border-color: var(--brand); font-weight: 600; }
.actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.est { font-size: 13px; color: var(--body-c); }
.loading { display: flex; align-items: center; gap: 10px; font-size: 14px; color: var(--body-c); padding: 12px 0; }
/* 拆解已耗时提示:弱化颜色,与主提示区分 */
.loading .elapsed { font-size: 12px; color: var(--weak); }
/* 拆解空结果/失败:持久可见的警示条 + 重试按钮,替代一闪而过的 toast */
.deconstruct-error { display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 13px; color: #b26a00; background: #fff8e6; border: 1px solid #ffe2a8; border-radius: 8px; padding: 10px 12px; line-height: 1.5; }
.shots { display: flex; flex-direction: column; gap: 14px; }
.shot { border: 1px solid var(--line); border-radius: 10px; padding: 12px; }
.shot-head { display: flex; align-items: center; gap: 10px; font-size: 13px; margin-bottom: 8px; }
.idx { font-weight: 600; color: #1a1a1a; }
.time { color: var(--weak); }
/* 时间码可点击:跳到原片该镜头起点做逐镜核对(下划线提示可交互) */
.time-link { cursor: pointer; text-decoration: underline dotted; }
.time-link:hover { color: var(--brand); }
/* 时长微调:靠右,只改结束时间(起点不动,避免与相邻镜头重叠或留空) */
.dur { display: inline-flex; align-items: center; gap: 4px; margin-left: auto; color: var(--weak); }
.dur .unit { font-size: 12px; }
/* 专家模式折叠头:整行可点击展开,默认收起 */
.expert-head { display: flex; align-items: center; justify-content: space-between; cursor: pointer; margin-bottom: 8px; }
.lbl-inline { font-size: 14px; font-weight: 500; color: #1a1a1a; }
.expert-head .caret { font-size: 12px; color: var(--brand); }
.expert-body { border: 1px dashed var(--line); border-radius: 8px; padding: 10px; }
.narration { font-size: 12px; color: var(--body-c); background: var(--bg); border-radius: 6px; padding: 6px 8px; margin-bottom: 8px; }
/* 无额度时的支付提示 */
.pay-tip { color: var(--brand); margin-left: 8px; }
/* 收银台 */
.pay { width: 311px; background: #fff; border-radius: 16px; padding: 24px; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.pay h3 { margin: 0; font-size: 18px; }
.pay-amount { font-size: 28px; font-weight: 700; color: var(--brand); }
.pay-qr { width: 220px; height: 220px; border-radius: 8px; border: 1px solid var(--line); }
.pay-mock-btn { width: 100%; height: 46px; border-radius: 23px; border: none; background: var(--brand); color: #fff; font-size: 15px; font-weight: 700; cursor: pointer; font-family: inherit; }
.pay-mock-btn:disabled { background: #DCDFE4; cursor: not-allowed; }
.pay-close { font-size: 13px; color: var(--weak); cursor: pointer; margin-top: 4px; }
</style>
