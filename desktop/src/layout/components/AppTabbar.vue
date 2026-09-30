<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const tabs = [
  { key: '/home', label: '首页', icon: 'M3 10.5L12 3L21 10.5V20C21 20.55 20.55 21 20 21H4C3.45 21 3 20.55 3 20V10.5Z' },
  { key: '/works', label: '我的作品', icon: 'M5 4h14a2 2 0 012 2v12a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2zM10 9l5 3-5 3V9z' },
  { key: '/user', label: '我的', icon: 'M12 12a4 4 0 100-8 4 4 0 000 8zM4 21c0-4.42 3.58-8 8-8s8 3.58 8 8' },
]

// 仅主 tab 页面显示底部 tabbar(与原型一致)
const visible = computed(() => !!route.meta?.tabbar)

const activeKey = computed(() => {
  if (route.path.startsWith('/works')) return '/works'
  if (route.path.startsWith('/user')) return '/user'
  return '/home'
})

function go(item) {
  if (item.key === route.path) return
  if ((item.key === '/works' || item.key === '/user') && !userStore.isLoggedIn) {
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
      <svg viewBox="0 0 24 24" class="tab-icon" fill="none" stroke="currentColor" stroke-width="1.8">
        <path :d="t.icon" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
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
    left: 0;
    right: 0;
    height: 60px;
    padding-bottom: env(safe-area-inset-bottom);
    background: #fff;
    border-top: 1px solid var(--line, #ECECEF);
    z-index: 200;
  }
  .tab-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    color: #9B9B9B;
    font-size: 11px;
    cursor: pointer;
  }
  .tab-item.active {
    color: #FF4D1C;
    font-weight: 500;
  }
  .tab-icon {
    width: 24px;
    height: 24px;
  }
}
</style>
