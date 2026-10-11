<template>
  <view class="app-empty">
    <view class="app-empty__icon">
      <AppIcon :name="icon" :size="48" color="#B23A2E" :stroke-width="2" />
    </view>
    <text class="app-empty__title">{{ title }}</text>
    <text v-if="desc" class="app-empty__desc">{{ desc }}</text>
    <view v-if="actionText" class="app-empty__action app-btn-brand" role="button" @click="$emit('action')">
      <AppIcon name="sparkles" :size="16" color="#FFFFFF" :stroke-width="2.5" />
      <text>{{ actionText }}</text>
    </view>
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
    border: 1px solid var(--line-2);
    border-radius: 4px;
    background: var(--paper-100);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 20px;
    transform: rotate(-2deg);
  }

  &__title {
    font-family: var(--font-serif);
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--ink-700);
  }

  &__desc {
    font-size: 14px;
    color: var(--ink-500);
    margin-top: 8px;
    text-align: center;
  }

  &__action {
    margin-top: 24px;
    padding: 12px 32px;
    font-size: 14px;
    border-radius: 4px;
  }
}
</style>
