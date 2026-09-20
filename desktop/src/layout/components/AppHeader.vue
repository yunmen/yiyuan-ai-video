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
// 额度来自 store,保证顶部与页面展示一致
const creditTotal = computed(() => userStore.creditTotal)

// 顶部导航只暴露主栏目,次要页面走个人中心入口
const menuOptions = [
  { label: '首页', key: '/home' },
  { label: '爆款视频', key: '/templates' },
  { label: '数字人', key: '/digital' },
  { label: '我的作品', key: '/works' },
]

watch(() => route.path, (val) => {
  if (val.startsWith('/templates') || val.startsWith('/upload') || val.startsWith('/generate')) activeKey.value = '/templates'
  else if (val.startsWith('/digital')) activeKey.value = '/digital'
  else if (val.startsWith('/works')) activeKey.value = '/works'
  else if (val.startsWith('/user')) activeKey.value = '/user'
  else activeKey.value = '/home'
  showDrawer.value = false
}, { immediate: true })

// 登录后拉取额度,头部展示快捷入口
async function loadCredits() {
  if (!userStore.isLoggedIn) { userStore.setCreditTotal(null); return }
  try {
    const res = await api.account.credits.post()
    if (res.code === 1) userStore.setCreditTotal(res.data.total)
  } catch (e) { userStore.setCreditTotal(null) }
}

watch(() => userStore.isLoggedIn, loadCredits, { immediate: true })
// 路由切换时刷新:覆盖签到、充值、生成消耗、失败返还等额度变化
watch(() => route.path, () => { if (userStore.isLoggedIn) loadCredits() })
onMounted(loadCredits)

const handleMenuUpdate = (key) => {
  if ((key === '/works' || key === '/user') && !userStore.isLoggedIn) {
    userStore.openLogin()
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
          额度 {{ creditTotal === null ? '—' : creditTotal }}
        </div>
        <n-button v-if="!userStore.isLoggedIn" tertiary round @click="userStore.openLogin()">登录</n-button>
        <div v-else class="avatar-wrap" @click="onAvatar">
          <n-avatar
            round
            size="small"
            :src="userStore.userInfo?.avatar"
          >{{ (userStore.userInfo?.nickname || '用').slice(0, 1) }}</n-avatar>
          <span class="nickname">{{ userStore.userInfo?.nickname || '用户' }}</span>
        </div>
        <n-button type="primary" round class="cta-btn" @click="router.push('/templates')">开始创作</n-button>
      </div>

      <button class="hamburger" aria-label="菜单" @click="showDrawer = true">
        <span></span><span></span><span></span>
      </button>
    </div>
  </header>

  <n-drawer v-model:show="showDrawer" placement="right" :width="260">
    <n-drawer-content title="一源" closable>
      <n-menu
        v-model:value="activeKey"
        :options="menuOptions"
        @update:value="handleMenuUpdate"
      />
      <div class="drawer-links">
        <div @click="router.push('/balance'); showDrawer = false">账户余额</div>
        <div @click="router.push('/support'); showDrawer = false">联系客服</div>
        <div @click="router.push('/settings'); showDrawer = false">设置</div>
      </div>
      <n-button v-if="!userStore.isLoggedIn" block round type="primary" style="margin-top:16px" @click="userStore.openLogin(); showDrawer = false">登录</n-button>
      <n-button v-else block round type="primary" style="margin-top:16px" @click="onAvatar(); showDrawer = false">进入个人中心</n-button>
    </n-drawer-content>
  </n-drawer>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, .92);
  backdrop-filter: saturate(180%) blur(8px);
  border-bottom: 1px solid var(--line);
}
.header-inner {
  max-width: var(--page-max);
  margin: 0 auto;
  padding: 0 16px;
  height: var(--header-h);
  display: flex;
  align-items: center;
  gap: 24px;
}
.logo-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  flex-shrink: 0;
}
.logo-badge {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  background: linear-gradient(135deg, #FF8A3D, #FF4D1C);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 10px rgba(255, 77, 28, .28);
}
.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a1a;
  white-space: nowrap;
  letter-spacing: .5px;
}
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
  border-radius: 8px;
  transition: color .15s, background .15s;
  white-space: nowrap;
}
.nav-item:hover { color: var(--brand); background: var(--brand-bg); }
.nav-item.on { color: var(--brand); font-weight: 600; }
.nav-item.on::after {
  content: '';
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 2px;
  height: 2px;
  border-radius: 2px;
  background: var(--brand);
}
.header-actions {
  flex-shrink: 0;
  display: none;
  align-items: center;
  gap: 12px;
}
.credit-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  height: 30px;
  padding: 0 12px;
  border-radius: 15px;
  background: var(--brand-bg);
  color: var(--brand);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.avatar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.nickname {
  font-size: 14px;
  color: #333;
  max-width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hamburger {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 36px;
  height: 36px;
  padding: 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  margin-left: auto;
}
.hamburger span {
  display: block;
  height: 2px;
  width: 100%;
  background: #333;
  border-radius: 2px;
}
.drawer-links {
  margin-top: 16px;
  border-top: 1px solid var(--line);
  padding-top: 8px;
}
.drawer-links div {
  padding: 10px 4px;
  font-size: 14px;
  color: var(--body-c);
  cursor: pointer;
}
@media (min-width: 768px) {
  .header-nav { display: flex; }
  .header-actions { display: flex; }
  .hamburger { display: none; }
  .header-inner { padding: 0 24px; }
}
</style>
