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

const creditTotal = computed(() => userStore.creditTotal)
const quotaText = computed(() => (userStore.isLoggedIn ? `${creditTotal.value ?? '—'} 额度` : '登录'))

// 功能入口（与设计稿 4 宫格一致）
const features = [
  {
    path: '/studio',
    title: '创作工作台',
    desc: '视频复刻 · 九宫格出片',
    color: '#4F46E5',
    bg: 'var(--grad-brand-soft)',
    icon: '<path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path>',
  },
  {
    path: '/digital',
    title: '数字人口播',
    desc: '真人形象 · 智能播报',
    color: '#7C3AED',
    bg: 'linear-gradient(135deg, rgba(124,58,237,0.1) 0%, rgba(236,72,153,0.1) 100%)',
    icon: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle>',
  },
  {
    path: '/render',
    title: '视频换口播',
    desc: '一键替换 · 多语言支持',
    color: '#3B82F6',
    bg: 'linear-gradient(135deg, rgba(59,130,246,0.1) 0%, rgba(79,70,229,0.1) 100%)',
    icon: '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>',
  },
  {
    path: '/ai-flavor',
    title: '文案去味',
    desc: 'AI优化 · 爆款文案',
    color: '#10B981',
    bg: 'linear-gradient(135deg, rgba(16,185,129,0.1) 0%, rgba(59,130,246,0.1) 100%)',
    icon: '<path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>',
  },
]

// 三步流程
const steps = [
  { n: 1, title: '选方式', desc: '复刻/九宫格' },
  { n: 2, title: '传素材', desc: '视频/商品图' },
  { n: 3, title: 'AI出片', desc: '一键生成' },
]

// 模板兜底数据（接口无数据时展示，保证与设计稿一致的观感）
const demoWorks = [
  { id: 'd1', title: '好物分享口播', meta: '数字人 · 15s', views: '12.8w', rate: '98%好评', badge: '爆款', img: '/assets/digital-avatars.jpg' },
  { id: 'd2', title: '产品展示九宫格', meta: '分镜 · 30s', views: '8.5w', rate: '95%好评', badge: '新品', img: '/assets/hero-main.jpg' },
  { id: 'd3', title: '剧情反转种草', meta: '剧情 · 45s', views: '6.2w', rate: '92%好评', badge: '', img: '/assets/studio-workflow.jpg' },
  { id: 'd4', title: '知识科普讲解', meta: '口播 · 60s', views: '5.1w', rate: '90%好评', badge: '', img: '/assets/digital-avatars.jpg' },
]

const fallbackImgs = ['/assets/digital-avatars.jpg', '/assets/hero-main.jpg', '/assets/studio-workflow.jpg']

const hotList = computed(() => {
  if (!templates.value.length) return demoWorks
  return templates.value.slice(0, 4).map((t, i) => ({
    id: t.id,
    title: t.title,
    meta: t.duration ? `模板 · ${t.duration}s` : '模板',
    views: ['12.8w', '8.5w', '6.2w', '5.1w'][i] || '3.2w',
    rate: `${94 - i}%好评`,
    badge: i === 0 ? '爆款' : (i === 1 ? '新品' : ''),
    img: t.cover || fallbackImgs[i % fallbackImgs.length],
    video_url: t.video_url,
  }))
})

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
  } else if (String(t.id).startsWith('d')) {
    router.push('/templates')
  } else {
    router.push(`/upload/${t.id}`)
  }
}

// 移动端没有全局顶栏,额度徽章作为进入个人中心(含余额/订单/设置)的入口
function onQuota() {
  if (!userStore.isLoggedIn) { userStore.openLogin(); return }
  router.push('/user')
}

onMounted(loadTemplates)
</script>

<template>
  <div class="home-page">
    <!-- ============ HERO ============ -->
    <header class="hero">
      <div class="hero-bg"><span class="orb orb-a"></span><span class="orb orb-b"></span></div>

      <div class="hero-inner">
        <!-- 移动端顶部：Logo + 额度 -->
        <div class="hero-top">
          <div class="hero-logo">
            <span class="logo-badge">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="23 7 16 12 23 17 23 7"></polygon>
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
              </svg>
            </span>
            <span class="logo-text">一源AI</span>
          </div>
          <button class="quota-badge" @click="onQuota">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
            </svg>
            <span>{{ quotaText }}</span>
          </button>
        </div>

        <div class="hero-main">
          <div class="hero-content">
            <div class="hero-pill">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#FCD34D" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
              <span>今日限时 · 新用户前 3 条免费</span>
            </div>

            <h1 class="hero-title">
              别人的爆款视频<br>1 分钟改成你的
            </h1>
            <p class="hero-desc">
              不用拍、不用剪、不用写文案 · 上传一条对标视频，AI 自动生成 10 条原创带货片
            </p>

            <div class="hero-visual">
              <div class="hero-img">
                <img src="/assets/hero-main.jpg" alt="AI视频创作" />
                <div class="hero-img-mask"></div>
                <div class="hero-img-meta">
                  <div class="hm-left">
                    <span class="av a1"></span><span class="av a2"></span><span class="av a3"></span>
                    <span class="hm-text">10万+ 创作者在用</span>
                  </div>
                  <div class="hm-right">
                    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                    </svg>
                    4.9 分好评
                  </div>
                </div>
              </div>
            </div>

            <button class="hero-cta" @click="router.push('/studio')">
              <span>立即免费生成</span>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            </button>

            <div class="hero-sub">
              <span class="hs-item">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                微信一键登录
              </span>
              <span class="hs-dot">·</span>
              <span class="hs-item">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                不满意不扣费
              </span>
              <span class="hs-dot">·</span>
              <span class="hs-item hs-warn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
                剩余 127 个名额
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>

    <div class="home-body">
      <!-- ============ 功能入口 ============ -->
      <section class="feat">
        <div class="feat-grid">
          <button v-for="f in features" :key="f.path" class="feature-card" @click="router.push(f.path)">
            <span class="feature-icon" :style="{ background: f.bg }">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" :stroke="f.color" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" v-html="f.icon"></svg>
            </span>
            <h3>{{ f.title }}</h3>
            <p>{{ f.desc }}</p>
          </button>
        </div>
      </section>

      <!-- ============ 三步流程 ============ -->
      <section class="steps-section">
        <h2 class="sec-title">三步生成爆款视频</h2>
        <div class="steps">
          <div v-for="s in steps" :key="s.n" class="step-item">
            <div class="step-line" v-if="s.n < steps.length"></div>
            <div class="step-circle" :class="{ done: s.n === steps.length }">
              <svg v-if="s.n === steps.length" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
              <template v-else>{{ s.n }}</template>
            </div>
            <p class="step-title">{{ s.title }}</p>
            <p class="step-desc">{{ s.desc }}</p>
          </div>
        </div>
        <div class="workflow-img">
          <img src="/assets/studio-workflow.jpg" alt="工作流示意" />
        </div>
      </section>

      <!-- ============ 热门模板 ============ -->
      <section class="hot">
        <div class="hot-head">
          <h2 class="sec-title">热门模板</h2>
          <button class="more" @click="router.push('/templates')">
            查看全部
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
          </button>
        </div>
        <div class="hot-grid">
          <button v-for="t in hotList" :key="t.id" class="template-card" @click="goTemplate(t)">
            <div class="template-thumb">
              <span v-if="t.badge" class="hot-badge" :class="{ alt: t.badge === '新品' }">{{ t.badge }}</span>
              <img :src="t.img" :alt="t.title" />
              <div class="template-usage">
                <span class="tu-views">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                  {{ t.views }}
                </span>
                <span>{{ t.rate }}</span>
              </div>
            </div>
            <div class="template-info">
              <h4 class="truncate">{{ t.title }}</h4>
              <p>{{ t.meta }}</p>
            </div>
          </button>
        </div>
      </section>

      <!-- ============ 底部 CTA 横幅 ============ -->
      <section class="cta-section">
        <div class="cta-banner" @click="router.push('/studio')">
          <div class="cta-inner">
            <h3>今天还能免费生成 3 条</h3>
            <p>错过今天，明天就要付费了</p>
            <button class="cta-btn">
              马上试试
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
            </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.home-page {
  background: var(--bg-page);
  min-height: 100vh;
  padding-bottom: calc(var(--nav-h) + 24px + env(safe-area-inset-bottom));
}

/* ============ HERO ============ */
.hero {
  position: relative;
  overflow: hidden;
  background: var(--grad-hero);
  padding-top: env(safe-area-inset-top);
}
.hero-bg { position: absolute; inset: 0; overflow: hidden; }
.orb { position: absolute; border-radius: 50%; pointer-events: none; }
.orb-a {
  width: 300px; height: 300px; top: -50%; right: -20%;
  background: radial-gradient(circle, rgba(124, 58, 237, .45) 0%, transparent 70%);
}
.orb-b {
  width: 250px; height: 250px; bottom: -30%; left: -10%;
  background: radial-gradient(circle, rgba(79, 70, 229, .35) 0%, transparent 70%);
}
.hero-inner {
  position: relative;
  z-index: 1;
  max-width: var(--page-max);
  margin: 0 auto;
  padding: 12px var(--s-5) var(--s-8);
}
.hero-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.hero-logo { display: flex; align-items: center; gap: 8px; }
.logo-badge {
  width: 32px; height: 32px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, .2);
  backdrop-filter: blur(8px);
  display: flex; align-items: center; justify-content: center;
}
.logo-text { color: #fff; font-weight: 700; font-size: 18px; }
.quota-badge {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, .15);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, .2);
  color: #fff; font-size: 12px;
  transition: background var(--transition-fast);
}
.quota-badge:hover { background: rgba(255, 255, 255, .25); }

.hero-main { padding-top: var(--s-4); }
.hero-content { text-align: center; }
.hero-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px; margin-bottom: var(--s-4);
  border-radius: var(--radius-full);
  background: linear-gradient(90deg, rgba(245, 158, 11, .2), rgba(244, 63, 94, .2));
  border: 1px solid rgba(251, 191, 36, .3);
  backdrop-filter: blur(4px);
  color: #FDE68A; font-size: 12px; font-weight: 500;
}
.hero-title {
  margin: 0 0 var(--s-3);
  color: #fff; font-size: 24px; font-weight: 800; line-height: 1.3;
}
.hero-desc {
  margin: 0 auto var(--s-5);
  color: rgba(255, 255, 255, .7);
  font-size: 14px; line-height: 1.7;
  max-width: 420px;
}
.hero-visual { margin-bottom: var(--s-5); }
.hero-img {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 24px 48px rgba(0, 0, 0, .35);
}
.hero-img img { width: 100%; height: 176px; object-fit: cover; display: block; }
.hero-img-mask {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0) 55%, rgba(0, 0, 0, .5) 100%);
}
.hero-img-meta {
  position: absolute; left: 12px; right: 12px; bottom: 12px;
  display: flex; align-items: center; justify-content: space-between;
  color: rgba(255, 255, 255, .85); font-size: 11px;
}
.hm-left { display: flex; align-items: center; gap: 6px; }
.av { width: 20px; height: 20px; border-radius: 50%; border: 2px solid rgba(255, 255, 255, .6); }
.av.a1 { background: #F472B6; }
.av.a2 { background: #60A5FA; margin-left: -6px; }
.av.a3 { background: #FBBF24; margin-left: -6px; }
.hm-right { display: flex; align-items: center; gap: 4px; }

.hero-cta {
  width: 100%;
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 16px;
  border: none; border-radius: var(--radius-full);
  background: var(--grad-brand); color: #fff;
  font-size: 16px; font-weight: 600;
  box-shadow: var(--shadow-brand-lg);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}
.hero-cta:active { transform: scale(.98); box-shadow: var(--shadow-brand); }
.hero-sub {
  display: flex; align-items: center; justify-content: center;
  flex-wrap: wrap; gap: 4px 16px; margin-top: 10px;
  color: rgba(255, 255, 255, .5); font-size: 12px;
}
.hs-item { display: inline-flex; align-items: center; gap: 4px; }
.hs-dot { color: rgba(255, 255, 255, .3); }
.hs-warn { color: #FCD34D; font-weight: 500; }

/* ============ BODY ============ */
.home-body {
  max-width: var(--page-max);
  margin: 0 auto;
  padding: 0 var(--s-5);
}

/* 功能入口 */
.feat { padding: var(--s-6) 0; }
.feat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-3); }
.feature-card {
  text-align: left;
  padding: var(--s-4);
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}
.feature-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-md); }
.feature-card:active { transform: scale(.98); }
.feature-icon {
  width: 48px; height: 48px;
  border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center;
  margin-bottom: var(--s-3);
}
.feature-card h3 { margin: 0 0 4px; font-size: 16px; font-weight: 600; color: var(--ink); }
.feature-card p { margin: 0; font-size: 12px; color: var(--text-tertiary); }

/* 三步流程 */
.steps-section { padding: var(--s-4) 0; }
.sec-title { margin: 0 0 var(--s-5); font-size: 18px; font-weight: 700; color: var(--ink); }
.steps { display: flex; justify-content: space-between; align-items: flex-start; }
.step-item { flex: 1; display: flex; flex-direction: column; align-items: center; position: relative; }
.step-line {
  position: absolute; top: 28px; left: 60%; width: 80%; height: 2px;
  background: linear-gradient(90deg, var(--brand-primary-light), var(--violet));
  opacity: .4;
}
.step-item:last-child .step-line { display: none; }
.step-circle {
  width: 56px; height: 56px; border-radius: 50%;
  background: var(--bg-card);
  border: 2px solid var(--brand-primary-light);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 18px; color: var(--brand-primary);
  box-shadow: var(--shadow-sm);
  position: relative; z-index: 1;
  transition: transform var(--transition-base);
}
.step-item:hover .step-circle { transform: scale(1.06); }
.step-circle.done { background: var(--grad-brand); border-color: transparent; color: #fff; }
.step-title { margin: var(--s-3) 0 0; font-size: 14px; font-weight: 500; color: var(--ink); text-align: center; }
.step-desc { margin: 4px 0 0; font-size: 12px; color: var(--text-tertiary); text-align: center; }
.workflow-img { margin-top: var(--s-6); border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow-md); }
.workflow-img img { width: 100%; height: 128px; object-fit: cover; display: block; }

/* 热门模板 */
.hot { padding: var(--s-4) 0; }
.hot-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--s-4); }
.hot-head .sec-title { margin: 0; }
.more {
  display: inline-flex; align-items: center; gap: 2px;
  border: none; background: none;
  font-size: 14px; font-weight: 500; color: var(--brand-primary);
}
.hot-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-3); }
.template-card {
  text-align: left;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}
.template-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-md); }
.template-thumb { position: relative; aspect-ratio: 9 / 16; background: var(--grad-brand-soft); overflow: hidden; }
.template-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.hot-badge {
  position: absolute; top: 8px; left: 8px; z-index: 1;
  padding: 2px 8px; border-radius: var(--radius-full);
  background: linear-gradient(135deg, #EF4444, #F59E0B);
  color: #fff; font-size: 10px; font-weight: 600;
}
.hot-badge.alt { background: var(--grad-brand); }
.template-usage {
  position: absolute; left: 8px; right: 8px; bottom: 8px;
  display: flex; align-items: center; justify-content: space-between;
  padding: 4px 8px; border-radius: var(--radius-sm);
  background: rgba(0, 0, 0, .5);
  backdrop-filter: blur(4px);
  color: #fff; font-size: 10px;
}
.tu-views { display: inline-flex; align-items: center; gap: 4px; }
.template-info { padding: var(--s-3); }
.template-info h4 { margin: 0; font-size: 14px; font-weight: 500; color: var(--ink); }
.template-info p { margin: 2px 0 0; font-size: 12px; color: var(--text-tertiary); }

/* 底部 CTA */
.cta-section { padding: var(--s-6) 0; }
.cta-banner {
  position: relative; overflow: hidden;
  border-radius: var(--radius-xl);
  padding: var(--s-5);
  background: var(--grad-brand);
  cursor: pointer;
  box-shadow: var(--shadow-brand);
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}
.cta-banner:hover { transform: translateY(-2px); box-shadow: var(--shadow-brand-lg); }
.cta-banner::before {
  content: '';
  position: absolute; top: -50%; right: -20%;
  width: 150px; height: 150px; border-radius: 50%;
  background: rgba(255, 255, 255, .1);
}
.cta-inner { position: relative; z-index: 1; }
.cta-inner h3 { margin: 0 0 4px; color: #fff; font-size: 18px; font-weight: 700; }
.cta-inner p { margin: 0 0 var(--s-4); color: rgba(255, 255, 255, .8); font-size: 14px; }
.cta-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 10px 20px;
  border: none; border-radius: var(--radius-full);
  background: #fff; color: var(--brand-primary);
  font-size: 14px; font-weight: 600;
  box-shadow: 0 8px 20px rgba(0, 0, 0, .18);
}

/* ============ 桌面端响应式扩展 ============ */
@media (min-width: 768px) {
  .home-page { padding-bottom: 0; }
  .hero-top { display: none; } /* 桌面端顶部导航已由 AppHeader 提供 */
  .hero-inner { padding: var(--s-8) var(--s-6) var(--s-9); }
  .hero-main { padding-top: 0; }
  .hero-content {
    display: grid;
    grid-template-columns: 1.05fr .95fr;
    align-items: center;
    gap: var(--s-8);
    text-align: left;
  }
  .hero-pill { margin-bottom: var(--s-5); }
  .hero-title { font-size: 44px; letter-spacing: -1px; }
  .hero-desc { margin: 0 0 var(--s-6); font-size: 15px; max-width: 460px; }
  .hero-visual { margin: 0; }
  .hero-img img { height: 340px; }
  .hero-cta { width: auto; padding: 16px 36px; }
  .hero-sub { justify-content: flex-start; }

  .home-body { padding: 0 var(--s-6); }
  .feat-grid { grid-template-columns: repeat(4, 1fr); gap: var(--s-4); }
  .workflow-img img { height: 220px; }
  .hot-grid { grid-template-columns: repeat(4, 1fr); gap: var(--s-4); }
  .steps { max-width: 720px; margin: 0 auto; }
}

@media (min-width: 1100px) {
  .hero-title { font-size: 52px; }
  .hero-img img { height: 400px; }
  .hot-grid { grid-template-columns: repeat(4, 1fr); }
}
</style>
