<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import QRCode from 'qrcode'
import api from '@/api'
import { uploadFile } from '@/api/model/common'
import { takeRefSource, clearRefSource } from '@/utils/video'
import { useUserStore } from '@/store/modules/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const template = ref(null)
const loading = ref(true)
const submitting = ref(false)
const confirmVisible = ref(false)

// 定价(来自后端业务配置,可在管理端修改)
const price = ref('9.90')

// 收银台
const payVisible = ref(false)
const payOrder = ref(null)          // { order_no, amount, gateway, code_url, mock }
const qrDataUrl = ref('')
const paying = ref(false)
let pollTimer = null

// 素材表单(按原型:产品图 / 大标题 / 副标题 / 口播文案 / Logo)
const productUrl = ref('')
const title = ref('')
const subtitle = ref('')
const script = ref('')
const logoUrl = ref('')
const logoOn = ref(false)

// 「上传参考做」抽出的参考画面:多于 1 张时作为多图参考素材,走参考生视频(r2v)
const refFrames = ref([])
// 用户上传的参考视频地址:预览区优先播放它,而不是模板的示例视频
const refVideoUrl = ref('')
// 画面要求(选填):如"把视频里的人换成我上传的商品图主体"。
// 不带字段前缀 → 后端归入 extra 并拼进提示词的[补充要求]段,不会被当成口播念出来。
const extraDemand = ref('')

// AI 草稿(替代已隐藏的「AI 写文案」按钮):
// 上传参考图后自动识别主体并生成 大标题/副标题/口播/画面要求 草稿,预填到表单供用户修改。
const aiDrafting = ref(false)
// AI 是否已预填过文案:用于识别"用户把预填文案删光了"(删空要提示,否则成片没字幕/口播却不自知)
const aiDrafted = ref(false)
// 用户是否手改过某字段:手改过的字段不再被 AI 草稿覆盖
const touched = ref({ title: false, subtitle: false, script: false, extra: false })

// 替换意图(多选 A 方案):product=换产品 / person=换人物 / scene=换场景;空=参考生视频(以图为主体)
const intent = ref([])
// 人物参考图 / 场景参考图(仅在对应意图勾选时出现并上传)
const personUrl = ref('')
const sceneUrl = ref('')
// 一键三换:用户用「同一张图」同时替换产品/人物/场景时的那张图(三个框共用同一地址)
const tripleUrl = ref('')
// 逐图中立识别出的真实主体类型(role→type,role∈person/product/scene):
// 校验用户标的"人物/产品/场景"是否名副其实(狗标人物→other),生成前强提示
const materialTypes = ref({})

// —— 生成规格(时长/画幅/清晰度)——
// 选项与当前生效值均来自 /estimate(后端 gen_rules 是唯一定义处):
// 此前规格全部由模板时长与系统配置写死,用户无从选择,是与成熟产品差距最大的一项。
const genOptions = ref({ durations: [], ratios: [], resolutions: [] })
const selDuration = ref(null)
const selRatio = ref('')
const selResolution = ref('')
// 下单前可见花费(与实扣同源)、预计耗时、视频编辑能力是否可用
const estCost = ref(null)
const estSeconds = ref(0)
const editAvailable = ref(true)
// 用户在确认弹窗中选择"去掉参考视频继续生成"时置真:doGenerate 据此丢弃参考视频,
// 使"用户看到的提示"与"实际提交的素材"一致(而不是提示了却照旧提交)。
const dropRefVideo = ref(false)

// 本次是否会提交参考视频:用户上传的(含人物复刻),或勾选替换意向后回退用的模板示例视频。
// 与 doGenerate 的组装逻辑保持一致,否则"能力校验"与"实际提交"会错位。
const hasRefVideo = computed(() =>
  !!refVideoUrl.value || (intent.value.length > 0 && !!template.value?.video_url)
)

// 预计耗时文案:与后端 TASK_PROFILES 同源(此前前端写死"约 2 分钟",后端是 300 秒,自相矛盾)
const estSecondsText = computed(() => {
  const s = estSeconds.value
  if (!s) return '预计生成约 2 分钟'
  if (s < 60) return `预计生成约 ${s} 秒`
  return `预计生成 ${Math.ceil(s / 60)} 分钟内完成`
})
// 本次消耗额度文案:与后端 cost_rules 同源(此前写死"消耗 1 次",附加计费无法体现)
const estCostText = computed(() => `消耗 ${estCost.value ?? 1} 次`)

// 画幅是否可选:带参考视频时成片画幅由模型自适应(方舟编辑任务只认 ratio=adaptive),
// 用户再选画幅也不会生效 —— 置灰并提示,避免"选了却没效果"的错觉。
const ratioSelectable = computed(() => !hasRefVideo.value || dropRefVideo.value)
function pickRatio(r) {
  if (!ratioSelectable.value) return
  selRatio.value = r
}

// 预估花费/规格选项:金额、预计耗时、可选规格,以及"带参考视频时视频编辑能力是否可用"
// 都在这里一次取回。失败不阻断下单(以下单时后端计算结果为准)。
async function refreshEstimate() {
  try {
    const res = await api.task.estimate.post({
      type: 'video',
      template_id: Number(route.params.id),
      duration: selDuration.value || undefined,
      ratio: selRatio.value || undefined,
      resolution: selResolution.value || undefined,
      has_reference_video: hasRefVideo.value,
    })
    if (res.code === 1 && res.data) {
      const d = res.data
      estCost.value = d.cost
      estSeconds.value = d.estimate_seconds || 0
      editAvailable.value = d.edit_available !== false
      if (d.options) genOptions.value = d.options
      // 首次拿回规格时按后端生效值回填选中项,保证"页面显示的就是实际下发的"
      if (!selDuration.value && d.gen_duration) selDuration.value = d.gen_duration
      if (!selRatio.value && d.gen_ratio) selRatio.value = d.gen_ratio
      if (!selResolution.value && d.gen_resolution) selResolution.value = d.gen_resolution
    }
  } catch (e) { /* 预估失败静默,不阻断下单 */ }
}

// 是否有任意可生成的素材(产品图/人物图/场景图/参考画面/参考视频任一即可)
const hasAnyMaterial = computed(() =>
  !!productUrl.value || !!personUrl.value || !!sceneUrl.value ||
  refFrames.value.length > 0 || !!refVideoUrl.value
)
const canGenerate = computed(() => hasAnyMaterial.value && !!title.value.trim())
// AI 预填过、但现在被清空 → 提示用户(不修改=原样保留;删掉了就要提醒)
const copyEmptied = computed(() =>
  aiDrafted.value && (!title.value.trim() || !script.value.trim())
)

async function loadDetail() {
  loading.value = true
  try {
    const res = await api.template.detail.post({ id: Number(route.params.id) })
    if (res.code === 1) {
      template.value = res.data
      // 刻意**不预填模板默认文案**:模板文案绑定原品类(如"洗发水"),
      // 用户换成别的品类时会把原品类直接串进口播与字幕。
      // 文案统一由「上传参考图 → 识别生成草稿 → 用户确认/修改」得到，
      // 点击生成时严格以用户确认的那份为准。
    }
  } catch (e) { /* 拦截器已提示 */ }
  loading.value = false
  // 模板加载完成后取一次预估:此时 template.video_url 已知,
  // has_reference_video 才能准确判断"视频编辑能力是否必需"。
  refreshEstimate()
}

function beforeUpload(data, type) {
  const imgExts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
  const ext = (data.file.name || '').split('.').pop().toLowerCase()
  if (!imgExts.includes(ext)) {
    window.$message?.error('仅支持图片格式')
    return false
  }
  if (data.file.file.size > 50 * 1024 * 1024) {
    window.$message?.error('文件大小不能超过50MB')
    return false
  }
  return true
}

function makeUploader(setter, tip) {
  return async function customRequest({ file, onFinish, onError, onProgress }) {
    try {
      const url = await uploadFile(file.file, {
        onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) })
      })
      setter(url)
      onFinish()
      window.$message?.success(tip)
    } catch (e) { onError() }
  }
}
// 产品图与参考视频的抽帧画面**并存**,不做替换:
// 视频编辑需要的正是「参考视频 + 商品图 + 新台词」三者,清掉任何一个都会让效果打折。
// (旧实现把"上传产品图"当成替换素材的信号,导致参考画面被清空、只剩模板示例视频)
const uploadProduct = makeUploader(v => { productUrl.value = v; ensureIntent('product'); autoDraftFromImage(v) }, '产品图已上传')
const uploadLogo = makeUploader(v => { logoUrl.value = v }, 'Logo 已上传')
const uploadPerson = makeUploader(v => { personUrl.value = v; ensureIntent('person'); autoDraftFromImage(v) }, '人物参考图已上传')
const uploadScene = makeUploader(v => { sceneUrl.value = v; ensureIntent('scene'); autoDraftFromImage(v) }, '场景参考图已上传')
// 一键三换:选一张图,同时作为产品/人物/场景的替换来源(三个框共用同一地址)。
// 后端按该图在 materials 中出现的位置依次取 product/person/scene 角色,避免字典按 URL 去重丢维度。
const uploadTriple = makeUploader(v => {
  tripleUrl.value = v
  productUrl.value = v
  personUrl.value = v
  sceneUrl.value = v
  intent.value = ['product', 'person', 'scene']
  autoDraftFromImage(v)
}, '已用同一张图作为产品/人物/场景替换来源')

// 参考视频直传入口:「换人物」强校验要求用户提供自己的参考视频(含人物),
// 但本页此前只能经「上传参考做」带入,校验在当前页无解,用户会一直被拦截。
// 扩展名与 50MB 大小口径与后端 ALLOWED_EXTENSIONS / MAX_SIZE 保持一致。
function beforeVideoUpload(data) {
  const videoExts = ['mp4', 'mov', 'm4v', 'webm']
  const ext = (data.file.name || '').split('.').pop().toLowerCase()
  if (!videoExts.includes(ext)) {
    window.$message?.error('仅支持视频格式(mp4/mov/m4v/webm)')
    return false
  }
  if (data.file.file && data.file.file.size > 50 * 1024 * 1024) {
    window.$message?.error('视频大小不能超过50MB')
    return false
  }
  return true
}
const uploadRefVideo = makeUploader(v => { refVideoUrl.value = v }, '参考视频已上传,生成时将按它替换出镜人物并还原时长')

// 当前已上传且"参与替换"的素材图(带角色):只在对应替换意图被选中时才统计,
// 避免取消某维度后,其已上传的图仍被写进 demand/识别结果(与"按 intent 决定是否替换"保持一致)。
// 人物图 + 产品图要**一起**送去识别,才能"结合人物与产品"生成文案(只送一张会漏掉另一半信息)。
function draftSubjects() {
  const images = []
  const roles = []
  if (intent.value.includes('product') && productUrl.value) { images.push(productUrl.value); roles.push('product') }
  if (intent.value.includes('person') && personUrl.value) { images.push(personUrl.value); roles.push('person') }
  if (intent.value.includes('scene') && sceneUrl.value) { images.push(sceneUrl.value); roles.push('scene') }
  return { images, roles }
}

// 依据当前已上传的替换素材图(产品/人物/场景)重新生成「画面要求」等草稿并预填到表单。
// 抽成独立函数:上传图片、切换替换意图芯片、增删素材时都复用它,保证 demand 始终跟手。
// 不把模板原配文案当草稿传进去:那会带出模板品类(如洗发水),与刚上传的新品类冲突,
// 所以「未手改」时只传图,让模型完全依据画面从零创作(对应后端 VISION_HINT_NO_DRAFT)。
async function regenerateDemand() {
  if (aiDrafting.value) return
  const { images, roles } = draftSubjects()
  if (!images.length) return   // 没有可识别的素材图时不触发,避免无意义的空请求
  aiDrafting.value = true
  try {
    const res = await api.common.copyGenerate.post({
      template_title: template.value?.title || '',
      category: template.value?.category || '',
      title: touched.value.title ? title.value.trim() : undefined,
      subtitle: touched.value.subtitle ? subtitle.value.trim() : undefined,
      script: touched.value.script ? script.value.trim() : undefined,
      images,
      // 角色与 images 一一对应,帮模型少猜一次(顺序即 draftSubjects 的 push 顺序)
      roles,
      with_demand: true,
    })
    if (res.code === 1 && res.data) {
      const d = res.data
      if (!touched.value.title && d.title) title.value = d.title
      if (!touched.value.subtitle && d.subtitle) subtitle.value = d.subtitle
      if (!touched.value.script && d.script) script.value = d.script
      if (!touched.value.extra && d.demand) extraDemand.value = d.demand
      if (d.title || d.script) aiDrafted.value = true
      // 逐图中立识别类型:校验用户标的"人物/产品/场景"是否名副其实(狗标人物→other)
      if (d.material_types) materialTypes.value = d.material_types
      const what = d.subject ? `识别到「${d.subject}」,` : ''
      // 只有真正用了视觉(vision=true)才说"结合素材图";未识别到画面时别误导用户以为看过了图
      const combined = (d.vision && images.length > 1) ? `已结合 ${images.length} 张素材图生成文案,` : ''
      window.$message?.success(
        d.fallback ? 'AI 暂不可用,已填入推荐文案,可手动修改'
          : `${what}${combined}已生成文案与画面要求,可手动修改`
      )
    }
  } catch (e) { /* 拦截器已提示 */ }
  aiDrafting.value = false
}

// 上传参考图 → 识别主体 → 大模型生成草稿 → 预填到表单(不覆盖用户手改过的字段)。
// 上传回调里 setter 已先行,故 draftSubjects() 已含刚上传的图,直接复用 regenerateDemand。
async function autoDraftFromImage(url) {
  if (!url) return
  await regenerateDemand()
}

// 参考视频入口(多张画面)自动生成草稿:与上传参考图体验一致,只是直接用参考画面作为识别图。
// 单独抽出是为了不与「单图上传要合并全部主体图」的 draftSubjects 逻辑混在一起。
async function autoDraftFromImages(images) {
  if (!images?.length || aiDrafting.value) return
  aiDrafting.value = true
  try {
    const res = await api.common.copyGenerate.post({
      template_title: template.value?.title || '',
      category: template.value?.category || '',
      title: touched.value.title ? title.value.trim() : undefined,
      subtitle: touched.value.subtitle ? subtitle.value.trim() : undefined,
      script: touched.value.script ? script.value.trim() : undefined,
      images,
      with_demand: true,
    })
    if (res.code === 1 && res.data) {
      const d = res.data
      if (!touched.value.title && d.title) title.value = d.title
      if (!touched.value.subtitle && d.subtitle) subtitle.value = d.subtitle
      if (!touched.value.script && d.script) script.value = d.script
      if (!touched.value.extra && d.demand) extraDemand.value = d.demand
      if (d.title || d.script) aiDrafted.value = true
      // 只有真正用了视觉(vision=true)才说"结合参考画面";未识别到画面时别误导用户
      const combined = (d.vision && images.length > 1) ? `已结合 ${images.length} 张参考画面生成文案,` : ''
      window.$message?.success(
        d.fallback ? 'AI 暂不可用,已填入推荐文案,可手动修改'
          : `${combined}已生成文案与画面要求,可手动修改`
      )
    }
  } catch (e) { /* 拦截器已提示 */ }
  aiDrafting.value = false
}

// 上传对应素材时自动连带选中该替换意图(如先传了产品图,再想明确"换产品"意图)
function ensureIntent(dim) {
  if (!intent.value.includes(dim)) intent.value = [...intent.value, dim]
}
// 点击意图芯片:切换选中。取消某维度时**只把它移出替换意图**,不再清空已上传的素材图
// (旧实现会直接 productUrl='' 把图删掉,而上传时又自动点亮芯片,导致用户"再点一下切换"时误关芯片、图被清空)。
// 已上传的图保留在对应 ref 里:再次点亮该维度即可恢复;生成时由 doGenerate 按 intent 决定是否下发,不会带无关图。
function toggleIntent(dim) {
  if (intent.value.includes(dim)) {
    intent.value = intent.value.filter(d => d !== dim)
  } else {
    intent.value = [...intent.value, dim]
  }
  // 切换替换意图会改变"要替换哪些元素",素材图随之增减 → 重新生成画面要求预填,让 demand 跟手
  regenerateDemand()
}

// AI 一键写文案(旧入口):有草稿则润色,无草稿则按模板主题从零创作。
// ⚠️ 已按产品决策**从前端入口隐藏**,且不再作为主要机制 ——
// 现由「上传参考图后自动生成草稿并预填」(autoDraftFromImage)替代:
// 区别是后者**以图片识别结果为准**,而这里只按模板主题,带不出新品类。
// 函数保留,便于后续以其它形式恢复。
const aiWriting = ref(false)
async function aiWriteCopy() {
  aiWriting.value = true
  try {
    const res = await api.common.copyGenerate.post({
      template_title: template.value?.title || '',
      category: template.value?.category || '',
      title: title.value.trim() || undefined,
      subtitle: subtitle.value.trim() || undefined,
      script: script.value.trim() || undefined,
      // 参考视频的关键画面:有则图文结合(没填草稿 → 按画面创作;填了草稿 → 图文润色)
      images: refFrames.value.length ? refFrames.value.slice(0, 3) : undefined,
    })
    if (res.code === 1 && res.data) {
      if (res.data.title) title.value = res.data.title
      if (res.data.subtitle) subtitle.value = res.data.subtitle
      if (res.data.script) script.value = res.data.script
      const tip = res.data.fallback
        ? 'AI 暂不可用,已填充推荐文案,可手动微调'
        : (res.data.vision ? 'AI 已结合参考画面生成文案,可手动微调' : 'AI 文案已生成,可手动微调')
      window.$message?.success(tip)
    }
  } catch (e) { /* 拦截器已提示 */ }
  aiWriting.value = false
}

function resetForm() {
  // 清空重填:不再回填模板默认文案(模板文案绑定原品类,会串进成片)
  productUrl.value = ''
  refFrames.value = []
  refVideoUrl.value = ''
  title.value = ''
  subtitle.value = ''
  script.value = ''
  extraDemand.value = ''
  logoUrl.value = ''
  logoOn.value = false
  intent.value = []
  personUrl.value = ''
  sceneUrl.value = ''
  tripleUrl.value = ''
  materialTypes.value = {}
  touched.value = { title: false, subtitle: false, script: false, extra: false }
  aiDrafted.value = false
  clearSavedState()
  window.$message?.success('已清空,重新上传参考图即可生成文案')
}

// 额度优先:登录且剩余额度>0 时直接扣额度生成,不再弹支付;额度为 0 才走单次支付
const hasCredit = computed(() => userStore.isLoggedIn && (userStore.creditTotal ?? 0) > 0)

async function refreshCredits() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await api.account.credits.post()
    if (res.code === 1) userStore.setCreditTotal(res.data.total)
  } catch (e) { /* 静默,以下单时后端校验为准 */ }
}

async function openConfirm() {
  if (!canGenerate.value) return
  // 所选替换意图必须与已上传的对应素材图一一对应:勾了意图却没传图,替换指令不会生效,直接拦截
  const missing = []
  if (intent.value.includes('product') && !productUrl.value) missing.push('产品图')
  if (intent.value.includes('person') && !personUrl.value) missing.push('人物参考图')
  if (intent.value.includes('scene') && !sceneUrl.value) missing.push('场景参考图')
  if (missing.length) {
    window.$message?.warning(`请先上传:${missing.join('、')}`)
    return
  }
  // ②-1 换人物校验:需要一个"参考视频"作为换人的底片。参考视频两类来源,满足任一即可:
  // ① 用户自己上传的(refVideoUrl);② 所选平台模板自带的示例视频(template.video_url)。
  // 二者都没有才是真正无参考视频,v2v 换人无法成立,只能退化成"用人物图直接图生视频",需知情确认。
  // (此前误把平台模板视频也当成"没有参考视频"而弹确认,其实选了带视频的模板即已提供底片,本次修正)
  if (intent.value.includes('person') && !refVideoUrl.value && !template.value?.video_url) {
    const ok = await new Promise((resolve) => {
      window.$dialog?.warning({
        title: '换人物缺少参考视频',
        content: '当前既未上传你自己的参考视频,所选模板也没有示例视频,无法做视频换人(只能改用你上传的人物图直接生成新视频,不替换原片)。上传参考视频或选择带视频的模板后可正常换人。是否仍要继续生成?',
        positiveText: '仍要生成',
        negativeText: '去上传参考视频',
        onPositiveClick: () => resolve(true),
        onNegativeClick: () => resolve(false),
        onClose: () => resolve(false),
      })
    })
    if (!ok) return
  }
  // ⑤ 换产品/换场景:既没上传参考视频、模板也没有示例视频时,替换指令无处生效,
  // 会退化成"用上传图直接生成新视频"。明确告知,别让用户等着看替换效果。
  if (intent.value.length && !refVideoUrl.value && !template.value?.video_url) {
    window.$message?.warning('当前没有可替换的参考视频，将用你上传的图直接生成新视频（不会替换原视频元素）；上传参考视频后才能按所选意图替换')
  }
  // ④ 参考图主体与所标意图不符 → 生成前强提示,确认后才继续。
  // 用中立识别(不带角色提示)判断真实类型,可命中"狗图当人物"等误标。
  const mis = mismatchMaterialType()
  if (mis) {
    const ok = await confirmMaterialType(mis.dim, mis.type)
    if (!ok) return
  }
  // 文案被删空要明确提示(不阻断:用户可能确实不想要口播)
  if (copyEmptied.value) {
    window.$message?.warning('文案已被删除，生成的视频会没有对应字幕/口播，建议先补全')
  }
  // 口播文案缺失提示(非阻断):选了替换意图/有参考素材却没填口播,成片将无字幕/口播。
  // 覆盖两类:① AI 预填失败(网络/模型异常,aiDrafted 未置真)导致用户没看到草稿;
  // ② 只传产品图选换产品意图、未走参考图流程,AI 从未预填过。
  // 纯模板生成(无意图、无参考素材)不提示,避免打扰;与 copyEmptied 互斥防止同次重复弹窗。
  if (!copyEmptied.value && !script.value.trim() && (intent.value.length || refVideoUrl.value || refFrames.value.length)) {
    window.$message?.warning('未填写口播文案,生成的视频将没有对应字幕/口播;如需请先补全,或重新上传参考图自动生成文案')
  }
  // 下单前取一次真实预估(费用/耗时/可选规格)与"视频编辑能力是否可用"
  await refreshEstimate()
  // 未启用视频编辑能力却带参考视频:后端会直接拒绝(否则 worker 只能丢弃参考视频,
  // 成片变成"用上传图重画"却显示成功)。这里在下单前明确告知,并把选择权交给用户。
  dropRefVideo.value = false
  if (hasRefVideo.value && !editAvailable.value) {
    const ok = await new Promise((resolve) => {
      window.$dialog?.warning({
        title: '当前无法按参考视频生成',
        content: '系统未启用视频编辑能力,无法替换或复刻参考视频里的内容。可去掉参考视频,直接用你上传的图片生成新视频;或联系管理员开启视频编辑模型。是否去掉参考视频继续生成?',
        positiveText: '去掉参考视频继续',
        negativeText: '取消',
        onPositiveClick: () => resolve(true),
        onNegativeClick: () => resolve(false),
        onClose: () => resolve(false),
      })
    })
    if (!ok) return
    dropRefVideo.value = true
  }
  await refreshCredits()
  confirmVisible.value = true
}

// ④ 参考图主体与所标意图不符时,生成前强提示,用户确认后才继续,
// 避免"狗图当人物"等误标白白消耗一次生成。
const TYPE_CN = { person: '人像', product: '商品', scene: '场景', other: '非标准主体(可能是宠物/物品)' }
const DIM_CN = { person: '人物', product: '产品', scene: '场景' }
// 仅当用户只勾选单一替换意图时校验:多意图下逐图聚合分类会有歧义,软提示会误伤。
function mismatchMaterialType() {
  const dims = intent.value.filter(d => ['person', 'product', 'scene'].includes(d))
  if (dims.length !== 1) return null
  const dim = dims[0]
  const t = materialTypes.value[dim]
  if (!t || t === dim) return null
  // other 仅对"人物"明确提示(狗/宠物);对产品/场景,other 可能是 logo 等合法素材,不打扰
  if (t === 'other') return dim === 'person' ? { dim, type: t } : null
  return { dim, type: t }
}

async function confirmMaterialType(dim, type) {
  return new Promise((resolve) => {
    const dimCn = DIM_CN[dim] || dim
    const typeCn = TYPE_CN[type] || type
    window.$dialog?.warning({
      title: `${dimCn}参考图可能不是${dimCn}`,
      content: `系统识别这张图的主体为「${typeCn}」,并非${dimCn}。用作换${dimCn}参考可能导致效果不可控,是否仍要继续生成?`,
      positiveText: '仍要生成',
      negativeText: '去换图',
      onPositiveClick: () => resolve(true),
      onNegativeClick: () => resolve(false),
      onClose: () => resolve(false),
    })
  })
}

async function doGenerate() {
  confirmVisible.value = false
  submitting.value = true
  try {
    const materials = [...refFrames.value]  // 参考画面(风格参考,非替换目标)
    // 兼容旧行为:没选任何意图时,产品图作为新视频主体(参考生视频)
    if (!intent.value.length && productUrl.value) materials.push(productUrl.value)
    // 按所选意图带上对应素材:三者都选=商品/人物/场景图都提交,后端据此全替换
    if (intent.value.includes('product') && productUrl.value) materials.push(productUrl.value)
    if (intent.value.includes('person') && personUrl.value) materials.push(personUrl.value)
    if (intent.value.includes('scene') && sceneUrl.value) materials.push(sceneUrl.value)
    // 参考视频:优先用用户自己上传的参考视频(上传参考做入口带入)。
    // 仅选模板且勾选了任意替换意图(换产品/人物/场景)时,回退用模板示例视频作为参考视频,
    // 从而进入 v2v 视频编辑模式(否则勾了替换意图却无参考视频会退化成普通图生视频,替换指令不生效)。
    // dropRefVideo:用户在确认弹窗里已同意"去掉参考视频继续生成"(当前未启用视频编辑能力),
    // 此时必须真的不提交它 —— 否则提示与实际提交不一致,后端也会直接拒绝该任务。
    const refVideo = dropRefVideo.value ? '' : (refVideoUrl.value
      || (intent.value.length && template.value?.video_url ? template.value.video_url : ''))
    if (refVideo) materials.push(refVideo)
    if (logoOn.value && logoUrl.value) materials.push(logoUrl.value)
    const remarkParts = []
    if (title.value.trim()) remarkParts.push(`大标题:${title.value.trim()}`)
    if (subtitle.value.trim()) remarkParts.push(`副标题:${subtitle.value.trim()}`)
    if (script.value.trim()) remarkParts.push(`口播文案:${script.value.trim()}`)
    // 画面要求不带字段前缀 → 后端归入 extra,拼进提示词的[补充要求]段(不参与口播)
    if (extraDemand.value.trim()) remarkParts.push(extraDemand.value.trim())
    // 图片地址 → 角色:后端视觉识别据此分组(只让模型自己看图,产品照会被误判成场景,
    // 导致"人物图 + 产品图"没能结合)。同一张图可被同时用作多个维度(一键三换),
    // 用逗号拼接多角色;后端按该图在 materials 图片序列中的出现顺序依次取角色,
    // 避免字典按 URL 去重把 product/person/scene 压成最后一个。
    const imageRoles = {}
    const addRole = (url, role) => {
      if (!url) return
      const k = String(url)
      const cur = imageRoles[k] ? imageRoles[k].split(',') : []
      if (!cur.includes(role)) cur.push(role)
      imageRoles[k] = cur.join(',')
    }
    addRole(productUrl.value, 'product')
    addRole(personUrl.value, 'person')
    addRole(sceneUrl.value, 'scene')
    const payload = {
      template_id: Number(route.params.id),
      materials,
      intent: intent.value,
      image_roles: Object.keys(imageRoles).length ? imageRoles : undefined,
      remark: remarkParts.join(';') || undefined,
      // 规格随单下发:用户选的时长/画幅/清晰度直接生效(后端做白名单与档位吸附兜底)
      duration: selDuration.value || undefined,
      ratio: selRatio.value || undefined,
      resolution: selResolution.value || undefined,
      device: window.innerWidth <= 768 ? 'mobile' : 'desktop'
    }
    // 有额度:直接扣额度创建生成任务,跳生成页
    if (hasCredit.value) {
      const res = await api.task.create.post(payload)
      if (res.code === 1 && res.data) {
        refreshCredits()
        clearRefSource()  // 已下单:清掉暂存,避免下次进来又被带回来
        window.$message?.success(`已扣除 ${estCost.value ?? 1} 次额度,开始生成`)
        router.replace(`/generate/${res.data.id}`)
      }
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
      startPolling(res.data.order_no)
    }
  } catch (e) { /* 拦截器已提示 */ }
  finally { submitting.value = false }
}

// 轮询订单状态,交付成功(3)后跳生成页
function startPolling(orderNo) {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const res = await api.payment.orderStatus.post({ order_no: orderNo })
      if (res.code === 1 && res.data) {
        if (res.data.status === 3 && res.data.task_id) {
          stopPolling()
          payVisible.value = false
          window.$message?.success('支付成功,开始生成')
          router.replace(`/generate/${res.data.task_id}`)
        } else if (res.data.status === 4) {
          stopPolling()
          payVisible.value = false
          window.$message?.warning('订单已超时取消,请重新下单')
        }
      }
    } catch (e) { /* 轮询失败静默重试 */ }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
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
  stopPolling()
  payVisible.value = false
}

async function loadPrice() {
  try {
    const res = await api.payment.genConfig.post()
    if (res.code === 1 && res.data?.['gen.video_price']) price.value = res.data['gen.video_price']
  } catch (e) { /* 用默认定价 */ }
}

// 「上传参考做」带入的参考视频信息:进入本页预填素材并预览原视频
function applyRefFrames() {
  // 只在「上传参考做」进来时应用(?ref=1):从"模板做"进来不该带上一次的参考数据
  if (!route.query.ref) return
  const { frames, videoUrl } = takeRefSource()
  if (!frames.length && !videoUrl) return
  refFrames.value = frames
  refVideoUrl.value = videoUrl
  if (frames.length) {
    window.$message?.success(`已使用参考视频的 ${frames.length} 张画面，可直接生成或重新上传`)
    // 参考视频入口同样自动生成文案草稿,与上传参考图体验一致(否则只能手动写标题才能生成)
    autoDraftFromImages(frames)
  }
}

function clearRefFrames() {
  refFrames.value = []
  refVideoUrl.value = ''
  clearRefSource()
  window.$message?.success('已清除参考画面')
}

// —— 表单状态持久化 ——
// 切路由/刷新会让组件卸载,内存里的 URL ref(含已上传素材的 COS 地址)随之丢失;
// 但图片本身已在 COS,只需记住这些 URL 字符串 + 文案即可恢复,无需重传。
// 按 template id 隔离,sessionStorage 跨刷新/路由保留、关页即清。
const persistRefs = {
  productUrl, personUrl, sceneUrl, tripleUrl,
  refFrames, refVideoUrl,
  title, subtitle, script, extraDemand,
  logoUrl, logoOn, intent, touched, aiDrafted,
  // 规格选择同样持久化:切路由/刷新后保持用户已选的时长/画幅/清晰度
  selDuration, selRatio, selResolution,
}
const PERSIST_KEY = () => `upload_form_${route.params.id}`

function saveState() {
  const id = route.params.id
  if (!id) return
  const snapshot = {}
  for (const k in persistRefs) snapshot[k] = persistRefs[k].value
  try { sessionStorage.setItem(PERSIST_KEY(), JSON.stringify(snapshot)) } catch (e) { /* 忽略 */ }
}
function restoreState() {
  const id = route.params.id
  if (!id) return
  const raw = sessionStorage.getItem(PERSIST_KEY())
  if (!raw) return
  try {
    const snap = JSON.parse(raw)
    for (const k in persistRefs) {
      if (k in snap && snap[k] !== undefined) persistRefs[k].value = snap[k]
    }
  } catch (e) { /* 损坏则忽略,重新来过 */ }
}
function clearSavedState() {
  const id = route.params.id
  if (id) sessionStorage.removeItem(PERSIST_KEY())
}
// 任意表单字段变化即落盘(含上传完成 setter 写入 URL、芯片切换、文案输入)
watch(
  () => Object.keys(persistRefs).map(k => persistRefs[k].value),
  saveState,
  { deep: true },
)

onMounted(() => { restoreState(); loadDetail(); loadPrice(); applyRefFrames(); refreshCredits() })
onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="material-page">
    <n-spin :show="loading">
      <div v-if="template" class="wrap mcols">
        <!-- 左:预览(「上传参考做」进来时优先播用户自己上传的参考视频) -->
        <div class="preview card">
          <div
            class="pv"
            :class="{ 'pv-fit': refVideoUrl || template.video_url }"
            :style="!refVideoUrl && template.cover ? { backgroundImage: `url(${template.cover})` } : {}"
          >
            <video
              v-if="refVideoUrl || template.video_url"
              :key="refVideoUrl || template.video_url"
              :src="refVideoUrl || template.video_url"
              :poster="refVideoUrl ? undefined : template.cover"
              controls
              playsinline
              class="pv-video"
            ></video>
            <template v-else>
              <div class="play">
                <svg width="24" height="24" viewBox="0 0 24 24"><path d="M9 6L18 12L9 18V6Z" fill="#fff"/></svg>
              </div>
            </template>
            <div v-if="!refVideoUrl" class="dur">0:{{ String(template.duration || 15).padStart(2, '0') }}</div>
            <div v-else class="badge-ref">我的参考视频</div>
          </div>
          <div class="pmeta">
            <b>{{ refVideoUrl ? '你的参考视频' : template.title }}</b>
            <span v-if="refVideoUrl">已提取 {{ refFrames.length }} 张画面 · 基于模板「{{ template.title }}」</span>
            <span v-else>{{ template.duration || 15 }}秒 · {{ template.category }}</span>
          </div>
        </div>

        <!-- 右:素材表单 -->
        <div class="form">
          <!-- 替换意图(多选 A 方案):决定"生成时换掉原视频的哪些元素" -->
          <div class="item">
            <div class="lbl">你想替换视频里的什么?(可多选)</div>
            <div class="intent-chips">
              <span :class="['chip', { on: intent.includes('product') }]" @click="toggleIntent('product')">换产品</span>
              <span :class="['chip', { on: intent.includes('person') }]" @click="toggleIntent('person')">换人物</span>
              <span :class="['chip', { on: intent.includes('scene') }]" @click="toggleIntent('scene')">换场景</span>
            </div>
            <div class="sub">都不选＝以你上传的图作为新视频主体(参考生视频);全选＝原视频的商品、人物、场景都换成你的。<br/>换人物需先上传你自己的参考视频(含人物):未上传时将以模板示例短视频为参考,出片时长较短且替换的是示例中的人物</div>
          </div>

          <!-- 一键三换:用同一张图同时替换产品/人物/场景 -->
          <div class="item">
            <div class="row">
              <div>
                <div class="lbl">一键三换(同一张图替换全部)</div>
                <div class="sub">选一张图,同时替换原视频的商品、出镜人物与场景背景;也可在各维度分别上传不同图</div>
              </div>
              <n-upload
                accept="image/*"
                :max="1"
                :show-file-list="false"
                :custom-request="uploadTriple"
                :before-upload="beforeUpload"
              >
                <div class="up" :class="{ gray: tripleUrl }">{{ tripleUrl ? '已上传' : '上传一张图' }}</div>
              </n-upload>
            </div>
          </div>

          <!-- 产品图:勾选「换产品」时出现;未选任何意图时也保留(旧流程:以图为主体参考生视频) -->
          <div v-if="!intent.length || intent.includes('product')" class="item">
            <div class="row">
              <div style="display:flex; gap:12px; align-items:center">
                <div class="thumb">
                  <img v-if="productUrl" :src="productUrl" alt="产品图" />
                  <svg v-else width="30" height="30" viewBox="0 0 30 30"><path d="M15 11V19M15 11L11.5 14.5M15 11L18.5 14.5" fill="none" stroke="#B0B3B8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 21H21" fill="none" stroke="#B0B3B8" stroke-width="1.8" stroke-linecap="round"/></svg>
                </div>
                <div>
                  <div class="lbl">你的产品图</div>
                  <div class="sub">拍照或相册选一张</div>
                </div>
              </div>
              <n-upload
                accept="image/*"
                :max="1"
                :show-file-list="false"
                :custom-request="uploadProduct"
                :before-upload="beforeUpload"
              >
                <div class="up" :class="{ gray: productUrl }">{{ productUrl ? '已上传' : '上传' }}</div>
              </n-upload>
            </div>
          </div>

          <!-- 参考画面(「上传参考做」自动填充,多张时走参考生视频 r2v) -->
          <div v-if="refFrames.length" class="item">
            <div class="row">
              <div class="lbl">参考画面（{{ refFrames.length }} 张）</div>
              <button class="ai-btn" @click="clearRefFrames">清除</button>
            </div>
            <div class="frame-list">
              <img v-for="(f, i) in refFrames" :key="i" :src="f" :alt="`参考画面 ${i + 1}`" />
            </div>
            <div class="sub">将用这些画面作为参考生成，效果更接近原视频</div>
          </div>

          <!-- 换人物:上传人物参考图,后端按意图把视频出镜人物替换成该图 -->
          <div v-if="intent.includes('person')" class="item">
            <div class="row">
              <div style="display:flex; gap:12px; align-items:center">
                <div class="thumb">
                  <img v-if="personUrl" :src="personUrl" alt="人物参考图" />
                  <svg v-else width="30" height="30" viewBox="0 0 30 30"><path d="M15 11V19M15 11L11.5 14.5M15 11L18.5 14.5" fill="none" stroke="#B0B3B8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 21H21" fill="none" stroke="#B0B3B8" stroke-width="1.8" stroke-linecap="round"/></svg>
                </div>
                <div>
                  <div class="lbl">人物参考图</div>
                  <div class="sub">请上传真人/人像照片,系统将替换原视频出镜人物;上传宠物、物品等非人图像会导致换人效果不可控</div>
                </div>
              </div>
              <n-upload
                accept="image/*"
                :max="1"
                :show-file-list="false"
                :custom-request="uploadPerson"
                :before-upload="beforeUpload"
              >
                <div class="up" :class="{ gray: personUrl }">{{ personUrl ? '已上传' : '上传' }}</div>
              </n-upload>
            </div>
            <!-- 换人物提示放在 .row 之外:作为 .row 的 flex 子项时整段按单行撑宽,
                 会把页面撑出横向溢出,导致吸底栏的「生成视频」按钮被推出视口右侧 -->
            <div v-if="!refVideoUrl" class="sub" style="color:#d03050;margin-top:6px">
              未上传参考视频:将基于模板示例短视频复刻,出片时长较短且替换的是示例中的人物;上传你的参考视频(含人物)可还原原片时长与人物
            </div>
            <!-- 参考视频直传入口:让「换人物需先上传参考视频」的校验在当前页可被满足,
                 上传后预览区会自动切换播放该视频(徽标"我的参考视频")并走 v2v 替换流程 -->
            <div v-if="!refVideoUrl" class="row" style="margin-top:10px">
              <div class="sub" style="flex:1; min-width:0; margin-top:0">
                没有参考视频?在这里直接上传(含人物,不超过50MB)
              </div>
              <n-upload
                accept="video/*"
                :max="1"
                :show-file-list="false"
                :custom-request="uploadRefVideo"
                :before-upload="beforeVideoUpload"
              >
                <div class="up">上传参考视频</div>
              </n-upload>
            </div>
          </div>

          <!-- 换场景:上传场景参考图,后端按意图把视频场景/背景替换成该图 -->
          <div v-if="intent.includes('scene')" class="item">
            <div class="row">
              <div style="display:flex; gap:12px; align-items:center">
                <div class="thumb">
                  <img v-if="sceneUrl" :src="sceneUrl" alt="场景参考图" />
                  <svg v-else width="30" height="30" viewBox="0 0 30 30"><path d="M15 11V19M15 11L11.5 14.5M15 11L18.5 14.5" fill="none" stroke="#B0B3B8" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 21H21" fill="none" stroke="#B0B3B8" stroke-width="1.8" stroke-linecap="round"/></svg>
                </div>
                <div>
                  <div class="lbl">场景参考图</div>
                  <div class="sub">想让视频发生的场景/背景长这样</div>
                </div>
              </div>
              <n-upload
                accept="image/*"
                :max="1"
                :show-file-list="false"
                :custom-request="uploadScene"
                :before-upload="beforeUpload"
              >
                <div class="up" :class="{ gray: sceneUrl }">{{ sceneUrl ? '已上传' : '上传' }}</div>
              </n-upload>
            </div>
          </div>

          <div v-if="aiDrafting" class="sub" style="margin-top:8px">AI 正在识别参考图并生成文案与画面要求…</div>
          <div v-if="copyEmptied" class="warn">文案已被删除，生成的视频将没有对应字幕/口播；请补全，或重新上传参考图重新生成文案</div>

          <div class="item">
            <div class="row">
              <div class="lbl">视频大标题</div>
              <div class="counter">{{ title.length }}/20</div>
            </div>
            <div class="inp"><input v-model="title" maxlength="20" placeholder="例如:全城最鲜火锅 开业5折" @input="touched.title = true"></div>
          </div>

          <div class="item">
            <div class="row"><div class="lbl">副标题 / 卖点</div><div class="counter">{{ subtitle.length }}/30</div></div>
            <div class="inp"><input v-model="subtitle" maxlength="30" placeholder="例如:招牌毛肚 8.8 元 进店就送" @input="touched.subtitle = true"></div>
          </div>

          <div class="item">
            <div class="row"><div class="lbl">想让视频说什么(选填)</div><div class="counter">{{ script.length }}/50</div></div>
            <div class="inp ta"><textarea v-model="script" maxlength="50" placeholder="例如:欢迎来本店,开业期间全场5折,错过等一年!" @input="touched.script = true"></textarea></div>
            <div class="sub" style="margin-top:8px">上传参考图后会自动生成草稿,可直接修改</div>
          </div>

          <div class="item">
            <div class="row"><div class="lbl">画面要求(选填)</div><div class="counter">{{ extraDemand.length }}/90</div></div>
            <div class="inp ta"><textarea v-model="extraDemand" maxlength="90" placeholder="例如:把视频里的人物换成我上传的商品图主体,场景和运镜保持不变" @input="touched.extra = true"></textarea></div>
            <div class="sub" style="margin-top:8px">只描述画面怎么改,不会作为口播念出来;上传参考图后会自动生成</div>
          </div>

          <!-- 生成规格(时长/画幅/清晰度):此前全部由模板与系统配置写死,用户无从选择 -->
          <div class="item">
            <div class="lbl">生成规格</div>
            <div v-if="genOptions.durations?.length" class="spec-row">
              <span class="spec-name">时长</span>
              <span
                v-for="d in genOptions.durations"
                :key="`dur${d}`"
                :class="['spec-chip', { on: selDuration === d }]"
                @click="selDuration = d; refreshEstimate()"
              >{{ d }}秒</span>
            </div>
            <div v-if="genOptions.ratios?.length" class="spec-row">
              <span class="spec-name">画幅</span>
              <span
                v-for="r in genOptions.ratios"
                :key="`ratio${r}`"
                :class="['spec-chip', { on: selRatio === r, gray: !ratioSelectable }]"
                @click="pickRatio(r)"
              >{{ r }}</span>
            </div>
            <div v-if="genOptions.resolutions?.length" class="spec-row">
              <span class="spec-name">清晰度</span>
              <span
                v-for="s in genOptions.resolutions"
                :key="`res${s}`"
                :class="['spec-chip', { on: selResolution === s }]"
                @click="selResolution = s; refreshEstimate()"
              >{{ s }}</span>
            </div>
            <div v-if="!ratioSelectable" class="sub" style="margin-top:8px">
              已带参考视频:成片画幅与时长跟随参考视频(由模型自适应),此处选择不生效
            </div>
          </div>

          <div class="item">
            <div class="lbl" style="margin-bottom:12px">你的 Logo(选填)</div>
            <div class="row">
              <n-upload
                accept="image/*"
                :max="1"
                :show-file-list="false"
                :custom-request="uploadLogo"
                :before-upload="beforeUpload"
              >
                <div class="up gray">{{ logoUrl ? 'Logo 已上传' : '上传 Logo' }}</div>
              </n-upload>
              <n-switch v-model:value="logoOn" />
            </div>
          </div>
        </div>
      </div>
    </n-spin>

    <!-- 底部生成栏 -->
    <div class="footer">
      <div class="footer-in">
        <div>
          <div style="font-size:13px; font-weight:500">{{ estSecondsText }}</div>
          <div class="sub">{{ hasCredit ? `剩余额度 ${userStore.creditTotal} 次 · 本次${estCostText}` : `单次生成 ¥${price}` }}</div>
        </div>
        <button class="gen-btn" :disabled="!canGenerate || submitting" @click="openConfirm">
          {{ submitting ? '提交中...' : '生成视频' }}
        </button>
      </div>
    </div>

    <!-- 生成确认 -->
    <n-modal v-model:show="confirmVisible" :mask-closable="true">
      <div class="confirm">
        <h3>确认开始生成？</h3>
        <p class="sub" style="text-align:center; line-height:1.7">将用你填写的素材替换模板内容，<br>{{ estSecondsText }}。</p>
        <div class="confirm-btns">
          <div class="btn-outline" @click="confirmVisible = false">再看看</div>
          <div class="btn-primary" @click="doGenerate">
            {{ hasCredit ? `${estCostText}额度生成（剩余 ${userStore.creditTotal} 次）` : `去支付 ¥${price}` }}
          </div>
        </div>
      </div>
    </n-modal>

    <!-- 收银台 -->
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
</template>

<style scoped>
.material-page {
  min-height: calc(100vh - var(--header-h));
  background: var(--bg);
  display: flex;
  flex-direction: column;
}
.wrap { max-width: var(--page-max); margin: 0 auto; }
.card { background: #fff; border-radius: var(--radius); box-shadow: var(--shadow-sm); }
.sub { font-size: 11px; color: var(--weak); margin-top: 4px; }

/* 预览 */
.preview { padding: 20px; margin: 16px 20px 0; }
.pv {
  height: 240px;
  border-radius: 12px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(90deg, #FA8C4D, #DB331F);
  background-size: cover;
  background-position: center;
  overflow: hidden;
}
/* 有视频时容器跟随视频自身比例:竖屏 9:16 塞进固定高度的宽框,会在左右留下黑边 */
.pv-fit { height: auto; width: fit-content; max-width: 100%; margin: 0 auto; background: #000; }
.pv-video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; background: #000; }
.pv-fit .pv-video {
  position: static; display: block; width: auto; height: auto;
  max-width: 100%; max-height: 62vh;
}
.play {
  width: 56px; height: 56px; border-radius: 50%;
  background: rgba(0, 0, 0, 0.3);
  display: flex; align-items: center; justify-content: center;
}
.dur {
  position: absolute; right: 10px; bottom: 10px;
  background: rgba(0, 0, 0, 0.5); color: #fff;
  font-size: 11px; padding: 4px 8px; border-radius: 6px;
}
.badge-ref {
  position: absolute; left: 10px; top: 10px;
  background: var(--brand); color: #fff;
  font-size: 11px; font-weight: 700;
  padding: 4px 8px; border-radius: 10px;
}
.pmeta { display: flex; justify-content: space-between; align-items: baseline; margin-top: 12px; }
.pmeta b { font-size: 15px; }
.pmeta span { font-size: 12px; color: var(--weak); }

/* 表单 */
.form { padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; }
.item { background: #fff; border-radius: 12px; padding: 16px; }
.row { display: flex; align-items: center; justify-content: space-between; }
.thumb {
  width: 56px; height: 56px; border-radius: 8px;
  background: #F0F1F3; border: 1.5px solid #D8DADE;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden; flex: 0 0 56px;
}
.thumb img { width: 100%; height: 100%; object-fit: cover; }
.lbl { font-size: 14px; font-weight: 500; }
.up {
  height: 36px; padding: 0 14px; border-radius: 18px;
  background: var(--brand-bg); color: var(--brand);
  font-size: 13px; font-weight: 500;
  display: flex; align-items: center; cursor: pointer; flex: 0 0 auto;
}
.up.gray { background: var(--bg); color: var(--body-c); }
.inp {
  height: 46px; border-radius: 10px; background: var(--bg);
  display: flex; align-items: center; padding: 0 12px; margin-top: 10px;
}
.inp input, .inp textarea {
  width: 100%; border: none; outline: none; background: transparent;
  font-size: 14px; font-family: inherit; color: var(--ink);
}
.inp.ta { height: 88px; align-items: flex-start; padding-top: 12px; }
.inp textarea { height: 64px; resize: none; line-height: 22px; }
.counter { font-size: 11px; color: var(--weak); }
.ai-btn {
  height: 26px; padding: 0 12px; border-radius: 13px; border: none;
  background: linear-gradient(90deg, #FF6A3D, var(--brand)); color: #fff;
  font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.ai-btn:disabled { opacity: 0.6; cursor: not-allowed; }

/* 文案被删空时的提示 */
.warn {
  margin-top: 10px; padding: 9px 12px; border-radius: 8px;
  background: #FFF7E6; color: #AD6800; font-size: 12px; line-height: 1.6;
  border: 1px solid #FFE0A3;
}

/* 替换意图多选芯片 */
.intent-chips { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
.chip {
  padding: 7px 16px; border-radius: 18px; background: var(--bg);
  font-size: 13px; color: var(--body-c); cursor: pointer;
  border: 1.5px solid transparent; user-select: none;
}
.chip.on {
  background: var(--brand-bg); color: var(--brand);
  border-color: var(--brand); font-weight: 600;
}

/* 生成规格(时长/画幅/清晰度):与替换意图芯片同风格,复用同一套视觉语言 */
.spec-row { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; align-items: center; }
.spec-name { font-size: 12px; color: var(--body-c); min-width: 42px; flex: 0 0 auto; }
.spec-chip {
  padding: 6px 14px; border-radius: 16px; background: var(--bg);
  font-size: 13px; color: var(--body-c); cursor: pointer;
  border: 1.5px solid transparent; user-select: none;
}
.spec-chip.on {
  background: var(--brand-bg); color: var(--brand);
  border-color: var(--brand); font-weight: 600;
}
/* 画幅在带参考视频时不可选(成片画幅由模型自适应):置灰,避免"选了却没效果" */
.spec-chip.gray { opacity: 0.45; cursor: not-allowed; }

/* 底部生成栏:滚动时吸在视口底部,滚到内容末尾则回到文档流中,
   落在站点页脚(AppFooter)之上,避免与页脚叠成两条底栏 */
.footer {
  position: sticky;
  bottom: 0;
  z-index: 90;
  margin-top: auto;
  background: #fff; border-top: 1px solid var(--line);
}
.footer-in {
  max-width: var(--page-max); margin: 0 auto;
  height: 76px;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px; gap: 12px;
}
.gen-btn {
  width: 176px; height: 48px; border-radius: 24px; border: none;
  background: var(--brand); color: #fff; font-size: 16px; font-weight: 700;
  cursor: pointer; font-family: inherit;
}
.gen-btn:disabled { background: #DCDFE4; cursor: not-allowed; }

/* 确认弹层 */
.confirm {
  width: 311px; background: #fff; border-radius: 16px; padding: 24px;
  display: flex; flex-direction: column; gap: 16px;
}
.confirm h3 { margin: 0; text-align: center; font-size: 18px; }
.confirm-btns { display: flex; gap: 10px; }
.btn-outline, .btn-primary {
  flex: 1; height: 48px; border-radius: 24px;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; cursor: pointer;
}
.btn-outline { background: #fff; color: var(--brand); border: 1.5px solid var(--brand); font-weight: 500; }
.btn-primary { background: var(--brand); color: #fff; font-weight: 700; }

/* 收银台 */
.pay {
  width: 311px; background: #fff; border-radius: 16px; padding: 24px;
  display: flex; flex-direction: column; align-items: center; gap: 12px;
}
.pay h3 { margin: 0; font-size: 18px; }
.pay-amount { font-size: 28px; font-weight: 700; color: var(--brand); }
.pay-qr { width: 220px; height: 220px; border-radius: 8px; border: 1px solid var(--line); }
.pay-mock-btn {
  width: 100%; height: 46px; border-radius: 23px; border: none;
  background: var(--brand); color: #fff; font-size: 15px; font-weight: 700;
  cursor: pointer; font-family: inherit;
}
.pay-mock-btn:disabled { background: #DCDFE4; cursor: not-allowed; }
.pay-close { font-size: 13px; color: var(--weak); cursor: pointer; margin-top: 4px; }

/* 桌面端双列 */
@media (min-width: 768px) {
  .mcols {
    display: grid;
    grid-template-columns: 420px 1fr;
    gap: 20px;
    padding: 24px;
    align-items: start;
  }
  .preview { margin: 0; position: sticky; top: calc(var(--header-h) + 16px); padding: 20px; }
  .pv { height: 320px; }
  .form { padding: 0; gap: 16px; }
  .item { padding: 20px; }
}
/* 参考视频抽出的画面列表 */
.frame-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}
.frame-list img {
  width: 76px;
  height: 76px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid #EEE;
  background: #F7F8FA;
}
</style>
