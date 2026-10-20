<template>
  <view class="app-empty">
    <view class="app-empty__icon">
      <AppIcon :name="icon" :size="48" color="#B23A2E" :stroke-width="2" />
    </view>
    <text class="app-empty__title">{{ title }}</text>
    <text v-if="desc" class="app-empty__desc">{{ desc }}</text>
    <button tabindex="0" role="button" v-if="actionText" class="app-empty__action app-btn-brand" @click="$emit('action')" @keydown.enter.prevent="$emit('action')" @keydown.space.prevent="$emit('action')">
      <text>{{ actionText }}</text>
      <view class="app-cta-icon"><AppIcon name="arrow-right" :size="16" color="#FFFFFF" /></view>
    </button>
  </view>
</template>

<script setup>
import AppIcon from '@/components/AppIcon.vue'

/**
 * 空态（对应设计稿「我的作品」空状态）：品牌渐变底色圆形图标 + 标题 + 说明 + 主行动按钮。
 */
defineProps({
  title: { type: String, default: '暂无内容' },
  desc: { type: String, default: '' },
  icon: { type: String, default: 'film' },
  actionText: { type: String, default: '' },
})

defineEmits(['action'])
</script>

<style lang="scss" scoped>
.app-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 72px 24px;

  &__icon {
    width: 88px;
    height: 88px;
    border: 6px solid var(--paper-100);
    border-radius: 28px;
    background: var(--paper-card);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 20px;
  }

  &__title {
    font-family: var(--font-serif);
    font-size: 21px;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: var(--ink-700);
  }

  &__desc {
    font-size: 12px;
    color: var(--ink-500);
    margin-top: 8px;
    text-align: center;
  }

  &__action {
    margin-top: 24px;
    padding: 7px 8px 7px 22px;
    font-size: 14px;
    border-radius: var(--radius-full);
    gap: 22px;
    min-height: 48px;
    &::after { border: none; }
  }
}
</style>
