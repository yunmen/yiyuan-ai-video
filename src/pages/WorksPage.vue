<script setup>
import { state, goTab, removeWork, toast } from '../store/app'
import { downloadWork } from '../store/generator'
import AppBar from '../components/AppBar.vue'
import TabBar from '../components/TabBar.vue'

function onDownload(w) { downloadWork(w) }
function onDelete(w) {
  removeWork(w.id)
  toast('已删除该作品')
}
</script>

<template>
  <section class="page active">
    <AppBar title="我的作品" back-target="home" hide-back />
    <div class="body">
      <div v-if="!state.works.length" class="empty">
        <svg width="96" height="96" viewBox="0 0 96 96"><rect x="14" y="22" width="68" height="50" rx="10" stroke="#D8DADE" stroke-width="3" fill="none"/><path d="M14 38H82" stroke="#D8DADE" stroke-width="3"/><circle cx="34" cy="30" r="3" fill="#D8DADE"/><circle cx="44" cy="30" r="3" fill="#D8DADE"/><path d="M40 46L54 54L40 62V46Z" fill="#E3E5E8"/></svg>
        <div style="font-size:14px;color:#9B9B9B">还没有作品，去做第一条爆款视频吧</div>
        <div class="btn-p" style="width:160px" @click="goTab('home')">去制作</div>
      </div>
      <div v-else style="padding:20px">
        <div v-for="w in state.works" :key="w.id" class="wcard">
          <div class="cov">
            <img v-if="w.cover" :src="w.cover" alt="封面">
            <svg v-else width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="rgba(0,0,0,.28)"/><path d="M9.5 7.5L16 12L9.5 16.5V7.5Z" fill="#fff"/></svg>
          </div>
          <div class="txt"><b>{{ w.n }}</b><span>{{ w.t }}</span></div>
          <div class="ops2">
            <button class="up" @click="onDownload(w)">下载</button>
            <button class="up gray" @click="onDelete(w)">删除</button>
          </div>
        </div>
      </div>
    </div>
    <TabBar active="works" />
  </section>
</template>
