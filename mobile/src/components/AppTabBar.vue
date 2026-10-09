<template>
  <view class="app-tabbar">
    <view
      v-for="item in items"
      :key="item.key"
      class="app-tabbar__item"
      :class="{ 'app-tabbar__item--active': item.key === active }"
      role="button"
      :aria-label="item.label"
      @click="switchTo(item)"
    >
      <AppIcon
        :name="item.icon"
        :size="24"
        :color="item.key === active ? '#4F46E5' : '#64748B'"
      />
      <text class="app-tabbar__label">{{ item.label }}</text>
    </view>
  </view>
</template>

<script setup>
import AppIcon from '@/components/AppIcon.vue'
import { go } from '@/utils/navigation'

/**
 * 底部三项导航（对应设计稿的 bottom-nav：首页 / 创作 / 作品）。
 *
 * 设计稿的导航条是自绘的 480px 居中固定条，与原生 tabBar 的样式差异明显，
 * 因此这里用共享组件承载，保证 H5 与小程序端视觉一致；页面注册为普通页面，
 * 切换走 reLaunch（由 utils/navigation 的 go() 统一处理）。
 */
defineProps({
  /** 当前高亮项：home / create / works */
  active: { type: String, default: 'home' },
})

const items = [
  { key: 'home', label: '首页', icon: 'home', path: '/pages/home/index' },
  { key: 'create', label: '创作', icon: 'plus-square', path: '/pages/studio/index' },
  { key: 'works', label: '作品', icon: 'file', path: '/pages/works/index' },
]

function switchTo(item) {
  go(item.path)
}
</script>

<style lang="scss" scoped>
.app-tabbar {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: var(--page-max);
  height: calc(60px + constant(safe-area-inset-bottom));
  height: calc(60px + env(safe-area-inset-bottom));
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
  background: var(--bg-card);
  border-top: 1px solid var(--border-light);
  box-shadow: 0 -2px 10px rgba(15, 23, 42, 0.04);
  display: flex;
  align-items: center;
  justify-content: space-around;
  z-index: 100;

  &__item {
    flex: 1;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    color: var(--text-tertiary);
    transition: color var(--transition-fast);

    &--active {
      color: var(--brand-primary);
    }
  }

  &__label {
    font-size: 12px;
    line-height: 1.2;
    white-space: nowrap;
  }
}
</style>
