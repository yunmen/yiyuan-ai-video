<script setup>
import { computed, onMounted } from 'vue'
import { state, go, toast } from '../store/app'
import { startGeneration, GEN_STEPS } from '../store/generator'
import AppBar from '../components/AppBar.vue'

const stepText = computed(() => '正在' + GEN_STEPS[state.gen.stepIdx])
const stepsHtml = computed(() =>
  GEN_STEPS.map((s, i) => `<span class="${i <= state.gen.stepIdx ? 'done' : 'todo'}">${s}</span>`).join('<span class="todo"> → </span>')
)

onMounted(() => {
  if (!state.gen.running && state.gen.p === 0) {
    startGeneration(() => { go('result') })
  } else if (state.gen.running) {
    // 中途切回此页（从结果页重新生成等）
    startGeneration(() => { go('result') })
  }
})

function leaveGen() {
  state.gen.left = true
  state.stack = []
  go('home', true)
  toast('已返回首页，生成完成后会通知你')
}
</script>

<template>
  <section class="page active">
    <AppBar title="生成中" back-target="templates" />
    <div class="center">
      <svg class="spin" height="96" viewBox="0 0 96 96" width="96"><circle cx="48" cy="48" fill="none" r="44" stroke="#FFE3D9" stroke-width="6"/><path d="M48 4C72.3 4 92 23.7 92 48" fill="none" stroke="#FF4D1C" stroke-linecap="round" stroke-width="6"/><rect fill="#FFF0EA" height="28" rx="8" width="36" x="30" y="34"/><path d="M43 42L54 48L43 54V42Z" fill="#FF4D1C"/></svg>
      <div style="font-size:16px; font-weight:700">正在为你生成爆款视频...</div>
      <div style="width:100%; display:flex; flex-direction:column; gap:10px">
        <div style="display:flex; justify-content:space-between; font-size:12px">
          <span style="color:var(--body)">{{ stepText }}</span>
          <span style="color:var(--brand); font-weight:700">{{ Math.round(state.gen.p * 100) }}%</span>
        </div>
        <div class="pbar"><i :style="{ width: state.gen.p * 100 + '%' }"></i></div>
        <div class="stepsrow" v-html="stepsHtml"></div>
      </div>
    </div>
    <div class="bottom-tip">
      <p class="muted" style="margin:0; text-align:center">生成大约需要 2 分钟，你可以先去做别的事</p>
      <p class="muted" style="margin:0; text-align:center">生成完成后会在「我的作品」里找到</p>
      <div class="linkbtn" @click="leaveGen">返回首页等</div>
    </div>
  </section>
</template>
