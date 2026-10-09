<template>
  <view class="app-nav" :class="{ 'app-nav--solid': solid, 'app-nav--transparent': transparent }">
    <view class="app-nav__statusbar" :style="{ height: statusBarHeight + 'px' }" />
    <view class="app-nav__bar">
      <view class="app-nav__left">
        <view
          v-if="canBack"
          class="app-nav__icon-btn"
          role="button"
          aria-label="返回"
          @click="goBack"
        >
          <AppIcon name="chevron-left" :size="22" color="#334155" />
        </view>
      </view>

      <view class="app-nav__title-wrap" :class="{ 'app-nav__title-wrap--left': align === 'left' }">
        <slot name="title">
          <text class="app-nav__title app-truncate">{{ title }}</text>
        </slot>
      </view>

      <view class="app-nav__right">
        <slot name="right" />
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import { isTabPage } from '@/utils/navigation'

/**
 * 通用顶部导航栏（对应设计稿的 header-bar）。
 *
 * 形态取自设计稿：白色半透明 + 20px 背景模糊 + 底部 1px 描边，高度 56px，
 * 标题 17px / 600；返回按钮 40×40 触控区。`solid` 切换为创作工作台使用的
 * 不透明白底形态，`align="left"` 对应「我的作品」的左对齐标题。
 */
const props = defineProps({
  title: { type: String, default: '' },
  /** 强制显示返回按钮；默认按页面栈自动判定 */
  showBack: { type: Boolean, default: false },
  /** 是否按页面栈自动判定返回按钮（H5 下二级页自动出现） */
  autoBack: { type: Boolean, default: true },
  /** 不透明白底（创作工作台形态） */
  solid: { type: Boolean, default: false },
  /** 透明（覆盖在渐变头图上，如首页） */
  transparent: { type: Boolean, default: false },
  /** 标题对齐：center（默认）/ left（我的作品） */
  align: { type: String, default: 'center' },
})

const statusBarHeight = ref(20)
const stackHasBack = ref(false)

const canBack = computed(() => props.showBack || (props.autoBack && stackHasBack.value))

function goBack() {
  const pages = getCurrentPages()
  if (pages && pages.length > 1) {
    uni.navigateBack()
    return
  }
  // 直接进入二级页（分享链接/刷新）时无上一页，退回首页兜底
  uni.reLaunch({ url: '/pages/home/index' })
}

onMounted(() => {
  try {
    const sys = uni.getSystemInfoSync()
    statusBarHeight.value = sys.statusBarHeight || 20
  } catch (err) {
    console.error('获取系统状态栏高度失败，使用默认值')
  }
  try {
    const pages = getCurrentPages()
    if (pages && pages.length > 1) {
      const route = `/${pages[pages.length - 1].route}`
      // 底部导航页与登录/注册页不展示返回，避免出现"退回登录页"的循环
      const noBackRoutes = ['/pages/login/index', '/pages/register/index']
      if (!isTabPage(route) && !noBackRoutes.includes(route)) stackHasBack.value = true
    }
  } catch (err) {
    console.error('读取页面栈失败，不展示返回按钮')
  }
})
</script>

<style lang="scss" scoped>
.app-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  width: 100%;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-light);

  &--solid {
    background: var(--bg-card);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }

  &--transparent {
    background: transparent;
    border-bottom: none;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }

  &__statusbar {
    width: 100%;
  }

  &__bar {
    height: 56px;
    display: flex;
    align-items: center;
    padding: 0 16px;
  }

  &__left,
  &__right {
    min-width: 40px;
    display: flex;
    align-items: center;
  }

  &__right {
    justify-content: flex-end;
  }

  &__icon-btn {
    width: 40px;
    height: 40px;
    margin-left: -8px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: background var(--transition-fast);
  }

  &__icon-btn:active {
    background: var(--bg-hover);
  }

  &__title-wrap {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    justify-content: center;

    &--left {
      justify-content: flex-start;
    }
  }

  &__title {
    font-size: 17px;
    font-weight: 600;
    color: var(--text-primary);
  }
}
</style>
