<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import api from '@/api'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const activeKey = ref('/home')
const showDrawer = ref(false)
const creditTotal = computed(() => userStore.creditTotal)

const menuOptions = [
  { label: '首页', key: '/home' },
  { label: '创作工作台', key: '/studio' },
  { label: '数字人', key: '/digital' },
  { label: '视频换口播', key: '/render' },
  { label: '我的作品', key: '/works' },
]

watch(() => route.path, (val) => {
  if (val.startsWith('/studio') || val.startsWith('/templates') || val.startsWith('/upload') ||
      val.startsWith('/generate') || val.startsWith('/replicate') || val.startsWith('/storyboard')) {
    activeKey.value = '/studio'
  } else if (val.startsWith('/digital')) activeKey.value = '/digital'
  else if (val.startsWith('/render')) activeKey.value = '/render'
  else if (val.startsWith('/works')) activeKey.value = '/works'
  else if (val.startsWith('/user')) activeKey.value = '/user'
  else activeKey.value = '/home'
  showDrawer.value = false
}, { immediate: true })

async function loadCredits() {
  if (!userStore.isLoggedIn) { userStore.setCreditTotal(null); return }
  try {
    const res = await api.account.credits.post()
    if (res.code === 1) userStore.setCreditTotal(res.data.total)
  } catch (e) { userStore.setCreditTotal(null) }
}

watch(() => userStore.isLoggedIn, loadCredits, { immediate: true })
watch(() => route.path, () => { if (userStore.isLoggedIn) loadCredits() })
onMounted(loadCredits)

const handleMenuUpdate = (key) => {
  if ((key === '/works' || key === '/user') && !userStore.isLoggedIn) {
    userStore.openLogin(key)
    return
  }
  router.push(key)
}

function goHome() { router.push('/home') }
function onAvatar() {
  if (!userStore.isLoggedIn) { userStore.openLogin(); return }
  router.push('/user')
}
</script>

<template>
  <header class="app-header">
    <div class="header-inner">
      <div class="logo-wrap" @click="goHome">
        <span class="logo-badge">
          <svg width="18" height="18" viewBox="0 0 28 28"><path d="M9 6.5L21 14L9 21.5V6.5Z" fill="#fff"/></svg>
        </span>
        <span class="logo-text">一源</span>
        <span class="logo-sub">AI视频</span>
      </div>

      <nav class="header-nav">
        <a
          v-for="m in menuOptions"
          :key="m.key"
          class="nav-item"
          :class="{ on: activeKey === m.key }"
          @click="handleMenuUpdate(m.key)"
        >{{ m.label }}</a>
      </nav>

      <div class="header-actions">
        <div v-if="userStore.isLoggedIn" class="credit-chip" @click="router.push('/balance')">
          <svg width="14" height="14" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M8 4.5V11.5M6 6.5H10M6 9H10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
          <span>额度</span>
          <b>{{ creditTotal === null ? '—' : creditTotal }}</b>
        </div>
        <div v-else class="login-chip" @click="userStore.openLogin()">登录</div>
        <div v-if="userStore.isLoggedIn" class="avatar-wrap" @click="onAvatar">
          <div class="av-dot">{{ (userStore.userInfo?.nickname || '用').slice(0, 1) }}</div>
        </div>
        <button class="cta-btn" @click="router.push('/studio')">
          <svg width="14" height="14" viewBox="0 0 16 16"><path d="M3 4L13 8L3 12V4Z" fill="currentColor"/></svg>
          开始创作
        </button>
      </div>

      <button class="hamburger" aria-label="菜单" @click="showDrawer = true">
        <span></span><span></span><span></span>
      </button>
    </div>
  </header>

  <n-drawer v-model:show="showDrawer" placement="right" :width="280" class="app-drawer">
    <n-drawer-content title="" closable>
      <div class="drawer-brand">
        <span class="logo-badge">
          <svg width="16" height="16" viewBox="0 0 28 28"><path d="M9 6.5L21 14L9 21.5V6.5Z" fill="#fff"/></svg>
        </span>
        <span class="drawer-brand-name">一源 AI 视频</span>
      </div>
      <n-menu
        v-model:value="activeKey"
        :options="menuOptions"
        @update:value="handleMenuUpdate"
      />
      <div class="drawer-links">
        <div @click="router.push('/balance'); showDrawer = false">
          <svg width="16" height="16" viewBox="0 0 16 16"><rect x="2" y="4" width="12" height="9" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6 8H10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          账户余额
        </div>
        <div @click="router.push('/orders'); showDrawer = false">
          <svg width="16" height="16" viewBox="0 0 16 16"><path d="M3 3H13V13H3V3Z" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M5 6H11M5 9H9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          我的订单
        </div>
        <div @click="router.push('/support'); showDrawer = false">
          <svg width="16" height="16" viewBox="0 0 16 16"><path d="M8 2C4.7 2 2 4.7 2 8C2 11.3 4.7 14 8 14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="8" r="1.5" fill="currentColor"/></svg>
          联系客服
        </div>
        <div @click="router.push('/settings'); showDrawer = false">
          <svg width="16" height="16" viewBox="0 0 16 16"><circle cx="8" cy="8" r="2.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M8 1.5V3M8 13V14.5M1.5 8H3M13 8H14.5M3.8 3.8L4.8 4.8M11.2 11.2L12.2 12.2M3.8 12.2L4.8 11.2M11.2 4.8L12.2 3.8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          设置
        </div>
      </div>
      <div class="drawer-cta">
        <n-button v-if="!userStore.isLoggedIn" block round type="primary" @click="userStore.openLogin(); showDrawer = false">登录 / 注册</n-button>
        <n-button v-else block round type="primary" @click="onAvatar(); showDrawer = false">进入个人中心</n-button>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, .85);
  backdrop-filter: saturate(180%) blur(16px);
  -webkit-backdrop-filter: saturate(180%) blur(16px);
  border-bottom: 1px solid var(--line);
}
.header-inner {
  max-width: var(--page-max);
  margin: 0 auto;
  padding: 0 var(--s-4);
  height: var(--header-h);
  display: flex;
  align-items: center;
  gap: var(--s-4);
}

/* Logo */
.logo-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
  flex-shrink: 0;
}
.logo-badge {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: var(--grad-brand);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-brand);
}
.logo-text {
  font-size: 18px;
  font-weight: 800;
  color: var(--ink);
  white-space: nowrap;
  letter-spacing: .5px;
}
.logo-sub {
  font-size: 11px;
  font-weight: 500;
  color: var(--brand);
  background: var(--brand-bg);
  padding: 2px 6px;
  border-radius: 6px;
  letter-spacing: 1px;
}

/* Nav */
.header-nav {
  flex: 1;
  min-width: 0;
  display: none;
  align-items: center;
  gap: 4px;
}
.nav-item {
  position: relative;
  padding: 8px 14px;
  font-size: 14px;
  color: var(--body-c);
  cursor: pointer;
  border-radius: 10px;
  transition: color .18s, background .18s;
  white-space: nowrap;
  font-weight: 500;
}
.nav-item:hover { color: var(--brand); background: var(--brand-bg); }
.nav-item.on {
  color: var(--brand);
  font-weight: 600;
  background: var(--brand-bg);
}

/* Actions */
.header-actions {
  flex-shrink: 0;
  display: none;
  align-items: center;
  gap: var(--s-3);
}
.credit-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 34px;
  padding: 0 14px;
  border-radius: var(--radius-pill);
  background: var(--brand-bg);
  color: var(--brand);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all .18s;
}
.credit-chip b { font-weight: 700; font-size: 14px; }
.credit-chip:hover {
  background: var(--brand);
  color: #fff;
}

.login-chip {
  height: 34px;
  padding: 0 16px;
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--ink-2);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all .18s;
}
.login-chip:hover { color: var(--brand); }

.avatar-wrap {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--grad-brand);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: transform .18s;
}
.avatar-wrap:hover { transform: scale(1.05); }
.av-dot { font-size: 14px; font-weight: 700; }

.cta-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 36px;
  padding: 0 18px;
  border: none;
  border-radius: var(--radius-pill);
  background: var(--grad-brand);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: var(--shadow-brand);
  transition: all .2s var(--ease-out);
}
.cta-btn:hover {
  box-shadow: var(--shadow-brand-lg);
  transform: translateY(-1px);
}

/* Hamburger */
.hamburger {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 36px;
  height: 36px;
  padding: 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  margin-left: auto;
  border-radius: 8px;
  transition: background .18s;
}
.hamburger:hover { background: var(--line-2); }
.hamburger span {
  display: block;
  height: 2px;
  width: 100%;
  background: var(--ink);
  border-radius: 2px;
}

/* Drawer */
.drawer-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.drawer-brand-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
}
.drawer-links {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.drawer-links div {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 8px;
  font-size: 14px;
  color: var(--body-c);
  cursor: pointer;
  border-radius: 8px;
  transition: all .18s;
}
.drawer-links div:hover {
  color: var(--brand);
  background: var(--brand-bg);
}
.drawer-cta {
  margin-top: 20px;
}

@media (min-width: 768px) {
  .header-nav { display: flex; }
  .header-actions { display: flex; }
  .hamburger { display: none; }
  .header-inner { padding: 0 var(--s-6); }
}
</style>
