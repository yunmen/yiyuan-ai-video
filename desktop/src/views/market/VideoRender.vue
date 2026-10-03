<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'
import { uploadFile } from '@/api/model/common'
import { useUserStore } from '@/store/modules/user'
import { useTaskCreate } from '@/composables/useTaskCreate'

const userStore = useUserStore()
const { createAndNavigate } = useTaskCreate()

// 源视频(视频 A)与口播提示词
const sourceVideo = ref('')
const sourceUploading = ref(false)
const prompt = ref('')
const voice = ref('')

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

const submitting = ref(false)

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
  captionTracking.value = false
  ducking.value = true
  captionStyle.value = ''
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
  <div class="av-page">
    <div class="wrap">
      <n-spin :show="false">
        <div class="rv-card">
          <h2 class="rv-title">视频换口播</h2>
          <p class="rv-sub">上传一段视频,输入要让它念出的提示词,可选换声音 / 换数字人 / 换场景(组合)</p>

          <div class="rv-field">
            <div class="rv-label">源视频（视频 A）</div>
            <div v-if="sourceVideo" class="bg-preview">
              <video :src="sourceVideo" controls style="max-width:240px;max-height:160px;border-radius:var(--radius-xs);display:block"></video>
              <span class="bg-remove" @click="removeSource">移除</span>
            </div>
            <n-upload v-else :show-file-list="false" accept="video/*" :custom-request="uploadSource">
              <n-button size="small" :loading="sourceUploading" secondary>上传视频</n-button>
            </n-upload>
          </div>

          <div class="rv-field">
            <div class="rv-label">口播提示词</div>
            <n-input
              v-model:value="prompt"
              type="textarea"
              :rows="4"
              maxlength="2000"
              show-count
              placeholder="输入要让视频重新口播的台词,例如:这家店的开业福利,全场五折仅限三天"
            />
          </div>

          <div class="rv-field">
            <div class="rv-label">变换方式</div>
            <div class="chips">
              <span
                v-for="m in MODE_OPTIONS"
                :key="m.key"
                :class="['chip', { on: mode === m.key }]"
                @click="mode = m.key"
              >{{ m.label }}</span>
            </div>
            <div class="pick-sub">
              换数字人:用平台数字人按提示词口播,可同时选场景 B;只换声音:保留原画面仅重新配音;
              换场景:把真人从绿幕视频抠出贴到场景 B(需绿幕素材)
            </div>
          </div>

          <div v-if="mode === 'digital'" class="rv-field">
            <div class="rv-label">数字人形象（必选）</div>
            <n-select
              v-model:value="digitalId"
              :options="avatars.map(a => ({ label: a.name, value: a.id }))"
              placeholder="选择平台数字人形象"
              clearable
            />
          </div>

          <div v-if="mode !== 'voice'" class="rv-field">
            <div class="rv-label">
              目标场景 B（{{ mode === 'scene' ? '必填' : '可选,同时换场景' }}）
            </div>
            <div v-if="scene" class="bg-preview">
              <video v-if="isVideo(scene)" :src="scene" controls style="max-width:160px;max-height:120px;border-radius:var(--radius-xs);display:block"></video>
              <img v-else :src="scene" alt="场景" style="max-width:160px;max-height:120px;border-radius:var(--radius-xs)" />
              <span class="bg-remove" @click="removeScene">移除</span>
            </div>
            <n-upload v-else :show-file-list="false" accept="image/*,video/*" :custom-request="uploadScene">
              <n-button size="small" :loading="sceneUploading" secondary>上传场景图/视频</n-button>
            </n-upload>
          </div>

          <n-collapse :default-expanded-names="[]" class="rv-adv">
            <n-collapse-item title="高级选项（全部可选）" name="adv">
              <div class="rv-field">
                <div class="rv-label">插入特写画面（可选，即 B-roll）</div>
                <div class="rv-sub">讲解到商品/场景时,把这段素材叠到成片指定时间窗,让画面配合口播。支持图片或视频。</div>
                <div v-if="brollAsset" class="bg-preview">
                  <video v-if="isVideo(brollAsset)" :src="brollAsset" controls style="max-width:160px;max-height:120px;border-radius:var(--radius-xs);display:block"></video>
                  <img v-else :src="brollAsset" alt="B-roll" style="max-width:160px;max-height:120px;border-radius:var(--radius-xs)" />
                  <span class="bg-remove" @click="removeBroll">移除</span>
                </div>
                <n-upload v-else :show-file-list="false" accept="image/*,video/*" :custom-request="uploadBroll">
                  <n-button size="small" :loading="brollUploading" secondary>上传图片或视频</n-button>
                </n-upload>
                <div v-if="brollAsset" class="broll-time">
                  <span>插入起始(秒)</span>
                  <n-input-number v-model:value="brollStart" :min="0" :max="60" size="small" style="width:120px" />
                  <span>插入结束(秒)</span>
                  <n-input-number v-model:value="brollEnd" :min="0" :max="60" size="small" style="width:120px" />
                </div>
                <div v-else class="rv-sub">上传素材后,此处可设置它在成片的插入起止秒数。</div>
              </div>

              <div class="rv-field">
                <div class="rv-label">字幕跟随头部（可选）</div>
                <div class="rv-row">
                  <n-switch v-model:value="captionTracking" />
                  <span class="rv-sub">开启后字幕锚定到说话人头部上方(需服务端配置头部检测网关,未配置自动回退底部字幕)</span>
                </div>
              </div>

              <div class="rv-field">
                <div class="rv-label">声音混音（可选）</div>
                <div class="rv-row">
                  <n-switch v-model:value="ducking" />
                  <span class="rv-sub">开启后背景音乐在人声段自动压低,突出口播清晰度</span>
                </div>
              </div>

              <div class="rv-field">
                <div class="rv-label">字幕风格（可选）</div>
                <n-select
                  v-model:value="captionStyle"
                  :options="CAPTION_STYLE_OPTIONS"
                  placeholder="默认(白字黑边)"
                  clearable
                />
              </div>

              <div class="rv-field">
                <div class="rv-label">音色（可选）</div>
                <n-input v-model:value="voice" placeholder="留空使用默认音色" />
              </div>
            </n-collapse-item>
          </n-collapse>

          <div class="rv-tip">{{ estTip }}</div>
          <n-button type="primary" :loading="submitting" :disabled="!canSubmit" @click="submit" block>
            开始生成
          </n-button>
        </div>
      </n-spin>
    </div>
  </div>
</template>

<style scoped>
.av-page {
  min-height: calc(100vh - var(--header-h));
  background: var(--bg);
  padding-bottom: 80px;
  display: flex;
  flex-direction: column;
}
.wrap { max-width: 680px; margin: 0 auto; width: 100%; flex: 1; padding: 20px; }
.rv-card {
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.rv-title { font-size: 18px; font-weight: 600; margin: 0; }
.rv-sub { font-size: 13px; color: var(--weak); margin: 0; }
.rv-field { display: flex; flex-direction: column; gap: 6px; }
.rv-label { font-size: 13px; font-weight: 500; }
.rv-tip { font-size: 12px; color: var(--weak); }
.pick-sub { font-size: 12px; color: var(--weak); margin-top: 6px; line-height: 1.5; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip { padding: 7px 16px; border-radius: 18px; background: var(--bg); font-size: 13px; color: var(--body-c); cursor: pointer; border: 1.5px solid transparent; user-select: none; }
.chip.on { background: var(--brand-bg); color: var(--brand); border-color: var(--brand); font-weight: 600; }
.bg-preview { position: relative; display: inline-block; }
.bg-preview .bg-remove { position: absolute; top: 4px; right: 4px; background: rgba(0, 0, 0, .55); color: #fff; font-size: 12px; padding: 2px 8px; border-radius: var(--radius-sm); cursor: pointer; }
.broll-time { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 6px; font-size: 12px; color: var(--weak); }
.rv-adv { margin-top: 2px; }
.rv-row { display: flex; align-items: center; gap: 10px; }
</style>
