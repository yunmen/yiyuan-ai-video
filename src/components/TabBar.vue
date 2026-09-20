<script setup>
import { goTab } from '../store/app'

defineProps({ active: { type: String, required: true } })
</script>

<template>
  <div class="tabbar">
    <div class="tab" :class="{ on: active === 'home' }" @click="goTab('home')">
      <svg height="24" viewBox="0 0 24 24" width="24"><path d="M3 10.5L12 3L21 10.5V20C21 20.55 20.55 21 20 21H4C3.45 21 3 20.55 3 20V10.5Z" fill="none" :stroke="active === 'home' ? '#FF4D1C' : '#9B9B9B'" stroke-linejoin="round" stroke-width="2"/></svg>
      <span :style="active === 'home' ? 'color:#FF4D1C' : ''">首页</span>
    </div>
    <div class="tab" :class="{ on: active === 'works' }" @click="goTab('works')">
      <svg height="24" viewBox="0 0 24 24" width="24"><rect fill="none" height="16" rx="3" :stroke="active === 'works' ? '#FF4D1C' : '#9B9B9B'" stroke-width="2" width="18" x="3" y="4"/><path d="M10 9L15 12L10 15V9Z" :fill="active === 'works' ? '#FF4D1C' : '#9B9B9B'"/></svg>
      <span :style="active === 'works' ? 'color:#FF4D1C' : ''">我的作品</span>
    </div>
    <div class="tab" :class="{ on: active === 'me' }" @click="goTab('me')">
      <svg height="24" viewBox="0 0 24 24" width="24"><circle cx="12" cy="8" fill="none" r="4" :stroke="active === 'me' ? '#FF4D1C' : '#9B9B9B'" stroke-width="2"/><path d="M4 21C4 16.58 7.58 13 12 13C16.42 13 20 16.58 20 21" fill="none" :stroke="active === 'me' ? '#FF4D1C' : '#9B9B9B'" stroke-linecap="round" stroke-width="2"/></svg>
      <span :style="active === 'me' ? 'color:#FF4D1C' : ''">我的</span>
    </div>
  </div>
</template>
