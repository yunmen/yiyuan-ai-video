<template>
  <view class="app-page app-page--plain">
    <AppNavBar :title="title" />
    <view class="service-body">
      <view class="service-heading">
        <text class="service-eyebrow">{{ eyebrow }}</text>
        <text class="service-title">{{ heading || title }}</text>
        <text class="service-subtitle">{{ subtitle }}</text>
      </view>
      <slot />
    </view>
  </view>
</template>

<script setup>
import AppNavBar from '@/components/AppNavBar.vue'

/** 个人服务页统一标题和纸白留白，业务内容由页面提供。 */
defineProps({ title: String, heading: String, subtitle: String, eyebrow: { type: String, default: '我的 · 创作日常' } })
</script>

<style scoped>
.service-body { padding: 20px var(--page-gutter) calc(32px + env(safe-area-inset-bottom)); }
.service-heading { display: flex; flex-direction: column; gap: 10px; margin: 4px 0 26px; }
.service-eyebrow { color: var(--brand-primary); font-size: 11px; letter-spacing: 0.12em; }
.service-title { color: var(--ink-900); font: 700 29px/1.3 var(--font-serif); }
.service-subtitle { color: var(--ink-500); font-size: 13px; line-height: 1.8; }
</style>
