<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '@/api'
import { uploadFile } from '@/api/model/common'
import { useUserStore } from '@/store/modules/user'
import { useTaskCreate } from '@/composables/useTaskCreate'
import { withCurrentVoiceOption, isDialectVoice, DIALECT_OPTIONS, detectDialectInText } from '@/constants/doubaoVoices'
import { voiceOptionsWithPreview } from '@/constants/voicePreviews'
import { useVoiceLabelRenderer } from '@/utils/voiceOptionRender'

const userStore = useUserStore()
const { createAndNavigate, submitHint } = useTaskCreate()

// 源视频(视频 A)与口播提示词
const sourceVideo = ref('')
const sourceUploading = ref(false)
const prompt = ref('')
const voice = ref('')
// 音色下拉:官方清单(含样音) + 已选自定义音色兜底(管理端自由输入,可能是清单外/方言 ID)
const voiceOptions = computed(() => withCurrentVoiceOption(voiceOptionsWithPreview(), voice.value))
const renderVoiceLabel = useVoiceLabelRenderer()

// 变换方式:数字人 / 只换声音 / 换场景(组合由字段推导)
const mode = ref('digital')
const MODE_OPTIONS = [
  { key: 'digital', label: '换数字人' },
  { key: 'voice', label: '只换声音' },
  { key: 'scene', label: '换场景' },
]

// 换数字人:从平台数字人列表选择
const avatars = ref([])
const digitalId = ref(null)
// 目标场景 B(换场景必填;换数字人时可选,实现"同时换场景+数字人")
const scene = ref('')
const sceneUploading = ref(false)
// 带货模式:商品图(数字人路线生效),作为数字人出镜的商品场景背景
const goods = ref('')
const goodsUploading = ref(false)
// 换动作(数字人路线生效):动作/姿态意图,透传数字人网关;留空由模型自行表演
const motion = ref('')
// 常用动作预设:点选即填入,避免用户凭空想动作描述;可再手工补充
const MOTION_PRESETS = [
  { key: '挥手介绍商品', label: '挥手介绍' },
  { key: '手举商品展示', label: '手举商品' },
  { key: '点头微笑讲解', label: '点头讲解' },
  { key: '指向画面右侧', label: '指向右侧' },
  { key: '双手比划强调', label: '比划强调' },
]

// 方言(数字人路线生效):方言语义键,与口播文案解耦;台词里写「用xx方言」会被自动识别并选中
const dialect = ref('')
const dialectHint = ref('')
function syncDialectFromText() {
  const hit = detectDialectInText(prompt.value)
  if (hit && dialect.value !== hit) {
    dialect.value = hit
    const label = (DIALECT_OPTIONS.find((o) => o.value === hit) || {}).label || hit
    dialectHint.value = `已从台词识别到「${label}」要求,已为你选用方言;请确认台词里只保留要念的内容。`
  } else if (!hit) {
    dialectHint.value = ''
  }
}
watch(prompt, syncDialectFromText)

const submitting = ref(false)
// 「更多设置」折叠区展开状态(默认收起,保持界面简洁)
const advOpen = ref(false)
// 口播文案实时字数(仅展示,不参与提交)
const promptLength = computed(() => (prompt.value || '').length)
// 顶部返回箭头:回到上一页,与设计稿交互一致
function goBack() { window.history.back() }

// 可提交校验:必有源视频与提示词;换数字人必选形象;换场景必传场景
const canSubmit = computed(() => {
  if (!sourceVideo.value || !prompt.value.trim()) return false
  if (mode.value === 'digital' && !digitalId.value) return false
  if (mode.value === 'scene' && !scene.value) return false
  return true
})

// 提示文案:补充「我的作品」查看入口说明
const estTip = computed(() =>
  `提交后将消耗 ${1} 次生成额度,可在「我的作品」查看进度`
)

async function loadAvatars() {
  try {
    const res = await api.digital.list.post({ pageNum: 1, pageSize: 50 })
    if (res.code === 1) avatars.value = res.data || []
  } catch (e) { /* 拦截器已提示 */ }
}

function reset() {
  sourceVideo.value = ''
  prompt.value = ''
  voice.value = ''
  mode.value = 'digital'
  digitalId.value = null
  scene.value = ''
  goods.value = ''
  motion.value = ''
  dialect.value = ''
  dialectHint.value = ''
  captionTracking.value = false
  ducking.value = true
  captionStyle.value = ''
  cardTitle.value = ''
  cardBody.value = ''
  badgeText.value = ''
}

// 源视频上传
async function uploadSource({ file, onFinish, onError, onProgress }) {
  sourceUploading.value = true
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    sourceVideo.value = url
    onFinish()
  } catch (e) {
    onError()
  } finally {
    sourceUploading.value = false
  }
}
function removeSource() { sourceVideo.value = '' }

// 目标场景 B 上传(图片或视频)
async function uploadScene({ file, onFinish, onError, onProgress }) {
  sceneUploading.value = true
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    scene.value = url
    onFinish()
  } catch (e) {
    onError()
  } finally {
    sceneUploading.value = false
  }
}
function removeScene() { scene.value = '' }

// 带货商品图上传(数字人路线生效);单张限制
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

// 可选 B-roll 素材(图片或视频):讲解到商品时叠到成片指定时间窗
const brollAsset = ref('')
const brollUploading = ref(false)
const brollStart = ref(0)
const brollEnd = ref(3)
async function uploadBroll({ file, onFinish, onError, onProgress }) {
  brollUploading.value = true
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    brollAsset.value = url
    onFinish()
  } catch (e) {
    onError()
  } finally {
    brollUploading.value = false
  }
}
function removeBroll() { brollAsset.value = '' }

// 判断素材地址是否为视频(用于预览区分 <video>/<img> 渲染,兼容 .mp4/.webm/.mov 等)
function isVideo(url) {
  if (!url) return false
  return /\.(mp4|webm|mov|m4v|avi|mkv)(\?.*)?$/i.test(url)
}

// 字幕跟随头部(caption-tracking):开启后字幕锚定到说话人头部上方
const captionTracking = ref(false)
// 声音混音 ducking(提升听感):默认开启,人声段自动压低 BGM,突出口播清晰度
const ducking = ref(true)
// 字幕风格预设(对齐 Hypit captions「Fine styles」)
const captionStyle = ref('')
const CAPTION_STYLE_OPTIONS = [
  { label: '默认(白字黑边)', value: '' },
  { label: '醒目(黄字粗描边)', value: 'highlight' },
  { label: '简约(细描边)', value: 'minimal' },
  { label: '活泼(绿字白描边)', value: 'variety' },
]

// 代码渲染层·信息卡(可选,对齐 Hypit lower-thirds):显式提供才叠加,不臆造商品信息
const cardTitle = ref('')
const cardBody = ref('')
// 代码渲染层·角标(可选,对齐 Hypit badge):成片角落的胶囊标签(品牌/卖点/水印)
const badgeText = ref('')
// 代码渲染层·动效信息层(可选,对齐 Hypit 动效组件):仅显式提供才叠加,绝不臆造内容
const rankTitle = ref('')
const rankText = ref('')
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

async function submit() {
  if (!userStore.isLoggedIn) {
    window.$message?.warning('请先登录后再使用视频换口播')
    userStore.openLogin()
    return
  }
  if (!canSubmit.value) {
    window.$message?.warning('请完善源视频、口播提示词与所选变换所需项')
    return
  }
  // 方言音色当前 TTS 网关不支持,提交前拦截,避免白跑一次必然失败的付费任务
  if (isDialectVoice(voice.value)) {
    window.$message?.error('当前网关不支持方言音色,请改选官方清单中的普通话音色')
    return
  }
  submitting.value = true
  try {
    const device = window.innerWidth <= 768 ? 'mobile' : 'desktop'
    const data = await createAndNavigate(
      () => api.task.renderCreate.post({
        source_video: sourceVideo.value,
        prompt: prompt.value.trim(),
        // 变换方式由字段推导:digital_id → 数字人;scene → 换场景;都没有 → 只换声音
        digital_id: mode.value === 'digital' ? digitalId.value : undefined,
        scene: scene.value || undefined,
        // 带货模式:商品图作为数字人出镜场景背景(仅数字人路线生效)
        goods: mode.value === 'digital' ? (goods.value || undefined) : undefined,
        // 换动作:数字人动作/姿态意图(仅数字人路线生效);网关未支持该能力时自动忽略
        motion: mode.value === 'digital' ? (motion.value.trim() || undefined) : undefined,
        // 方言(仅数字人路线生效):方言语义键,经后端透传 TTS 网关
        dialect: mode.value === 'digital' ? (dialect.value || undefined) : undefined,
        voice: voice.value.trim() || undefined,
        // 可选 B-roll 层:把素材叠到成片指定时间窗(讲解到商品时切特写)
        broll: brollAsset.value
          ? {
              asset: brollAsset.value,
              start: Number(brollStart.value) || 0,
              end: Number(brollEnd.value) || 0,
            }
          : undefined,
        // 字幕跟随头部:开启后字幕锚定到说话人头部(需服务端配置头部检测网关,否则回退底部字幕)
        caption_tracking: captionTracking.value,
        // 声音混音 ducking:开启后背景音乐在人声段自动压低,突出口播清晰度
        ducking: ducking.value,
        // 字幕风格预设:留空用默认白字黑边
        caption_style: captionStyle.value || undefined,
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
        device,
      }),
      { message: '已提交生成，正在为你重渲染口播视频' }
    )
    if (data) reset()
  } catch (e) { /* 拦截器已提示 */ }
  finally { submitting.value = false }
}

onMounted(loadAvatars)
</script>

<template>
  <div class="rv-page">
    <!-- 移动端顶部标题栏(桌面端隐藏,改用全局 AppHeader) -->
    <div class="page-head">
      <button class="ph-back" type="button" aria-label="返回" @click="goBack">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m15 18-6-6 6-6" />
        </svg>
      </button>
      <h1 class="ph-title">视频换口播</h1>
      <div class="ph-right"></div>
    </div>

    <div class="rv-body">
      <!-- 上传视频 -->
      <section class="section-card">
        <div class="rc-head">
          <h2 class="section-title">上传视频</h2>
          <span class="tag-chip tag-hot">热门</span>
        </div>

        <!-- 未上传:虚线上传区(点击即触发上传) -->
        <n-upload
          v-if="!sourceVideo"
          class="rv-upload"
          :show-file-list="false"
          accept="video/*"
          :disabled="sourceUploading"
          :custom-request="uploadSource"
        >
          <div class="upload-zone">
            <div class="uz-icon">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="23 7 16 12 23 17 23 7" />
                <rect width="15" height="14" x="1" y="5" rx="2" ry="2" />
              </svg>
            </div>
            <p class="uz-title">点击或拖拽上传视频</p>
            <p class="uz-sub">支持 MP4 / MOV / AVI · 最长 10 分钟</p>
            <span class="uz-btn">{{ sourceUploading ? '上传中…' : '选择文件' }}</span>
          </div>
        </n-upload>

        <!-- 已上传:视频预览 -->
        <div v-else class="video-preview-wrap">
          <div class="video-preview">
            <video :src="sourceVideo" controls class="vp-video"></video>
            <button class="vp-remove" type="button" @click="removeSource">移除</button>
          </div>
          <div class="vp-meta">
            <span class="vp-ok">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 6 9 17l-5-5" />
              </svg>
              视频已就绪
            </span>
            <n-upload :show-file-list="false" accept="video/*" :disabled="sourceUploading" :custom-request="uploadSource">
              <button class="vp-reup" type="button">{{ sourceUploading ? '上传中…' : '重新上传' }}</button>
            </n-upload>
          </div>
        </div>
      </section>

      <!-- 口播文案 -->
      <section class="section-card">
        <h2 class="section-title">口播文案</h2>
        <n-input
          v-model:value="prompt"
          type="textarea"
          :rows="5"
          maxlength="2000"
          placeholder="输入要让视频重新口播的台词,例如:这家店的开业福利,全场五折仅限三天"
        />
        <div class="field-foot">
          <span>已输入 {{ promptLength }} 字</span>
        </div>
      </section>

      <!-- 功能选择 -->
      <section class="section-card">
        <h2 class="section-title">功能选择</h2>
        <div class="chips">
          <span
            v-for="m in MODE_OPTIONS"
            :key="m.key"
            :class="['chip', { on: mode === m.key }]"
            @click="mode = m.key"
          >
            <svg v-if="m.key === 'voice'" class="chip-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" x2="12" y1="19" y2="22" />
            </svg>
            <svg v-else-if="m.key === 'digital'" class="chip-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="8" r="6" />
              <path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11" />
            </svg>
            <svg v-else class="chip-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect width="18" height="18" x="3" y="3" rx="2" />
              <circle cx="9" cy="9" r="2" />
              <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
            </svg>
            <span>{{ m.label }}</span>
          </span>
        </div>
        <div class="pick-sub">
          换数字人:用平台数字人按提示词口播,可同时选场景 B;只换声音:保留原画面仅重新配音;
          换场景:把真人从绿幕视频抠出贴到场景 B(需绿幕素材)
        </div>

        <!-- 换数字人:形象必选 -->
        <div v-if="mode === 'digital'" class="rv-field">
          <div class="rv-label">数字人形象（必选）</div>
          <n-select
            v-model:value="digitalId"
            :options="avatars.map(a => ({ label: a.name, value: a.id }))"
            placeholder="选择平台数字人形象"
            clearable
          />
        </div>

        <!-- 目标场景 B(换场景必填;换数字人时可选) -->
        <div v-if="mode !== 'voice'" class="rv-field">
          <div class="rv-label">目标场景 B（{{ mode === 'scene' ? '必填' : '可选,同时换场景' }}）</div>
          <div v-if="scene" class="bg-preview">
            <video v-if="isVideo(scene)" :src="scene" controls></video>
            <img v-else :src="scene" alt="场景" />
            <span class="bg-remove" @click="removeScene">移除</span>
          </div>
          <n-upload v-else :show-file-list="false" accept="image/*,video/*" :disabled="sceneUploading" :custom-request="uploadScene">
            <div class="up-box">{{ sceneUploading ? '上传中…' : '＋ 上传场景图 / 视频' }}</div>
          </n-upload>
        </div>

        <!-- 带货模式:商品图(数字人路线生效) -->
        <div v-if="mode === 'digital'" class="rv-field">
          <div class="rv-label">商品图（带货模式，可选）</div>
          <div v-if="goods" class="bg-preview">
            <img :src="goods" alt="商品" />
            <span class="bg-remove" @click="removeGoods">移除</span>
          </div>
          <n-upload v-else :show-file-list="false" accept="image/*" :disabled="goodsUploading" :custom-request="uploadGoods">
            <div class="up-box">{{ goodsUploading ? '上传中…' : '＋ 上传商品图' }}</div>
          </n-upload>
          <div class="rv-sub">开启带货:数字人将被合成到该商品场景中,适合"边讲边卖"</div>
        </div>

        <!-- 换动作(数字人路线生效) -->
        <div v-if="mode === 'digital'" class="rv-field">
          <div class="rv-label">换动作（可选）</div>
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
          <div class="rv-sub">动作描述会随任务下发给数字人模型;模型未支持该能力时自动忽略,不影响出片。</div>
        </div>
      </section>

      <!-- 音色选择 + 更多设置 -->
      <section class="section-card">
        <h2 class="section-title">音色选择</h2>
        <n-select
          v-model:value="voice"
          :options="voiceOptions"
          :render-label="renderVoiceLabel"
          placeholder="默认音色(系统)"
          filterable
          clearable
        />
        <div class="rv-sub">豆包语音合成 2.0 官方音色;留空则使用系统默认音色。下拉项右侧 ▶ 可试听样音(样音为 AI 预生成,实际合成以所选项为准)。</div>

        <!-- 更多设置:默认折叠 -->
        <div class="collapse-head" @click="advOpen = !advOpen">
          <span class="collapse-title">更多设置</span>
          <svg class="collapse-arrow" :class="{ open: advOpen }" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m6 9 6 6 6-6" />
          </svg>
        </div>

        <div v-show="advOpen" class="collapse-body">
          <!-- 插入特写画面(B-roll) -->
          <div class="rv-field">
            <div class="rv-label">插入特写画面（可选，即 B-roll）</div>
            <div class="rv-sub">讲解到商品/场景时,把这段素材叠到成片指定时间窗,让画面配合口播。支持图片或视频。</div>
            <div v-if="brollAsset" class="bg-preview">
              <video v-if="isVideo(brollAsset)" :src="brollAsset" controls></video>
              <img v-else :src="brollAsset" alt="B-roll" />
              <span class="bg-remove" @click="removeBroll">移除</span>
            </div>
            <n-upload v-else :show-file-list="false" accept="image/*,video/*" :disabled="brollUploading" :custom-request="uploadBroll">
              <div class="up-box">{{ brollUploading ? '上传中…' : '＋ 上传图片或视频' }}</div>
            </n-upload>
            <div v-if="brollAsset" class="broll-time">
              <span>插入起始(秒)</span>
              <n-input-number v-model:value="brollStart" :min="0" :max="60" size="small" style="width:120px" />
              <span>插入结束(秒)</span>
              <n-input-number v-model:value="brollEnd" :min="0" :max="60" size="small" style="width:120px" />
            </div>
            <div v-else class="rv-sub">上传素材后,此处可设置它在成片的插入起止秒数。</div>
          </div>

          <!-- 字幕跟随头部 -->
          <div class="rv-field">
            <div class="rv-label">字幕跟随头部（可选）</div>
            <div class="rv-row">
              <n-switch v-model:value="captionTracking" />
              <span class="rv-sub">开启后字幕锚定到说话人头部上方(需服务端配置头部检测网关,未配置自动回退底部字幕)</span>
            </div>
          </div>

          <!-- 声音混音 -->
          <div class="rv-field">
            <div class="rv-label">声音混音（可选）</div>
            <div class="rv-row">
              <n-switch v-model:value="ducking" />
              <span class="rv-sub">开启后背景音乐在人声段自动压低,突出口播清晰度</span>
            </div>
          </div>

          <!-- 字幕风格 -->
          <div class="rv-field">
            <div class="rv-label">字幕风格（可选）</div>
            <n-select
              v-model:value="captionStyle"
              :options="CAPTION_STYLE_OPTIONS"
              placeholder="默认(白字黑边)"
              clearable
            />
          </div>

          <!-- 方言(数字人路线生效) -->
          <div v-if="mode === 'digital'" class="rv-field">
            <div class="rv-label">方言（可选）</div>
            <n-select v-model:value="dialect" :options="DIALECT_OPTIONS" placeholder="普通话(默认)" clearable />
            <div class="rv-sub">豆包语音 2.0 音色自带多方言(川渝含重庆/四川、粤语、东北、北京、天津、河南、上海、陕西、台湾、广西);网关不支持则忽略。也可直接在口播文案里写「用xx方言」,会自动选中。</div>
            <div v-if="dialectHint" class="rv-warn">{{ dialectHint }}</div>
          </div>

          <!-- 信息卡 -->
          <div class="rv-field">
            <div class="rv-label">信息卡（可选）</div>
            <div class="rv-sub">在成片底部叠加一张设计感信息卡(标题 + 正文),突出商品名/卖点。仅填了才出现,绝不臆造信息。</div>
            <n-input v-model:value="cardTitle" placeholder="卡片标题,如:开业福利" maxlength="20" show-count />
            <n-input
              v-model:value="cardBody"
              type="textarea"
              :rows="2"
              placeholder="卡片正文,如:全场五折仅限三天"
              maxlength="40"
              show-count
            />
          </div>

          <!-- 角标 -->
          <div class="rv-field">
            <div class="rv-label">角标（可选）</div>
            <div class="rv-sub">在成片右上角叠加一枚胶囊标签,如品牌名/卖点/「AI 生成」水印。</div>
            <n-input v-model:value="badgeText" placeholder="角标文字,如:限时特惠" maxlength="12" show-count />
          </div>

          <!-- 动效层 -->
          <div class="rv-field">
            <div class="rv-label">动效层（可选）</div>
            <div class="rv-sub">在成片叠加排行榜 / 揭示板 / 彩色闪烁 / 评论贴纸等动效;仅填了才出现,绝不臆造内容。</div>

            <div class="rv-sub strong">排行榜（逐条落位）</div>
            <n-input v-model:value="rankTitle" placeholder="榜单标题,如:本周热度榜" maxlength="20" show-count />
            <n-input
              v-model:value="rankText"
              type="textarea"
              :rows="3"
              placeholder="每行一条:名称 数值(或 名称|数值),如 小龙虾 98 / 烤鸭 87"
              style="margin-top:8px"
            />
            <div class="row-wrap">
              <n-input-number v-model:value="rankStart" :min="0" placeholder="首条出现(ms)" style="width:160px" />
              <n-input-number v-model:value="rankStagger" :min="80" placeholder="逐条错峰(ms)" style="width:160px" />
            </div>

            <div class="rv-sub strong">揭示板（表情符号弹出）</div>
            <div class="row-wrap">
              <n-input v-model:value="revealText" placeholder="揭示文案,如:上新啦" maxlength="20" show-count style="flex:1;min-width:200px" />
              <n-input v-model:value="revealEmoji" placeholder="emoji ✨" maxlength="4" style="width:120px" />
              <n-input-number v-model:value="revealAt" :min="0" placeholder="出现(ms)" style="width:140px" />
            </div>

            <div class="rv-sub strong">彩色闪烁</div>
            <div class="row-wrap">
              <n-input v-model:value="flashColor" placeholder="颜色 #RRGGBB" maxlength="9" style="width:160px" />
              <n-input-number v-model:value="flashAt" :min="0" placeholder="出现(ms)" style="width:140px" />
              <n-input-number v-model:value="flashDur" :min="120" placeholder="时长(ms)" style="width:140px" />
            </div>

            <div class="rv-sub strong">评论贴纸（侧边滑入）</div>
            <div class="row-wrap">
              <n-input v-model:value="stickerText" placeholder="贴纸文案,如:这个我买过" maxlength="30" show-count style="flex:1;min-width:200px" />
              <n-select v-model:value="stickerSide" :options="[{label:'左侧',value:'l'},{label:'右侧',value:'r'}]" style="width:120px" />
              <n-input-number v-model:value="stickerAt" :min="0" placeholder="出现(ms)" style="width:140px" />
            </div>

            <div class="rv-sub strong">自动 B-roll（对齐）</div>
            <div class="rv-row">
              <n-switch v-model:value="autoBrollEnabled" />
              <span class="rv-sub">开启后按时间轴自动插入商品/场景特写,失败自动回退原片</span>
            </div>
            <template v-if="autoBrollEnabled">
              <div class="row-wrap">
                <n-select v-model:value="autoBrollSource" :options="[{label:'商品图',value:'goods'},{label:'场景图',value:'scene'},{label:'指定URL',value:'url'},{label:'自动生成',value:'gen'}]" style="width:140px" />
                <n-select v-model:value="autoBrollStrategy" :options="[{label:'均匀插窗',value:'even'},{label:'关键词命中',value:'mention'}]" style="width:140px" />
                <n-select v-model:value="autoBrollPos" :options="[{label:'居中',value:'center'},{label:'右下',value:'br'},{label:'左下',value:'bl'},{label:'右上',value:'tr'},{label:'左上',value:'tl'}]" style="width:140px" />
              </div>
              <n-input v-if="autoBrollStrategy === 'mention'" v-model:value="autoBrollKeywords" placeholder="关键词,用逗号分隔,如 小龙虾,烤鸭" style="margin-top:8px" />
              <n-input v-if="autoBrollSource === 'gen'" v-model:value="autoBrollPrompt" type="textarea" placeholder="文生图提示词,描述想穿插的画面,如 食材翻炒特写、城市夜景空镜" style="margin-top:8px" />
              <div class="row-wrap">
                <n-input-number v-model:value="autoBrollInterval" :min="2" placeholder="间隔(秒)" style="width:140px" />
                <n-input-number v-model:value="autoBrollWindow" :min="1" placeholder="单窗(秒)" style="width:140px" />
              </div>
            </template>
          </div>
          <div class="rv-tip">{{ estTip }}</div>
          <n-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="submit" block>
            {{ submitting ? submitHint : '开始生成' }}
          </n-button>
        </div>
      </section>

      <!-- 底部固定主操作(移动端悬浮于底部导航之上;桌面端回落为普通区块) -->
      <div class="bottom-action">
        <button class="btn-primary rv-submit" type="button" :disabled="!canSubmit || submitting" @click="submit">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          {{ submitting ? '提交中…' : '开始换口播' }}
        </button>
        <p class="ba-tip">{{ estTip }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rv-page {
  min-height: calc(100vh - var(--header-h));
  background: var(--bg);
}
/* 移动端顶部标题栏用全局 .page-head 样式,桌面端隐藏;h1 需清除浏览器默认外边距 */
.page-head { z-index: 50; }
.page-head .ph-title { margin: 0; }

.rv-body {
  padding: var(--s-4);
  padding-bottom: calc(var(--nav-h) + 128px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  gap: var(--s-4);
}

/* 章节卡头(标题 + 右侧标签) */
.rc-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--s-3); }
.rc-head .section-title { margin: 0; }

/* 虚线上传区:n-upload 触发器铺满整宽,保证虚线上传区/加号框为整宽块 */
.rv-body :deep(.n-upload),
.rv-body :deep(.n-upload-trigger) { display: block; width: 100%; }
.upload-zone {
  border: 2px dashed var(--border-medium);
  border-radius: var(--radius-lg);
  background: var(--grad-brand-soft);
  padding: var(--s-8) var(--s-6);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-base);
}
.upload-zone:active { border-color: var(--brand); background: var(--brand-bg); transform: scale(.99); }
.uz-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-lg);
  background: var(--grad-brand);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--s-3);
  box-shadow: var(--shadow-brand);
}
.uz-title { font-size: 14px; font-weight: 600; color: var(--ink-2); margin: 0 0 4px; }
.uz-sub { font-size: 12px; color: var(--weak); margin: 0 0 var(--s-3); }
.uz-btn {
  font-size: 12px;
  font-weight: 500;
  color: var(--brand);
  background: var(--brand-bg);
  padding: 6px 16px;
  border-radius: var(--radius-pill);
}

/* 视频预览 */
.video-preview {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  background: #000;
  aspect-ratio: 16 / 9;
}
.vp-video { width: 100%; height: 100%; object-fit: contain; display: block; background: #000; }
.vp-remove {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0, 0, 0, .6);
  color: #fff;
  font-size: 12px;
  padding: 6px 10px;
  border-radius: var(--radius-pill);
  border: none;
  cursor: pointer;
  backdrop-filter: blur(4px);
}
.vp-meta { display: flex; align-items: center; justify-content: space-between; margin-top: var(--s-3); }
.vp-ok { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--body-2); }
.vp-ok svg { color: var(--success); }
.vp-reup {
  font-size: 12px;
  color: var(--brand);
  background: var(--brand-bg);
  padding: 6px 14px;
  border-radius: var(--radius-pill);
  border: none;
  cursor: pointer;
}

/* 文案字数行 */
.field-foot { display: flex; justify-content: flex-end; margin-top: var(--s-2); font-size: 12px; color: var(--weak); }

/* 字段通用 */
.rv-field { display: flex; flex-direction: column; gap: 6px; margin-top: var(--s-4); }
.rv-label { font-size: 13px; font-weight: 500; color: var(--ink-3); }
.rv-sub { font-size: 12px; color: var(--weak); margin: 0; line-height: 1.5; }
.rv-sub.strong { font-weight: 600; color: var(--body-c); margin-top: var(--s-3); }
.pick-sub { font-size: 12px; color: var(--weak); margin-top: var(--s-3); line-height: 1.5; }
.rv-row { display: flex; align-items: center; gap: 10px; }
.rv-warn { font-size: 12px; color: var(--warning); line-height: 1.5; }
.row-wrap { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }

/* 芯片组 */
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip-icon { width: 16px; height: 16px; }

/* 小号上传按钮 */
.up-box {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1.5px dashed var(--border-medium);
  border-radius: var(--radius-md);
  padding: 14px;
  color: var(--weak);
  font-size: 13px;
  cursor: pointer;
  background: var(--bg);
  transition: all var(--transition-fast);
}
.up-box:hover, .up-box:active { border-color: var(--brand); color: var(--brand); background: var(--brand-bg); }

/* 素材预览 */
.bg-preview { position: relative; display: inline-block; }
.bg-preview img, .bg-preview video { max-width: 180px; max-height: 140px; border-radius: var(--radius-sm); display: block; }
.bg-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  background: rgba(0, 0, 0, .55);
  color: #fff;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.broll-time { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 6px; font-size: 12px; color: var(--weak); }

/* 折叠区(更多设置) */
.collapse-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--s-4);
  padding-top: var(--s-4);
  border-top: 1px solid var(--line-2);
  cursor: pointer;
}
.collapse-title { font-size: 14px; font-weight: 500; color: var(--ink-3); }
.collapse-arrow { color: var(--weak); transition: transform var(--transition-base); }
.collapse-arrow.open { transform: rotate(180deg); }
.collapse-body { padding-top: var(--s-4); display: flex; flex-direction: column; gap: var(--s-4); }

/* 底部固定主操作 */
.bottom-action {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: calc(var(--nav-h) + env(safe-area-inset-bottom));
  width: 100%;
  max-width: 480px;
  background: rgba(255, 255, 255, .95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: 1px solid var(--border-light);
  padding: 12px var(--s-4) calc(12px + env(safe-area-inset-bottom));
  z-index: 45;
}
.rv-submit {
  width: 100%;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  border-radius: var(--radius-md);
  border: none;
  color: #fff;
  transition: all var(--transition-fast);
}
.rv-submit:active { transform: scale(.98); }
.rv-submit:disabled { opacity: .5; cursor: not-allowed; }
.ba-tip { margin: 8px 0 0; text-align: center; font-size: 12px; color: var(--weak); }

/* 桌面端:隐藏移动端标题栏,内容居中并两列排布,底部操作回落到文档流 */
@media (min-width: 768px) {
  .page-head { display: none; }
  .rv-body {
    max-width: var(--page-max);
    margin: 0 auto;
    padding: var(--s-6) var(--s-6) 64px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--s-5);
    align-items: start;
  }
  .bottom-action {
    position: static;
    transform: none;
    width: 100%;
    max-width: none;
    grid-column: 1 / -1;
    background: transparent;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
    border-top: none;
    padding: 0;
    margin-top: var(--s-2);
  }
}
</style>
