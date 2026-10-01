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
              <video :src="sourceVideo" controls style="max-width:240px;max-height:160px;border-radius:8px;display:block"></video>
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
              <video v-if="scene.endsWith('.mp4')" :src="scene" controls style="max-width:160px;max-height:120px;border-radius:8px;display:block"></video>
              <img v-else :src="scene" alt="场景" style="max-width:160px;max-height:120px;border-radius:8px" />
              <span class="bg-remove" @click="removeScene">移除</span>
            </div>
            <n-upload v-else :show-file-list="false" accept="image/*,video/*" :custom-request="uploadScene">
              <n-button size="small" :loading="sceneUploading" secondary>上传场景图/视频</n-button>
            </n-upload>
          </div>

          <div class="rv-field">
            <div class="rv-label">音色（可选）</div>
            <n-input v-model:value="voice" placeholder="留空使用默认音色" />
          </div>

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
  background: #fff;
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
.bg-preview .bg-remove { position: absolute; top: 4px; right: 4px; background: rgba(0, 0, 0, .55); color: #fff; font-size: 12px; padding: 2px 8px; border-radius: 10px; cursor: pointer; }
</style>
