<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '@/api'
import { uploadFile } from '@/api/model/common'
import { useUserStore } from '@/store/modules/user'
import { useTaskEstimate } from '@/composables/useTaskEstimate'
import { useTaskCreate } from '@/composables/useTaskCreate'
import { formatDuration } from '@/utils/format'

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

// 预估逻辑下沉到公共 composable,多页面复用,避免副本漂移
const { estCost, estSeconds, estOptions, refresh: estRefresh } = useTaskEstimate()
const { createAndNavigate } = useTaskCreate()

// 选人弹窗内「更多设置(可选)」:时长 / 画幅 / 清晰度 / 出镜视图 / 背景参考图
const advOpen = ref(false)
const duration = ref(8)
const ratio = ref('')          // 空串=系统默认
const resolution = ref('')     // 空串=系统默认
const pose = ref('')           // 空串=主视图
const background = ref('')     // 空串=无背景
const bgUploading = ref(false)

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

// 取一次预估:携带当前时长,失败不阻断提交(以下单时后端计算结果为准)
function refreshEstimate() {
  return estRefresh('digital', { duration: duration.value })
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
  // 重置高阶设置到默认(系统默认规格 / 主视图 / 无背景)
  advOpen.value = false
  duration.value = 8
  ratio.value = ''
  resolution.value = ''
  pose.value = ''
  background.value = ''
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

async function submit() {
  if (!canSubmit.value) {
    window.$message?.warning('请填写口播文案')
    return
  }
  if (!current.value) return
  submitting.value = true
  try {
    const device = window.innerWidth <= 768 ? 'mobile' : 'desktop'
    const data = await createAndNavigate(
      () => api.task.digitalCreate.post({
        digital_id: current.value.id,
        text: script.value.trim(),
        voice: voice.value.trim() || undefined,
        duration: duration.value,
        ratio: ratio.value || undefined,
        resolution: resolution.value || undefined,
        pose: pose.value || undefined,
        background: background.value || undefined,
        device,
      }),
      { message: '已提交生成，正在为你合成口播视频' }
    )
    if (data) pickVisible.value = false
  } catch (e) { /* 拦截器已提示 */ }
  finally { submitting.value = false }
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

/* 更多设置(可选)折叠区:默认收起,小白不调参 */
.pick-adv { margin-top: 4px; }
.pick-adv-head { display: flex; align-items: center; justify-content: space-between; cursor: pointer; margin: 6px 0 10px; }
.pick-adv-body { border: 1px dashed var(--line); border-radius: 8px; padding: 12px; }
.pick-sub { font-size: 12px; color: var(--weak); margin-top: 6px; line-height: 1.5; }
/* 折叠头文案/箭头(与 AdvancedCreationSettings 同形) */
.lbl-inline { font-size: 13px; font-weight: 500; color: #1a1a1a; }
.caret { font-size: 12px; color: var(--brand); }
/* 芯片组:与 AdvancedCreationSettings 同形,保证多页面体验一致 */
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip { padding: 7px 16px; border-radius: 18px; background: var(--bg); font-size: 13px; color: var(--body-c); cursor: pointer; border: 1.5px solid transparent; user-select: none; }
.chip.on { background: var(--brand-bg); color: var(--brand); border-color: var(--brand); font-weight: 600; }
/* 背景参考图预览 */
.bg-preview { position: relative; display: inline-block; }
.bg-preview img { max-width: 160px; max-height: 120px; border-radius: 8px; display: block; }
.bg-preview .bg-remove { position: absolute; top: 4px; right: 4px; background: rgba(0, 0, 0, .55); color: #fff; font-size: 12px; padding: 2px 8px; border-radius: 10px; cursor: pointer; }

@media (min-width: 768px) {
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; padding: 20px; }
  .avcard { width: auto; }
}
</style>
