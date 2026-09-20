<script setup>
import { computed } from 'vue'
import { state, go, shareLink } from '../store/app'
import { downloadWork, startGeneration } from '../store/generator'
import AppBar from '../components/AppBar.vue'

const work = computed(() => state.works.find(w => w.id === state.gen.workId) || state.works[0])

function onDownload() { downloadWork(work.value) }
function onShare() { shareLink('一源AI视频', work.value ? work.value.title : '我刚用一源做了条爆款视频') }
function regen() { startGeneration(() => go('result')) }
</script>

<template>
  <section class="page active">
    <AppBar title="生成结果" back-target="home" action-text="分享" @action="onShare" />
    <div class="body">
      <div style="padding:20px">
        <div class="vframe">
          <img v-if="work && work.cover" :src="work.cover" alt="视频封面">
          <div class="play">
            <svg height="24" viewBox="0 0 24 24" width="24"><path d="M9 6L18 12L9 18V6Z" fill="#fff"/></svg>
          </div>
          <button class="re" @click="regen">重新生成</button>
        </div>
        <div class="ctl">
          <svg height="20" viewBox="0 0 20 20" width="20"><path d="M6 4L15 10L6 16V4Z" fill="#1A1A1A"/></svg>
          <div class="track"><i :style="{ width: (state.gen.p * 100) + '%' }"></i></div>
          <span class="muted">0:15</span>
          <svg height="20" viewBox="0 0 20 20" width="20"><path d="M4 8V12C4 12.55 4.45 13 5 13H7.5L11 16.5V3.5L7.5 7H5C4.45 7 4 7.45 4 8Z" fill="none" stroke="#5C5C5C" stroke-linejoin="round" stroke-width="1.8"/><path d="M14 7.5C15.2 8.7 15.2 11.3 14 12.5" fill="none" stroke="#5C5C5C" stroke-linecap="round" stroke-width="1.8"/></svg>
        </div>
      </div>
      <div class="ops">
        <div class="btn-p" @click="onDownload">下载视频</div>
        <div class="muted">无水印高清版</div>
        <div class="btn-s" @click="go('templates')">再做一个</div>
        <div style="font-size:14px; color:var(--body); cursor:pointer" @click="onShare">分享给好友</div>
      </div>
      <div class="info">
        <b>{{ work ? work.n : state.tpl.n }} · 我的成品</b>
        <span class="muted">{{ work ? work.t : '' }}</span>
        <span style="font-size:12px; color:var(--body)">15 秒 · 1080P 竖版，适合发抖音</span>
      </div>
    </div>
  </section>
</template>
