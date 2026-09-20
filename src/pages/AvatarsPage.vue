<script setup>
import { toast } from '../store/app'
import { AVATARS } from '../data'
import AppBar from '../components/AppBar.vue'
</script>

<template>
  <section class="page active">
    <AppBar title="数字人口播" back-target="home" />
    <div class="body">
      <div class="grid">
        <div v-for="(a, i) in AVATARS" :key="a.n" class="card" style="width:159px;padding:8px;text-align:center">
          <svg viewBox="0 0 143 180" width="100%" height="180"><rect width="143" height="180" rx="10" :fill="a.bg"/><circle cx="71.5" cy="70" r="28" :fill="a.fg"/><path d="M30 142C30 112 48 96 71.5 96C95 96 113 112 113 142V180H30V142Z" :fill="a.fg"/></svg>
          <div style="font-size:13px;font-weight:500;margin:8px 0">{{ a.n }}</div>
          <div class="up" :class="{ gray: i !== 0 }" style="justify-content:center;border-radius:16px;height:32px" @click="toast('功能开发中')">选择</div>
        </div>
      </div>
    </div>
    <div style="flex:0 0 auto; background:#FFF7F2; padding:14px 20px; text-align:center; font-size:12px; color:#FF7A45">
      数字人功能持续更新中，敬请期待
    </div>
  </section>
</template>
