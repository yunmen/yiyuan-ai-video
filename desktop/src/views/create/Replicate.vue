<script setup>
// 带货视频复刻页:对标视频 + 产品图 → 拆解分镜(可视化可编辑) → 生成复刻视频。
// 与 douyin-video-replication 的「复刻链路」一致:先「看懂原片」(拆解),再替换出片。
// 拆解与生成分别复用既有后端契约:/v1/task/deconstruct(只分析、不扣额度)与 /v1/task/create。
import { ref, reactive, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '@/api'
import { useSkill } from '@/composables/useSkill'
import { uploadFile } from '@/api/model/common'
import { useUserStore } from '@/store/modules/user'
import { useTaskEstimate } from '@/composables/useTaskEstimate'
import { useTaskCreate } from '@/composables/useTaskCreate'
import { useGenConfig } from '@/composables/useGenConfig'
import { takePendingRef } from '@/utils/pendingRef'
import QRCode from 'qrcode'
import AdvancedCreationSettings from '@/components/create/AdvancedCreationSettings.vue'
import TemplatePicker from '@/components/create/TemplatePicker.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
// 被「创作工作台」内嵌时(route 以 /studio 开头),隐藏本页独立的大标题与三步引导,
// 这些已由工作台的 Hero 与模式卡片承担,避免三层重复(顶栏/工作台/本页标题)。
const embedded = computed(() => route.path.startsWith('/studio'))
const { estText, refresh: estRefresh } = useTaskEstimate()
const { createAndNavigate, submitHint } = useTaskCreate()

// 对标视频最小时长(秒):过短的视频无法稳定拆解镜头/编辑成片,提前拦截避免浪费额度。
// 与 worker 视频编辑下限保持一致;如需调整请同步 worker 侧约束。
const MIN_REF_VIDEO_SECONDS = 5

// 高级创作设置(复刻模式 / 替换意图 / 形态 / 主角表现 / 创意档位 / 开头钩子 / 专家模式)
// 统一收口到 AdvancedCreationSettings 组件:选项来自后端 /gen-config(单一来源),
// 本页只持有这一份响应式对象,组件的“顶层复刻模式 → 各旋钮联动”归位逻辑随之复用,不再在本页重复实现。
const adv = reactive({
  mode: 'replace',            // replace=换元素复刻(参考图替换人/货/景) / full=原样照搬 / viral=爆款改写
  intent: [],                 // 替换意图(产品/人物/场景)
  format: '',                 // 复刻目标形态(可选)
  leadAct: '',                // 主角表现(仅换人物生效)
  // 创意档位:默认即「完全复刻」,必须从忠实档起跑 —— 此前初始为空、随后被 /gen-config
  // 推荐默认值回填成改写档,导致“没点过任何选项的默认完全复刻”实际按改写档出片;
  // 只有手动点一次「完全复刻」芯片才归位,与用户预期(不选=完全复刻)相悖
  creativeLevel: 'faithful',
  hookBoost: '',              // 开头钩子:同上
  assetOverride: '',          // 专家模式:本次任务追加的创作要求
  showExpert: false,          // 专家模式折叠开关
})

// 一句话目标(小白主入口):用大白话描述自由诉求(风格/受众/语气等结构化控件表达不了的内容),选填。
// 与上方结构化控件(替换意图 / 复刻形态 / 开头钩子)职责分离:结构化控件负责「离散选择」,
// 这里只负责「感受类、无法枚举」的自由描述;两者都下发,worker 在结构化旋钮之外多一份人话意图。
// 示例芯片只把这类自由描述填进文本框,不复述结构化控件里的选项,避免同页出现两套表达。
const goal = ref('')
const goalExamples = ['更电影感', '适合发小红书', '更有反转', '画面更精致']
// 进阶装饰与批量能力默认收起:小白首屏只看到「上传素材 → 生成」主链路,
// 展开后仍可设置文字标签 / 动效 / 模板化,不影响既有字段与接口下发。
const showAdvanced = ref(false)
// 代码渲染层·信息卡(可选,对齐 Hypit lower-thirds):显式提供才叠加,不臆造商品信息
const cardTitle = ref('')
const cardBody = ref('')
// 代码渲染层·角标(可选,对齐 Hypit badge):成片角落胶囊标签(品牌/卖点/水印)
const badgeText = ref('')
// 代码渲染层·动效信息层(可选,对齐 Hypit 动效组件):仅显式提供才叠加,绝不臆造内容
const rankTitle = ref('')
const rankText = ref('')        // 每行一条:名称 数值(或 名称|数值)
const rankStart = ref(0)
const rankStagger = ref(500)
const revealText = ref('')
const revealEmoji = ref('✨')
const revealAt = ref(1000)
const flashColor = ref('#FFD400')
const flashAt = ref(800)
const flashDur = ref(400)
const stickerText = ref('')
const stickerSide = ref('l')
const stickerAt = ref(2000)
// 自动 B-roll(可选,对齐 Hypit B-roll 素材镜头承接):显式开启才生效,失败回退原片
const autoBrollEnabled = ref(false)
const autoBrollSource = ref('goods')
const autoBrollStrategy = ref('even')
const autoBrollKeywords = ref('')
const autoBrollInterval = ref(8)
const autoBrollWindow = ref(3)
const autoBrollPos = ref('center')
// 自动生成素材来源(gen)时使用的文生图提示词;缺失则用通用电商特写
const autoBrollPrompt = ref('')
// 工程模板(参数模板化 / 一套结构百变体):保存创意配置快照,换素材/主播/排名/语言批量出变体
const templateTitle = ref('')
const templateList = ref([])
const selectedTemplateId = ref(null)
const tplSaving = ref(false)
const tplLoading = ref(false)
const batchMaterials = ref('')
const batchSaving = ref(false)
// 模板多语言变体「一键本地化」:开启后把画面可见文案翻译为所选语言,逐语言出变体
const localizeEnabled = ref(false)
const localizeLangs = ref([])
const localizing = ref(false)
const LANG_OPTIONS = [
  { label: '英语', value: 'en' },
  { label: '日语', value: 'ja' },
  { label: '韩语', value: 'ko' },
  { label: '西班牙语', value: 'es' },
  { label: '法语', value: 'fr' },
  { label: '德语', value: 'de' },
]
// 本地化文本字段顺序(与后端翻译返回顺序一致);口播由源视频生成,不在此翻译
const LOC_FIELDS = ['goal', 'asset_override', 'card_title', 'card_body', 'badge', 'reveal', 'sticker', 'rank_title']
const skLocal = useSkill()
const templateOptions = computed(() => (templateList.value || []).map((t) => ({ label: t.title, value: t.id })))
// worker 拆解回写的「推荐方案」:人话解释 + 建议取值,前端只展示解释、静默套用取值
const planReason = ref('')

// —— AI 内容准备(标准技能流)——
// 复刻的文案/图提示词/词锚点统一走技能流水线(video-replicate-prep),黑板传递标准产物;
// 渲染仍走既有 task.create(终态交接)。这里只持有流程状态与产物预览,不重复写轮询。
const skPrep = useSkill()
const prepLoading = skPrep.loading
const prepError = skPrep.error
const prepQualityWarn = skPrep.qualityWarn
const runPipeline = skPrep.runPipeline
// 「AI 润色」是用户显式触发的单技能调用(text-generation),与准备流状态隔离,不属于流水线编排
const { loading: polishing, runCopy: runPolish, error: polishError } = useSkill()
const prepCopy = ref(null)      // 三段文案 {title, subtitle, script, subject, demand}(可编辑)
const prepApplied = ref(false)  // 是否已把 AI 文案作为创作方向应用到生成
// 智能体编排(实验):开启后改用工具调用式 agent 计划(video-replicate-prep-agent),
// 首步由模型自主选择调用技能,下游读取其自由文本答案;关闭则走确定性 video-replicate-prep。
const agentMode = ref(false)

// 智能默认:配置到位后用 /gen-config 的推荐值预填(用户不感知,展开高级设置仍可改)。
// 完全复刻(含默认未点选状态)除外:该模式语义就是“照搬原片”,档位锁定忠实档,
// 不吃推荐默认,否则“默认完全复刻”会带着改写档位下发给 worker
// /gen-config 的单一来源实例(组件与本页共用同一份缓存):单价与推荐默认值都从这里取,
// 避免同一页面对本接口重复请求
const cfg = useGenConfig()
const cfgDefaults = cfg.defaults
watch(cfgDefaults, (d) => {
  // 换元素复刻(replace)与原样照搬(full)都锁定忠实档,不吃后端推荐默认(否则会按“适度改造”出片);
  // 只有爆款改写(viral)才用推荐默认值预填
  if (!d || adv.mode !== 'viral') return
  if (d.creative_level && !adv.creativeLevel) adv.creativeLevel = d.creative_level
  if (d.hook_boost && !adv.hookBoost) adv.hookBoost = d.hook_boost
}, { deep: true, immediate: true })

// 切换复刻方式时同步原片元素检测:进入"换元素复刻"且有视频即检测;切走则清空槽位,
// 避免非替换模式下仍展示"绑定到原片"选择器造成误导。
watch(
  () => adv.mode,
  (m) => {
    if (m === 'replace' && refVideo.value) detectOriginalElements()
    else originalElements.value = []
  },
)

// 套用 worker 建议方案:只补"用户没指定"的旋钮,不让系统覆盖用户的显式选择。
// 完全复刻模式同样只展示建议说明,不套用任何改写取值(与上方推荐默认的约束一致)
function applyPlan(plan) {
  const v = plan?.values || {}
  // 换元素复刻/原样照搬只展示建议说明,不套用改写取值(锁定忠实档);仅爆款改写套用推荐档位/钩子
  if (adv.mode !== 'viral') {
    if (plan?.reason) planReason.value = plan.reason
    return
  }
  if (v.creative_level && !adv.creativeLevel) adv.creativeLevel = v.creative_level
  if (v.hook_boost && !adv.hookBoost) adv.hookBoost = v.hook_boost
  if (v.format && !adv.format) adv.format = v.format
  if (v.lead_act && !adv.leadAct) adv.leadAct = v.lead_act
  if (v.intent?.length && !adv.intent.length) adv.intent = [...v.intent]
  if (plan?.reason) planReason.value = plan.reason
}

// —— 上传 ——
const refVideo = ref('')          // 对标视频地址
const refVideoName = ref('')
const refVideoDuration = ref(0)   // 对标视频真实时长(秒),用于最小时长校验与提示
const productImages = ref([])     // 替换素材图(可多张,作为替换素材)
// 每张上传图的角色标注:URL → product/person/scene。随建单下发 image_roles,
// 后端据此给视觉模型“这张是人物图/产品图/场景图”的强提示,避免把人物/场景误判成产品
// (实测:无角色提示时庭院里的狗照会被判成场景、人物图可能被错叫商品,导致换人/换场景失效)。
const imageRoles = reactive({})
// AI 预识别状态:上传后异步识别角色,识别中显示 loading、命中打"AI 已识别"标记;
// 用户手动点选会清除标记(视为人工修正)。不再默认标"产品",避免人脸被当产品静默错配。
const aiLoading = reactive({})
const aiTagged = reactive({})
// 已标注角色统计:实时显示"人物 N / 产品 N / 场景 N",让用户一眼看清映射是否齐全。
const roleSummary = computed(() => {
  const c = { person: 0, product: 0, scene: 0 }
  for (const v of Object.values(imageRoles)) if (v in c) c[v]++
  const parts = []
  if (c.person) parts.push(`人物 ${c.person}`)
  if (c.product) parts.push(`产品 ${c.product}`)
  if (c.scene) parts.push(`场景 ${c.scene}`)
  return parts.length ? parts.join(' / ') : '尚未标注'
})
// 原片元素槽位:换元素复刻时,上传对标视频即检测原片里可替换的元素(人物/产品/场景),
// 用户把上传的替换图精确绑定到"原片具体的哪个元素",避免多人/多物视频里换错人、换错货。
// 仅做增强:检测失败/未配置视觉模型时 originalElements 为空,用户仍可照常按角色替换,不阻断。
const originalElements = ref([])   // [{id, kind, label, time, thumbnail, bbox?, start?, end?}]
const elementsLoading = ref(false)
// 上传图 → 原片元素槽位 id 的绑定(仅换元素复刻且有检测结果显示时生效)
const imageSlot = reactive({})
// 检测原片元素:只在换元素复刻模式、且有对标视频时调用;结果驱动上传区的"绑定到原片"选择器。
async function detectOriginalElements() {
  if (adv.mode !== 'replace' || !refVideo.value) {
    originalElements.value = []
    return
  }
  elementsLoading.value = true
  try {
    const res = await api.task.detectElements.post({ reference_video: refVideo.value })
    originalElements.value = Array.isArray(res?.data?.elements) ? res.data.elements : []
  } catch (e) {
    originalElements.value = []   // 降级:检测失败不阻断复刻
  } finally {
    elementsLoading.value = false
  }
}
// 上传图已选角色后,可绑定的原片元素(同类才允许绑定,避免"人脸绑到产品槽位")
function slotOptionsFor(url) {
  const role = imageRoles[url]
  if (!role) return []
  return originalElements.value.filter((e) => e.kind === role)
}

// —— 拆解分镜 ——
const deconstructId = ref(null)
// deconstructing:仅表示“建单请求”进行中(很快结束);
// deconstructPending:表示拆解任务已提交、正在后台执行(轮询中)。
// 二者必须分开:此前建单返回即把 deconstructing 复位,而轮询期间页面无任何加载态,
// 用户会以为点击无效/任务没在跑。二者任一为真都视为“拆解进行中”,整页展示进度视图。
const deconstructing = ref(false)
const deconstructPending = ref(false)
const deconstructElapsed = ref(0) // 拆解已进行秒数,给用户“任务确实在跑”的直观反馈
const shotsCardRef = ref(null)    // “步骤 2”分镜卡片 DOM,拆解完成后滚动到可视区
const deconstructError = ref('')  // 拆解空结果/失败的持久提示:此前只弹 2 秒 toast,卡片直接消失,用户以为没反应
// deconstructNote:「不是失败但需要用户知道」的提示(如部分镜头没逆推出描述)。
// 与 deconstructError 分开:失败要阻断并引导重试,提示只说明可继续但要人工补。
const deconstructNote = ref('')
const shots = ref([])             // [{index,start,end,duration,narration,description}]
let pollTimer = null
let elapsedTimer = null

// 拆解任务进行中(建单请求中或后台执行中):整页切换为转圈进度视图,与生成页体验一致。
// 此前只在下方插入一张小卡片,用户停留在上方上传区时看不到任何页面变化,以为点击无效。
const deconstructActive = computed(() => deconstructing.value || deconstructPending.value)
// 拆解阶段(依据已耗时粗略推进):拆解任务没有后端百分比,因此不使用假百分比进度条,
// 仅用阶段高亮 + 真实已耗时给用户“任务在往前走”的方向感,不作为完成依据。
const DECONSTRUCT_STAGES = ['解析对标视频', '切分镜头', '逆推分镜描述']
const deconstructStageIndex = computed(() => {
  const s = deconstructElapsed.value
  if (s < 8) return 0
  if (s < 24) return 1
  return 2
})
// 拆解进度视图切回正常页面时,把“步骤 2”的结果/失败卡片滚动到可视区:
// 成功看分镜、失败看原因,都不需要用户自己往下找。
watch(deconstructActive, async (now, prev) => {
  if (prev && !now) {
    await nextTick()
    shotsCardRef.value?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
  }
})

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
// 定价(来自后端业务配置,可在管理端修改);无额度用户走单次支付时使用。
// 与 useGenConfig 同源,本页不再单独拉一次 /gen-config
const price = computed(() => cfg.price)
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
  () => !!refVideo.value
    && !(refVideoDuration.value && refVideoDuration.value < MIN_REF_VIDEO_SECONDS)
    && !deconstructing.value && !deconstructPending.value,
)
// 素材缺失引导:缺失项由后端 /v1/task/precheck 结构化下发(单一来源),
// 前端只负责渲染"缺什么/为什么/怎么补",不再自己写一套校验规则(两边必然漂移)。
const missing = ref([])
const refVideoFieldRef = ref(null)
const imageFieldRef = ref(null)
let precheckTimer = null

// 素材变化后防抖预检:让用户上传过程中就能看到"还缺什么",而不是点生成才报错
watch([refVideo, refVideoDuration, productImages, () => adv.intent.join(',')], () => {
  if (precheckTimer) clearTimeout(precheckTimer)
  precheckTimer = setTimeout(runPrecheck, 400)
}, { deep: true })

async function runPrecheck() {
  try {
    const res = await api.task.precheck.post({
      reference_video: refVideo.value || undefined,
      materials: [...productImages.value, ...(refVideo.value ? [refVideo.value] : [])],
      intent: effectiveIntent.value,
      // 带上真实时长,后端才能判定"视频太短"这一类缺失
      duration: refVideoDuration.value || undefined,
    })
    if (res.code === 1) missing.value = res.data?.missing || []
  } catch (e) {
    missing.value = []   // 预检失败不阻断:建单侧仍有兜底校验
  }
}

// 一键去补:滚动到对应上传区(真人照片这类则直接去数字人页),用户不必自己找入口
function goFix(action) {
  if (action === 'open_digital') {
    router.push('/digital')
    return
  }
  const target = action === 'upload_image' ? imageFieldRef.value : refVideoFieldRef.value
  const el = target?.$el || target
  el?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
}

// 复刻不再让用户选择模板(成片直接以对标视频为蓝本编辑,时长跟随原片);
// 完全复刻(未选任何替换意图)只需拆解结果即可生成,无需替换素材图;
// 一旦选了替换意图,则必须至少传一张替换图,避免"选了换产品却空跑"。
// 生效替换意图:优先用结构化意图;完全复刻(默认)由上传图标注的角色(image_roles)推导,
// 这样只上传图、不手动选意图的小白也能触发正确替换维度(后端据此分流“换人/换产品/换场景”)
// 替换维度仅“换元素复刻(replace)”模式按上传图角色自动推断;
// 爆款改写(viral)/原样照搬(full)上传的参考图只作风格 / 运镜参考,绝不触发元素替换。
const effectiveIntent = computed(() => {
  if (adv.mode !== 'replace') return []
  if (adv.intent.length) return adv.intent
  const fromRoles = Object.values(imageRoles)
  return [...new Set(fromRoles)].filter(Boolean)
})

const canGenerate = computed(() => {
  if (!shots.value.length || submitting.value) return false
  // 换元素复刻需要参考图:没图就只是原样复制,与“换元素复刻”语义不符,需引导上传
  if (adv.mode === 'replace' && !effectiveIntent.value.length) return false
  if (adv.intent.length && productImages.value.length === 0) return false
  if (missing.value.length) return false   // 后端判定素材缺失时不放行
  return true
})

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
    refPrefilled.value = false  // 用户已重新上传,撤销“热门模板已带入”提示
    shots.value = []
    deconstructId.value = null
    deconstructError.value = ''
    deconstructNote.value = ''
    // 换视频时终止上一轮拆解轮询,避免旧任务状态污染新素材的展示
    stopPolling()
    onFinish()
    // 换元素复刻:立即检测原片元素槽位,供用户把上传图精确绑定到原片具体元素
    detectOriginalElements()
    window.$message?.success('对标视频已上传,可开始拆解分镜')
  } catch (e) {
    onError()
  }
}

// 上传替换素材图(最多 9 张)。不再默认标"产品":上传后立即异步 AI 识别角色并预标,
// 识别失败/清空则留空,由用户手动点选,杜绝"人脸被当产品"的静默错配。
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
    onFinish()
    // 异步 AI 预标角色,不阻塞上传完成
    aiLoading[url] = true
    try {
      const res = await api.task.classifyImages.post({ urls: [url] })
      const role = String((res?.data?.roles?.[url]) || '').trim()
      if (role) {
        imageRoles[url] = role
        aiTagged[url] = true
      }
    } catch (e) {
      // 识别失败不阻断:留空,用户手动选
    } finally {
      aiLoading[url] = false
    }
  } catch (e) {
    onError()
  }
}
function setRole(url, role) {
  imageRoles[url] = role
  aiTagged[url] = false  // 人工修正,清除 AI 标记
  // 角色变更后,原绑定的原片槽位若类别不符则清除(避免"人脸绑到产品槽位")
  const slot = imageSlot[url]
  if (slot) {
    const el = originalElements.value.find((e) => e.id === slot)
    if (!el || el.kind !== role) delete imageSlot[url]
  }
}
function removeProduct(url) {
  productImages.value = productImages.value.filter((u) => u !== url)
  delete imageRoles[url]
  delete aiTagged[url]
  delete aiLoading[url]
  delete imageSlot[url]
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
      intent: effectiveIntent.value,
      // 一句话目标:与生成侧同一份,让"看懂原片"和"出片"按同一目标组织
      goal: goal.value.trim() || undefined,
      // 与生成建单传同一个形态:保证"理解原片"与"重塑出片"一致
      format: adv.format,
      // 创意档位/钩子同样必须与生成侧一致:拆解按"忠实复刻"理解原片、却按"爆款改写"出片时,
      // 用户看到的分镜描述就不再是成片的依据
      creative_level: adv.creativeLevel || undefined,
      hook_boost: adv.hookBoost || undefined,
      device: device(),
    })
    if (res.code === 1 && res.data?.id) {
      deconstructId.value = res.data.id
      // 建单成功 → 进入“任务执行中”状态:deconstructActive 变真,页面整体切换为拆解进度视图
      deconstructPending.value = true
      window.$message?.success('已提交拆解,正在解析对标视频…')
      startPolling()
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
      // 逐帧对照:帧 URL 写在 result_text 分镜 JSON(不落库 tb_shot,避免改表),
      // 按 index 合并到已落库的分镜上,让每个镜头卡片显示 AI 实际看到的画面缩略图
      if (sb.shots && sb.shots.length) {
        const fm = {}
        for (const s of sb.shots) if (s.frame) fm[s.index] = s.frame
        if (Object.keys(fm).length) {
          shots.value = shots.value.map((s) => ({ ...s, frame: fm[s.index] || s.frame || '' }))
        }
      }
      // 拆解完成即自动生成建议文案:编排(文案→图提示词→词锚点)在后端+worker 透明完成,
      // 前端不展示任何技能/流水线字样,用户无感,只需在下方修改或点「润色」。
      runPrep()
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
        // 套用 worker 的推荐方案(只补用户没指定的旋钮),让用户不用理解"档位"也能拿到合理默认
        if (detail?.usage?.plan) applyPlan(detail.usage.plan)
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
      frame: String(s?.frame || ''),
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
    // 原片元素绑定(仅换元素复刻生效):把上传图精确绑定到"原片具体的哪个元素",
    // 减少多人/多物视频里换错人、换错货的错位;同时把绑定关系写进备注为人话提示。
    // 非替换模式(爆款改写/原样照搬)上传图只作风格参考,不绑定、不写入备注,避免误导生成。
    // 实例级定位增强:若检测给出了 bbox(归一化包围盒)与时间跨度,一并写进备注,
    // 让生成更精确地替换"原片里那个具体对象、那段出现时间",而非整类角色。
    const image_slots = {}
    const slotNotes = []
    if (adv.mode === 'replace') {
      for (const u of productImages.value) {
        const slotId = imageSlot[u]
        if (!slotId) continue
        const el = originalElements.value.find((e) => e.id === slotId)
        if (!el) continue
        image_slots[u] = slotId
        const roleLabel = { person: '人物', product: '产品', scene: '场景' }[el.kind] || '元素'
        // 时空定位修饰:位置(bbox)+ 出现时段(start~end),模型给不出则留空不误导
        const loc = []
        if (Array.isArray(el.bbox) && el.bbox.length === 4) {
          loc.push(`位置[${el.bbox.map((n) => Number(n).toFixed(2)).join(', ')}]`)
        }
        if (el.start != null && el.end != null && el.end - el.start > 0.1) {
          loc.push(`${el.start}~${el.end}s`)
        }
        const where = loc.length ? `(${loc.join('，')})` : ''
        slotNotes.push(`将${roleLabel}参考图替换原片中出现的「${el.label}」${where}`)
      }
    }
    const remarkWithSlots = [remark, slotNotes.length ? slotNotes.join('；') : ''].filter(Boolean).join('\n')
    const payload = {
      materials,
      intent: effectiveIntent.value,
      // 一句话目标:随建单下发,worker 在结构化旋钮缺失时据此推断方案
      goal: goal.value.trim() || undefined,
      // 复刻目标形态(可选):后端按白名单校验后注入形态提示词,不指定则沿用原片结构
      format: adv.format || undefined,
      // 主角表现(可选,仅“换人物”时生效):跳舞/推广等创意增强;不传=跟随原片
      lead_act: (adv.intent.includes('person') && adv.leadAct) ? adv.leadAct : undefined,
      // 创意档位/开头钩子(可选):决定在原片骨架上改多少、是否重写前 3 秒;
      // 与拆解时传的值同源,保证"看懂原片"与"重塑出片"用的是同一档
      creative_level: adv.creativeLevel || undefined,
      hook_boost: adv.hookBoost || undefined,
      // 专家模式(可选):本次任务追加的创作要求,拼在创作要求段末尾(位置即优先级)
      asset_override: adv.assetOverride.trim() || undefined,
      image_roles: Object.keys(image_roles).length ? image_roles : undefined,
      image_slots: Object.keys(image_slots).length ? image_slots : undefined,
      // 代码渲染层·信息卡(可选,对齐 Hypit lower-thirds):显式提供才叠加,不臆造商品信息
      overlay_card: (cardTitle.value.trim() || cardBody.value.trim())
        ? { title: cardTitle.value.trim(), body: cardBody.value.trim(), corner: 'bl' }
        : undefined,
      // 代码渲染层·角标(可选,对齐 Hypit badge):成片角落胶囊标签
      overlay_badge: badgeText.value.trim()
        ? { text: badgeText.value.trim(), corner: 'tr' }
        : undefined,
      // 代码渲染层·动效信息层(可选,对齐 Hypit 动效组件):仅显式提供才叠加,绝不臆造内容
      overlay_ranking: (rankTitle.value.trim() || rankText.value.trim())
        ? (() => {
            const items = rankText.value.split('\n').map((s) => s.trim()).filter(Boolean).map((line) => {
              const idx = line.indexOf('|')
              const sep = idx >= 0 ? '|' : /\s+/
              const parts = line.split(sep).map((p) => p.trim()).filter(Boolean)
              return { label: parts[0] || '', value: (parts.slice(1).join(' ') || '') }
            })
            return items.length
              ? { title: rankTitle.value.trim(), items, corner: 'bl', start_ms: Number(rankStart.value) || 0, stagger_ms: Number(rankStagger.value) || 500 }
              : undefined
          })()
        : undefined,
      overlay_reveal: revealText.value.trim()
        ? { text: revealText.value.trim(), emoji: revealEmoji.value.trim() || '✨', at_ms: Number(revealAt.value) || 0, corner: 'br' }
        : undefined,
      overlay_flash: flashColor.value.trim()
        ? { color: flashColor.value.trim(), at_ms: Number(flashAt.value) || 0, duration_ms: Number(flashDur.value) || 400 }
        : undefined,
      overlay_sticker: stickerText.value.trim()
        ? { text: stickerText.value.trim(), side: stickerSide.value || 'l', at_ms: Number(stickerAt.value) || 0 }
        : undefined,
      // 自动 B-roll(可选,对齐 Hypit B-roll):显式开启才生效,失败回退原片,绝不阻断出片
      auto_broll: autoBrollEnabled.value
        ? {
            enabled: true,
            source: autoBrollSource.value || 'goods',
            strategy: autoBrollStrategy.value || 'even',
            keywords: autoBrollKeywords.value.trim()
              ? autoBrollKeywords.value.split(/[,，\s]+/).map((s) => s.trim()).filter(Boolean)
              : [],
            interval: Number(autoBrollInterval.value) || 8,
            window: Number(autoBrollWindow.value) || 3,
            position: autoBrollPos.value || 'center',
            prompt: autoBrollPrompt.value.trim() || undefined,
          }
        : undefined,
      remark: remarkWithSlots || undefined,
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

// —— 工程模板(参数模板化 / 一套结构百变体)——
// 只保存「创意配置快照」:复刻形态 + 创意旋钮 + 信息卡/动效/自动 B-roll;不存素材。
// 生成变体时由调用方补入新素材(materials)与覆盖项(换主播/排名/语言/画幅等),复用同一套出片链路。
function buildTemplateParams() {
  const rankItems = rankText.value.split('\n').map((s) => s.trim()).filter(Boolean).map((line) => {
    const idx = line.indexOf('|')
    const sep = idx >= 0 ? '|' : /\s+/
    const parts = line.split(sep).map((p) => p.trim()).filter(Boolean)
    return { label: parts[0] || '', value: (parts.slice(1).join(' ') || '') }
  })
  const params = {
    format: adv.format || '',
    intent: [...(adv.intent || [])],
    creative_level: adv.creativeLevel || 'faithful',
    hook_boost: adv.hookBoost || '',
    asset_override: adv.assetOverride.trim() || '',
    goal: goal.value.trim() || '',
    overlay_card: (cardTitle.value.trim() || cardBody.value.trim())
      ? { title: cardTitle.value.trim(), body: cardBody.value.trim() }
      : undefined,
    overlay_badge: badgeText.value.trim() ? { text: badgeText.value.trim(), corner: 'tr' } : undefined,
    overlay_ranking: (rankTitle.value.trim() || rankText.value.trim()) && rankItems.length
      ? { title: rankTitle.value.trim(), items: rankItems, corner: 'bl', start_ms: Number(rankStart.value) || 0, stagger_ms: Number(rankStagger.value) || 500 }
      : undefined,
    overlay_reveal: revealText.value.trim()
      ? { text: revealText.value.trim(), emoji: revealEmoji.value.trim() || '✨', at_ms: Number(revealAt.value) || 0, corner: 'br' }
      : undefined,
    overlay_flash: flashColor.value.trim()
      ? { color: flashColor.value.trim(), at_ms: Number(flashAt.value) || 0, duration_ms: Number(flashDur.value) || 400 }
      : undefined,
    overlay_sticker: stickerText.value.trim()
      ? { text: stickerText.value.trim(), side: stickerSide.value || 'l', at_ms: Number(stickerAt.value) || 0 }
      : undefined,
    auto_broll: autoBrollEnabled.value
      ? {
          enabled: true,
          source: autoBrollSource.value || 'goods',
          strategy: autoBrollStrategy.value || 'even',
          keywords: autoBrollKeywords.value.trim()
            ? autoBrollKeywords.value.split(/[,，\s]+/).map((s) => s.trim()).filter(Boolean)
            : [],
          interval: Number(autoBrollInterval.value) || 8,
          window: Number(autoBrollWindow.value) || 3,
          position: autoBrollPos.value || 'center',
          prompt: autoBrollPrompt.value.trim() || undefined,
        }
      : undefined,
  }
  // 去掉未设置的键,保持模板精简
  Object.keys(params).forEach((k) => { if (params[k] === undefined) delete params[k] })
  return params
}

function applyTemplateParams(p) {
  if (!p) return
  if (p.format) adv.format = p.format
  if (Array.isArray(p.intent)) adv.intent = [...p.intent]
  if (p.creative_level) adv.creativeLevel = p.creative_level
  if (p.hook_boost) adv.hookBoost = p.hook_boost
  if (p.asset_override) adv.assetOverride = p.asset_override
  if (p.goal) goal.value = p.goal
  const card = p.overlay_card || {}
  cardTitle.value = card.title || ''
  cardBody.value = card.body || ''
  badgeText.value = (p.overlay_badge && p.overlay_badge.text) || ''
  const rk = p.overlay_ranking || {}
  rankTitle.value = rk.title || ''
  rankText.value = (rk.items || []).map((it) => `${it.label} ${it.value}`).join('\n')
  rankStart.value = rk.start_ms || 0
  rankStagger.value = rk.stagger_ms || 500
  const rv = p.overlay_reveal || {}
  revealText.value = rv.text || ''
  revealEmoji.value = rv.emoji || '✨'
  revealAt.value = rv.at_ms || 1000
  const fl = p.overlay_flash || {}
  flashColor.value = fl.color || ''
  flashAt.value = fl.at_ms || 800
  flashDur.value = fl.duration_ms || 400
  const st = p.overlay_sticker || {}
  stickerText.value = st.text || ''
  stickerSide.value = st.side || 'l'
  stickerAt.value = st.at_ms || 2000
  const ab = p.auto_broll || {}
  autoBrollEnabled.value = !!ab.enabled
  autoBrollSource.value = ab.source || 'goods'
  autoBrollStrategy.value = ab.strategy || 'even'
  autoBrollKeywords.value = Array.isArray(ab.keywords) ? ab.keywords.join(',') : (ab.keywords || '')
  autoBrollInterval.value = ab.interval || 8
  autoBrollWindow.value = ab.window || 3
  autoBrollPos.value = ab.position || 'center'
  autoBrollPrompt.value = ab.prompt || ''
}

async function saveTemplate() {
  if (!templateTitle.value.trim()) { window.$message?.warning('请先填模板标题'); return }
  if (!requireLogin()) return
  tplSaving.value = true
  try {
    const res = await api.genTemplate.save.post({
      title: templateTitle.value.trim(),
      format: adv.format || '',
      params: buildTemplateParams(),
    })
    if (res.code === 1) {
      window.$message?.success('已保存为工程模板,可在「载入模板」复用或批量出变体')
      await loadTemplateList()
    }
  } catch (e) { /* 拦截器已提示 */ }
  finally { tplSaving.value = false }
}

async function loadTemplateList() {
  tplLoading.value = true
  try {
    const res = await api.genTemplate.list.post({ pageNum: 1, pageSize: 50 })
    if (res.code === 1) templateList.value = (res.data && res.data.list) || []
  } catch (e) { /* 拦截器已提示 */ }
  finally { tplLoading.value = false }
}

async function handleDeleteTemplate(id) {
  if (!requireLogin()) return
  try {
    const res = await api.genTemplate.remove.post({ id })
    if (res.code === 1) {
      window.$message?.success('模板已删除')
      if (selectedTemplateId.value === id) selectedTemplateId.value = null
      await loadTemplateList()
    }
  } catch (e) { /* 拦截器已提示 */ }
}

function loadSelectedTemplate(id) {
  const t = (templateList.value || []).find((x) => x.id === id)
  if (t && t.params) {
    applyTemplateParams(t.params)
    window.$message?.success(`已载入模板「${t.title}」,换素材即可复用`)
  }
}

// 收集当前模板表单里的「画面可见文案」(口播由源视频生成,不在此翻译),按 LOC_FIELDS 顺序返回文本列表
function collectLocTexts() {
  return [
    (goal.value || '').trim(),
    (adv.assetOverride || '').trim(),
    (cardTitle.value || '').trim(),
    (cardBody.value || '').trim(),
    (badgeText.value || '').trim(),
    (revealText.value || '').trim(),
    (stickerText.value || '').trim(),
    (rankTitle.value || '').trim(),
  ]
}

// 基于已载入模板的当前表单状态重建完整 params(保留 corner/side 等结构),再用翻译结果替换可见文案。
// 返回的对象直接作为变体 overrides,经后端浅合并后整组替换顶层键,不会丢嵌套字段。
function buildLocalizedParams(translated) {
  const p = buildTemplateParams()
  if (translated.goal != null) p.goal = translated.goal
  if (translated.asset_override != null) p.asset_override = translated.asset_override
  if (p.overlay_card) {
    if (translated.card_title != null) p.overlay_card.title = translated.card_title
    if (translated.card_body != null) p.overlay_card.body = translated.card_body
  }
  if (p.overlay_badge && translated.badge != null) p.overlay_badge.text = translated.badge
  if (p.overlay_reveal && translated.reveal != null) p.overlay_reveal.text = translated.reveal
  if (p.overlay_sticker && translated.sticker != null) p.overlay_sticker.text = translated.sticker
  if (p.overlay_ranking && translated.rank_title != null) p.overlay_ranking.title = translated.rank_title
  return p
}

// LOC_FIELDS 顺序 → 翻译结果按索引回填到命名字段(翻译空则回退原文,保证不丢文案)
function translatedToMap(texts, translatedList) {
  const map = {}
  LOC_FIELDS.forEach((k, i) => {
    const t = (translatedList && translatedList[i] != null) ? String(translatedList[i]).trim() : ''
    map[k] = t || (texts[i] || '')
  })
  return map
}

async function batchGenerate() {
  if (!selectedTemplateId.value) { window.$message?.warning('请先选择模板'); return }
  const materials = batchMaterials.value.split('\n').map((s) => s.trim()).filter(Boolean)
  if (!materials.length) { window.$message?.warning('请至少填一个对标视频 URL'); return }
  if (!requireLogin()) return

  // 本地化:逐个目标语言翻译可见文案,得到 {lang: overrides}
  const langOverrides = {}
  if (localizeEnabled.value && localizeLangs.value.length) {
    const texts = collectLocTexts()
    localizing.value = true
    try {
      for (const lang of localizeLangs.value) {
        const res = await skLocal.runTranslate({ texts, target_lang: lang })
        if (res.status !== 'done' || !res.data?.result?.content?.translated) {
          window.$message?.warning(`翻译到 ${lang} 失败,该语言按原文出片`)
          langOverrides[lang] = buildLocalizedParams(translatedToMap(texts, texts))
          continue
        }
        langOverrides[lang] = buildLocalizedParams(translatedToMap(texts, res.data.result.content.translated))
      }
    } finally {
      localizing.value = false
    }
  }

  // 构造变体:本地化关闭 → 每素材 1 个(空 override);开启 → 每素材 × 每语言 1 个
  const variants = []
  if (localizeEnabled.value && localizeLangs.value.length) {
    for (const m of materials) {
      for (const lang of localizeLangs.value) {
        variants.push({ materials: [m], overrides: langOverrides[lang] || {}, remark: `本地化·${lang}` })
      }
    }
  } else {
    for (const m of materials) {
      variants.push({ materials: [m], overrides: {}, remark: '批量变体' })
    }
  }
  // 变体数上限(后端强制 ≤20),超出截断并提示
  const MAX = 20
  if (variants.length > MAX) {
    variants.length = MAX
    window.$message?.warning(`变体超过 ${MAX} 个,已截断`)
  }
  batchSaving.value = true
  try {
    const res = await api.genTemplate.batch.post({
      template_id: selectedTemplateId.value,
      variants,
    })
    if (res.code === 1) window.$message?.success(`已提交 ${res.data && res.data.count} 个变体,正在出片`)
  } catch (e) { /* 拦截器已提示 */ }
  finally { batchSaving.value = false }
}

onMounted(() => { loadTemplateList() })

// —— AI 内容准备:走标准技能流水线(类 agent 工作流)——
// 点「AI 内容准备」即把「复刻这段视频」交给技能编排器,顺序跑
// text-generation → image-generation → script-anchor,黑板把文案喂给图提示词与词锚点,
// 最终产物(copy/img_prompts/anchors)预览给用户;渲染仍由下方 generate() 走 task.create。
async function runPrep() {
  if (!requireLogin()) return
  if (!shots.value.length) {
    window.$message?.warning('请先拆解分镜,再生成 AI 内容')
    return
  }
  // 智能体编排(实验):改用工具调用式 agent 计划(video-replicate-prep-agent),
  // 首步由模型自主选择调用技能,下游读取其自由文本答案(bb.copy.answer)。
  const plan = agentMode.value ? { name: 'video-replicate-prep-agent' } : null
  const { status, data } = await runPipeline(
    goal.value.trim() || '复刻这段视频',
    {
      intent: 'replicate',
      // 成片时长供词锚点估算;对标视频作为计划上下文(worker 端会抽关键帧做视觉锚定文案)
      duration: refVideoDuration.value || 0,
      reference_video: refVideo.value || '',
    },
    plan,
  )
  if (status === 'done' && data?.content) {
    const bb = data.content
    // 智能体模式:agent 步骤产出自由文本答案(bb.copy.answer),映射入口播框供查看/参考;
    // 普通模式:结构化三段文案(title/subtitle/script/subject/demand)直接可编辑。
    if (agentMode.value && bb.copy?.answer) {
      prepCopy.value = { script: String(bb.copy.answer) }
    } else {
      prepCopy.value = bb.copy || null
    }
    prepApplied.value = false
    window.$message?.success('建议文案已生成,可直接修改或点「润色」')
  } else if (status === 'error') {
    window.$message?.error(prepError.value || '建议文案生成失败,可重试')
  } else if (status === 'timeout') {
    window.$message?.warning('建议文案生成超时,请稍后重试')
  }
}

// 把技能流产出的三段文案作为创作方向,套进生成载荷的 goal(既有字段,安全),
// 让 worker 在结构化旋钮之外多一份「人话」创作意图。
function applyPrep() {
  if (!prepCopy.value) return
  const c = prepCopy.value
  goal.value = [c.title, c.script].filter(Boolean).join('；')
  prepApplied.value = true
  window.$message?.success('已把文案作为创作方向,点击生成即生效')
}

// AI 润色:把用户当前(可能已手改的)文案作为草稿,再调 text-generation 单技能结合素材画面润色。
// 这是用户显式触发的单技能,不属于流水线编排;中间编排(文案→图提示词→词锚点)仍在 worker。
async function polishCopy() {
  if (!prepCopy.value) return
  if (!requireLogin()) return
  const c = prepCopy.value
  const { status, data } = await runPolish({
    template_title: (c.title || goal.value.trim() || '复刻视频').slice(0, 20),
    category: '零售带货',
    title: c.title || undefined,
    subtitle: c.subtitle || undefined,
    script: c.script || undefined,
    with_demand: true,
    // 对齐流水线:润色单技能也带对标视频,worker 自动抽帧做视觉锚定(无视觉网关则纯文本,不阻断)
    reference_video: refVideo.value || undefined,
  })
  if (status === 'done' && data?.content) {
    prepCopy.value = { ...prepCopy.value, ...(data.content || {}) }
    window.$message?.success('文案已润色')
  } else if (status === 'error') {
    window.$message?.error(polishError.value || '文案润色失败,可重试')
  } else if (status === 'timeout') {
    window.$message?.warning('文案润色超时,请稍后重试')
  }
}

// 额度优先:登录用户拉取最新剩余额度,决定走「扣额度」还是「支付」
async function refreshCredits() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await api.account.credits.post()
    if (res.code === 1) userStore.setCreditTotal(res.data.total)
  } catch (e) { /* 静默,以下单时后端校验为准 */ }
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

// 是否由平台模板/热门模板带入对标视频:是则提示用户可直接拆解,只需上传替换参考图
const refPrefilled = ref(false)
// 平台模板选择弹窗:模板替换属于复刻的一种,只是对标视频来自平台模板而非用户上传
const tplPickerVisible = ref(false)

// 选中平台模板后直接作为对标视频预填(不再走单独的“模板替换”页),
// 同时清空上一轮拆解结果,避免新旧素材混用。
function onPickTemplate(t) {
  if (!t.video_url) {
    window.$message?.error('该模板暂无成片视频,请换一个模板或直接上传自己的视频')
    return
  }
  refVideo.value = t.video_url
  refVideoName.value = t.title || '平台模板'
  refPrefilled.value = true
  refVideoDuration.value = 0
  shots.value = []
  deconstructId.value = null
  deconstructError.value = ''
  deconstructNote.value = ''
  stopPolling()
  tplPickerVisible.value = false
  // 换元素复刻:带入对标视频后同样检测原片元素槽位
  detectOriginalElements()
  window.$message?.success('已带入模板成片,可开始拆解分镜')
}

onMounted(() => {
  // 复刻无需加载平台模板列表;额度决定走「扣额度」还是「支付」(单价由 useGenConfig 提供)
  refreshCredits()
  runPrecheck()   // 首屏即给出"还缺什么",不等用户点生成才发现
  // 从热门模板「做同款」进入:优先读 sessionStorage 中转的对标视频(不暴露 OSS 地址),
  // 兼容旧链接里 query 带 ref 的方式;预填后用户只需上传替换参考图即可开始拆解。
  const pending = takePendingRef()
  let refUrl = pending?.url || ''
  let refTitle = pending?.title || ''
  if (!refUrl) {
    refUrl = String(route.query.ref || '')
    refTitle = String(route.query.title || '')
  }
  if (/^https?:\/\//.test(refUrl)) {
    refVideo.value = refUrl
    refVideoName.value = refTitle || '热门模板视频'
    refPrefilled.value = true
  }
})
onBeforeUnmount(() => { stopPolling(); stopPayPolling() })
</script>

<template>
  <div class="replicate-page">
    <div class="wrap" :class="{ 'is-deconstructing': deconstructActive }">
      <!-- 拆解进行中:整页切换为转圈进度视图(与生成页一致的体验),其余步骤由 .is-deconstructing 隐藏;
           拆解完成/失败后自动移除此状态,回到正常的分镜编辑页 -->
      <section v-if="deconstructActive" class="dc-progress">
        <svg class="dc-spin" width="96" height="96" viewBox="0 0 96 96" aria-hidden="true">
          <circle cx="48" cy="48" r="44" fill="none" stroke="#C7D2FE" stroke-width="6" />
          <path d="M48 4C72.3 4 92 23.7 92 48" fill="none" stroke="var(--brand)" stroke-width="6" stroke-linecap="round" />
          <rect x="30" y="34" width="36" height="28" rx="8" fill="#EEF2FF" />
          <path d="M43 42L54 48L43 54V42Z" fill="var(--brand)" />
        </svg>
        <div class="dc-title">正在拆解对标视频</div>
        <div class="dc-sub">AI 正在理解原片画面并切分镜头，通常需要 30~60 秒</div>
        <!-- 不确定态流动进度条:拆解任务没有后端百分比,用滚动色块表达“进行中”,不虚构具体进度 -->
        <div class="dc-pbar"><i /></div>
        <div class="dc-steps">
          <template v-for="(s, i) in DECONSTRUCT_STAGES" :key="s">
            <span :class="i < deconstructStageIndex ? 'done' : (i === deconstructStageIndex ? 'doing' : 'todo')">{{ s }}</span>
            <span v-if="i < DECONSTRUCT_STAGES.length - 1" class="sep">→</span>
          </template>
        </div>
        <div class="dc-elapsed">已进行 {{ deconstructElapsed }} 秒，请勿关闭页面</div>
      </section>

      <div class="hero" v-if="!embedded">
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

        <!-- 复刻方式:放在第一位,用户先选模式再看对应素材要求(如“原样照搬”无需参考图) -->
        <AdvancedCreationSettings v-model="adv" />

        <!-- 一句话目标:自由描述(风格/受众/语气等);结构化选择请用上方芯片或更多设置 -->
        <div class="field">
          <div class="lbl">想做成什么样?<span class="lbl-tip">选填,用大白话补充风格/受众,例如“更电影感、适合发小红书”</span></div>
          <n-input
            v-model:value="goal"
            type="textarea"
            :rows="2"
            maxlength="200"
            show-count
            placeholder="例如:整体更电影感、更适合发小红书、更有反转"
          />
          <div class="chips" style="margin-top:8px">
            <span v-for="g in goalExamples" :key="g" class="chip" @click="goal = g">{{ g }}</span>
          </div>
          <div class="sub">这里只写“感觉 / 风格 / 受众”这类没法用选项表达的要求;要不要换人物、换商品、换场景,请用上方的「替换意图」选择。</div>
          <!-- worker 回写的推荐方案:只展示人话解释,取值已静默套用 -->
          <div v-if="planReason" class="sub">AI 建议:{{ planReason }}</div>
        </div>

        <!-- 进阶装饰与批量能力默认收起:小白首屏只看到「上传素材 → 生成」主链路,展开仍有完整能力 -->
        <div class="expert-head" @click="showAdvanced = !showAdvanced">
          <span class="lbl-inline">加文字标签 / 动效特效 / 批量出片（可选，进阶）</span>
          <span class="caret">{{ showAdvanced ? '收起' : '展开' }}</span>
        </div>
        <div v-show="showAdvanced" class="expert-body">
          <div class="field">
            <div class="lbl">在视频上加文字标签（可选）</div>
          <div class="sub">想让成片显示商品名、卖点这类文字就填这里，不填就不会出现，绝不臆造信息。</div>
          <n-input v-model:value="cardTitle" placeholder="卡片标题,如:开业福利" maxlength="20" show-count />
          <n-input
            v-model:value="cardBody"
            type="textarea"
            :rows="2"
            placeholder="卡片正文,如:全场五折仅限三天"
            maxlength="40"
            show-count
            style="margin-top:8px"
          />
          <n-input v-model:value="badgeText" placeholder="角标文字,如:限时特惠" maxlength="12" show-count style="margin-top:8px" />
        </div>

        <div class="field">
          <div class="lbl">加动效特效（可选）</div>
          <div class="sub">排行榜 / 表情揭示 / 彩色闪烁 / 评论贴纸等特效，想用再填，不填就没有。</div>

          <div class="fx-group">
            <div class="fx-title">排行榜（逐条出现）</div>
            <n-input v-model:value="rankTitle" placeholder="榜单标题,如:本周热度榜" maxlength="20" show-count />
            <n-input
              v-model:value="rankText"
              type="textarea"
              :rows="3"
              placeholder="每行一条:名称 数值(或 名称|数值),如 小龙虾 98 / 烤鸭 87"
              style="margin-top:8px"
            />
            <div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap">
              <n-input-number v-model:value="rankStart" :min="0" placeholder="首条出现(ms)" style="width:160px" />
              <n-input-number v-model:value="rankStagger" :min="80" placeholder="逐条错峰(ms)" style="width:160px" />
            </div>
          </div>

          <div class="fx-group">
            <div class="fx-title">揭示板（表情弹出）</div>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <n-input v-model:value="revealText" placeholder="揭示文案,如:上新啦" maxlength="20" show-count style="flex:1;min-width:200px" />
              <n-input v-model:value="revealEmoji" placeholder="emoji ✨" maxlength="4" style="width:120px" />
              <n-input-number v-model:value="revealAt" :min="0" placeholder="出现(ms)" style="width:140px" />
            </div>
          </div>

          <div class="fx-group">
            <div class="fx-title">彩色闪烁</div>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <n-input v-model:value="flashColor" placeholder="颜色 #RRGGBB" maxlength="9" style="width:160px" />
              <n-input-number v-model:value="flashAt" :min="0" placeholder="出现(ms)" style="width:140px" />
              <n-input-number v-model:value="flashDur" :min="120" placeholder="时长(ms)" style="width:140px" />
            </div>
          </div>

          <div class="fx-group">
            <div class="fx-title">评论贴纸（侧边滑入）</div>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <n-input v-model:value="stickerText" placeholder="贴纸文案,如:这个我买过" maxlength="30" show-count style="flex:1;min-width:200px" />
              <n-select v-model:value="stickerSide" :options="[{label:'左侧',value:'l'},{label:'右侧',value:'r'}]" style="width:120px" />
              <n-input-number v-model:value="stickerAt" :min="0" placeholder="出现(ms)" style="width:140px" />
            </div>
          </div>

          <div class="fx-group">
            <div class="fx-title">自动插入特写画面</div>
            <n-switch v-model:value="autoBrollEnabled" />
            <span class="sub" style="margin-left:8px">开启后按时间轴自动插入商品/场景特写,失败自动回退原片</span>
            <template v-if="autoBrollEnabled">
              <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">
                <n-select v-model:value="autoBrollSource" :options="[{label:'商品图',value:'goods'},{label:'场景图',value:'scene'},{label:'指定URL',value:'url'},{label:'自动生成',value:'gen'}]" style="width:140px" />
                <n-select v-model:value="autoBrollStrategy" :options="[{label:'均匀插入',value:'even'},{label:'关键词命中',value:'mention'}]" style="width:140px" />
                <n-select v-model:value="autoBrollPos" :options="[{label:'居中',value:'center'},{label:'右下',value:'br'},{label:'左下',value:'bl'},{label:'右上',value:'tr'},{label:'左上',value:'tl'}]" style="width:140px" />
              </div>
              <n-input v-if="autoBrollStrategy === 'mention'" v-model:value="autoBrollKeywords" placeholder="关键词,用逗号分隔,如 小龙虾,烤鸭" style="margin-top:8px" />
              <n-input v-if="autoBrollSource === 'gen'" v-model:value="autoBrollPrompt" type="textarea" placeholder="文生图提示词,描述想穿插的画面,如 食材翻炒特写、城市夜景空镜" style="margin-top:8px" />
              <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">
                <n-input-number v-model:value="autoBrollInterval" :min="2" placeholder="间隔(秒)" style="width:140px" />
                <n-input-number v-model:value="autoBrollWindow" :min="1" placeholder="单窗(秒)" style="width:140px" />
              </div>
            </template>
          </div>
        </div>

        <div class="field">
          <div class="lbl">保存搭配 / 批量出片（可选）</div>
          <div class="sub">把当前这套设置存成模板，下次换素材直接复用；也能一次生成多个语言版本。</div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
            <n-input v-model:value="templateTitle" placeholder="模板标题,如:小龙虾带货黄金结构" style="width:240px" />
            <n-button type="primary" :loading="tplSaving" @click="saveTemplate">保存为模板</n-button>
            <n-select
              v-model:value="selectedTemplateId"
              :options="templateOptions"
              placeholder="载入模板(换素材复用)"
              style="width:240px"
              :loading="tplLoading"
              @update:value="loadSelectedTemplate"
            />
            <n-button quaternary @click="loadTemplateList">刷新模板</n-button>
          </div>
          <!-- 我的模板管理:列表化展示,支持载入与删除(删除走二次确认,防误删) -->
          <div v-if="templateList.length" style="margin-top:10px;display:flex;flex-direction:column;gap:6px">
            <div
              v-for="t in templateList"
              :key="t.id"
              style="display:flex;gap:8px;align-items:center;justify-content:space-between;padding:6px 10px;border:1px solid var(--n-border-color);border-radius:8px"
            >
              <div style="display:flex;gap:8px;align-items:center;min-width:0">
                <span :title="t.title" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:320px">{{ t.title }}</span>
                <n-tag v-if="t.format" size="small" :bordered="false" type="info">{{ t.format }}</n-tag>
              </div>
              <div style="display:flex;gap:6px;align-items:center;flex-shrink:0">
                <n-button
                  size="small"
                  type="primary"
                  secondary
                  @click="selectedTemplateId = t.id; loadSelectedTemplate(t.id)"
                >载入</n-button>
                <n-popconfirm @positive-click="handleDeleteTemplate(t.id)">
                  <template #trigger>
                    <n-button size="small" quaternary type="error">删除</n-button>
                  </template>
                  确认删除该模板?删除后无法恢复
                </n-popconfirm>
              </div>
            </div>
          </div>
          <div v-else class="sub" style="margin-top:8px">暂无已保存的模板,先填好创意配置后点「保存为模板」。</div>
          <div class="sub" style="margin-top:10px">批量出变体:每行一个对标视频 URL,套用所选模板结构一次生成多片</div>
          <n-input v-model:value="batchMaterials" type="textarea" :rows="3" placeholder="每行一个对标视频 URL" style="margin-top:6px" />
          <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px">
            <n-switch v-model:value="localizeEnabled" />
            <span class="sub">一键本地化:把画面可见文案(信息卡/角标/揭示/贴纸)翻译为指定语言,逐语言出变体</span>
          </div>
          <template v-if="localizeEnabled">
            <n-select
              v-model:value="localizeLangs"
              :options="LANG_OPTIONS"
              multiple
              placeholder="选择目标语言(可多选)"
              style="margin-top:8px;max-width:420px"
            />
            <div class="sub" style="margin-top:4px">提示:口播旁白由源视频生成,本版仅本地化画面可见文案;旁白翻译为后续 worker 端增强。</div>
          </template>
          <n-button :loading="batchSaving || localizing" style="margin-top:8px" @click="batchGenerate">批量生成变体</n-button>
          </div>
        </div>

        <div class="field" ref="refVideoFieldRef">
          <div class="lbl">对标视频 <i class="req">*</i></div>
          <!-- 热门模板带入对标视频时,给出明确提示:可直接拆解,只需上传替换参考图 -->
          <div v-if="refPrefilled" class="sub" style="margin-top:0">
            已带入「{{ refVideoName }}」作为对标视频,可直接点击「开始拆解分镜」;如需替换参考图,在下方上传即可。
          </div>
          <div class="row">
            <!-- 对标视频两种来源:自己上传,或从平台模板库选一个(模板替换即复刻) -->
            <n-upload
              accept="video/*"
              :show-file-list="false"
              :custom-request="uploadRefVideo"
            >
              <n-button secondary>{{ refVideo ? '重新上传对标视频' : '上传对标视频' }}</n-button>
            </n-upload>
            <n-button secondary @click="tplPickerVisible = true">从模板库选</n-button>
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

        <div class="field" ref="imageFieldRef" v-if="adv.mode === 'replace' || adv.mode === 'viral'">
          <div class="lbl">参考图 <i v-if="adv.mode === 'replace'" class="req">*</i><span class="lbl-tip">
            {{ adv.mode === 'viral' ? '作为风格 / 构图 / 运镜参考(不替换原片元素),最多 9 张' : '你的脸 / 人 / 产品 / 角色,将按视频重塑,最多 9 张' }}
          </span></div>
          <div class="role-summary" v-if="adv.mode === 'replace' && productImages.length">
            已标注：{{ roleSummary }}
          </div>
          <!-- 原片元素槽位:换元素复刻时,把对标视频里可替换的人/物/景识别出来,
               让用户把上传图精确绑定到"原片具体的哪个元素",避免多人/多物视频换错对象 -->
          <div class="ori-elements" v-if="adv.mode === 'replace'">
            <div class="oe-title">
              AI 从原片找到可替换的对象
              <span v-if="elementsLoading" class="oe-loading">检测中…</span>
              <span v-else-if="!originalElements.length" class="oe-empty">（未检测到或暂不可用，可只按角色替换）</span>
            </div>
            <div class="oe-list" v-if="originalElements.length">
              <div v-for="e in originalElements" :key="e.id" class="oe-chip" :class="e.kind">
                <span class="oe-kind">{{ { person: '人物', product: '产品', scene: '场景' }[e.kind] }}</span>
                <span class="oe-label">{{ e.label }}</span>
                <span class="oe-time" v-if="e.start != null && e.end != null && e.end - e.start > 0.1">@{{ e.start }}~{{ e.end }}s</span>
                <span class="oe-time" v-else-if="e.time != null">@{{ e.time }}s</span>
              </div>
            </div>
          </div>
          <div class="thumbs">
            <div v-for="(u, i) in productImages" :key="u" class="thumb-wrap">
              <div class="thumb">
                <img :src="u" alt="替换素材" />
                <span class="del" @click="removeProduct(u)">×</span>
                <div class="role-sel" v-if="adv.mode === 'replace'">
                  <span v-if="aiLoading[u]" class="ai-tag loading">识别中…</span>
                  <template v-else>
                    <span :class="['r', { on: imageRoles[u] === 'product' }]" @click="setRole(u, 'product')">产品</span>
                    <span :class="['r', { on: imageRoles[u] === 'person' }]" @click="setRole(u, 'person')">人物</span>
                    <span :class="['r', { on: imageRoles[u] === 'scene' }]" @click="setRole(u, 'scene')">场景</span>
                    <span v-if="aiTagged[u] && imageRoles[u]" class="ai-tag">AI 已识别</span>
                  </template>
                </div>
              </div>
              <div class="role-hint" v-if="adv.mode === 'replace' && !aiLoading[u] && !imageRoles[u]">
                这张图是产品 / 人物 / 场景?点一下告诉系统替换原片里的哪个
              </div>
              <!-- 绑定到原片元素:角色选好后,若原片检测到同类元素,则让用户指定"替换原片中的哪一个" -->
              <div class="slot-sel" v-if="adv.mode === 'replace' && imageRoles[u] && slotOptionsFor(u).length">
                <span class="slot-label">替换原片中的：</span>
                <select :value="imageSlot[u] || ''" @change="imageSlot[u] = $event.target.value">
                  <option value="">不指定（按角色整体替换）</option>
                  <option v-for="o in slotOptionsFor(u)" :key="o.id" :value="o.id">
                    {{ o.label }}（@{{ o.time }}s）
                  </option>
                </select>
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
          <div class="sub" v-if="adv.mode === 'replace'">每张图点一下是产品 / 人物 / 场景，系统就知道替换原片里的对应对象；不点也会按画面自动判断。</div>
          <div class="sub" v-else>参考图仅作风格 / 构图 / 运镜参考,不会替换原片元素;上传越贴近目标风格的画面,成片越贴近你的预期。</div>
          <div class="note">
            当前视频供应商不接受真人照片作为成片素材。选择“换人物”并上传本人照片，照片可能被移除，最终只按文字描述生成非本人角色，无法实现本人替换。
            可改用插画/虚拟形象图、用文字描述角色，或选择换产品/换场景；如需真人口播，可使用
            <router-link to="/digital">平台数字人形象</router-link>（不是本人克隆）。
          </div>
        </div>

        <!-- 素材缺失引导:结构化展示"缺什么/为什么/怎么补",点「去补」直接定位到上传区 -->
        <div v-if="missing.length" class="missing-box">
          <div class="mb-title">还差这几样就能出片</div>
          <div v-for="m in missing" :key="m.field" class="mb-item">
            <div class="mb-text">
              <b>{{ m.label }}</b>
              <span>{{ m.why }}</span>
              <i>{{ m.hint }}</i>
            </div>
            <div class="mb-btn" @click="goFix(m.action)">去补</div>
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
      <section v-if="deconstructing || deconstructPending || shots.length || deconstructError" ref="shotsCardRef" class="card">
        <div class="step"><b>2</b> 拆解分镜(可编辑描述后生成)</div>
        <div v-if="deconstructing || deconstructPending" class="loading">
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
            <img v-if="s.frame" :src="s.frame" class="shot-frame" alt="镜头画面" />
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

      <!-- 视频文案:拆解后由后端自动产出建议文案(编排对前端透明,用户无感),仅作可修改的参考 -->
      <section v-if="shots.length" class="card">
        <div class="step">视频文案</div>
        <div class="sub">系统已根据对标视频生成建议文案,可直接修改;觉得不够贴合时点「润色」。</div>
        <div v-if="prepCopy" class="prep">
          <div class="prep-block">
            <div class="prep-title">文案（可直接修改）</div>
            <div class="prep-field"><b>大标题</b><n-input v-model:value="prepCopy.title" :maxlength="20" placeholder="大标题" /></div>
            <div class="prep-field"><b>副标题</b><n-input v-model:value="prepCopy.subtitle" :maxlength="30" placeholder="副标题" /></div>
            <div class="prep-field"><b>口播</b><n-input v-model:value="prepCopy.script" type="textarea" :rows="3" :maxlength="200" placeholder="口播文案" /></div>
            <div class="prep-field" v-if="prepCopy.subject"><b>主体</b><n-input v-model:value="prepCopy.subject" :maxlength="40" placeholder="主体" /></div>
            <div class="prep-field" v-if="prepCopy.demand"><b>画面要求</b><n-input v-model:value="prepCopy.demand" type="textarea" :rows="2" :maxlength="200" placeholder="画面要求" /></div>
          </div>
          <n-alert v-if="prepQualityWarn" type="warning" :title="'内容质量提示'" style="margin:0 0 8px">{{ prepQualityWarn }}</n-alert>
          <div class="actions">
            <label class="agent-toggle" title="开启后改用工具调用式智能体编排(实验):模型自主选择调用技能,效果可能不稳定">
              <n-switch v-model:value="agentMode" size="small" />
              <span>智能体编排(实验)</span>
            </label>
            <n-button size="small" secondary type="primary" :loading="polishing" @click="polishCopy">
              {{ polishing ? '润色中…' : '润色' }}
            </n-button>
            <n-button size="small" secondary :loading="prepLoading" @click="runPrep">
              {{ prepLoading ? '生成中…' : '重新生成' }}
            </n-button>
            <n-button size="small" secondary type="primary" @click="applyPrep">应用到出片</n-button>
          </div>
        </div>
        <div v-else class="sub" style="margin-top:0">正在生成建议文案…</div>
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
            {{ submitting ? submitHint : (hasCredit ? '生成复刻视频' : `去支付 ¥${price} 生成`) }}
          </n-button>
        </div>
      </section>

      <!-- 平台模板选择:模板替换属于复刻,选中后直接作为对标视频预填 -->
      <n-modal
        v-model:show="tplPickerVisible"
        preset="card"
        title="选择平台模板"
        style="max-width: 720px; border-radius: 16px"
      >
        <div class="sub" style="margin-top:0;margin-bottom:12px">
          选一个平台模板作为对标视频,成片会按它的结构来,你只需上传替换参考图。
        </div>
        <TemplatePicker @pick="onPickTemplate" />
      </n-modal>

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
.hero h1 { font-size: 22px; font-weight: 700; margin: 0 0 8px; color: var(--ink); }
.hero p { font-size: 13px; color: var(--weak); margin: 0; }
/* 三步流程引导条:让用户一眼看懂操作顺序 */
.guide { display: flex; align-items: center; justify-content: center; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
.guide .g { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: var(--body-c); background: var(--bg); border: 1px solid var(--line); border-radius: 18px; padding: 5px 12px; }
.guide .g b { display: inline-flex; width: 18px; height: 18px; border-radius: 50%; background: var(--brand); color: #fff; align-items: center; justify-content: center; font-size: 12px; }
.guide .arrow { color: var(--weak); font-size: 14px; }
/* 意图动态说明、按钮引导、拆解空描述引导 */
.intent-hint { font-size: 12px; color: var(--weak); margin-top: 8px; line-height: 1.5; }
.btn-tip { font-size: 12px; color: var(--weak); }
.shot-tip { font-size: 12px; color: var(--warning); background: var(--warning-bg); border: 1px solid #F7D6B0; border-radius: var(--radius-xs); padding: 8px 10px; line-height: 1.5; margin-bottom: 14px; }
/* 部分镜头未逆推成功:与 .shot-tip 同色系(可继续但要人工补),区别于失败的红色 .deconstruct-error */
.deconstruct-note { font-size: 12px; color: var(--warning); background: var(--warning-bg); border: 1px solid #F7D6B0; border-radius: var(--radius-xs); padding: 8px 10px; line-height: 1.5; margin-bottom: 12px; }
.card { background: #fff; border-radius: var(--radius); padding: 20px; margin-bottom: 16px; }
.step { font-size: 15px; font-weight: 600; color: var(--ink); margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.step b { display: inline-flex; width: 22px; height: 22px; border-radius: 50%; background: var(--brand); color: #fff; align-items: center; justify-content: center; font-size: 13px; }
.field { margin-bottom: 18px; }
.lbl { font-size: 14px; font-weight: 500; margin-bottom: 8px; color: var(--ink); }
.req { color: var(--danger); font-style: normal; }
.sub { font-size: 12px; color: var(--weak); margin-top: 8px; }
.note { font-size: 12px; color: var(--warning); background: var(--warning-bg); border: 1px solid #F7D6B0; border-radius: var(--radius-xs); padding: 8px 10px; margin-top: 8px; line-height: 1.5; }
.row { display: flex; align-items: center; gap: 12px; }
.name { font-size: 13px; color: var(--body-c); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* 对标视频预览:上传成功即可播放,确认内容与画幅后再拆解 */
.video-preview { width: 100%; max-height: 320px; display: block; margin-top: 10px; border-radius: var(--radius-sm); border: 1px solid var(--line); background: #000; object-fit: contain; }
.thumbs { display: flex; flex-wrap: wrap; gap: 10px; }
.thumb { position: relative; width: 72px; height: 72px; border-radius: var(--radius-xs); overflow: hidden; border: 1px solid var(--line); }
.thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.thumb .del { position: absolute; top: 2px; right: 4px; color: #fff; background: rgba(0,0,0,.5); border-radius: 50%; width: 16px; height: 16px; line-height: 16px; text-align: center; font-size: 12px; cursor: pointer; }
.thumb .role-sel { position: absolute; left: 0; right: 0; bottom: 0; display: flex; gap: 2px; padding: 2px; background: rgba(0, 0, 0, 0.55); }
.thumb .role-sel .r { flex: 1; text-align: center; font-size: 10px; line-height: 15px; color: #cbd5e1; cursor: pointer; border-radius: 3px; user-select: none; }
.thumb .role-sel .r:hover { color: #fff; }
.thumb .role-sel .r.on { background: var(--brand); color: #fff; }
/* 已标注角色统计:让用户一眼看清人/物/景映射是否齐全 */
.role-summary { font-size: 12px; color: var(--brand); margin-bottom: 8px; }
/* 原片元素槽位面板:检测出的可替换元素,引导用户把上传图精确绑定到原片具体对象 */
.ori-elements { margin-bottom: 12px; border: 1px dashed var(--line); border-radius: var(--radius-sm); padding: 10px 12px; background: var(--bg); }
.oe-title { font-size: 13px; font-weight: 600; color: var(--ink); margin-bottom: 8px; }
.oe-loading, .oe-empty { font-size: 12px; font-weight: 400; color: var(--weak); margin-left: 6px; }
.oe-list { display: flex; flex-wrap: wrap; gap: 8px; }
.oe-chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 14px; background: #fff; border: 1px solid var(--line); font-size: 12px; }
.oe-chip .oe-kind { font-size: 11px; padding: 1px 6px; border-radius: 8px; color: #fff; }
.oe-chip.person .oe-kind { background: #3b82f6; }
.oe-chip.product .oe-kind { background: #f59e0b; }
.oe-chip.scene .oe-kind { background: #10b981; }
.oe-chip .oe-label { color: var(--ink); }
.oe-chip .oe-time { color: var(--weak); font-size: 11px; }
/* 逐图绑定到原片元素:角色选好后出现的下拉,把"我的图"对应到"原片哪个对象" */
.slot-sel { display: flex; align-items: center; gap: 4px; max-width: 180px; }
.slot-sel .slot-label { font-size: 11px; color: var(--weak); white-space: nowrap; }
.slot-sel select { flex: 1; min-width: 0; font-size: 11px; padding: 3px 4px; border: 1px solid var(--line); border-radius: 6px; background: #fff; color: var(--body-c); }
/* 每张图外层列容器:缩略图 + 未标注提示,提示不再被固定尺寸裁切 */
.thumb-wrap { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.thumb-wrap .role-hint { font-size: 11px; color: #e0533d; text-align: center; max-width: 72px; line-height: 1.3; }
/* AI 预识别标记:覆盖在角色条内,命中显示绿标,识别中显示灰标 */
.thumb .role-sel .ai-tag { flex: 1; text-align: center; font-size: 9px; line-height: 15px; color: #fff; background: rgba(34,197,94,.9); border-radius: 3px; }
.thumb .role-sel .ai-tag.loading { background: rgba(0,0,0,.6); color: #ffe; }
.add { width: 72px; height: 72px; border: 1.5px dashed #d6d9de; border-radius: var(--radius-xs); display: flex; align-items: center; justify-content: center; color: var(--weak); font-size: 13px; cursor: pointer; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip { padding: 7px 16px; border-radius: 18px; background: var(--bg); font-size: 13px; color: var(--body-c); cursor: pointer; border: 1.5px solid transparent; user-select: none; }
.chip.on { background: var(--brand-bg); color: var(--brand); border-color: var(--brand); font-weight: 600; }
.actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
/* 智能体编排(实验)开关:与按钮同排,弱化配色,提示其为不稳定实验能力 */
.agent-toggle { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: var(--weak); cursor: pointer; }
.est { font-size: 13px; color: var(--body-c); }
/* 素材缺失引导:与"失败红框"区分,用中性提示色,重点是给用户可执行的一步 */
.missing-box { border: 1px solid #F7D6B0; background: var(--warning-bg); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 14px; }
.mb-title { font-size: 13px; font-weight: 700; color: var(--warning); margin-bottom: 8px; }
.mb-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-top: 1px dashed #F7D6B0; }
.mb-item:first-of-type { border-top: none; }
.mb-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.mb-text b { font-size: 13px; color: var(--ink); }
.mb-text span { font-size: 12px; color: var(--warning); line-height: 1.5; }
.mb-text i { font-size: 12px; color: var(--weak); font-style: normal; }
.mb-btn { flex-shrink: 0; height: 32px; padding: 0 16px; border-radius: 16px; background: var(--brand); color: #fff; font-size: 13px; font-weight: 600; display: flex; align-items: center; cursor: pointer; }
@media (max-width: 768px) {
  .mb-item { flex-direction: column; align-items: stretch; }
  .mb-btn { justify-content: center; }
}
/* 拆解进行中的整页进度视图:与生成页(Generate.vue 的 .center)一致的转圈 + 阶段反馈。
   .is-deconstructing 期间隐藏其余步骤(表单/分镜/生成),拆解完成后自动恢复为正常页面。 */
.wrap.is-deconstructing > *:not(.dc-progress) { display: none; }
.dc-progress { min-height: 58vh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px; text-align: center; padding: 40px 20px; }
.dc-spin { animation: dcspin 2.4s linear infinite; }
@keyframes dcspin { to { transform: rotate(360deg); } }
.dc-title { font-size: 16px; font-weight: 700; color: var(--ink); }
.dc-sub { font-size: 13px; color: var(--weak); }
.dc-pbar { width: 100%; max-width: 420px; height: 8px; border-radius: 4px; background: #F0F1F3; overflow: hidden; }
.dc-pbar i { display: block; height: 100%; width: 40%; border-radius: 4px; background: var(--brand); animation: dcflow 1.6s ease-in-out infinite; }
@keyframes dcflow { 0% { margin-left: -40%; } 100% { margin-left: 100%; } }
.dc-steps { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 6px; font-size: 12px; }
.dc-steps .done { color: var(--brand); font-weight: 700; }
.dc-steps .doing { color: var(--brand); font-weight: 700; }
.dc-steps .todo, .dc-steps .sep { color: #C9CCD1; }
.dc-elapsed { font-size: 12px; color: var(--weak); }
.loading { display: flex; align-items: center; gap: 10px; font-size: 14px; color: var(--body-c); padding: 12px 0; }
/* 拆解已耗时提示:弱化颜色,与主提示区分 */
.loading .elapsed { font-size: 12px; color: var(--weak); }
/* 拆解空结果/失败:持久可见的警示条 + 重试按钮,替代一闪而过的 toast */
.deconstruct-error { display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 13px; color: var(--warning); background: var(--warning-bg); border: 1px solid #F7D6B0; border-radius: var(--radius-xs); padding: 10px 12px; line-height: 1.5; }
.shots { display: flex; flex-direction: column; gap: 14px; }
.shot { border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 12px; }
.shot-head { display: flex; align-items: center; gap: 10px; font-size: 13px; margin-bottom: 8px; }
.idx { font-weight: 600; color: var(--ink); }
.time { color: var(--weak); }
/* 时间码可点击:跳到原片该镜头起点做逐镜核对(下划线提示可交互) */
.time-link { cursor: pointer; text-decoration: underline dotted; }
.time-link:hover { color: var(--brand); }
/* 时长微调:靠右,只改结束时间(起点不动,避免与相邻镜头重叠或留空) */
.dur { display: inline-flex; align-items: center; gap: 4px; margin-left: auto; color: var(--weak); }
.dur .unit { font-size: 12px; }
/* 专家模式折叠头:整行可点击展开,默认收起 */
.expert-head { display: flex; align-items: center; justify-content: space-between; cursor: pointer; margin-bottom: 8px; }
.lbl-inline { font-size: 14px; font-weight: 500; color: var(--ink); }
.expert-head .caret { font-size: 12px; color: var(--brand); }
.expert-body { border: 1px dashed var(--line); border-radius: var(--radius-xs); padding: 10px; }
.narration { font-size: 12px; color: var(--body-c); background: var(--bg); border-radius: var(--radius-xs); padding: 6px 8px; margin-bottom: 8px; }
.shot-frame { width: 100%; max-width: 180px; height: 100px; object-fit: cover; border-radius: var(--radius-xs); border: 1px solid var(--line); display: block; margin-bottom: 8px; }
/* 无额度时的支付提示 */
.pay-tip { color: var(--brand); margin-left: 8px; }
/* 收银台 */
.pay { width: 311px; background: #fff; border-radius: var(--radius-xl); padding: 24px; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.pay h3 { margin: 0; font-size: 18px; }
.pay-amount { font-size: 28px; font-weight: 700; color: var(--brand); }
.pay-qr { width: 220px; height: 220px; border-radius: var(--radius-xs); border: 1px solid var(--line); }
.pay-mock-btn { width: 100%; height: 46px; border-radius: 23px; border: none; background: var(--brand); color: #fff; font-size: 15px; font-weight: 700; cursor: pointer; font-family: inherit; }
.pay-mock-btn:disabled { background: #DCDFE4; cursor: not-allowed; }
.pay-close { font-size: 13px; color: var(--weak); cursor: pointer; margin-top: 4px; }
/* AI 内容准备(技能流)产物预览:紧凑卡片,弱化配色与拆解/失败提示区分 */
.prep { margin-top: 14px; display: flex; flex-direction: column; gap: 12px; }
.prep-block { border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 12px; background: var(--bg); }
.prep-title { font-size: 13px; font-weight: 600; color: var(--ink); margin-bottom: 8px; }
/* AI 文案字段:标签 + 可编辑输入,纵向排列,便于逐字段修改与 AI 润色 */
.prep-field { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 8px; }
.prep-field > b { flex-shrink: 0; width: 56px; color: var(--weak); font-weight: 500; padding-top: 6px; }
.prep-field .n-input { flex: 1; }
/* 小屏:操作区改为上下排列 + 按钮占满宽度,避免按钮与提示文字并排挤压换行 */
@media (max-width: 768px) {
  .card { padding: 16px; }
  .actions { flex-direction: column; align-items: stretch; gap: 10px; }
  .actions .n-button { width: 100%; }
  .btn-tip { line-height: 1.5; }
}
</style>
