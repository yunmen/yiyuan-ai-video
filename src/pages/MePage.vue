<script setup>
import { state, go, goTab, toast } from '../store/app'
import AppBar from '../components/AppBar.vue'
import TabBar from '../components/TabBar.vue'

function logout() {
  state.logged = false
  state.stack = []
  go('home', true)
  toast('已退出登录')
}

const arrow = 'M7.5 4L13.5 10L7.5 16'
</script>

<template>
  <section class="page active">
    <AppBar title="我的" back-target="home" />
    <div class="body">
      <div class="profile">
        <div class="av">张</div>
        <div>
          <div style="font-size:17px; font-weight:700">火锅张老板</div>
          <div class="muted" style="margin-top:5px">138****6688</div>
        </div>
      </div>
      <div style="padding:20px; display:flex; flex-direction:column; gap:12px">
        <div class="menu" @click="goTab('works')">
          我的作品
          <svg height="20" viewBox="0 0 20 20" width="20"><path :d="arrow" fill="none" stroke="#C9CCD1" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>
        </div>
        <div class="menu" @click="go('balance')">
          <span>账户余额</span>
          <span style="display:flex; align-items:center; gap:6px; color:var(--weak); font-size:13px">剩余 {{ state.credits }} 次
            <svg height="20" viewBox="0 0 20 20" width="20"><path :d="arrow" fill="none" stroke="#C9CCD1" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>
          </span>
        </div>
        <div class="menu" @click="go('support')">
          联系客服
          <svg height="20" viewBox="0 0 20 20" width="20"><path :d="arrow" fill="none" stroke="#C9CCD1" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>
        </div>
        <div class="menu" @click="go('settings')">
          设置
          <svg height="20" viewBox="0 0 20 20" width="20"><path :d="arrow" fill="none" stroke="#C9CCD1" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>
        </div>
        <div style="height:48px; border-radius:24px; background:#fff; display:flex; align-items:center; justify-content:center; color:var(--brand); font-weight:500; font-size:15px; cursor:pointer; margin-top:8px" @click="logout">退出登录</div>
      </div>
    </div>
    <TabBar active="me" />
  </section>
</template>
