<script setup>
import { state, go, goTab, toast } from '../store/app'
import TabBar from '../components/TabBar.vue'
</script>

<template>
  <section class="page active">
    <div class="nav">
      <div class="logo">
        <svg height="28" viewBox="0 0 28 28" width="28"><rect fill="#FF4D1C" height="28" rx="8" width="28"/><path d="M11 8.5L19.5 14L11 19.5V8.5Z" fill="#fff"/></svg>
        <span>一源</span>
      </div>
      <div v-if="state.logged" class="avatar" @click="goTab('me')">张</div>
      <div v-else class="login-btn" @click="state.overlay = 'login'">登录</div>
    </div>
    <div class="body">
      <div class="banner">
        <h2>一键生成爆款营销视频</h2>
        <p>选参考 → 说卖点 → 出成片</p>
      </div>
      <div class="feat">
        <div class="big" @click="go('templates')">
          <div class="top">
            <svg height="40" viewBox="0 0 40 40" width="40"><rect fill="#FFF0EA" height="38" rx="12" width="38" x="1" y="1"/><rect fill="none" height="18" rx="4" stroke="#FF4D1C" stroke-width="2" width="19" x="7" y="11"/><path d="M26 16.5L32 13V27L26 23.5V16.5Z" fill="none" stroke="#FF4D1C" stroke-linejoin="round" stroke-width="2"/></svg>
            <b>画面复刻</b>
          </div>
          <p>上传参考画面，复刻它的质感</p>
          <p class="tip">同场景 · 同构图 · 同色调</p>
          <div class="btn-p">立即制作</div>
        </div>
        <div class="small" @click="go('avatars')">
          <div class="top">
            <svg height="40" viewBox="0 0 40 40" width="40"><rect fill="#FFF0EA" height="38" rx="12" width="38" x="1" y="1"/><circle cx="20" cy="16" fill="none" r="6" stroke="#FF4D1C" stroke-width="2"/><path d="M9 32C9 26.5 13.9 22 20 22C26.1 22 31 26.5 31 32" fill="none" stroke="#FF4D1C" stroke-linecap="round" stroke-width="2"/></svg>
            <b>数字人口播</b>
          </div>
          <p>AI 数字人帮你念台词</p>
          <div class="btn-s">去看看</div>
        </div>
        <div class="steps">
          <div class="s"><div class="n">1</div><span>选参考</span></div>
          <div class="s"><div class="n">2</div><span>说卖点</span></div>
          <div class="s"><div class="n">3</div><span>出成片</span></div>
        </div>
      </div>
    </div>
    <TabBar active="home" />
    <button class="kefu" @click="toast('客服：工作日 9:00-21:00')">
      <svg height="26" viewBox="0 0 26 26" width="26"><path d="M6 14V12C6 7.58 9.58 4 14 4C18.42 4 22 7.58 22 12V14" fill="none" stroke="#FF4D1C" stroke-linecap="round" stroke-width="2"/><rect fill="#FF4D1C" height="7" rx="2.25" width="4.5" x="3" y="13"/><rect fill="#FF4D1C" height="7" rx="2.25" width="4.5" x="18.5" y="13"/></svg>
    </button>
  </section>
</template>
