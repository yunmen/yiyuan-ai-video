<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'
import { uploadFile } from '@/api/model/common'
import { useUserStore } from '@/store/modules/user'
import { useTaskEstimate } from '@/composables/useTaskEstimate'
import { useTaskCreate } from '@/composables/useTaskCreate'

// AI 创作页:把后端**早已实现但 C 端无法触达**的三条生成链路接出来
// (图片 / 音频 / 文本)。此前只有视频与数字人有页面,这三类任务的
// 路由、worker 工具、计费规则全都齐备,却没有任何入口 —— 能力等于不存在。
//
// ⚠️ 本页暂**不在主导航暴露**(AppHeader 的 menuOptions 中不含 /creator):
//    三条链路尚未在真实网关验收,先以「可直连、不曝光」方式交付,
//    避免对全体用户开放未验证的能力。验收通过后再决定是否加入导航。
const router = useRouter()
const userStore = useUserStore()

// 创作类型,与 worker 的 GenTypeEnum 一致(image/audio/text)
const TAB_LABELS = [
  { key: 'image', label: 'AI 图片' },
  { key: 'audio', label: 'AI 音频' },
  { key: 'text', label: 'AI 文案' },
]
const tab = ref('image')
const submitting = ref(false)
const aiRef = ref([])

// —— 图片 ——
const imgPrompt = ref('')
const imgRatio = ref('1:1')
const imgCount = ref(1)
// 画幅选项与 ImageCreateSchema 的白名单一致(非法值后端会回退默认画幅)
const IMG_RATIOS = ['1:1', '16:9', '9:16', '4:3', '3:4']

// —— 音频 ——
const audioType = ref('tts')
const audioText = ref('')
const audioPrompt = ref('')
const audioLyrics = ref('')
const audioVoice = ref('')
const instrumental = ref(false)

// —— 文本 ——
const textPrompt = ref('')

// 预估逻辑下沉到公共 composable,多页面复用,避免副本漂移
const { estCost, estSeconds, estText, refresh: estRefresh } = useTaskEstimate()
const { createAndNavigate } = useTaskCreate()

// 取一次预估:失败不阻断提交(以下单时后端计算结果为准)
async function refreshEstimate() {
  await estRefresh(tab.value, tab.value === 'image' ? { num_images: imgCount.value } : {})
}

const canSubmit = computed(() => {
  if (tab.value === 'image') return !!imgPrompt.value.trim()
  if (tab.value === 'audio') {
    return audioType.value === 'tts' ? !!audioText.value.trim() : !!audioPrompt.value.trim()
  }
  return !!textPrompt.value.trim()
})

// 切换创作类型:价格与预计耗时随类型变化,重新预估
async function switchTab(key) {
  if (tab.value === key) return
  tab.value = key
  aiRef.value = []
  await refreshEstimate()
}

// 图片参考图(可选):上传后走图生图,不传则纯文生图
async function uploadRef({ file, onFinish, onError, onProgress }) {
  try {
    const url = await uploadFile(file.file, {
      onProgress: (percent) => onProgress({ percent: Math.round(percent * 100) }),
    })
    aiRef.value = [url]
    onFinish()
    window.$message?.success('参考图已上传,将按图生成')
  } catch (e) { onError() }
}
function clearRef() { aiRef.value = [] }

// 图片数量变化会影响单价(每多 1 张可能加价),重新预估
async function onCountChange() {
  await refreshEstimate()
}

// 未登录先引导登录:创作会扣额度,不能等到提交才失败
function requireLogin() {
  if (userStore.isLoggedIn) return true
  window.$message?.warning('请先登录后再创作')
  userStore.openLogin()
  return false
}

async function submit() {
  if (!canSubmit.value || submitting.value) return
  if (!requireLogin()) return
  submitting.value = true
  try {
    const device = window.innerWidth <= 768 ? 'mobile' : 'desktop'
    let createFn
    if (tab.value === 'image') {
      createFn = () => api.task.imageCreate.post({
        prompt: imgPrompt.value.trim(),
        ratio: imgRatio.value,
        num_images: imgCount.value,
        materials: aiRef.value,
        device,
      })
    } else if (tab.value === 'audio') {
      createFn = () => api.task.audioCreate.post({
        audio_type: audioType.value,
        text: audioType.value === 'tts' ? audioText.value.trim() : undefined,
        prompt: audioType.value === 'bgm' ? audioPrompt.value.trim() : undefined,
        lyrics: audioLyrics.value.trim() || undefined,
        voice: audioVoice.value.trim() || undefined,
        is_instrumental: instrumental.value,
        device,
      })
    } else {
      createFn = () => api.task.textCreate.post({ prompt: textPrompt.value.trim(), device })
    }
    await createAndNavigate(createFn, { message: `已扣除 ${estCost.value ?? 1} 次额度,开始生成` })
  } catch (e) { /* 拦截器已提示 */ }
  finally { submitting.value = false }
}

onMounted(refreshEstimate)
</script>

<template>
  <div class="creator-page">
    <div class="wrap">
      <div class="hero">
        <h1>AI 创作</h1>
        <p>图片、音频、文案一次到位 · 生成结果在「我的作品」永久保存</p>
      </div>

      <!-- 创作类型 -->
      <div class="tabs">
        <span
          v-for="t in TAB_LABELS"
          :key="t.key"
          :class="['tab', { on: tab === t.key }]"
          @click="switchTab(t.key)"
        >{{ t.label }}</span>
      </div>

      <div class="pane">
        <!-- 图片 -->
        <template v-if="tab === 'image'">
          <div class="field">
            <div class="lbl">画面描述 <i class="req">*</i></div>
            <textarea
              v-model="imgPrompt"
              class="ta"
              rows="4"
              maxlength="2000"
              placeholder="例如:暖色调的咖啡馆桌面,一杯拉花拿铁,清晨侧逆光,浅景深"
            ></textarea>
          </div>
          <div class="field">
            <div class="lbl">画幅</div>
            <div class="chips">
              <span
                v-for="r in IMG_RATIOS"
                :key="r"
                :class="['chip', { on: imgRatio === r }]"
                @click="imgRatio = r"
              >{{ r }}</span>
            </div>
          </div>
          <div class="field">
            <div class="lbl">生成数量</div>
            <div class="chips">
              <span
                v-for="n in 4"
                :key="n"
                :class="['chip', { on: imgCount === n }]"
                @click="imgCount = n; onCountChange()"
              >{{ n }} 张</span>
            </div>
          </div>
          <div class="field">
            <div class="lbl">参考图(选填)</div>
            <div class="row">
              <n-upload
                accept="image/*"
                :max="1"
                :show-file-list="false"
                :custom-request="uploadRef"
              >
                <div class="up" :class="{ gray: aiRef.length }">{{ aiRef.length ? '已上传' : '上传参考图' }}</div>
              </n-upload>
              <button v-if="aiRef.length" class="link" @click="clearRef">清除</button>
            </div>
            <div class="sub">上传后按参考图生成(图生图);不上传则按文字从零创作</div>
          </div>
        </template>

        <!-- 音频 -->
        <template v-else-if="tab === 'audio'">
          <div class="field">
            <div class="lbl">音频类型</div>
            <div class="chips">
              <span :class="['chip', { on: audioType === 'tts' }]" @click="audioType = 'tts'">语音合成</span>
              <span :class="['chip', { on: audioType === 'bgm' }]" @click="audioType = 'bgm'">背景音乐</span>
            </div>
          </div>
          <template v-if="audioType === 'tts'">
            <div class="field">
              <div class="lbl">朗读文本 <i class="req">*</i></div>
              <textarea
                v-model="audioText"
                class="ta"
                rows="5"
                placeholder="例如:欢迎光临本店,开业期间全场五折,错过再等一年。"
              ></textarea>
            </div>
            <div class="field">
              <div class="lbl">音色(选填)</div>
              <input v-model="audioVoice" class="inp" placeholder="留空使用系统默认音色" />
            </div>
          </template>
          <template v-else>
            <div class="field">
              <div class="lbl">音乐风格 <i class="req">*</i></div>
              <textarea
                v-model="audioPrompt"
                class="ta"
                rows="3"
                placeholder="例如:轻快的国风电子,适合美食短视频,节奏明快"
              ></textarea>
            </div>
            <div class="field">
              <div class="lbl">歌词(选填)</div>
              <textarea
                v-model="audioLyrics"
                class="ta"
                rows="3"
                placeholder="留空则由模型按风格自行发挥"
              ></textarea>
            </div>
            <div class="field">
              <div class="row">
                <div class="lbl">纯音乐</div>
                <n-switch v-model:value="instrumental" />
              </div>
            </div>
          </template>
        </template>

        <!-- 文本 -->
        <template v-else>
          <div class="field">
            <div class="lbl">写作要求 <i class="req">*</i></div>
            <textarea
              v-model="textPrompt"
              class="ta"
              rows="6"
              maxlength="5000"
              placeholder="例如:为一家川味火锅店写 3 条抖音口播文案,每条不超过 30 字,要求有钩子和行动号召"
            ></textarea>
          </div>
        </template>

        <!-- 提交栏 -->
        <div class="footer">
          <div class="est">{{ estText }}</div>
          <button class="gen-btn" :disabled="!canSubmit || submitting" @click="submit">
            {{ submitting ? '提交中...' : '开始生成' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.creator-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); padding: 24px 16px 40px; }
.wrap { max-width: 720px; margin: 0 auto; }
.hero { text-align: center; margin-bottom: 20px; }
.hero h1 { font-size: 22px; font-weight: 700; margin: 0 0 8px; color: var(--ink); }
.hero p { font-size: 13px; color: var(--weak); margin: 0; }
.tabs { display: flex; gap: 10px; justify-content: center; margin-bottom: 16px; flex-wrap: wrap; }
.tab {
  padding: 8px 18px; border-radius: 18px; background: #fff;
  font-size: 14px; color: var(--body-c); cursor: pointer;
  border: 1.5px solid transparent; user-select: none;
}
.tab.on { background: var(--brand-bg); color: var(--brand); border-color: var(--brand); font-weight: 600; }
.pane { background: #fff; border-radius: var(--radius); padding: 20px; }
.field { margin-bottom: 18px; }
.lbl { font-size: 14px; font-weight: 500; margin-bottom: 8px; color: var(--ink); }
.req { color: var(--danger); font-style: normal; }
.sub { font-size: 12px; color: var(--weak); margin-top: 8px; }
.row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.inp, .ta {
  width: 100%; box-sizing: border-box; border: 1.5px solid #e6e8eb; border-radius: var(--radius-sm);
  padding: 10px 12px; font-size: 14px; font-family: inherit; outline: none; background: #fff;
}
.inp:focus, .ta:focus { border-color: var(--brand); }
.ta { resize: vertical; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  padding: 7px 16px; border-radius: 18px; background: var(--bg);
  font-size: 13px; color: var(--body-c); cursor: pointer;
  border: 1.5px solid transparent; user-select: none;
}
.chip.on { background: var(--brand-bg); color: var(--brand); border-color: var(--brand); font-weight: 600; }
.up {
  height: 36px; padding: 0 14px; border-radius: 18px;
  background: var(--brand-bg); color: var(--brand);
  font-size: 13px; font-weight: 500;
  display: flex; align-items: center; cursor: pointer; flex: 0 0 auto;
}
.up.gray { background: var(--bg); color: var(--body-c); }
.link { border: none; background: transparent; color: var(--brand); font-size: 13px; cursor: pointer; }
.footer {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; padding-top: 16px; border-top: 1px solid var(--line); margin-top: 4px;
}
.est { font-size: 13px; color: var(--body-c); }
.gen-btn {
  height: 44px; padding: 0 28px; border-radius: 22px; border: none;
  background: var(--brand); color: #fff; font-size: 15px; font-weight: 700; cursor: pointer;
}
.gen-btn:disabled { opacity: .5; cursor: not-allowed; }
</style>
