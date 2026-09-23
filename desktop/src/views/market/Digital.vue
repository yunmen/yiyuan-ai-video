<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { useUserStore } from '@/store/modules/user'

const router = useRouter()
const userStore = useUserStore()

const avatars = ref([])
const loading = ref(false)

// 选人弹窗:填写口播文案后提交数字人任务
const pickVisible = ref(false)
const current = ref(null)
const script = ref('')
const voice = ref('')
const submitting = ref(false)

// 形象预览弹窗
const preview = ref({ visible: false, url: '', name: '' })

const canSubmit = computed(() => !!script.value.trim())

// 预估(与建单扣减同源):消耗次数与预计耗时不再写死"消耗 1 次"
const estCost = ref(null)
const estSeconds = ref(0)
const estTip = computed(() => {
  const parts = [`提交后将消耗 ${estCost.value ?? 1} 次生成额度`]
  const s = estSeconds.value
  if (s) parts.push(s < 60 ? `预计约 ${s} 秒` : `预计 ${Math.ceil(s / 60)} 分钟内完成`)
  parts.push('可在「我的作品」查看进度')
  return parts.join('，')
})

// 取一次预估:失败不阻断提交(以下单时后端计算结果为准)
async function refreshEstimate() {
  try {
    const res = await api.task.estimate.post({ type: 'digital' })
    if (res.code === 1 && res.data) {
      estCost.value = res.data.cost
      estSeconds.value = res.data.estimate_seconds || 0
    }
  } catch (e) { /* 静默 */ }
}

async function load() {
  loading.value = true
  try {
    const res = await api.digital.list.post({ pageNum: 1, pageSize: 50 })
    if (res.code === 1) avatars.value = res.data || []
  } catch (e) { /* 拦截器已提示 */ }
  loading.value = false
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
  refreshEstimate()
  pickVisible.value = true
}

function showPreview(a) {
  preview.value = { visible: true, url: a.preview_video, name: a.name }
}

async function submit() {
  if (!canSubmit.value) {
    window.$message?.warning('请填写口播文案')
    return
  }
  if (!current.value) return
  submitting.value = true
  try {
    const res = await api.task.digitalCreate.post({
      digital_id: current.value.id,
      text: script.value.trim(),
      voice: voice.value.trim() || undefined,
      device: window.innerWidth <= 768 ? 'mobile' : 'desktop'
    })
    if (res.code === 1 && res.data?.id) {
      pickVisible.value = false
      window.$message?.success('已提交生成，正在为你合成口播视频')
      router.push(`/generate/${res.data.id}`)
    }
  } catch (e) { /* 拦截器已提示 */ }
  submitting.value = false
}

onMounted(load)
</script>

<template>
  <div class="av-page">
    <div class="wrap">
      <n-spin :show="loading">
        <div v-if="avatars.length" class="grid">
          <div v-for="a in avatars" :key="a.id" class="avcard">
            <div class="avcover" @click="a.preview_video && showPreview(a)">
              <img v-if="a.avatar" :src="a.avatar" :alt="a.name" />
              <svg v-else viewBox="0 0 143 180" width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
                <rect width="143" height="180" fill="#F3E8FF"/>
                <circle cx="71.5" cy="70" r="28" fill="#C4A0E8"/>
                <path d="M30 142C30 112 48 96 71.5 96C95 96 113 112 113 142V180H30V142Z" fill="#C4A0E8"/>
              </svg>
              <div v-if="a.preview_video" class="avplay">
                <svg width="20" height="20" viewBox="0 0 24 24"><path d="M9 6L18 12L9 18V6Z" fill="#fff"/></svg>
              </div>
            </div>
            <div class="avname">{{ a.name }}</div>
            <div class="avsub">{{ a.gender === '男' ? '男声' : '女声' }}<template v-if="a.style"> · {{ a.style }}</template></div>
            <div class="avbtn" @click="openPick(a)">选择</div>
          </div>
        </div>
        <n-empty v-else-if="!loading" description="数字人整理中，敬请期待" style="padding:60px 0" />
      </n-spin>
    </div>

    <!-- 填写口播文案并提交 -->
    <n-modal v-model:show="pickVisible" preset="card" :title="`用「${current?.name || ''}」生成口播视频`" style="max-width: 520px">
      <div class="pick-body">
        <div class="pick-head">
          <img v-if="current?.avatar" :src="current.avatar" class="pick-avatar" :alt="current?.name" />
          <div class="pick-meta">
            <b>{{ current?.name }}</b>
            <span class="muted">{{ current?.gender === '男' ? '男声' : '女声' }}<template v-if="current?.style"> · {{ current.style }}</template></span>
            <span v-if="current?.desc" class="muted">{{ current.desc }}</span>
          </div>
        </div>
        <div class="pick-field">
          <div class="pick-label">口播文案</div>
          <n-input
            v-model:value="script"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-count
            placeholder="输入要让数字人念出的台词，例如：欢迎来本店，开业期间全场5折"
          />
        </div>
        <div class="pick-field">
          <div class="pick-label">音色（可选）</div>
          <n-input v-model:value="voice" placeholder="留空使用该数字人的默认音色" />
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

    <!-- 形象预览 -->
    <n-modal v-model:show="preview.visible" preset="card" :title="`形象预览 - ${preview.name}`" style="max-width: 420px">
      <video v-if="preview.visible" :src="preview.url" controls autoplay style="width:100%;border-radius:8px"></video>
    </n-modal>

    <div class="avtip">数字人口播：选择形象，输入台词，一键生成口型同步视频</div>
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
.wrap { max-width: var(--page-max); margin: 0 auto; width: 100%; flex: 1; }
.grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 16px 20px;
}
.avcard {
  width: calc(50% - 8px);
  background: #fff;
  border-radius: var(--radius);
  padding: 8px 8px 12px;
  text-align: center;
  box-shadow: var(--shadow-sm);
  transition: transform .2s, box-shadow .2s;
}
.avcard:hover { transform: translateY(-3px); box-shadow: var(--shadow-brand); }
.avcover {
  aspect-ratio: 143 / 180;
  border-radius: 10px;
  overflow: hidden;
  background: #F3E8FF;
  position: relative;
}
.avcover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.avplay {
  position: absolute; inset: 0; margin: auto;
  width: 40px; height: 40px; border-radius: 50%;
  background: rgba(0, 0, 0, .38);
  display: flex; align-items: center; justify-content: center;
}
.avname { font-size: 13px; font-weight: 500; margin: 8px 0 2px; }
.avsub { font-size: 11px; color: var(--weak); margin-bottom: 8px; }
.avbtn {
  height: 32px;
  border-radius: 16px;
  background: var(--brand-bg);
  color: var(--brand);
  font-size: 13px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.avtip {
  background: #FFF7F2;
  padding: 14px 20px;
  text-align: center;
  font-size: 12px;
  color: #FF7A45;
}

/* 选人弹窗 */
.pick-body { display: flex; flex-direction: column; gap: 16px; }
.pick-head { display: flex; gap: 12px; align-items: center; }
.pick-avatar { width: 56px; height: 56px; border-radius: 10px; object-fit: cover; background: #F3E8FF; }
.pick-meta { display: flex; flex-direction: column; gap: 2px; text-align: left; }
.pick-meta .muted { font-size: 12px; color: var(--weak); }
.pick-field { display: flex; flex-direction: column; gap: 6px; }
.pick-label { font-size: 13px; font-weight: 500; }
.pick-tip { font-size: 12px; color: var(--weak); }
.pick-footer { display: flex; justify-content: flex-end; gap: 12px; }

@media (min-width: 768px) {
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; padding: 20px; }
  .avcard { width: auto; }
}
</style>
