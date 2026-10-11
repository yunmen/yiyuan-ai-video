<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import api from '@/api'
import { uploadFile } from '@/api/model/common'
import { useSkill } from '@/composables/useSkill'
import { useUserStore } from '@/store/modules/user'
import { useTaskEstimate } from '@/composables/useTaskEstimate'
import { useTaskCreate } from '@/composables/useTaskCreate'
import { formatDuration } from '@/utils/format'
import { withCurrentVoiceOption, isDialectVoice, DIALECT_OPTIONS, detectDialectInText, stripDialectInstruction, hasDialectInstruction } from '@/constants/doubaoVoices'
import { voiceOptionsWithPreview } from '@/constants/voicePreviews'
import { useVoiceLabelRenderer } from '@/utils/voiceOptionRender'

const userStore = useUserStore()
// 统一技能入口:口播「试听配音」走 audio-synthesis 技能(worker 内 AudioGenTool,纯语音网关调用)
const { runVoice: runSkill, error: skillError } = useSkill()

const avatars = ref([])
const loading = ref(false)

// 选人弹窗:填写口播文案后提交数字人任务
const pickVisible = ref(false)
const current = ref(null)
const script = ref('')
const voice = ref('')
// 方言:方言语义键(如 chuanyu/cantonese)。与口播文案解耦 —— 用户写「用重庆方言说」会被识别并转成该字段,
// 台词里「用xx方言说：」这类前缀会在成片口播时自动剥离(方言指令不会念出来),方言本身经 dialect 字段生效。
const dialect = ref('')
// 台词方言识别提示:识别到方言要求自动选用,并把「指令会被自动去除」告知用户
const dialectHint = ref('')
// 从口播文案识别方言要求:识别到且当前方言不等于该值时自动选用(不改写可见台词,只在提交/试听时剥离前缀);
// 若写了方言指令却未解析出具体方言(如仅写「用方言说：」),提示用户手动在「方言」下拉选择,否则按普通话合成。
function syncDialectFromText() {
  const text = useSegments.value
    ? segments.value.map((s) => (s.text || '').trim()).join(' ')
    : script.value
  const hit = detectDialectInText(text)
  if (hit) {
    if (dialect.value !== hit) dialect.value = hit
    const label = (DIALECT_OPTIONS.find((o) => o.value === hit) || {}).label || hit
    dialectHint.value = `已从台词识别到「${label}」,方言指令(如「用${label}说：」)会在成片口播时自动去除,不会念出来。`
  } else if (hasDialectInstruction(text)) {
    // 含方言指令但没匹配到具体方言:剥离指令,提醒手动选方言(否则按普通话合成)
    dialectHint.value = '已识别到方言指令,但未能匹配具体方言,成片将按普通话合成;如需方言请在下方「方言」下拉选择。'
  } else {
    dialectHint.value = ''
  }
}
const submitting = ref(false)
// 音色下拉:官方清单(含样音) + 当前绑定的自定义音色兜底(选人弹窗的本次音色、创建/编辑弹窗的默认音色)。
// 管理端「音色」是自由文本输入,运营可能填了清单外甚至方言的 voice_type,
// 兜底项保证这类值有中文可读说明且能被识别为不可用,而不是直接把英文 ID 甩给用户。
const voiceOptions = computed(() =>
  withCurrentVoiceOption(
    voiceOptionsWithPreview(),
    voice.value || current.value?.voice || createForm.voice
  )
)
const renderVoiceLabel = useVoiceLabelRenderer()
// 任务级声纹覆盖:本次口播临时换一个声纹样本(优先级高于音色与数字人绑定声纹);
// 留空则沿用该数字人绑定的声纹。修复此前「后端自动回落生效但前端无控件」的隐性行为。
const voiceRefTask = ref('')
const voiceRefTaskUploading = ref(false)

// 试听配音:用 audio-synthesis 技能把当前口播/分镜台词合成音频,返回直链供前端播放试听
const ttsPreview = ref('')
const ttsLoading = ref(false)

// 形象预览弹窗
const preview = ref({ visible: false, url: '', name: '' })

// 可提交校验:多段模式下至少有一段填了台词;单段模式要求口播文案非空
const canSubmit = computed(() => {
  if (useSegments.value) {
    return segments.value.some((s) => (s.text || '').trim())
  }
  return !!script.value.trim()
})

// 预估逻辑下沉到公共 composable,多页面复用,避免副本漂移
const { estCost, estSeconds, estOptions, refresh: estRefresh } = useTaskEstimate()
const { createAndNavigate } = useTaskCreate()

// 选人弹窗内「更多设置(可选)」:时长 / 画幅 / 清晰度 / 出镜视图 / 背景参考图
const advOpen = ref(false)
const duration = ref(8)
const ratio = ref('')          // 空串=系统默认
const resolution = ref('')     // 空串=系统默认
const pose = ref('')           // 空串=主视图
// 语速(0.5x–2.0x):TTS 合成语速,默认 1.0x(正常),与后端 schema / worker 同区间
const speed = ref(1.0)
const speedMarks = { 0.5: '0.5x', 1: '1x', 1.5: '1.5x', 2: '2x' }
const background = ref('')     // 空串=无背景
const bgUploading = ref(false)
// 带货模式:商品图(作为数字人出镜的商品场景背景);留空=非带货
const goods = ref('')
const goodsUploading = ref(false)

// 多段脚本(逐段镜头):开启后按段填写台词与时长,worker 逐段生成后拼接成一条成片
const useSegments = ref(false)
const segments = ref([{ text: '', duration: 8 }])
// 文案(单段/多段)变化时实时识别方言;deep 监听多段数组的元素文本。
// 必须在 segments/useSegments 声明之后注册,否则 setup 阶段访问未初始化的响应式变量会触发 TDZ 报错。
watch([script, segments, useSegments], syncDialectFromText, { deep: true })
// 画中画(presenter-led-explainer):上传背景视频后,把数字人成片缩成小窗叠到背景之上
const overlay = ref('')            // 空串=不叠加
const overlayUploading = ref(false)
const pipPosition = ref('br')      // 小窗位置:右下/左下/右上/左上
const pipScale = ref(0.3)          // 小窗相对背景宽度的比例
// 背景原声音量(仅影响背景铺底,不影响口播):0=静音背景,缺省用后端/worker 默认 0.2
const pipBgVolume = ref(0.2)
const PIP_POSITIONS = [
  { key: 'br', label: '右下' }, { key: 'bl', label: '左下' },
  { key: 'tr', label: '右上' }, { key: 'tl', label: '左上' },
]
const PIP_SCALES = [
  { key: 0.25, label: '小窗' }, { key: 0.3, label: '适中' }, { key: 0.4, label: '较大' },
]
// 背景音量档位:静音 0 / 小 0.15 / 中 0.3;数字人口播恒为 1.0,不受此项影响
const PIP_BG_VOLUMES = [
  { key: 0, label: '静音' }, { key: 0.15, label: '小' }, { key: 0.3, label: '中' },
]
// 换动作(可选):动作/姿态意图,透传数字人网关;留空由模型自行表演
const motion = ref('')
const MOTION_PRESETS = [
  { key: '挥手介绍商品', label: '挥手介绍' },
  { key: '手举商品展示', label: '手举商品' },
  { key: '点头微笑讲解', label: '点头讲解' },
  { key: '双手比划强调', label: '比划强调' },
]

// 我的专属形象(用户自助上传形象生成):tab 切换平台形象 / 我的形象
const tab = ref('platform')
const mine = ref([])
const mineLoading = ref(false)

// 创建/编辑专属数字人弹窗:两者复用同一表单(字段一致),editingId 为空表示新建
const createVisible = ref(false)
const creating = ref(false)
const imageUploading = ref(false)
// editingId:非空即编辑该专属形象(此前用户只能删了重建,无法改名称/音色/默认文案)
const editingId = ref(null)
const createForm = reactive({
  name: '',
  gender: '女',
  image: '',
  voice: '',
  voice_reference: '',
  default_text: '',
  // 以下三项后端 UserCreateSchema/UserUpdateSchema 已支持,此前前端未开放(补齐运营展示位)
  style: '',   // 风格标签(如「亲和」「专业」)
  desc: '',    // 一句话简介
  avatar: '',  // 列表封面图,留空则用形象图
})
// 封面图上传:与形象图同一套对象存储直传逻辑,单张限制
const avatarUploading = ref(false)
// 声纹样本上传(可复用声纹,跨镜头/跨任务保持同一声音;优先级高于音色)
const voiceRefUploading = ref(false)

// 拉取我的专属形象(登录后);失败不阻断平台形象展示
async function loadMine() {
  if (!userStore.isLoggedIn) { mine.value = []; return }
  mineLoading.value = true
  try {
    const res = await api.digital.personalList.post({})
    if (res.code === 1) mine.value = res.data || []
  } catch (e) { /* 拦截器已提示 */ }
  finally { mineLoading.value = false }
}

// 形象图上传:复用平台直传逻辑(对象存储预签名优先,失败不回退中转)
async function uploadImage({ file, onFinish, onError, onProgress }) {
  if (createForm.image) {
    window.$message?.warning('形象图只能上传一张,请先移除')
    onError(); return
  }
  imageUploading.value = true
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    createForm.image = url
    onFinish()
  } catch (e) { onError() }
  finally { imageUploading.value = false }
}
function removeImage() { createForm.image = '' }

// 列表封面图上传:留空时后端与列表展示均回退形象图
async function uploadAvatar({ file, onFinish, onError, onProgress }) {
  if (createForm.avatar) {
    window.$message?.warning('封面图只能上传一张,请先移除')
    onError(); return
  }
  avatarUploading.value = true
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    createForm.avatar = url
    onFinish()
  } catch (e) { onError() }
  finally { avatarUploading.value = false }
}
function removeAvatar() { createForm.avatar = '' }

// 声纹样本上传:与形象图同一套对象存储直传逻辑;可替换(编辑时可换声纹)
async function uploadVoiceRef({ file, onFinish, onError, onProgress }) {
  if (createForm.voice_reference) {
    window.$message?.warning('声纹样本只能上传一段,请先移除')
    onError(); return
  }
  voiceRefUploading.value = true
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    createForm.voice_reference = url
    onFinish()
  } catch (e) { onError() }
  finally { voiceRefUploading.value = false }
}
function removeVoiceRef() { createForm.voice_reference = '' }

// 新建:清空表单并打开
function openCreate() {
  if (!userStore.isLoggedIn) {
    window.$message?.warning('请先登录后再创建专属形象')
    userStore.openLogin()
    return
  }
  editingId.value = null
  createForm.name = ''
  createForm.gender = '女'
  createForm.image = ''
  createForm.voice = ''
  createForm.voice_reference = ''
  createForm.default_text = ''
  createForm.style = ''
  createForm.desc = ''
  createForm.avatar = ''
  createVisible.value = true
}

// 编辑:回填既有专属形象(仅本人可编辑,归属校验在后端)
function openEdit(a) {
  editingId.value = a.id
  createForm.name = a.name || ''
  createForm.gender = a.gender || '女'
  createForm.image = a.image || a.avatar || ''
  createForm.voice = a.voice || ''
  createForm.voice_reference = a.voice_reference || ''
  createForm.default_text = a.default_text || ''
  createForm.style = a.style || ''
  createForm.desc = a.desc || ''
  // 封面图独立于形象图:预填既有值,避免未改动时被清空
  createForm.avatar = a.avatar || ''
  createVisible.value = true
}

// 提交:按 editingId 走创建或编辑接口(两者字段一致,运营侧字段不在用户表单内)
async function submitForm() {
  if (!createForm.name.trim()) {
    window.$message?.warning('请填写形象名称')
    return
  }
  if (!createForm.image) {
    window.$message?.warning('请上传形象图(正面半身照,口型驱动底图)')
    return
  }
  creating.value = true
  try {
    const payload = {
      name: createForm.name.trim(),
      gender: createForm.gender,
      image: createForm.image,
      voice: createForm.voice.trim() || undefined,
      voice_reference: createForm.voice_reference.trim() || undefined,
      default_text: createForm.default_text.trim() || undefined,
      // 风格 / 简介 / 封面图:后端 UserCreateSchema 与 UserUpdateSchema 均已支持
      style: createForm.style.trim() || undefined,
      desc: createForm.desc.trim() || undefined,
      avatar: createForm.avatar.trim() || undefined,
    }
    if (editingId.value) payload.id = editingId.value
    const res = editingId.value
      ? await api.digital.personalUpdate.post(payload)
      : await api.digital.personalCreate.post(payload)
    if (res.code === 1) {
      window.$message?.success(editingId.value ? '专属形象已更新' : '专属形象已创建,可直接用于口播')
      createVisible.value = false
      await loadMine()
      // 新建后自动切到我的形象,方便立即使用
      if (!editingId.value) tab.value = 'mine'
    } else {
      window.$message?.error(res.message || (editingId.value ? '更新失败' : '创建失败'))
    }
  } catch (e) { /* 拦截器已提示 */ }
  finally { creating.value = false }
}

// 复用 App.vue 经 createDiscreteApi 暴露的全局对话框(无需 n-dialog-provider 祖先)
const dialog = window.$dialog

// 删除专属形象:二次确认,仅删除记录,已生成的视频不受影响
function deleteMine(a) {
  dialog.warning({
    title: '删除专属形象',
    content: `确定删除「${a.name}」？删除后该形象不可恢复,已生成的口播视频不受影响。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const res = await api.digital.personalDelete.post({ id: a.id })
        if (res.code === 1) {
          window.$message?.success('已删除')
          await loadMine()
        } else {
          window.$message?.error(res.message || '删除失败')
        }
      } catch (e) { /* 拦截器已提示 */ }
    },
  })
}

// 平台支持的画幅/清晰度选项(与后端 gen_rules 白名单同源,前端不另存副本)
const RATIO_OPTIONS = [
  { key: '9:16', label: '竖屏 9:16' },
  { key: '16:9', label: '横屏 16:9' },
  { key: '1:1', label: '方形 1:1' },
]
const RES_OPTIONS = [
  { key: '1080P', label: '1080P 高清' },
  { key: '720P', label: '720P 流畅' },
]
// 时长档位取自预估接口回传的 options.durations(与 worker 吸附档一致,避免 UI 显示与实际不符),
// 未拿到时回退 [5,10]。
const durationOptions = computed(() => estOptions.value?.durations?.length ? estOptions.value.durations : [5, 10])
// 出镜视图:主视图 + 数字人配置的派生视图(pose_variants)
const poseOptions = computed(() => {
  const variants = current.value?.pose_variants || []
  return [{ key: '', label: '主视图' }, ...variants.map((v) => ({ key: v.name, label: v.name }))]
})

// 数字人页专属提示文案:在通用额度/耗时基础上,补充「我的作品」查看入口说明
const estTip = computed(() => {
  const parts = [`提交后将消耗 ${estCost.value ?? 1} 次生成额度`]
  const s = estSeconds.value
  if (s) parts.push(`预计 ${formatDuration(s)}`)
  parts.push('可在「我的作品」查看进度')
  return parts.join('，')
})

// 取一次预估:携带当前时长(多段模式按各段时长之和),失败不阻断提交(以下单时后端计算结果为准)
function refreshEstimate() {
  const dur = useSegments.value
    ? segments.value.reduce((sum, s) => sum + (Number(s.duration) || 8), 0)
    : duration.value
  return estRefresh('digital', { duration: dur })
}

// 时长档位随预估回传的 options.durations 变化:若当前值与可用档位不一致,吸附到最接近 8 秒的档位,
// 保证 UI 选中的时长与 worker 实际吸附档一致,不会"显示 8 秒、实际 10 秒"。
function syncDurationDefault() {
  const opts = durationOptions.value
  if (!opts.length || opts.includes(duration.value)) return
  duration.value = opts.reduce((a, b) => Math.abs(b - 8) < Math.abs(a - 8) ? b : a, opts[0])
}

async function load() {
  loading.value = true
  try {
    const res = await api.digital.list.post({ pageNum: 1, pageSize: 50 })
    if (res.code === 1) avatars.value = res.data || []
  } catch (e) { /* 拦截器已提示 */ }
  loading.value = false
  // 平台形象与我的形象并行加载,互不阻断
  loadMine()
}

function openPick(a) {
  if (!userStore.isLoggedIn) {
    window.$message?.warning('请先登录后再使用数字人口播')
    userStore.openLogin()
    return
  }
  current.value = a
  // 预填后台为该数字人配置的默认台词与音色,用户可自行修改
  script.value = a.default_text || ''
  voice.value = a.voice || ''
  // 预填该数字人绑定的声纹:用户可临时替换,也可移除改用纯音色
  voiceRefTask.value = a.voice_reference || ''
  // 重置高阶设置到默认(系统默认规格 / 主视图 / 无背景)
  advOpen.value = false
  duration.value = 8
  ratio.value = ''
  resolution.value = ''
  pose.value = ''
  speed.value = 1.0          // 切换形象回到默认语速
  background.value = ''
  goods.value = ''          // 切换形象清空带货商品图
  // 重置多段脚本与画中画(每次选人都回到单段 + 无叠加的默认形态)
  useSegments.value = false
  segments.value = [{ text: '', duration: 8 }]
  overlay.value = ''
  pipPosition.value = 'br'
  pipScale.value = 0.3
  pipBgVolume.value = 0.2
  motion.value = ''      // 切换形象清空上一段动作意图
  dialect.value = ''     // 切换形象清空上一段方言选择
  dialectHint.value = ''
  ttsPreview.value = ''   // 切换形象清空上一段试听
  refreshEstimate().then(syncDurationDefault)
  pickVisible.value = true
}

// 时长变化即重新预估耗时(仅弹窗打开时)
watch(duration, () => {
  if (pickVisible.value) refreshEstimate()
})

function showPreview(a) {
  preview.value = { visible: true, url: a.preview_video, name: a.name }
}

// 背景参考图上传:复用平台直传逻辑;单张限制,先移除再传
async function uploadBackground({ file, onFinish, onError, onProgress }) {
  if (background.value) {
    window.$message?.warning('背景图只能上传一张,请先移除')
    onError(); return
  }
  bgUploading.value = true
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    background.value = url
    onFinish()
  } catch (e) {
    onError()
  } finally {
    bgUploading.value = false
  }
}
function removeBackground() { background.value = '' }

// 带货模式:商品图上传(作为数字人出镜场景背景);单张限制,先移除再传
async function uploadGoods({ file, onFinish, onError, onProgress }) {
  if (goods.value) {
    window.$message?.warning('商品图只能上传一张,请先移除')
    onError(); return
  }
  goodsUploading.value = true
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    goods.value = url
    onFinish()
  } catch (e) {
    onError()
  } finally {
    goodsUploading.value = false
  }
}
function removeGoods() { goods.value = '' }

// 多段脚本:新增/删除段落(每段一个镜头,段边界驱动切镜)
function addSegment() {
  segments.value.push({ text: '', duration: duration.value || 8 })
}
function removeSegment(idx) {
  if (segments.value.length <= 1) return
  segments.value.splice(idx, 1)
}

// 画中画背景视频上传:复用平台直传逻辑,单段限制
async function uploadOverlay({ file, onFinish, onError, onProgress }) {
  overlayUploading.value = true
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    overlay.value = url
    onFinish()
  } catch (e) {
    onError()
  } finally {
    overlayUploading.value = false
  }
}
function removeOverlay() { overlay.value = '' }

// 任务级声纹样本上传:单段限制,可先移除再换;留空则用该数字人绑定的声纹
async function uploadTaskVoiceRef({ file, onFinish, onError, onProgress }) {
  if (voiceRefTask.value) {
    window.$message?.warning('声纹样本只能上传一段,请先移除')
    onError(); return
  }
  voiceRefTaskUploading.value = true
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    voiceRefTask.value = url
    onFinish()
  } catch (e) { onError() }
  finally { voiceRefTaskUploading.value = false }
}
function removeTaskVoiceRef() { voiceRefTask.value = '' }

// 试听配音:用 audio-synthesis 技能把当前口播(单段)或各段台词(多段)合成音频,
// 产物 audio URL 写入 ttsPreview 供 <audio> 播放。与正式「数字人渲染」(digitalCreate)解耦:
// 这里只验证音色/语气,不消耗数字人渲染额度,改文案可即时重听。
async function previewVoice() {
  // 与正式提交一致:先剥离「用xx方言说：」前缀再试听,避免把方言指令念出来,所见即所得
  const text = stripDialectInstruction(
    useSegments.value
      ? segments.value.map((s) => (s.text || '').trim()).join(' ')
      : script.value
  )
  if (!text) {
    window.$message?.warning(useSegments.value ? '请至少填写一段口播台词' : '请填写口播文案')
    return
  }
  if (ttsLoading.value) return
  // 音色里填方言 ID 不支持:方言请走下方「方言」选择,不要往音色字段塞方言 voice_type
  if (isDialectVoice(voice.value)) {
    window.$message?.error('音色不支持填方言 ID,方言请在下方「方言」下拉选择')
    return
  }
  ttsLoading.value = true
  try {
    const { status, data } = await runSkill({
      text,
      voice: voice.value.trim() || undefined,
      // 与正式提交保持一致:勾了「本次声纹覆盖」就按该声纹试听,否则听到的音色与出片不同
      voice_reference: voiceRefTask.value.trim() || undefined,
      speed: speed.value,
      // 试听也带方言,所见即所得(网关不支持方言则该项被忽略)
      dialect: dialect.value || undefined,
    })
    // audio-synthesis 产物 content 为音频直链;失败(网关未配/合成异常)时 metadata.success=False
    if (status === 'done' && data?.content && data?.metadata?.success !== false) {
      ttsPreview.value = data.content
      window.$message?.success('已生成试听配音,可播放试听')
    } else if (status === 'timeout') {
      window.$message?.error('试听合成超时,请稍后重试或联系管理员确认音频网关状态')
    } else if (status === 'not_found') {
      window.$message?.error('试听任务未找到,请检查音频网关(gen.audio_model)是否已配置')
    } else {
      window.$message?.error(skillError.value || '试听失败:请检查音频网关(gen.audio_model)是否已配置,或改用音色右侧 ▶ 试听预置样音')
    }
  } catch (e) { /* 拦截器已提示 */ }
  finally { ttsLoading.value = false }
}

async function submit() {
  if (!canSubmit.value) {
    window.$message?.warning(useSegments.value ? '请至少填写一段口播台词' : '请填写口播文案')
    return
  }
  if (!current.value) return
  // 音色里填方言 ID 不支持(方言请走「方言」下拉),提交前拦截,避免白跑一次失败任务
  if (isDialectVoice(voice.value)) {
    window.$message?.error('音色不支持填方言 ID,方言请在下方「方言」下拉选择')
    return
  }
  // 单段模式:去除方言指令后若没有实际口播内容,提示补充(避免后端因 text 为空失败)
  if (!useSegments.value && !stripDialectInstruction(script.value)) {
    window.$message?.warning('请填写要念出的口播内容(仅写方言指令无效)')
    return
  }
  submitting.value = true
  try {
    const device = window.innerWidth <= 768 ? 'mobile' : 'desktop'
    // 成片口播文本:剥离「用xx方言说：」前缀(方言指令不念出),方言经 dialect 字段生效
    const spokenText = useSegments.value ? undefined : stripDialectInstruction(script.value)
    // 多段模式:用 segments(每段 {text,duration}) 替代顶层 text;单段模式沿用 text
    const payload = {
      digital_id: current.value.id,
      text: spokenText,
      voice: voice.value.trim() || undefined,
      // 声纹复用:本次口播用哪个声纹样本(留空则沿用该数字人绑定的声纹)
      voice_reference: voiceRefTask.value.trim() || undefined,
      speed: speed.value,
      duration: duration.value,
      ratio: ratio.value || undefined,
      resolution: resolution.value || undefined,
      pose: pose.value || undefined,
      // 换动作:动作/姿态意图透传数字人网关(网关未支持该能力时自动忽略)
      motion: motion.value.trim() || undefined,
      // 方言:方言语义键,经后端透传 TTS 网关(网关不支持则忽略)
      dialect: dialect.value || undefined,
      background: background.value || undefined,
      goods: goods.value || undefined,
      device,
    }
    if (useSegments.value) {
      // 多段逐段剥离方言指令前缀,空段直接丢弃(与单段校验一致)
      payload.segments = segments.value
        .map((s) => ({ text: stripDialectInstruction(s.text), duration: Number(s.duration) || 8 }))
        .filter((s) => s.text)
    }
    // 画中画:提供背景视频则把数字人成片缩窗叠到背景上,并带上位置/大小/背景音量参数
    // (bg_volume=0 表示背景静音,数字人口播恒为 1.0 不受影响)
    if (overlay.value) {
      payload.overlay = overlay.value
      payload.pip = { position: pipPosition.value, scale: pipScale.value, bg_volume: pipBgVolume.value }
    }
    const data = await createAndNavigate(
      () => api.task.digitalCreate.post(payload),
      { message: '已提交生成，正在为你合成口播视频' }
    )
    if (data) pickVisible.value = false
  } catch (e) { /* 拦截器已提示 */ }
  finally { submitting.value = false }
}

// 移动端标题栏返回键:返回上一页(桌面端由全局导航承担)
function goBack() {
  window.history.back()
}

onMounted(load)
</script>

<template>
  <div class="av-page">
    <!-- 移动端顶部标题栏(设计稿 .header-bar):桌面端由全局 AppHeader 承担,≥768px 隐藏 -->
    <header class="page-head">
      <button type="button" class="ph-back" aria-label="返回" @click="goBack">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
      </button>
      <h1 class="ph-title">数字人口播</h1>
      <button type="button" class="ph-upload" @click="openCreate">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
        <span>上传</span>
      </button>
    </header>

    <div class="wrap">
      <!-- 平台形象 / 我的形象 切换(设计稿 .tab-switcher) -->
      <div class="avtabs">
        <button type="button" class="avtab" :class="{ on: tab === 'platform' }" @click="tab = 'platform'">平台形象</button>
        <button type="button" class="avtab" :class="{ on: tab === 'mine' }" @click="tab = 'mine'">我的形象</button>
      </div>

      <!-- 平台形象:运营上架的通用数字人 -->
      <n-spin v-if="tab === 'platform'" :show="loading">
        <div v-if="avatars.length" class="grid">
          <div v-for="a in avatars" :key="a.id" class="avatar-card">
            <div class="card-cover" @click="a.preview_video && showPreview(a)">
              <img v-if="a.avatar" :src="a.avatar" :alt="a.name" />
              <svg v-else viewBox="0 0 143 180" width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
                <rect width="143" height="180" fill="#EEF2FF"/>
                <circle cx="71.5" cy="70" r="28" fill="#818CF8"/>
                <path d="M30 142C30 112 48 96 71.5 96C95 96 113 112 113 142V180H30V142Z" fill="#818CF8"/>
              </svg>
              <span class="tag-chip" :class="a.gender === '男' ? 'tag-male' : 'tag-female'">
                {{ a.gender === '男' ? '男声' : '女声' }}<template v-if="a.style">·{{ a.style }}</template>
              </span>
              <div v-if="a.preview_video" class="avplay">
                <svg width="20" height="20" viewBox="0 0 24 24"><path d="M9 6L18 12L9 18V6Z" fill="#fff"/></svg>
              </div>
            </div>
            <div class="card-body">
              <div class="card-name truncate">{{ a.name }}</div>
              <button type="button" class="select-btn" @click="openPick(a)">选择</button>
            </div>
          </div>
        </div>
        <n-empty v-else-if="!loading" description="数字人整理中，敬请期待" style="padding:60px 0" />
      </n-spin>

      <!-- 我的形象:用户自助上传形象生成的专属数字人 -->
      <n-spin v-else :show="mineLoading">
        <div v-if="mine.length" class="grid">
          <div v-for="a in mine" :key="a.id" class="avatar-card">
            <div class="card-cover" @click="a.preview_video && showPreview(a)">
              <img v-if="a.image || a.avatar" :src="a.image || a.avatar" :alt="a.name" />
              <svg v-else viewBox="0 0 143 180" width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
                <rect width="143" height="180" fill="#EEF2FF"/>
                <circle cx="71.5" cy="70" r="28" fill="#C7D2FE"/>
                <path d="M30 142C30 112 48 96 71.5 96C95 96 113 112 113 142V180H30V142Z" fill="#C7D2FE"/>
              </svg>
              <span class="tag-chip" :class="a.gender === '男' ? 'tag-male' : 'tag-female'">
                {{ a.gender === '男' ? '男声' : '女声' }}<template v-if="a.style">·{{ a.style }}</template>
              </span>
              <div v-if="a.preview_video" class="avplay">
                <svg width="20" height="20" viewBox="0 0 24 24"><path d="M9 6L18 12L9 18V6Z" fill="#fff"/></svg>
              </div>
            </div>
            <div class="card-body">
              <div class="card-name truncate">{{ a.name }}</div>
              <button type="button" class="select-btn" @click="openPick(a)">用这个口播</button>
              <div class="avops">
                <button type="button" class="avdel" @click="openEdit(a)">编辑</button>
                <button type="button" class="avdel" @click="deleteMine(a)">删除</button>
              </div>
            </div>
          </div>
          <!-- 上传我的形象(设计稿 mine-grid 上传占位) -->
          <button type="button" class="avatar-card upload-tile" @click="openCreate">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
            <span class="ut-title">上传我的形象</span>
            <span class="ut-sub">支持图片/视频</span>
          </button>
        </div>
        <div v-else-if="!mineLoading" class="mine-empty">
          <button type="button" class="avatar-card upload-tile" @click="openCreate">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
            <span class="ut-title">上传我的形象</span>
            <span class="ut-sub">支持图片/视频</span>
          </button>
          <p class="mine-hint">还没有专属形象,上传你的照片即可生成专属数字人</p>
        </div>
      </n-spin>

      <!-- 底部提示条(设计稿 .tip-bar) -->
      <div class="tip-bar">
        <div class="tip-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
        </div>
        <div class="tip-text">
          <p class="tip-title">选择形象，输入台词</p>
          <p class="tip-sub">一键生成口型同步视频</p>
        </div>
      </div>
    </div>

    <!-- 填写口播文案并提交 -->
    <n-modal v-model:show="pickVisible" preset="card" :title="`用「${current?.name || ''}」生成口播视频`" style="max-width: 520px">
      <div class="pick-body">
        <div class="pick-head">
          <img v-if="current?.avatar" :src="current.avatar" class="pick-avatar" :alt="current?.name" />
          <div class="pick-meta">
            <b class="pick-name">{{ current?.name }}</b>
            <span class="tag-chip" :class="current?.gender === '男' ? 'tag-male' : 'tag-female'">{{ current?.gender === '男' ? '男声' : '女声' }}<template v-if="current?.style">·{{ current.style }}</template></span>
            <span v-if="current?.desc" class="muted">{{ current.desc }}</span>
          </div>
        </div>
        <!-- 脚本模式:默认单段(一句话口播);需要分段讲解/切镜时切到多段分镜 -->
        <div class="pick-field">
          <div class="pick-label">脚本模式</div>
          <div class="chips">
            <span :class="['chip', { on: !useSegments }]" @click="useSegments = false">单段口播</span>
            <span :class="['chip', { on: useSegments }]" @click="useSegments = true">多段分镜</span>
          </div>
          <div class="pick-sub">多段分镜:每段一个镜头,逐段生成后自动拼接,适合"先讲卖点、再讲优惠"的讲解节奏</div>
        </div>
        <div v-if="!useSegments" class="pick-field">
          <div class="pick-label">
            口播文案
            <n-button size="tiny" secondary :loading="ttsLoading" title="用当前音色真实合成一句试听(需已配置音频网关)" @click="previewVoice">试听配音</n-button>
          </div>
          <n-input
            v-model:value="script"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-count
            placeholder="输入要让数字人念出的台词，例如：欢迎来本店，开业期间全场5折。方言可写「用xx方言说：…」，会自动识别方言并从口播中去除该指令"
          />
          <div v-if="dialectHint" class="pick-warn">{{ dialectHint }}</div>
          <audio v-if="ttsPreview" :src="ttsPreview" controls style="margin-top:8px;width:100%" />
        </div>
        <div v-else class="pick-field">
          <div class="pick-label">
            分镜脚本（每段一句台词,逐段生成后拼接）
            <n-button size="tiny" secondary :loading="ttsLoading" title="用当前音色真实合成一句试听(需已配置音频网关)" @click="previewVoice">试听配音</n-button>
          </div>
          <div class="seg-list">
            <div v-for="(s, i) in segments" :key="i" class="seg-item">
              <div class="seg-head">
                <span class="seg-no">第{{ i + 1 }}段</span>
                <span v-if="segments.length > 1" class="seg-del" @click="removeSegment(i)">删除</span>
              </div>
              <n-input
                v-model:value="s.text"
                type="textarea"
                :rows="2"
                maxlength="200"
                show-count
                placeholder="这一段要数字人念出的台词"
              />
              <div class="seg-dur">
                <span class="seg-dur-lbl">时长</span>
                <span
                  v-for="d in durationOptions"
                  :key="d"
                  :class="['chip', 'mini', { on: s.duration === d }]"
                  @click="s.duration = d"
                >{{ d }}秒</span>
              </div>
            </div>
          </div>
          <n-button size="small" secondary @click="addSegment">+ 添加一段</n-button>
          <audio v-if="ttsPreview" :src="ttsPreview" controls style="margin-top:8px;width:100%" />
        </div>
        <div class="pick-field">
          <div class="pick-label">音色（可选）</div>
          <n-select
            v-model:value="voice"
            :options="voiceOptions"
            :render-label="renderVoiceLabel"
            placeholder="默认音色(数字人绑定)"
            filterable
            clearable
          />
          <div class="pick-sub">豆包语音合成 2.0 官方音色;留空则使用该数字人绑定的默认音色。下拉项右侧 ▶ 可试听样音(样音为 AI 预生成,实际合成以所选项为准)。</div>
        </div>
        <!-- 方言:与口播文案解耦。在台词里写「用重庆方言说」会被自动识别并转成此处选择,方言指令不会当成台词念出 -->
        <div class="pick-field">
          <div class="pick-label">方言（可选）</div>
          <n-select
            v-model:value="dialect"
            :options="DIALECT_OPTIONS"
            placeholder="普通话(默认)"
            clearable
          />
          <div class="pick-sub">豆包语音 2.0 音色自带多方言(川渝含重庆/四川、粤语、东北、北京、天津、河南、上海、陕西、台湾、广西);网关不支持则忽略。也可直接在口播文案里写「用xx方言」,会在这里自动选中。</div>
        </div>
        <!-- 任务级声纹覆盖:本次口播临时换一个声纹样本,不动数字人本身的绑定 -->
        <div class="pick-field">
          <div class="pick-label">本次声纹覆盖（可选）</div>
          <div v-if="voiceRefTask" class="bg-preview">
            <audio :src="voiceRefTask" controls style="width:100%"></audio>
            <span class="bg-remove" @click="removeTaskVoiceRef">移除</span>
          </div>
          <n-upload v-else :show-file-list="false" accept="audio/*" :custom-request="uploadTaskVoiceRef">
            <n-button size="small" :loading="voiceRefTaskUploading" secondary>上传声纹样本</n-button>
          </n-upload>
          <div class="pick-sub">已预填该数字人绑定的声纹;移除则本次只用音色合成,不会改动形象配置</div>
        </div>
        <!-- 语速:TTS 合成语速,0.5x 慢速沉稳 ~ 2.0x 激情快讲;与后端 schema / worker 同区间 -->
        <div class="pick-field">
          <div class="pick-label">语速（可选）</div>
          <div style="display:flex;align-items:center;gap:12px">
            <n-slider v-model:value="speed" :min="0.5" :max="2" :step="0.1" :marks="speedMarks" style="flex:1" />
            <span style="min-width:42px;text-align:right;color:var(--n-text-color-3);font-size:13px">{{ speed.toFixed(1) }}x</span>
          </div>
          <div class="pick-sub">0.5x 慢速沉稳 · 1.0x 正常 · 2.0x 激情快讲</div>
        </div>

        <!-- 更多设置:小白不调参默认折叠,专业用户展开后仍有完整控制 -->
        <div class="pick-adv">
          <div class="pick-adv-head" @click="advOpen = !advOpen">
            <span class="lbl-inline">更多设置（可选）</span>
            <span class="caret">{{ advOpen ? '收起' : '展开' }}</span>
          </div>
          <div v-if="advOpen" class="pick-adv-body">
            <!-- 成片时长 -->
            <div class="pick-field">
              <div class="pick-label">成片时长</div>
              <div class="chips">
                <span
                  v-for="d in durationOptions"
                  :key="d"
                  :class="['chip', { on: duration === d }]"
                  @click="duration = d"
                >{{ d }}秒</span>
              </div>
              <div class="pick-sub">口播时长以音频为准时,该值仅作目标时长占位</div>
            </div>
            <!-- 画幅 -->
            <div class="pick-field">
              <div class="pick-label">画幅</div>
              <div class="chips">
                <span :class="['chip', { on: ratio === '' }]" @click="ratio = ''">系统默认</span>
                <span
                  v-for="r in RATIO_OPTIONS"
                  :key="r.key"
                  :class="['chip', { on: ratio === r.key }]"
                  @click="ratio = r.key"
                >{{ r.label }}</span>
              </div>
            </div>
            <!-- 清晰度 -->
            <div class="pick-field">
              <div class="pick-label">清晰度</div>
              <div class="chips">
                <span :class="['chip', { on: resolution === '' }]" @click="resolution = ''">系统默认</span>
                <span
                  v-for="r in RES_OPTIONS"
                  :key="r.key"
                  :class="['chip', { on: resolution === r.key }]"
                  @click="resolution = r.key"
                >{{ r.label }}</span>
              </div>
            </div>
            <!-- 出镜视图(派生视图) -->
            <div v-if="poseOptions.length > 1" class="pick-field">
              <div class="pick-label">出镜视图</div>
              <div class="chips">
                <span
                  v-for="p in poseOptions"
                  :key="p.key"
                  :class="['chip', { on: pose === p.key }]"
                  @click="pose = p.key"
                >{{ p.label }}</span>
              </div>
              <div class="pick-sub">派生视图只换姿势/景别,不换人,保持同一张脸</div>
            </div>
            <!-- 背景参考图 -->
            <div class="pick-field">
              <div class="pick-label">背景参考图（可选）</div>
              <div v-if="background" class="bg-preview">
                <img :src="background" alt="背景" />
                <span class="bg-remove" @click="removeBackground">移除</span>
              </div>
              <n-upload v-else :show-file-list="false" accept="image/*" :custom-request="uploadBackground">
                <n-button size="small" :loading="bgUploading" secondary>上传背景图</n-button>
              </n-upload>
              <div class="pick-sub">上传贴近目标场景的画面,数字人将被合成到该背景中</div>
            </div>
            <!-- 带货模式:商品图作为数字人出镜的商品场景背景(主播立于商品场景中口播) -->
            <div class="pick-field">
              <div class="pick-label">商品图（带货模式，可选）</div>
              <div v-if="goods" class="bg-preview">
                <img :src="goods" alt="商品" />
                <span class="bg-remove" @click="removeGoods">移除</span>
              </div>
              <n-upload v-else :show-file-list="false" accept="image/*" :custom-request="uploadGoods">
                <n-button size="small" :loading="goodsUploading" secondary>上传商品图</n-button>
              </n-upload>
              <div class="pick-sub">开启带货:数字人将被合成到该商品场景中,适合"边讲边卖"</div>
            </div>
            <!-- 画中画背景视频:把数字人成片缩成小窗叠到演示/图表背景上(presenter-led-explainer) -->
            <div class="pick-field">
              <div class="pick-label">画中画背景视频（可选）</div>
              <div v-if="overlay" class="bg-preview">
                <video :src="overlay" controls style="max-width:200px;max-height:120px;border-radius:var(--radius-xs);display:block"></video>
                <span class="bg-remove" @click="removeOverlay">移除</span>
              </div>
              <n-upload v-else :show-file-list="false" accept="video/*" :custom-request="uploadOverlay">
                <n-button size="small" :loading="overlayUploading" secondary>上传背景视频</n-button>
              </n-upload>
              <template v-if="overlay">
                <div class="pick-sub">
                  小窗位置：
                  <span
                    v-for="p in PIP_POSITIONS"
                    :key="p.key"
                    :class="['chip', 'mini', { on: pipPosition === p.key }]"
                    @click="pipPosition = p.key"
                  >{{ p.label }}</span>
                </div>
                <div class="pick-sub">
                  小窗大小：
                  <span
                    v-for="sc in PIP_SCALES"
                    :key="sc.key"
                    :class="['chip', 'mini', { on: pipScale === sc.key }]"
                    @click="pipScale = sc.key"
                  >{{ sc.label }}</span>
                </div>
                <div class="pick-sub">
                  背景音量：
                  <span
                    v-for="bv in PIP_BG_VOLUMES"
                    :key="bv.key"
                    :class="['chip', 'mini', { on: pipBgVolume === bv.key }]"
                    @click="pipBgVolume = bv.key"
                  >{{ bv.label }}</span>
                </div>
              </template>
              <div class="pick-sub">提供背景视频后,数字人成片会缩成小窗叠在其上,适合"边讲边演示";背景音量只压背景铺底,数字人口播始终清晰</div>
            </div>
            <!-- 换动作:动作/姿态意图,透传数字人网关 -->
            <div class="pick-field">
              <div class="pick-label">换动作（可选）</div>
              <div class="chips">
                <span
                  v-for="m in MOTION_PRESETS"
                  :key="m.key"
                  :class="['chip', { on: motion === m.key }]"
                  @click="motion = motion === m.key ? '' : m.key"
                >{{ m.label }}</span>
              </div>
              <n-input
                v-model:value="motion"
                maxlength="200"
                placeholder="描述数字人的动作,如:挥手介绍商品;留空则由模型自行表演"
              />
              <div class="pick-sub">模型未支持该能力时自动忽略,不影响出片</div>
            </div>
          </div>
        </div>

        <div class="pick-tip">{{ estTip }}</div>
      </div>
      <template #footer>
        <div class="pick-footer">
          <n-button @click="pickVisible = false">取消</n-button>
          <n-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="submit">开始生成</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 上传我的形象 → 专属数字人(创建与编辑共用同一表单,字段一致) -->
    <n-modal
      v-model:show="createVisible"
      preset="card"
      :title="editingId ? '编辑专属形象' : '上传我的形象，生成专属数字人'"
      style="max-width: 520px"
    >
      <div class="pick-body">
        <div class="pick-field">
          <div class="pick-label">形象图（必填）</div>
          <div v-if="createForm.image" class="bg-preview">
            <img :src="createForm.image" alt="形象" />
            <span class="bg-remove" @click="removeImage">移除</span>
          </div>
          <n-upload v-else :show-file-list="false" accept="image/*" :custom-request="uploadImage">
            <n-button size="small" :loading="imageUploading" secondary>上传正面半身照</n-button>
          </n-upload>
          <div class="pick-sub">口型驱动底图:建议正方形、正面、光线均匀、看镜头的清晰半身照;质量越好,对口型越自然</div>
        </div>
        <div class="pick-field">
          <div class="pick-label">形象名称（必填）</div>
          <n-input v-model:value="createForm.name" maxlength="50" placeholder="如:我的形象 / 老板出镜" />
        </div>
        <div class="pick-field">
          <div class="pick-label">性别</div>
          <div class="chips">
            <span :class="['chip', { on: createForm.gender === '女' }]" @click="createForm.gender = '女'">女</span>
            <span :class="['chip', { on: createForm.gender === '男' }]" @click="createForm.gender = '男'">男</span>
          </div>
        </div>
        <!-- 音色:绑定到该形象,以后每次口播默认用这个声音 -->
        <div class="pick-field">
          <div class="pick-label">默认音色（可选）</div>
          <n-select
            v-model:value="createForm.voice"
            :options="voiceOptions"
            :render-label="renderVoiceLabel"
            placeholder="默认音色(系统)"
            filterable
            clearable
          />
          <div class="pick-sub">豆包语音合成 2.0 官方音色;留空则用网关默认音色,可在每次口播时临时更换</div>
        </div>
        <!-- 声纹复用:绑定一段自己的声音样本,同一形象跨镜头/跨任务保持同一声音 -->
        <div class="pick-field">
          <div class="pick-label">声纹样本（可选）</div>
          <div v-if="createForm.voice_reference" class="bg-preview">
            <audio :src="createForm.voice_reference" controls style="width:100%"></audio>
            <span class="bg-remove" @click="removeVoiceRef">移除</span>
          </div>
          <n-upload v-else :show-file-list="false" accept="audio/*" :custom-request="uploadVoiceRef">
            <n-button size="small" :loading="voiceRefUploading" secondary>上传声纹样本</n-button>
          </n-upload>
          <div class="pick-sub">上传一段约 5s 的清晰人声;绑定后该形象每次口播都用同一声音,优先级高于音色</div>
        </div>
        <div class="pick-field">
          <div class="pick-label">默认口播文案（可选）</div>
          <n-input v-model:value="createForm.default_text" type="textarea" :rows="3" maxlength="500" show-count placeholder="不填也可在口播时临时输入" />
        </div>
        <!-- 风格 / 简介:列表卡片与选人弹窗会展示,便于区分多个专属形象 -->
        <div class="pick-field">
          <div class="pick-label">风格（可选）</div>
          <n-input v-model:value="createForm.style" maxlength="20" placeholder="如:亲和 / 专业 / 干练" />
        </div>
        <div class="pick-field">
          <div class="pick-label">一句话简介（可选）</div>
          <n-input v-model:value="createForm.desc" maxlength="50" show-count placeholder="如:店门口出镜的老板娘" />
        </div>
        <div class="pick-field">
          <div class="pick-label">列表封面图（可选）</div>
          <div v-if="createForm.avatar" class="bg-preview">
            <img :src="createForm.avatar" alt="封面" />
            <span class="bg-remove" @click="removeAvatar">移除</span>
          </div>
          <n-upload v-else :show-file-list="false" accept="image/*" :custom-request="uploadAvatar">
            <n-button size="small" :loading="avatarUploading" secondary>上传封面图</n-button>
          </n-upload>
          <div class="pick-sub">不填则用形象图作为封面;封面图只影响列表展示,不影响口型驱动底图</div>
        </div>
        <div class="pick-tip">生成口播需先在「业务配置」接入数字人模型;专属形象仅你本人可使用</div>
      </div>
      <template #footer>
        <div class="pick-footer">
          <n-button @click="createVisible = false">取消</n-button>
          <n-button type="primary" :loading="creating" @click="submitForm">{{ editingId ? '保存修改' : '创建并生成' }}</n-button>
        </div>
      </template>
    </n-modal>

    <!-- 形象预览 -->
    <n-modal v-model:show="preview.visible" preset="card" :title="`形象预览 - ${preview.name}`" style="max-width: 420px">
      <video v-if="preview.visible" :src="preview.url" controls autoplay style="width:100%;border-radius:var(--radius-xs)"></video>
    </n-modal>

  </div>
</template>

<style scoped>
.av-page {
  min-height: calc(100vh - var(--header-h));
  background: var(--bg);
  display: flex;
  flex-direction: column;
  /* 为移动端底部 tabbar 预留空间,避免内容被遮挡 */
  padding-bottom: calc(var(--nav-h) + env(safe-area-inset-bottom) + var(--s-4));
}

/* 移动端顶部标题栏(设计稿 .header-bar):桌面端隐藏,由全局 AppHeader 承担 */
.page-head { gap: var(--s-2); }
.page-head .ph-back { border: none; cursor: pointer; }
.page-head .ph-upload {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 32px;
  padding: 0 12px;
  border: none;
  border-radius: var(--radius-pill);
  background: var(--brand-bg);
  color: var(--brand);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.page-head .ph-upload:hover { background: var(--brand-xl); }
.page-head .ph-upload svg { display: block; }

.wrap { width: 100%; max-width: 480px; margin: 0 auto; flex: 1; }

/* 平台形象 / 我的形象 切换(设计稿 .tab-switcher) */
.avtabs {
  position: sticky;
  top: var(--header-h);
  z-index: 40;
  display: flex;
  background: var(--bg-elev);
  border-bottom: 1px solid var(--line);
}
.avtab {
  flex: 1;
  height: 48px;
  border: none;
  background: transparent;
  position: relative;
  font-size: 14px;
  color: var(--body-2);
  cursor: pointer;
  transition: color var(--transition-fast);
}
.avtab:hover { color: var(--brand); }
.avtab.on { color: var(--brand); font-weight: 600; }
.avtab.on::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 24px;
  height: 3px;
  border-radius: 2px;
  background: var(--grad-brand);
}

/* 形象卡片网格:移动端 2 列,桌面端 3~4 列 */
.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--s-3);
  padding: var(--s-4);
}
.avatar-card {
  display: flex;
  flex-direction: column;
  background: var(--bg-elev);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  border: 1.5px solid transparent;
  cursor: pointer;
  font-family: inherit;
  transition: transform var(--transition-base), box-shadow var(--transition-base), border-color var(--transition-base);
}
.avatar-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); }
.card-cover {
  position: relative;
  aspect-ratio: 3 / 4;
  background: var(--brand-bg);
  overflow: hidden;
}
.card-cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.card-cover .tag-chip { position: absolute; top: var(--s-2); left: var(--s-2); }
.tag-female { background: linear-gradient(135deg, rgba(124, 58, 237, .1), rgba(236, 72, 153, .1)); color: var(--violet); }
.tag-male { background: linear-gradient(135deg, rgba(79, 70, 229, .1), rgba(59, 130, 246, .1)); color: var(--brand); }
.avplay {
  position: absolute; inset: 0; margin: auto;
  width: 40px; height: 40px; border-radius: 50%;
  background: rgba(15, 23, 42, .38);
  display: flex; align-items: center; justify-content: center;
}
.card-body {
  padding: var(--s-3);
  display: flex;
  flex-direction: column;
  gap: var(--s-2);
}
.card-name { font-size: 14px; font-weight: 500; color: var(--ink); }
.select-btn {
  width: 100%;
  height: 34px;
  border: none;
  border-radius: var(--radius-pill);
  background: var(--grad-brand);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-brand);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}
.select-btn:active { transform: scale(.97); box-shadow: var(--shadow-sm); }
/* 我的形象操作区:编辑 / 删除 */
.avops { display: flex; gap: var(--s-2); }
.avdel {
  flex: 1;
  height: 30px;
  border: 1px solid var(--line);
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--body-2);
  font-size: 12px;
  cursor: pointer;
  transition: color var(--transition-fast), border-color var(--transition-fast);
}
.avdel:hover { color: var(--brand); border-color: var(--brand); }

/* 上传我的形象占位卡(设计稿 mine-grid 上传位) */
.upload-tile {
  align-items: center;
  justify-content: center;
  gap: var(--s-2);
  min-height: 190px;
  padding: var(--s-4);
  background: var(--grad-brand-soft);
  border: 1.5px dashed var(--brand);
  color: var(--brand);
}
.upload-tile .ut-title { font-size: 14px; font-weight: 600; color: var(--brand); }
.upload-tile .ut-sub { font-size: 12px; color: var(--brand-l); }
.mine-empty { padding: var(--s-4); }
.mine-hint { margin: var(--s-3) 0 0; text-align: center; font-size: 12px; color: var(--weak); }

/* 底部提示条(设计稿 .tip-bar) */
.tip-bar {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  margin: 0 var(--s-4) var(--s-4);
  padding: var(--s-3) var(--s-4);
  border-radius: var(--radius);
  background: var(--grad-brand-soft);
  border: 1px solid var(--brand-xl);
}
.tip-icon {
  width: 32px; height: 32px; flex-shrink: 0;
  border-radius: 50%;
  background: var(--grad-brand);
  display: flex; align-items: center; justify-content: center;
}
.tip-text { flex: 1; }
.tip-title { margin: 0; font-size: 14px; font-weight: 600; color: var(--ink-3); }
.tip-sub { margin: 2px 0 0; font-size: 12px; color: var(--body-2); }

/* 选人弹窗 */
.pick-body { display: flex; flex-direction: column; gap: 16px; }
.pick-head { display: flex; gap: 12px; align-items: flex-start; }
.pick-avatar { width: 88px; height: 116px; border-radius: var(--radius); object-fit: cover; background: var(--brand-bg); }
.pick-meta { display: flex; flex-direction: column; gap: 6px; text-align: left; }
.pick-meta .pick-name { font-size: 16px; }
.pick-meta .tag-chip { align-self: flex-start; }
.pick-meta .muted { font-size: 12px; color: var(--weak); }
.pick-field { display: flex; flex-direction: column; gap: 6px; }
.pick-label { font-size: 13px; font-weight: 500; display: flex; align-items: center; gap: 8px; }
.pick-tip { font-size: 12px; color: var(--weak); }
.pick-footer { display: flex; justify-content: flex-end; gap: 12px; }

/* 更多设置(可选)折叠区:默认收起,小白不调参 */
.pick-adv { margin-top: 4px; }
.pick-adv-head { display: flex; align-items: center; justify-content: space-between; cursor: pointer; margin: 6px 0 10px; }
.pick-adv-body { border: 1px dashed var(--line); border-radius: var(--radius-xs); padding: 12px; }
.pick-sub { font-size: 12px; color: var(--weak); margin-top: 6px; line-height: 1.5; }
/* 折叠头文案/箭头(与 AdvancedCreationSettings 同形) */
.lbl-inline { font-size: 13px; font-weight: 500; color: var(--ink); }
.caret { font-size: 12px; color: var(--brand); }
/* 芯片组:与 AdvancedCreationSettings 同形,保证多页面体验一致 */
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip { padding: 7px 16px; border-radius: 18px; background: var(--bg); font-size: 13px; color: var(--body-c); cursor: pointer; border: 1.5px solid transparent; user-select: none; }
.chip.on { background: var(--brand-bg); color: var(--brand); border-color: var(--brand); font-weight: 600; }
/* 小窗 chip:与画中画位置/大小选择共用,尺寸更小 */
.chip.mini { padding: 4px 10px; font-size: 12px; border-radius: 14px; }

/* 多段分镜编辑区 */
.seg-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 8px; }
.seg-item { border: 1px solid var(--line); border-radius: var(--radius-xs); padding: 10px; background: var(--bg); }
.seg-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.seg-no { font-size: 12px; font-weight: 600; color: var(--brand); }
.seg-del { font-size: 12px; color: var(--weak); cursor: pointer; }
.seg-del:hover { color: var(--brand); }
.seg-dur { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
.seg-dur-lbl { font-size: 12px; color: var(--weak); margin-right: 2px; }
/* 背景参考图预览 */
.bg-preview { position: relative; display: inline-block; }
.bg-preview img { max-width: 160px; max-height: 120px; border-radius: var(--radius-xs); display: block; }
.bg-preview .bg-remove { position: absolute; top: 4px; right: 4px; background: rgba(0, 0, 0, .55); color: #fff; font-size: 12px; padding: 2px 8px; border-radius: var(--radius-sm); cursor: pointer; }

/* 桌面端:隐藏移动端标题栏,内容居中放大,卡片多列排布 */
@media (min-width: 768px) {
  .av-page { padding-bottom: var(--s-6); }
  .page-head { display: none; }
  .wrap { max-width: var(--page-max); }
  .avtabs { position: static; border-radius: var(--radius); margin-bottom: var(--s-2); }
  .grid { grid-template-columns: repeat(3, 1fr); gap: var(--s-5); padding: var(--s-5) 0; }
  .tip-bar { margin-left: 0; margin-right: 0; }
  .mine-empty { padding: var(--s-5) 0; }
  .mine-empty .upload-tile { max-width: 420px; margin: 0 auto; }
}
@media (min-width: 1024px) {
  .grid { grid-template-columns: repeat(4, 1fr); }
}
</style>
