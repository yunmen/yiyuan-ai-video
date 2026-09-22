<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '@/api'

const router = useRouter()
const route = useRoute()

const detail = ref(null)
const timer = ref(null)
const downloading = ref(false)

// 生成阶段(与后端 TASK_PROFILES 对齐,按任务类型展示)
const STAGES = {
  video: ['解析模板结构', 'AI改写视频脚本', '提交生成任务', '模型生成视频', '回传成片'],
  digital: ['解析口播文案', '合成口播音频', '提交数字人任务', '口型驱动合成', '回传成片']
}
const stages = computed(() => STAGES[detail.value?.type] || STAGES.video)
const isDigital = computed(() => detail.value?.type === 'digital')
const genTitle = computed(() => (isDigital.value ? '正在为你生成数字人口播视频...' : '正在为你生成爆款视频...'))
// 作品标题:视频任务取模板标题,数字人任务取数字人名称
const workTitle = computed(
  () => detail.value?.template_title || detail.value?.params?.digital_name || (isDigital.value ? '数字人口播' : '我的成品')
)

async function fetchDetail() {
  try {
    const res = await api.task.detail.post({ id: Number(route.params.id) })
    if (res.code !== 1) return
    detail.value = res.data
    if (res.data.status === 'processing') {
      if (!timer.value) timer.value = setInterval(fetchDetail, 2000)
    } else {
      stopPolling()
    }
  } catch (e) { /* 拦截器已提示 */ }
}

function stopPolling() {
  if (timer.value) { clearInterval(timer.value); timer.value = null }
}

function formatRemain(sec) {
  if (sec == null || sec <= 0) return '即将完成'
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return m > 0 ? `约 ${m} 分 ${s} 秒` : `约 ${s} 秒`
}

// 返回首页等(后台继续生成)
function leaveGen() {
  stopPolling()
  window.$message?.success('已返回首页，生成完成后会通知你')
  router.push('/home')
}

async function onDownload() {
  if (!detail.value?.result_video) return
  downloading.value = true
  try {
    const videoUrl = detail.value.result_video
    const link = document.createElement('a')
    link.href = videoUrl
    link.download = `视频_${detail.value.template_title}_${Date.now()}.mp4`
    link.target = '_blank'
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.$message?.success('已开始下载 · 无水印高清版')
  } catch (e) {
    window.$message?.error('下载失败，请重试')
  } finally {
    downloading.value = false
  }
}

async function onShare() {
  const url = detail.value?.result_video || window.location.href
  try {
    await navigator.clipboard.writeText(url)
    window.$message?.success('链接已复制，去发给好友吧')
  } catch (e) {
    window.$message?.success('链接已复制，去发给好友吧')
  }
}

async function onRegenerate() {
  try {
    const res = await api.task.regenerate.post({ id: Number(route.params.id) })
    if (res.code === 1) {
      window.$message?.success('已重新生成')
      detail.value = null
      fetchDetail()
      if (!timer.value) timer.value = setInterval(fetchDetail, 2000)
    }
  } catch (e) { /* 拦截器已提示 */ }
}

async function onResume() {
  try {
    const res = await api.task.resume.post({ id: Number(route.params.id) })
    if (res.code === 1) {
      window.$message?.success('已继续生成，将从上次中断处接着完成')
      detail.value = null
      fetchDetail()
      if (!timer.value) timer.value = setInterval(fetchDetail, 2000)
    }
  } catch (e) { /* 拦截器已提示 */ }
}

onMounted(() => {
  fetchDetail()
  timer.value = setInterval(fetchDetail, 2000)
})
onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="gen-page">
    <!-- 生成中 -->
    <template v-if="!detail || detail.status === 'processing'">
      <div class="center">
        <svg class="spin" width="96" height="96" viewBox="0 0 96 96">
          <circle cx="48" cy="48" r="44" fill="none" stroke="#FFE3D9" stroke-width="6"/>
          <path d="M48 4C72.3 4 92 23.7 92 48" fill="none" stroke="#FF4D1C" stroke-width="6" stroke-linecap="round"/>
          <rect x="30" y="34" width="36" height="28" rx="8" fill="#FFF0EA"/>
          <path d="M43 42L54 48L43 54V42Z" fill="#FF4D1C"/>
        </svg>
        <div class="gen-title">{{ genTitle }}</div>
        <div class="prog-wrap">
          <div class="prog-row">
            <span class="stage-now">{{ detail?.stage || '排队等待' }}</span>
            <span class="pct">{{ detail?.progress || 0 }}%</span>
          </div>
          <div class="pbar"><i :style="{ width: (detail?.progress || 0) + '%' }"></i></div>
          <div class="stepsrow">
            <template v-for="(s, i) in stages" :key="s">
              <span :class="detail && stages.indexOf(detail.stage) >= i ? 'done' : 'todo'">{{ s }}</span>
              <span v-if="i < stages.length - 1" class="todo sep"> → </span>
            </template>
          </div>
          <div v-if="detail" class="remain muted">预计剩余 {{ formatRemain(detail.remain_seconds) }}</div>
        </div>
      </div>
      <div class="bottom-tip">
        <p class="muted">生成大约需要 2 分钟，你可以先去做别的事</p>
        <p class="muted">生成完成后会在「我的作品」里找到</p>
        <div class="linkbtn" @click="leaveGen">返回首页等</div>
      </div>
    </template>

    <!-- 生成成功:结果预览 -->
    <template v-else-if="detail.status === 'success'">
      <div class="wrap rcols">
        <div class="rcol-video">
          <div class="vframe" :class="{ fit: detail.result_video }">
            <video
              v-if="detail.result_video"
              :src="detail.result_video"
              :poster="detail.template_cover"
              controls
              playsinline
              class="vframe-video"
            ></video>
            <div v-else class="play">
              <svg width="24" height="24" viewBox="0 0 24 24"><path d="M9 6L18 12L9 18V6Z" fill="#fff"/></svg>
            </div>
            <div class="re" @click="onRegenerate">重新生成</div>
          </div>
        </div>
        <div class="rcol-ops">
          <div class="ops">
            <div class="btn-primary" :class="{ disabled: downloading }" @click="onDownload">
              {{ downloading ? '下载中...' : '下载视频' }}
            </div>
            <div class="muted" style="text-align:center">无水印高清版</div>
            <div class="btn-outline" @click="router.push('/templates')">再做一个</div>
            <div class="share" @click="onShare">分享给好友</div>
          </div>
          <div class="info">
            <b>{{ workTitle }} · 我的成品</b>
            <span class="muted">{{ detail.create_time }} 生成</span>
            <span class="meta">{{ detail.gen_duration }} 秒 · {{ detail.gen_resolution }} 竖版 {{ detail.gen_ratio }}，适合发抖音</span>
            <span class="muted">任务编号：{{ detail.task_no }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- 生成失败 -->
    <template v-else>
      <div class="center">
        <svg width="96" height="96" viewBox="0 0 96 96">
          <circle cx="48" cy="48" r="44" fill="#FFF0EA"/>
          <path d="M34 34L62 62M62 34L34 62" stroke="#FF4D1C" stroke-width="5" stroke-linecap="round"/>
        </svg>
        <div class="gen-title">生成中断了</div>
        <p class="fail-msg">抱歉，生成过程中网络出现波动，已为你安全保存进度。</p>
        <div class="prog-wrap" style="max-width: 360px">
          <div class="prog-row">
            <span class="stage-now">中断时进度</span>
            <span class="pct">{{ detail?.progress || 0 }}%</span>
          </div>
          <div class="pbar"><i :style="{ width: (detail?.progress || 0) + '%' }"></i></div>
        </div>
        <div style="display:flex; gap:12px">
          <div class="btn-primary" style="width:160px" @click="onResume">继续生成</div>
          <div class="btn-outline" style="width:160px" @click="onRegenerate">重新生成</div>
          <div class="btn-outline" style="width:160px" @click="router.push('/templates')">返回模板库</div>
        </div>
        <p class="muted" style="margin-top:4px">继续生成将从上次中断处接着完成，不重复扣额度。</p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.gen-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); display: flex; flex-direction: column; }
.wrap { max-width: var(--page-max); margin: 0 auto; width: 100%; }
.muted { font-size: 12px; color: var(--weak); }

/* 生成中 */
.center {
  flex: 1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 20px; gap: 26px; text-align: center;
}
.spin { animation: spin 2.4s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.gen-title { font-size: 16px; font-weight: 700; }
.fail-msg { font-size: 13px; color: var(--weak); margin: 0; max-width: 320px; line-height: 1.6; }
.prog-wrap { width: 100%; max-width: 420px; display: flex; flex-direction: column; gap: 10px; }
.prog-row { display: flex; justify-content: space-between; font-size: 12px; }
.stage-now { color: var(--body-c); }
.pct { color: var(--brand); font-weight: 700; }
.pbar { height: 8px; border-radius: 4px; background: #F0F1F3; width: 100%; overflow: hidden; }
.pbar i { display: block; height: 100%; width: 0; border-radius: 4px; background: var(--brand); transition: width 0.3s linear; }
.stepsrow { font-size: 12px; }
.stepsrow .done { color: var(--brand); font-weight: 700; }
.stepsrow .todo { color: #C9CCD1; }
.remain { text-align: left; }
.bottom-tip {
  padding: 0 20px 28px;
  display: flex; flex-direction: column; align-items: center; gap: 8px;
}
.bottom-tip p { margin: 0; text-align: center; }
.linkbtn { font-size: 14px; color: var(--brand); font-weight: 500; cursor: pointer; }

/* 结果页 */
.rcol-video { padding: 20px; }
.vframe {
  height: 300px; border-radius: var(--radius); position: relative;
  background: linear-gradient(90deg, #FA8C4D, #DB331F);
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}
/* 有视频时:容器尺寸跟随视频自身比例 —— 竖屏 9:16 若塞进固定高度的宽框,
   object-fit: contain 会在左右留下大片黑边(成片本身没有黑边,是播放器框的问题) */
.vframe.fit { height: auto; width: fit-content; max-width: 100%; margin: 0 auto; background: #000; }
.vframe-video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; background: #000; }
/* fit 态下让视频参与布局撑开容器,max-height 防止竖屏视频高过一屏 */
.vframe.fit .vframe-video {
  position: static; display: block; width: auto; height: auto;
  max-width: 100%; max-height: 62vh;
}
.play {
  width: 56px; height: 56px; border-radius: 50%;
  background: rgba(0, 0, 0, 0.32);
  display: flex; align-items: center; justify-content: center;
}
.re {
  position: absolute; top: 12px; right: 12px; z-index: 2;
  background: rgba(0, 0, 0, 0.42); color: #fff;
  font-size: 11px; padding: 6px 10px; border-radius: 14px; cursor: pointer;
}
.rcol-ops { padding: 0 20px 20px; }
.ops { display: flex; flex-direction: column; align-items: stretch; gap: 12px; }
.btn-primary {
  height: 48px; border-radius: 24px; background: var(--brand); color: #fff;
  font-size: 16px; font-weight: 700;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.btn-primary.disabled { opacity: 0.6; pointer-events: none; }
.btn-outline {
  height: 48px; border-radius: 24px; background: #fff; color: var(--brand);
  font-size: 16px; font-weight: 500; border: 1.5px solid var(--brand);
  display: flex; align-items: center; justify-content: center; cursor: pointer;
}
.share { font-size: 14px; color: var(--body-c); cursor: pointer; text-align: center; }
.info { padding: 16px 0 0; display: flex; flex-direction: column; gap: 6px; }
.info b { font-size: 15px; }
.info .meta { font-size: 12px; color: var(--body-c); }

@media (min-width: 768px) {
  .rcols { display: grid; grid-template-columns: 1.2fr 1fr; gap: 24px; align-items: start; padding: 4px 20px 0; }
  .rcol-video { padding: 20px 0; }
  .rcol-ops { padding: 20px 0; }
}
</style>
