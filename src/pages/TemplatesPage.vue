<script setup>
import { ref, computed } from 'vue'
import { go, toast, pickTemplate } from '../store/app'
import { TPLS, CATS } from '../data'
import AppBar from '../components/AppBar.vue'
import FilePicker from '../components/FilePicker.vue'

const seg = ref('tpl')
const curCat = ref('餐饮')
const picker = ref(null)

const list = computed(() => TPLS.filter(t => curCat.value === '全部' || t.c === curCat.value))

function onPicked({ file }) {
  toast(`已选择 ${file.name}，开始解析…`)
  setTimeout(() => go('material'), 800)
}
function onErr(msg) { toast(msg) }
</script>

<template>
  <section class="page active">
    <AppBar title="爆款视频" back-target="home" />
    <div class="seg">
      <div :class="{ on: seg === 'tpl' }" @click="seg = 'tpl'"><b>选模板做</b><i></i></div>
      <div :class="{ on: seg === 'up' }" @click="seg = 'up'"><b>上传参考做</b><i></i></div>
    </div>
    <div v-show="seg === 'tpl'" class="body">
      <div class="cats">
        <div v-for="c in CATS" :key="c" :class="{ on: c === curCat }" @click="curCat = c">{{ c }}</div>
      </div>
      <div class="grid">
        <div v-if="!list.length" style="width:100%;text-align:center;padding:60px 0;color:#9B9B9B;font-size:13px">该分类模板整理中，先看看其他分类</div>
        <div v-for="t in list" :key="t.n" class="tcard" @click="pickTemplate(t)">
          <div class="cover" :style="{ background: `linear-gradient(180deg,${t.g[0]},${t.g[1]})` }">
            <div class="play"><svg width="18" height="18" viewBox="0 0 18 18"><path d="M6 3L14 9L6 15V3Z" fill="#fff"/></svg></div>
            <div class="tag">做同款</div>
          </div>
          <p>{{ t.n }}</p>
        </div>
      </div>
    </div>
    <div v-show="seg === 'up'" class="body">
      <div class="upload-zone" @click="picker.open()">
        <div class="ic"><svg height="28" viewBox="0 0 28 28" width="28"><path d="M14 20V7M14 7L8.5 12.5M14 7L19.5 12.5" fill="none" stroke="#FF4D1C" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/><path d="M5 22H23" fill="none" stroke="#FF4D1C" stroke-linecap="round" stroke-width="2"/></svg></div>
        <p>拖拽视频到这里，或点击上传</p>
        <p class="muted">支持 5-30 秒短视频，MP4 格式</p>
      </div>
      <div style="padding:0 20px"><div class="btn-p" @click="picker.open()">上传视频</div></div>
    </div>
    <FilePicker ref="picker" accept="video/mp4,video/webm,video/quicktime" :max-size-m-b="100" @picked="onPicked" @error="onErr" />
  </section>
</template>
