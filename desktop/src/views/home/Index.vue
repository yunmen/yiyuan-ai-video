<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import { setPendingRef } from '@/utils/pendingRef'
import api from '@/api'

const router = useRouter()
const userStore = useUserStore()
const templates = ref([])
const loading = ref(false)
const signData = ref(null)
const signing = ref(false)
// 首页 Hero 预览:优先用推荐模板里第一个带真实视频的成片当预览,无可用视频时回退到占位 SVG。
// 之前 Hero 右侧是写死的 SVG 渐变+播放按钮(纯装饰占位),换成真实成片更直观体现产品效果。
const previewVideo = computed(() => (templates.value || []).find((t) => t.video_url)?.video_url || '')

// 三步流程文案与工作台实际链路对齐:先选创作方式,再传素材,最后 AI 出片
const steps = [
  { n: '1', title: '选方式', desc: '复刻爆款 / 九宫格 / 模板替换' },
  { n: '2', title: '传素材', desc: '对标视频或商品信息，替换图文' },
  { n: '3', title: '出视频', desc: 'AI 自动成片，直接下载' },
]

// 入口卡片:与顶栏/工作台信息架构对齐 —— 「选模板做」「上传视频做」都收口在创作工作台,
// 首页不再单独暴露「爆款视频」入口,避免同一能力两个名字造成产品割裂。
const features = [
  {
    path: '/studio',
    title: '创作工作台',
    desc: '视频复刻 / 九宫格出片 / 模板替换，一站式出片',
    btn: '进入工作台',
    primary: true,
    icon: '<rect x="1" y="1" width="38" height="38" rx="12" fill="#FFF0EA"/><rect x="7" y="11" width="19" height="18" rx="4" fill="none" stroke="#FF4D1C" stroke-width="2"/><path d="M26 16.5L32 13V27L26 23.5V16.5Z" fill="none" stroke="#FF4D1C" stroke-width="2" stroke-linejoin="round"/>'
  },
  {
    path: '/digital',
    title: '数字人口播',
    // 能力开发中:文案与按钮统一为"敬请期待";点击仍进入 /digital 的「开发中」占位页
    desc: '开发中，敬请期待',
    btn: '敬请期待',
    primary: false,
    icon: '<rect x="1" y="1" width="38" height="38" rx="12" fill="#FFF0EA"/><circle cx="20" cy="16" r="6" fill="none" stroke="#FF4D1C" stroke-width="2"/><path d="M9 32C9 26.5 13.9 22 20 22C26.1 22 31 26.5 31 32" fill="none" stroke="#FF4D1C" stroke-width="2" stroke-linecap="round"/>'
  },
]

async function loadTemplates() {
  loading.value = true
  try {
    // 首页热门取后台配置的推荐位(未配置时后端按热度兜底)
    const res = await api.template.recommend.post()
    if (res.code === 1) templates.value = (res.data || []).slice(0, 8)
  } catch (e) { /* 拦截器已提示 */ }
  loading.value = false
}

// 热门模板卡片点击:有成片视频的直接进工作台「视频复刻」,并把模板视频预填为对标视频,
// 用户只需上传替换参考图即可开始拆解;无视频的模板回退到模板替换流程页。
// 视频地址经 sessionStorage 中转,不拼进 URL,避免暴露 OSS 存储桶链接。
function goTemplate(t) {
  if (t.video_url) {
    setPendingRef({ url: t.video_url, title: t.title })
    router.push('/studio/replicate')
  } else {
    router.push(`/upload/${t.id}`)
  }
}

async function loadSign() {
  if (!userStore.isLoggedIn) { signData.value = null; return }
  try {
    const res = await api.account.signStatus.post()
    if (res.code === 1) signData.value = res.data
  } catch (e) { signData.value = null }
}

// 同步剩余额度到 store,顶部额度chip 随签到等变化即时更新
async function loadCredits() {
  if (!userStore.isLoggedIn) { userStore.setCreditTotal(null); return }
  try {
    const res = await api.account.credits.post()
    if (res.code === 1) userStore.setCreditTotal(res.data.total)
  } catch (e) { /* 拦截器已提示 */ }
}

async function doSign() {
  if (!userStore.isLoggedIn) { userStore.openLogin(); return }
  if (signData.value?.signed || signing.value) return
  signing.value = true
  try {
    const res = await api.account.sign.post()
    if (res.code === 1) {
      signData.value = { ...(signData.value || {}), signed: true, streak: res.data.streak, credits: res.data.credits }
      window.$message?.success(res.message || '签到成功')
      await loadCredits()
    }
  } catch (e) { /* 拦截器已提示 */ }
  signing.value = false
}

onMounted(() => {
  loadTemplates()
  loadSign()
})
</script>

<template>
  <div class="home-page">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-inner">
        <div class="hero-copy">
          <span class="hero-tag">AI 智能成片 · 无需剪辑</span>
          <h1>一键生成<br />爆款营销视频</h1>
          <p>复刻爆款 / 九宫格分镜 / 模板替换，一站式出片，日均产出提升 10 倍</p>
          <div class="hero-actions">
            <button class="btn-primary" @click="router.push('/studio')">开始创作</button>
            <button class="btn-ghost" @click="router.push('/works')">我的作品</button>
          </div>
        </div>
        <div class="hero-visual">
          <div class="vshell">
            <div class="vscreen">
              <!-- 有真实预览视频时直接播放成片,无则回退到占位插画 -->
              <video
                v-if="previewVideo"
                class="vpreview"
                :src="previewVideo"
                muted
                loop
                autoplay
                playsinline
              ></video>
              <template v-else>
                <svg viewBox="0 0 260 460" width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
                  <defs>
                    <linearGradient id="hg" x1="0" y1="0" x2="1" y2="1">
                      <stop offset="0%" stop-color="#FF9A5A" />
                      <stop offset="100%" stop-color="#FF3D2E" />
                    </linearGradient>
                  </defs>
                  <rect width="260" height="460" fill="url(#hg)" />
                  <circle cx="130" cy="150" r="52" fill="rgba(255,255,255,.22)" />
                  <rect x="40" y="250" width="180" height="14" rx="7" fill="rgba(255,255,255,.65)" />
                  <rect x="66" y="282" width="128" height="10" rx="5" fill="rgba(255,255,255,.42)" />
                  <rect x="84" y="318" width="92" height="10" rx="5" fill="rgba(255,255,255,.28)" />
                </svg>
                <div class="vplay">
                  <svg width="20" height="20" viewBox="0 0 20 20"><path d="M6.5 3L15 10L6.5 17V3Z" fill="#fff"/></svg>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </section>

    <div class="wrap">
      <!-- 每日签到 -->
      <div
        v-if="userStore.isLoggedIn"
        class="sign-banner"
        :class="{ done: signData?.signed }"
        @click="doSign"
      >
        <div class="sb-icon">
          <svg width="22" height="22" viewBox="0 0 24 24"><path d="M12 2l2.5 6.5L21 9l-5 4.5L17.5 21 12 17l-5.5 4L8 13.5 3 9l6.5-.5L12 2z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>
        </div>
        <div class="sb-text">
          <b>{{ signData?.signed ? `已连续签到 ${signData.streak} 天` : '每日签到领额度' }}</b>
          <span>{{ signData?.signed ? '明天再来领取～' : `签到可得 ${signData?.daily_credits || 1} 次生成额度` }}</span>
        </div>
        <div class="sb-btn">{{ signData?.signed ? '已签到' : (signing ? '签到中' : '签到') }}</div>
      </div>

      <!-- 功能入口 -->
      <section class="feat">
        <div
          v-for="f in features"
          :key="f.path"
          class="fcard"
          @click="router.push(f.path)"
        >
          <div class="fc-top">
            <svg width="40" height="40" viewBox="0 0 40 40" v-html="f.icon"></svg>
            <b>{{ f.title }}</b>
          </div>
          <p>{{ f.desc }}</p>
          <div class="fc-btn" :class="{ primary: f.primary }">{{ f.btn }}</div>
        </div>
      </section>

      <!-- 流程 -->
      <section class="steps">
        <div v-for="s in steps" :key="s.n" class="step">
          <div class="n">{{ s.n }}</div>
          <b>{{ s.title }}</b>
          <span>{{ s.desc }}</span>
        </div>
        <div class="step-line"></div>
      </section>

      <!-- 热门模板 -->
      <section class="hot">
        <div class="sec-head">
          <h2>热门模板</h2>
          <span class="more" @click="router.push('/templates')">查看全部
            <svg width="14" height="14" viewBox="0 0 14 14"><path d="M5 3L9 7L5 11" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>
        <n-spin :show="loading">
          <div v-if="templates.length" class="tgrid">
            <div v-for="t in templates" :key="t.id" class="tcard" @click="goTemplate(t)">
              <div class="cover" :style="t.cover ? { backgroundImage: `url(${t.cover})` } : {}">
                <div class="play">
                  <svg width="18" height="18" viewBox="0 0 18 18"><path d="M6 3L14 9L6 15V3Z" fill="#fff"/></svg>
                </div>
                <div class="tag">做同款</div>
                <div v-if="t.duration" class="dur">{{ t.duration }}s</div>
              </div>
              <p>{{ t.title }}</p>
            </div>
          </div>
          <div v-else-if="!loading" class="hot-empty">模板整理中，先去模板库看看吧</div>
        </n-spin>
      </section>
    </div>
  </div>
</template>

<style scoped>
.home-page {
  min-height: calc(100vh - var(--header-h));
  background: var(--bg);
  padding-bottom: 80px;
}
.wrap {
  max-width: var(--page-max);
  margin: 0 auto;
  padding: 0 16px;
}

/* Hero */
.hero {
  background: linear-gradient(120deg, #FF8A3D 0%, #FF4D1C 55%, #F5300F 100%);
  color: #fff;
}
.hero-inner {
  max-width: var(--page-max);
  margin: 0 auto;
  padding: 32px 20px 36px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  text-align: center;
}
.hero-tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, .18);
  font-size: 12px;
}
.hero-copy h1 {
  margin: 14px 0 0;
  font-size: 30px;
  line-height: 1.25;
  font-weight: 800;
}
.hero-copy p {
  margin: 12px 0 0;
  font-size: 14px;
  opacity: .92;
}
.hero-actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}
.btn-primary,
.btn-ghost {
  height: 46px;
  padding: 0 28px;
  border-radius: 23px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  border: none;
}
.btn-primary {
  background: #fff;
  color: #FF4D1C;
  box-shadow: 0 8px 20px rgba(0, 0, 0, .14);
}
.btn-ghost {
  background: rgba(255, 255, 255, .16);
  color: #fff;
  border: 1.5px solid rgba(255, 255, 255, .6);
}
.hero-visual { display: none; }
.vshell {
  width: 260px;
  border-radius: 28px;
  padding: 10px;
  background: rgba(255, 255, 255, .22);
  box-shadow: 0 18px 40px rgba(0, 0, 0, .22);
}
.vscreen {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  aspect-ratio: 9 / 16;
}
.vpreview {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.vplay {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(0, 0, 0, .3);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 每日签到 */
.sign-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: -28px;
  padding: 14px 16px;
  background: linear-gradient(135deg, #FFF4E6, #FFE3C4);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
  cursor: pointer;
}
.sign-banner.done { background: #F4F5F7; cursor: default; }
.sb-icon {
  width: 40px; height: 40px; border-radius: 12px; flex-shrink: 0;
  background: linear-gradient(135deg, #FF8A3D, #FF4D1C);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
}
.sign-banner.done .sb-icon { background: #D8DADF; }
.sb-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.sb-text b { font-size: 15px; color: #6B3B12; }
.sign-banner.done .sb-text b { color: var(--weak); }
.sb-text span { font-size: 12px; color: #9A6B3A; }
.sign-banner.done .sb-text span { color: var(--weak); }
.sb-btn {
  flex-shrink: 0;
  height: 34px; padding: 0 18px; border-radius: 17px;
  background: linear-gradient(135deg, #FF8A3D, #FF4D1C);
  color: #fff; font-size: 13px; font-weight: 700;
  display: flex; align-items: center;
}
.sb-btn:active { transform: scale(.97); }
.sign-banner.done .sb-btn { background: #D8DADF; }

/* 功能卡片 */
.feat {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  margin-top: -28px;
}
/* 登录后显示签到横幅时,功能卡片恢复正常间距,不再上移覆盖横幅 */
.sign-banner + .feat {
  margin-top: 16px;
}
.fcard {
  background: #fff;
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  gap: 10px;
  cursor: pointer;
  transition: transform .2s, box-shadow .2s;
}
.fcard:hover { transform: translateY(-3px); box-shadow: var(--shadow-brand); }
.fc-top { display: flex; align-items: center; gap: 10px; }
.fc-top b { font-size: 18px; }
.fcard p { margin: 0; font-size: 13px; color: var(--body-c); }
.fc-btn {
  margin-top: auto;
  height: 40px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  border: 1.5px solid var(--brand);
  color: var(--brand);
  background: #fff;
}
.fc-btn.primary { background: var(--brand); color: #fff; }

/* 流程 */
.steps {
  position: relative;
  margin-top: 24px;
  background: #fff;
  border-radius: var(--radius-lg);
  padding: 22px 16px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  box-shadow: var(--shadow-sm);
}
.step { display: flex; flex-direction: column; align-items: center; gap: 6px; text-align: center; }
.step .n {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, #FF8A3D, #FF4D1C);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.step b { font-size: 14px; }
.step span { font-size: 12px; color: var(--weak); line-height: 1.5; }

/* 热门模板 */
.hot { margin-top: 32px; }
.sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.sec-head h2 { margin: 0; font-size: 18px; font-weight: 700; }
.more {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 13px;
  color: var(--brand);
  cursor: pointer;
}
.tgrid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.tcard { cursor: pointer; }
.cover {
  aspect-ratio: 159 / 220;
  border-radius: var(--radius);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #FFB88A, #FF5A20);
  background-size: cover;
  background-position: center;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: transform .2s;
}
.tcard:hover .cover { transform: translateY(-3px); }
.play {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(0, 0, 0, .32);
  display: flex;
  align-items: center;
  justify-content: center;
}
.tag {
  position: absolute;
  right: 8px;
  bottom: 8px;
  background: var(--brand);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 10px;
}
.dur {
  position: absolute;
  left: 8px;
  bottom: 8px;
  background: rgba(0, 0, 0, .5);
  color: #fff;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 6px;
}
.tcard p {
  margin: 8px 0 0;
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hot-empty { text-align: center; color: var(--weak); font-size: 13px; padding: 40px 0; }

@media (min-width: 768px) {
  .wrap { padding: 0 24px; }
  .hero-inner {
    flex-direction: row;
    justify-content: space-between;
    text-align: left;
    padding: 48px 24px 56px;
    gap: 40px;
  }
  .hero-copy h1 { font-size: 40px; }
  .hero-copy p { font-size: 15px; }
  .hero-actions { justify-content: flex-start; }
  .hero-visual { display: block; flex-shrink: 0; }
  .feat { grid-template-columns: 1.3fr 1fr; margin-top: -40px; }
  .steps { padding: 26px; gap: 20px; }
  .tgrid { grid-template-columns: repeat(4, 1fr); gap: 18px; }
}
@media (min-width: 1100px) {
  .tgrid { grid-template-columns: repeat(5, 1fr); }
}
</style>
