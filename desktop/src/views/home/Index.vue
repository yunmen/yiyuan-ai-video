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

const previewVideo = computed(() => (templates.value || []).find((t) => t.video_url)?.video_url || '')

// 三步流程
const steps = [
  { n: '1', title: '选方式', desc: '复刻爆款 / 九宫格 / 模板替换' },
  { n: '2', title: '传素材', desc: '对标视频或商品信息' },
  { n: '3', title: 'AI出片', desc: '自动成片，直接下载' },
]

// 功能入口（更精致的图标装饰）
const features = [
  {
    path: '/studio',
    title: '创作工作台',
    desc: '视频复刻 / 九宫格出片 / 模板替换，一站式出片',
    btn: '立即进入',
    primary: true,
    accent: '#FF4D1C',
    stat: '日均出片 5000+',
    icon: `<svg viewBox="0 0 48 48" fill="none"><rect x="4" y="4" width="40" height="40" rx="12" fill="#FFF0EA"/><rect x="10" y="14" width="22" height="18" rx="4" fill="none" stroke="#FF4D1C" stroke-width="2.2"/><path d="M32 19L40 15V33L32 29V19Z" fill="none" stroke="#FF4D1C" stroke-width="2.2" stroke-linejoin="round"/></svg>`
  },
  {
    path: '/digital',
    title: '数字人口播',
    desc: '选择形象 · 输入台词 · 一键生成口型同步视频',
    btn: '敬请期待',
    primary: false,
    accent: '#3A7BE8',
    stat: '200+ 数字人形象',
    icon: `<svg viewBox="0 0 48 48" fill="none"><rect x="4" y="4" width="40" height="40" rx="12" fill="#EAF2FF"/><circle cx="24" cy="19" r="7" fill="none" stroke="#3A7BE8" stroke-width="2.2"/><path d="M11 40C11 32.8 16.8 27 24 27C31.2 27 37 32.8 37 40" fill="none" stroke="#3A7BE8" stroke-width="2.2" stroke-linecap="round"/></svg>`
  },
  {
    path: '/render',
    title: '视频换口播',
    desc: '上传视频 · 换声/换数字人/换场景 · 秒级重渲染',
    btn: '立即进入',
    primary: false,
    accent: '#18A058',
    stat: '口播同步更精准',
    icon: `<svg viewBox="0 0 48 48" fill="none"><rect x="4" y="4" width="40" height="40" rx="12" fill="#E8F7EE"/><path d="M14 18H34V30H14V18Z" fill="none" stroke="#18A058" stroke-width="2.2" stroke-linejoin="round"/><path d="M20 14V34M28 14V34" stroke="#18A058" stroke-width="2.2" stroke-linecap="round"/></svg>`
  },
]

// Hero 亮点数据
const highlights = [
  { num: '10×', label: '出片效率' },
  { num: '3min', label: '最快成片' },
  { num: '98%', label: '用户好评' },
]

async function loadTemplates() {
  loading.value = true
  try {
    const res = await api.template.recommend.post()
    if (res.code === 1) templates.value = (res.data || []).slice(0, 8)
  } catch (e) { }
  loading.value = false
}

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

async function loadCredits() {
  if (!userStore.isLoggedIn) { userStore.setCreditTotal(null); return }
  try {
    const res = await api.account.credits.post()
    if (res.code === 1) userStore.setCreditTotal(res.data.total)
  } catch (e) { }
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
  } catch (e) { }
  signing.value = false
}

onMounted(() => {
  loadTemplates()
  loadSign()
})
</script>

<template>
  <div class="home-page">
    <!-- ============ HERO ============ -->
    <section class="hero">
      <!-- 装饰元素 -->
      <div class="hero-bg">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>
      </div>
      
      <div class="hero-inner">
        <div class="hero-content">
          <!-- 顶部徽章 -->
          <div class="hero-badge">
            <span class="badge-dot"></span>
            AI 智能成片 · 无需剪辑经验
          </div>
          
          <h1 class="hero-title">
            <span>一键生成</span>
            <span class="title-grad">爆款营销视频</span>
          </h1>
          
          <p class="hero-desc">
            复刻爆款 / 九宫格分镜 / 模板替换 / 数字人口播，<br/>
            一站式出片，日均产出提升 <b>10 倍</b>
          </p>
          
          <!-- CTA -->
          <div class="hero-cta">
            <button class="hero-btn-primary" @click="router.push('/studio')">
              <svg width="16" height="16" viewBox="0 0 16 16"><path d="M3 4L13 8L3 12V4Z" fill="currentColor"/></svg>
              免费开始创作
            </button>
            <button class="hero-btn-ghost" @click="router.push('/works')">
              我的作品
              <svg width="14" height="14" viewBox="0 0 14 14"><path d="M5 3L9 7L5 11" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
          </div>
          
          <!-- 亮点数据 -->
          <div class="hero-highlights">
            <div v-for="h in highlights" :key="h.label" class="hl">
              <b>{{ h.num }}</b>
              <span>{{ h.label }}</span>
            </div>
          </div>
        </div>
        
        <!-- 右侧视觉：桌面端显示 -->
        <div class="hero-visual">
          <div class="phone-frame">
            <div class="phone-notch"></div>
            <div class="phone-screen">
              <!-- 视频预览 -->
              <video
                v-if="previewVideo"
                class="phone-video"
                :src="previewVideo"
                muted loop autoplay playsinline
              ></video>
              <template v-else>
                <div class="phone-placeholder">
                  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                    <rect x="4" y="8" width="40" height="32" rx="6" fill="rgba(255,255,255,.2)"/>
                    <circle cx="18" cy="20" r="4" fill="rgba(255,255,255,.5)"/>
                    <path d="M10 32L20 24L26 30L36 20L42 26V36H6V28L10 32Z" fill="rgba(255,255,255,.3)"/>
                  </svg>
                  <span>实时预览成片效果</span>
                </div>
              </template>
              <!-- 播放按钮 -->
              <div class="phone-play">
                <svg width="20" height="20" viewBox="0 0 20 20"><path d="M6.5 3L15 10L6.5 17V3Z" fill="#fff"/></svg>
              </div>
            </div>
          </div>
          <!-- 浮动装饰卡片 -->
          <div class="float-card fc-1">
            <svg width="14" height="14" viewBox="0 0 16 16"><path d="M2 13L6 9L9 12L14 4V13H2Z" fill="#18A058"/></svg>
            <span>生成完成</span>
            <b>98%</b>
          </div>
          <div class="float-card fc-2">
            <div class="fc-avatars">
              <span></span><span></span><span></span>
            </div>
            <span class="fc-text">5000+ 商家正在使用</span>
          </div>
        </div>
      </div>
    </section>

    <div class="page-wrap main-content">
      <!-- ============ 每日签到 ============ -->
      <div
        v-if="userStore.isLoggedIn"
        class="sign-banner"
        :class="{ done: signData?.signed }"
        @click="doSign"
      >
        <div class="sb-icon">
          <svg width="20" height="20" viewBox="0 0 24 24"><path d="M12 2l2.5 6.5L21 9l-5 4.5L17.5 21 12 17l-5.5 4L8 13.5 3 9l6.5-.5L12 2z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>
        </div>
        <div class="sb-text">
          <b>{{ signData?.signed ? `已连续签到 ${signData.streak} 天` : '每日签到领额度' }}</b>
          <span>{{ signData?.signed ? '明天再来领取～' : `签到可得 ${signData?.daily_credits || 1} 次生成额度` }}</span>
        </div>
        <div class="sb-btn">
          {{ signData?.signed ? '已签到' : (signing ? '签到中' : '签到') }}
        </div>
      </div>

      <!-- ============ 功能入口 ============ -->
      <section class="feat">
        <div
          v-for="f in features"
          :key="f.path"
          class="fcard"
          :class="{ primary: f.primary }"
          @click="router.push(f.path)"
        >
          <div class="fc-accent" :style="{ background: f.accent }"></div>
          <div class="fc-inner">
            <div class="fc-top">
              <div class="fc-icon" v-html="f.icon"></div>
              <div class="fc-info">
                <b>{{ f.title }}</b>
                <span class="fc-stat">{{ f.stat }}</span>
              </div>
            </div>
            <p>{{ f.desc }}</p>
            <div class="fc-btn">
              {{ f.btn }}
              <svg v-if="f.btn !== '敬请期待'" width="14" height="14" viewBox="0 0 14 14"><path d="M5 3L9 7L5 11" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </div>
          </div>
        </div>
      </section>

      <!-- ============ 三步流程 ============ -->
      <section class="steps-section">
        <div class="section-head">
          <h2>3 步搞定爆款视频</h2>
          <span class="section-sub">从创意到成片，从未如此简单</span>
        </div>
        <div class="steps">
          <div v-for="(s, i) in steps" :key="s.n" class="step">
            <div class="step-num">
              {{ s.n }}
              <svg v-if="i < steps.length - 1" class="step-arrow" width="24" height="12" viewBox="0 0 24 12">
                <path d="M0 6H20M15 1L20 6L15 11" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="step-body">
              <b>{{ s.title }}</b>
              <span>{{ s.desc }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- ============ 热门模板 ============ -->
      <section class="hot">
        <div class="section-head">
          <h2>🔥 热门模板</h2>
          <span class="more" @click="router.push('/templates')">
            查看全部
            <svg width="14" height="14" viewBox="0 0 14 14"><path d="M5 3L9 7L5 11" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>
        <n-spin :show="loading">
          <div v-if="templates.length" class="tgrid">
            <div v-for="t in templates" :key="t.id" class="tcard" @click="goTemplate(t)">
              <div class="cover" :style="t.cover ? { backgroundImage: `url(${t.cover})` } : {}">
                <div class="cover-overlay"></div>
                <div class="play">
                  <svg width="16" height="16" viewBox="0 0 18 18"><path d="M6 3L14 9L6 15V3Z" fill="#fff"/></svg>
                </div>
                <div class="tag">做同款</div>
                <div v-if="t.duration" class="dur">{{ t.duration }}s</div>
              </div>
              <p>{{ t.title }}</p>
            </div>
          </div>
          <div v-else-if="!loading" class="hot-empty">模板整理中，先去创作工作台看看吧</div>
        </n-spin>
      </section>

      <!-- ============ CTA Banner ============ -->
      <section class="cta-banner" @click="router.push('/studio')">
        <div class="cta-banner-inner">
          <div class="cta-banner-text">
            <b>准备好做你的第一条爆款视频了吗？</b>
            <span>免费额度每日 0 点重置，现在就开始创作</span>
          </div>
          <button class="cta-banner-btn">
            免费开始
            <svg width="14" height="14" viewBox="0 0 14 14"><path d="M5 3L9 7L5 11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>
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
.page-wrap {
  max-width: var(--page-max);
  margin: 0 auto;
  padding: 0 var(--s-4);
}
.main-content {
  padding-top: var(--s-6);
}

/* ================ HERO ================ */
.hero {
  position: relative;
  background: var(--grad-hero);
  color: #fff;
  overflow: hidden;
}
/* 背景装饰 */
.hero-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: .5;
}
.orb-1 {
  width: 300px; height: 300px;
  top: -80px; left: -80px;
  background: #FFB27A;
  animation: float 8s ease-in-out infinite;
}
.orb-2 {
  width: 200px; height: 200px;
  bottom: -40px; right: -40px;
  background: #FF6A3D;
  animation: float 10s ease-in-out infinite reverse;
}
.orb-3 {
  width: 150px; height: 150px;
  top: 40%; right: 20%;
  background: #FFD0B8;
  opacity: .3;
}
@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(20px, -20px); }
}

.hero-inner {
  position: relative;
  max-width: var(--page-max);
  margin: 0 auto;
  padding: var(--s-8) var(--s-5) var(--s-9);
  display: flex;
  flex-direction: column;
  gap: var(--s-7);
}

.hero-content { text-align: center; }

/* 徽章 */
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, .18);
  backdrop-filter: blur(8px);
  font-size: 12px;
  font-weight: 500;
  margin-bottom: var(--s-4);
  border: 1px solid rgba(255, 255, 255, .25);
}
.badge-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #fff;
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: .6; transform: scale(1.3); }
}

/* 标题 */
.hero-title {
  margin: 0;
  font-size: 32px;
  line-height: 1.2;
  font-weight: 900;
  letter-spacing: -0.5px;
}
.hero-title .title-grad {
  display: block;
  background: linear-gradient(180deg, #FFFFFF 0%, #FFE0CC 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-top: 4px;
}

/* 描述 */
.hero-desc {
  margin: var(--s-4) auto 0;
  font-size: 14px;
  opacity: .92;
  line-height: 1.7;
  max-width: 420px;
}
.hero-desc b {
  font-weight: 700;
  background: rgba(255, 255, 255, .2);
  padding: 2px 8px;
  border-radius: 6px;
}

/* CTA */
.hero-cta {
  margin-top: var(--s-6);
  display: flex;
  gap: var(--s-3);
  justify-content: center;
  flex-wrap: wrap;
}
.hero-btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 48px;
  padding: 0 28px;
  border: none;
  border-radius: var(--radius-pill);
  background: #fff;
  color: var(--brand);
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 12px 32px rgba(0, 0, 0, .2);
  transition: all .2s var(--ease-out);
}
.hero-btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 40px rgba(0, 0, 0, .25);
}
.hero-btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 48px;
  padding: 0 24px;
  border: 1.5px solid rgba(255, 255, 255, .5);
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, .12);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  backdrop-filter: blur(8px);
  transition: all .2s var(--ease-out);
}
.hero-btn-ghost:hover {
  background: rgba(255, 255, 255, .2);
  border-color: rgba(255, 255, 255, .7);
}

/* 亮点数据 */
.hero-highlights {
  margin-top: var(--s-7);
  display: flex;
  justify-content: center;
  gap: var(--s-6);
}
.hl {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.hl b {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.5px;
}
.hl span {
  font-size: 11px;
  opacity: .8;
}

/* 右侧视觉（桌面端） */
.hero-visual {
  display: none;
  position: relative;
  width: 280px;
  margin: 0 auto;
}
.phone-frame {
  width: 280px;
  aspect-ratio: 9 / 16;
  border-radius: 32px;
  padding: 12px;
  background: rgba(255, 255, 255, .2);
  backdrop-filter: blur(10px);
  box-shadow: 0 24px 64px rgba(0, 0, 0, .3);
  position: relative;
}
.phone-notch {
  position: absolute;
  top: 18px;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 20px;
  background: rgba(0, 0, 0, .25);
  border-radius: 0 0 16px 16px;
  z-index: 2;
}
.phone-screen {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 22px;
  overflow: hidden;
  background: linear-gradient(180deg, #FFB27A, #FF3D1C);
}
.phone-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.phone-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: rgba(255, 255, 255, .8);
  font-size: 12px;
  text-align: center;
}
.phone-play {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(0, 0, 0, .35);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
}
/* 浮动卡片 */
.float-card {
  position: absolute;
  background: rgba(255, 255, 255, .95);
  border-radius: var(--radius-lg);
  padding: 10px 14px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, .15);
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--ink);
  backdrop-filter: blur(8px);
}
.fc-1 {
  top: 20px;
  left: -20px;
  animation: floatIn 4s ease-in-out infinite;
}
.fc-1 b {
  color: var(--success);
  font-size: 14px;
}
.fc-2 {
  bottom: 40px;
  right: -30px;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 12px 14px;
  animation: floatIn 4s ease-in-out infinite reverse;
}
.fc-avatars {
  display: flex;
}
.fc-avatars span {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--grad-brand);
  border: 2px solid #fff;
}
.fc-avatars span:nth-child(2) {
  margin-left: -10px;
  background: linear-gradient(135deg, #3A7BE8, #18A058);
}
.fc-avatars span:nth-child(3) {
  margin-left: -10px;
  background: linear-gradient(135deg, #E8873A, #D03050);
}
.fc-text {
  font-size: 11px;
  color: var(--body-c);
  font-weight: 500;
}
@keyframes floatIn {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

/* 签到 */
.sign-banner {
  display: flex;
  align-items: center;
  gap: var(--s-3);
  margin-top: -20px;
  padding: var(--s-4) var(--s-5);
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  cursor: pointer;
  position: relative;
  z-index: 2;
  transition: transform .2s;
}
.sign-banner:active { transform: scale(.98); }
.sign-banner.done { background: #fff; cursor: default; opacity: .75; }
.sb-icon {
  width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
  background: var(--grad-brand);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  box-shadow: var(--shadow-brand);
}
.sign-banner.done .sb-icon { background: #D8DADF; box-shadow: none; }
.sb-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.sb-text b { font-size: 15px; color: var(--ink); }
.sign-banner.done .sb-text b { color: var(--weak); }
.sb-text span { font-size: 12px; color: var(--body-2); }
.sign-banner.done .sb-text span { color: var(--weak); }
.sb-btn {
  flex-shrink: 0;
  height: 36px; padding: 0 20px; border-radius: var(--radius-pill);
  background: var(--grad-brand);
  color: #fff; font-size: 13px; font-weight: 700;
  display: flex; align-items: center;
  box-shadow: var(--shadow-brand);
}
.sign-banner.done .sb-btn { background: var(--bg); box-shadow: none; color: var(--weak); }

/* ================ 功能卡片 ================ */
.feat {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--s-4);
  margin-top: var(--s-5);
}
.fcard {
  position: relative;
  background: #fff;
  border-radius: var(--radius-lg);
  padding: 0;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  overflow: hidden;
  transition: all .25s var(--ease-out);
}
.fcard:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}
.fc-accent {
  position: absolute;
  top: 0; left: 0;
  width: 4px; height: 100%;
  opacity: .8;
}
.fcard.primary .fc-accent { width: 100%; height: 3px; opacity: 1; }
.fc-inner {
  padding: var(--s-5);
  display: flex;
  flex-direction: column;
  gap: var(--s-3);
}
.fc-top {
  display: flex;
  align-items: center;
  gap: var(--s-3);
}
.fc-icon {
  width: 48px; height: 48px;
  flex-shrink: 0;
}
.fc-icon svg { width: 100%; height: 100%; }
.fc-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.fc-info b { font-size: 17px; font-weight: 700; color: var(--ink); }
.fc-stat { font-size: 11px; color: var(--brand); font-weight: 500; }
.fcard.primary .fc-stat { color: var(--body-2); }
.fcard p {
  margin: 0;
  font-size: 13px;
  color: var(--body-c);
  line-height: 1.6;
}
.fc-btn {
  margin-top: auto;
  height: 36px;
  border-radius: var(--radius-pill);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  border: 1.5px solid var(--brand);
  color: var(--brand);
  background: #fff;
  width: fit-content;
  padding: 0 18px;
  transition: all .18s;
}
.fc-btn:hover {
  background: var(--brand);
  color: #fff;
}
.fcard.primary .fc-btn {
  background: var(--brand);
  color: #fff;
}
.fcard.primary .fc-btn:hover {
  background: var(--brand-600);
}

/* ================ 三步流程 ================ */
.steps-section {
  margin-top: var(--s-8);
}
.section-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: var(--s-5);
}
@media (min-width: 768px) {
  .section-head {
    flex-direction: row;
    align-items: baseline;
    justify-content: space-between;
  }
}
.section-head h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  color: var(--ink);
}
.section-sub {
  font-size: 13px;
  color: var(--weak);
}
.more {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 13px;
  color: var(--brand);
  cursor: pointer;
}

.steps {
  position: relative;
  background: #fff;
  border-radius: var(--radius-lg);
  padding: var(--s-5) var(--s-3);
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--s-3);
  box-shadow: var(--shadow-sm);
}
.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--s-2);
  text-align: center;
  padding: var(--s-3) var(--s-2);
  position: relative;
}
.step-num {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--grad-brand);
  color: #fff;
  font-size: 15px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-brand);
  margin-bottom: var(--s-2);
}
.step-arrow {
  display: none;
}
.step-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.step-body b { font-size: 14px; font-weight: 700; color: var(--ink); }
.step-body span { font-size: 12px; color: var(--weak); line-height: 1.5; }

/* ================ 热门模板 ================ */
.hot { margin-top: var(--s-8); }
.tgrid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--s-3);
}
.tcard {
  cursor: pointer;
  transition: transform .2s var(--ease-out);
}
.tcard:hover { transform: translateY(-4px); }
.cover {
  aspect-ratio: 9 / 16;
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
}
.cover-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 40%, rgba(0,0,0,.3) 100%);
  opacity: 0;
  transition: opacity .2s;
}
.tcard:hover .cover-overlay { opacity: 1; }
.play {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(0, 0, 0, .3);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  position: absolute;
  transition: transform .2s, background .2s;
}
.tcard:hover .play {
  transform: scale(1.15);
  background: rgba(255, 77, 28, .8);
}
.tag {
  position: absolute;
  right: 8px;
  bottom: 8px;
  background: var(--brand);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 10px;
}
.dur {
  position: absolute;
  left: 8px;
  bottom: 8px;
  background: rgba(0, 0, 0, .5);
  backdrop-filter: blur(4px);
  color: #fff;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 6px;
  font-weight: 500;
}
.tcard p {
  margin: var(--s-2) 0 0;
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hot-empty { text-align: center; color: var(--weak); font-size: 13px; padding: var(--s-9) 0; }

/* ================ CTA Banner ================ */
.cta-banner {
  margin-top: var(--s-9);
  background: var(--grad-brand);
  border-radius: var(--radius-xl);
  padding: var(--s-6);
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: transform .2s, box-shadow .2s;
  box-shadow: var(--shadow-brand);
}
.cta-banner:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-brand-lg);
}
.cta-banner::after {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 300px;
  height: 300px;
  border-radius: 50%;
  background: rgba(255, 255, 255, .1);
  pointer-events: none;
}
.cta-banner-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-4);
  position: relative;
  z-index: 1;
}
.cta-banner-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #fff;
}
.cta-banner-text b { font-size: 15px; font-weight: 700; }
.cta-banner-text span { font-size: 12px; opacity: .85; }
.cta-banner-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 40px;
  padding: 0 20px;
  border: none;
  border-radius: var(--radius-pill);
  background: #fff;
  color: var(--brand);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  flex-shrink: 0;
}

/* ================ 响应式 ================ */
@media (min-width: 768px) {
  .page-wrap { padding: 0 var(--s-6); }
  .main-content { padding-top: var(--s-7); }

  .hero-inner {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    text-align: left;
    padding: var(--s-9) var(--s-6) var(--s-10);
    gap: var(--s-8);
  }
  .hero-content { text-align: left; flex: 1; max-width: 560px; }
  .hero-title { font-size: 44px; letter-spacing: -1px; }
  .hero-desc { font-size: 15px; margin-left: 0; }
  .hero-cta { justify-content: flex-start; }
  .hero-highlights { justify-content: flex-start; }
  .hero-visual { display: block; }

  /* 功能卡片：桌面端网格 */
  .feat { grid-template-columns: repeat(3, 1fr); margin-top: var(--s-6); }
  .fcard.primary { grid-row: span 1; }

  /* 步骤流程 */
  .steps { padding: var(--s-6); gap: var(--s-4); }
  .step { padding: 0 var(--s-4); flex-direction: row; gap: var(--s-3); text-align: left; }
  .step-num { margin-bottom: 0; flex-shrink: 0; }

  /* 模板网格 */
  .tgrid { grid-template-columns: repeat(4, 1fr); gap: var(--s-4); }
}
@media (min-width: 1100px) {
  .tgrid { grid-template-columns: repeat(5, 1fr); }
  .hero-title { font-size: 52px; }
}
</style>
