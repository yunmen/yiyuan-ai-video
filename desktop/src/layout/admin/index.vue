<script setup>
import { computed, h } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { createDiscreteApi } from 'naive-ui'
import { ADMIN_TOKEN_KEY, ADMIN_INFO_KEY } from '@/api/admin'

const route = useRoute()
const router = useRouter()
const { dialog } = createDiscreteApi(['dialog'])

const adminInfo = computed(() => {
  try {
    return JSON.parse(localStorage.getItem(ADMIN_INFO_KEY) || '{}')
  } catch {
    return {}
  }
})

const menuOptions = [
  {
    label: () => h(RouterLink, { to: '/admin/template' }, { default: () => '模板管理' }),
    key: '/admin/template'
  },
  {
    label: () => h(RouterLink, { to: '/admin/task' }, { default: () => '任务监控' }),
    key: '/admin/task'
  },
  {
    label: () => h(RouterLink, { to: '/admin/config' }, { default: () => '业务配置' }),
    key: '/admin/config'
  },
  {
    label: () => h(RouterLink, { to: '/admin/order' }, { default: () => '订单管理' }),
    key: '/admin/order'
  }
]

const activeKey = computed(() => route.path)

const handleLogout = () => {
  dialog.warning({
    title: '退出登录',
    content: '确定要退出管理后台吗?',
    positiveText: '退出',
    negativeText: '取消',
    onPositiveClick: () => {
      localStorage.removeItem(ADMIN_TOKEN_KEY)
      localStorage.removeItem(ADMIN_INFO_KEY)
      router.replace('/admin/login')
    }
  })
}
</script>

<template>
  <n-layout has-sider class="admin-layout">
    <n-layout-sider
      bordered
      :width="220"
      class="admin-sider"
    >
      <div class="admin-logo">
        <span class="admin-logo-dot"></span>
        <span>一源AI 管理后台</span>
      </div>
      <n-menu
        :value="activeKey"
        :options="menuOptions"
        :indent="18"
        class="admin-menu"
      />
    </n-layout-sider>
    <n-layout>
      <n-layout-header bordered class="admin-header">
        <div class="admin-header-title">{{ route.meta.title || '管理后台' }}</div>
        <div class="admin-header-right">
          <n-avatar
            round
            :size="32"
            :src="adminInfo.avatar || undefined"
            class="admin-avatar"
          >
            {{ (adminInfo.nickname || 'A').charAt(0) }}
          </n-avatar>
          <span class="admin-nickname">{{ adminInfo.nickname || '管理员' }}</span>
          <n-button quaternary size="small" @click="handleLogout">退出</n-button>
        </div>
      </n-layout-header>
      <n-layout-content class="admin-content">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<style scoped>
.admin-layout {
  height: 100vh;
}
.admin-sider {
  background: #10151F;
}
.admin-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
}
.admin-logo-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--brand);
}
.admin-menu {
  --n-item-color-hover: rgba(255, 77, 28, 0.12) !important;
  --n-item-color-active: rgba(255, 77, 28, 0.18) !important;
  --n-item-text-color-active: var(--brand) !important;
  --n-item-icon-color-active: var(--brand) !important;
}
.admin-sider :deep(.n-menu .n-menu-item-content) {
  color: rgba(255, 255, 255, 0.75);
}
.admin-sider :deep(.n-menu .n-menu-item-content a) {
  color: inherit;
  text-decoration: none;
}
.admin-sider :deep(.n-menu .n-menu-item-content--selected),
.admin-sider :deep(.n-menu .n-menu-item-content--selected a) {
  color: var(--brand) !important;
}
.admin-sider :deep(.n-menu .n-menu-item-content:hover) {
  background: rgba(255, 255, 255, 0.06);
}
.admin-sider :deep(.n-menu .n-menu-item-content--selected) {
  background: rgba(255, 77, 28, 0.16) !important;
}
.admin-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #fff;
}
.admin-header-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--ink);
}
.admin-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.admin-avatar {
  background: var(--brand);
  color: #fff;
}
.admin-nickname {
  font-size: 14px;
  color: var(--body-c);
}
.admin-content {
  padding: 20px;
  background: var(--bg);
  height: calc(100vh - 60px);
  overflow: auto;
}
</style>
