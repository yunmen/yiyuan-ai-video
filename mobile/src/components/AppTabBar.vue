<template>
  <view class="app-tabbar">
    <view class="app-tabbar__surface">
      <button tabindex="0" role="button"
        v-for="item in items"
        :key="item.key"
        class="app-tabbar__item"
        :class="{ 'app-tabbar__item--active': item.key === active }"
        :aria-label="item.label"
        :aria-current="item.key === active ? 'page' : undefined"
        @click="switchTo(item)"
       @keydown.enter.prevent="switchTo(item)" @keydown.space.prevent="switchTo(item)">
        <view class="app-tabbar__icon"><AppIcon :name="item.icon" :size="21" :color="item.key === active ? '#B23A2E' : '#77746B'" /></view>
        <text class="app-tabbar__label">{{ item.label }}</text>
        <view v-if="item.key === active" class="app-tabbar__dot" />
      </button>
    </view>
  </view>
</template>

<script setup>
import AppIcon from '@/components/AppIcon.vue'
import { go } from '@/utils/navigation'

/** 四项导航使用 uni-app 按钮，显式补齐 H5 键盘操作与读屏语义。 */
const props = defineProps({
  /** 当前高亮项，与既有页面名称保持一致。 */
  active: { type: String, default: 'home' },
})

/** 仅导航到现有业务页面，不额外维护页面栈。 */
const items = [
  { key: 'home', label: '首页', icon: 'home', path: '/pages/home/index' },
  { key: 'create', label: '创作', icon: 'plus-square', path: '/pages/studio/index' },
  { key: 'works', label: '作品', icon: 'film', path: '/pages/works/index' },
  { key: 'profile', label: '我的', icon: 'user', path: '/pages/profile/index' },
]

/** 避免重复点击当前页触发重新导航，其他页面交给统一路由层。 */
function switchTo(item) {
  if (item.key !== props.active) go(item.path)
}
</script>

<style lang="scss" scoped>
/* 外托盘与内芯均为同心圆角；安全区只在外层偏移一次。 */
.app-tabbar {
  position: fixed;
  bottom: calc(12px + env(safe-area-inset-bottom));
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 32px);
  max-width: calc(var(--page-max) - 32px);
  padding: 5px;
  border-radius: 26px;
  background: rgba(232, 228, 218, 0.85);
  box-shadow: 0 10px 36px -15px rgba(52, 43, 27, 0.22), inset 0 1px 0 rgba(255,255,255,.7);
  z-index: var(--z-tabbar);
}
.app-tabbar__surface { display: flex; align-items: center; padding: 3px; border-radius: 21px; background: var(--paper-card); }
.app-tabbar__item { position: relative; flex: 1; min-width: 0; height: 54px; margin: 0; padding: 5px 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; background: transparent; color: var(--text-tertiary); border-radius: 17px; line-height: 1.2; transition: transform var(--transition-fast); }
.app-tabbar__item::after { border: none; }
.app-tabbar__item:active { transform: scale(.94); }
.app-tabbar__item--active { background: var(--brand-primary-lighter); color: var(--brand-primary); }
.app-tabbar__icon { display: flex; align-items: center; justify-content: center; }
.app-tabbar__label { font-size: 10px; letter-spacing: 1px; }
.app-tabbar__dot { position: absolute; width: 3px; height: 3px; bottom: 3px; border-radius: 50%; background: var(--brand-primary); }
</style>
