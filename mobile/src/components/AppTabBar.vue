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
      <view class="app-tabbar__indicator" />
      <AppIcon
        :name="item.icon"
        :size="24"
        :color="item.key === active ? '#B23A2E' : '#6B6357'"
      />
      <text class="app-tabbar__label">{{ item.label }}</text>
    </view>
  </view>
</template>

<script setup>
import AppIcon from '@/components/AppIcon.vue'
import { go } from '@/utils/navigation'

/**
 * 底部四项导航：首页 / 创作 / 作品 / 我的。
 *
 * 使用共享组件承载自绘导航条，保证 H5 与小程序端视觉一致；页面切换
 * 由 utils/navigation 的 go() 统一处理。
 */
defineProps({
  /** 当前高亮项：home / create / works / profile */
  active: { type: String, default: 'home' },
})

const items = [
  { key: 'home', label: '首页', icon: 'home', path: '/pages/home/index' },
  { key: 'create', label: '创作', icon: 'plus-square', path: '/pages/studio/index' },
  { key: 'works', label: '作品', icon: 'file', path: '/pages/works/index' },
  { key: 'profile', label: '我的', icon: 'user', path: '/pages/profile/index' },
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
  height: calc(var(--nav-h) + constant(safe-area-inset-bottom));
  height: calc(var(--nav-h) + env(safe-area-inset-bottom));
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
  background: var(--paper-card);
  border-top: 1px solid var(--line-1);
  box-shadow: 0 -4px 14px rgba(31, 29, 26, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-around;
  z-index: 100;

  &__item {
    position: relative;
    flex: 1;
    height: 52px;
    margin-top: 2px;
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

  /* 选中态：顶部朱砂短线，一点即可 */
  &__indicator {
    position: absolute;
    top: -2px;
    width: 24px;
    height: 3px;
    border-radius: 0 0 3px 3px;
    background: var(--brand-primary);
    opacity: 0;
    transition: opacity var(--transition-fast);
  }

  &__item--active &__indicator {
    opacity: 1;
  }

  &__label {
    font-family: var(--font-sans);
    font-size: 12px;
    letter-spacing: 0.05em;
    line-height: 1.2;
    white-space: nowrap;
  }
}
</style>
