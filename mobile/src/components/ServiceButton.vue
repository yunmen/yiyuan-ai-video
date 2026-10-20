<template>
  <button class="service-button" :class="{ 'service-button--secondary': secondary }" role="button" tabindex="0" :disabled="disabled || loading" :aria-busy="loading" @click="activate" @keydown.enter.prevent="activate" @keydown.space.prevent="activate">
    <AppIcon v-if="loading" name="loader" :size="17" :color="secondary ? '#48463F' : '#FFFFFF'" class="app-spin" />
    <text>{{ loading ? loadingText : text }}</text>
  </button>
</template>
<script setup>
import AppIcon from '@/components/AppIcon.vue'
/** 服务页面按钮统一处理提交锁和键盘操作。 */
const props = defineProps({ text: String, disabled: Boolean, loading: Boolean, secondary: Boolean, loadingText: { type: String, default: '处理中…' } })
const emit = defineEmits(['click'])
/** 加载和禁用期间阻止重复提交。 */
function activate() { if (!props.disabled && !props.loading) emit('click') }
</script>
<style scoped>
.service-button { display: flex; align-items: center; justify-content: center; gap: 9px; width: 100%; min-height: 48px; padding: 10px 20px; margin: 0; border-radius: 999px; background: var(--brand-primary); color: #fff; font-size: 14px; line-height: 1.7; transition: transform 180ms cubic-bezier(0.22,1,0.36,1); }
.service-button::after { border: none; }
.service-button--secondary { background: var(--paper-100); color: var(--ink-700); }
.service-button:active { transform: scale(0.98); }
.service-button[disabled] { opacity: 0.55; }
.service-button:focus-visible { outline: 2px solid var(--brand-primary); outline-offset: 3px; }
</style>
