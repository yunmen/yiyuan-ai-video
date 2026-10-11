<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const tabs = [
  {
    key: '/home',
    label: '首页',
    icon: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
  },
  {
    key: '/studio',
    label: '创作',
    icon: '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>',
  },
  {
    key: '/works',
    label: '作品',
    icon: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
  },
]

// 仅主 tab 页面显示底部 tabbar(与设计稿一致)
const visible = computed(() => !!route.meta?.tabbar)

const activeKey = computed(() => {
  if (route.path.startsWith('/works')) return '/works'
  if (route.path.startsWith('/studio') || route.path.startsWith('/digital') ||
      route.path.startsWith('/render') || route.path.startsWith('/ai-flavor') ||
      route.path.startsWith('/templates') || route.path.startsWith('/replicate') ||
      route.path.startsWith('/storyboard')) return '/studio'
  if (route.path.startsWith('/home')) return '/home'
  return ''
})

function go(item) {
  if (item.key === route.path) return
  if (item.key === '/works' && !userStore.isLoggedIn) {
    // 未登录点入需登录的 tab:登录成功后跳到该页面
    userStore.openLogin(item.key)
    return
  }
  router.push(item.key)
}
</script>

<template>
  <nav v-if="visible" class="tabbar">
    <div
      v-for="t in tabs"
      :key="t.key"
      class="tab-item"
      :class="{ active: activeKey === t.key }"
      @click="go(t)"
    >
      <svg viewBox="0 0 24 24" class="tab-icon" fill="none" stroke="currentColor" stroke-width="1.8" v-html="t.icon"></svg>
      <span>{{ t.label }}</span>
    </div>
  </nav>
</template>

<style scoped>
.tabbar {
  display: none;
}
@media (max-width: 768px) {
  .tabbar {
    display: flex;
    position: fixed;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 100%;
    max-width: 640px;
    height: calc(var(--nav-h) + env(safe-area-inset-bottom));
    padding-bottom: env(safe-area-inset-bottom);
    background: rgba(255, 255, 255, .95);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-top: 1px solid var(--border-light);
    z-index: 200;
  }
  .tab-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    color: var(--text-tertiary);
    font-size: 11px;
    cursor: pointer;
    transition: color var(--transition-fast);
  }
  .tab-item.active {
    color: var(--brand-primary);
    font-weight: 600;
  }
  .tab-icon {
    width: 24px;
    height: 24px;
  }
}
</style>
