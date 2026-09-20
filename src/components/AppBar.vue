<script setup>
import { pageBack } from '../store/app'

defineProps({
  title: { type: String, required: true },
  backTarget: { type: String, default: '' },
  actionText: { type: String, default: '' },
  hideBack: { type: Boolean, default: false }
})
const emit = defineEmits(['action'])
</script>

<template>
  <div class="appbar">
    <div class="back" :style="{ visibility: hideBack ? 'hidden' : 'visible' }" @click="pageBack(backTarget)">
      <svg height="24" viewBox="0 0 24 24" width="24"><path d="M15 5L8 12L15 19" fill="none" stroke="#1A1A1A" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>
    </div>
    <h1>{{ title }}</h1>
    <div v-if="actionText" class="act" @click="emit('action')">{{ actionText }}</div>
    <div v-else class="spacer"></div>
  </div>
</template>
