<script setup>
import { computed, ref } from 'vue'
import { state, toast, resetMaterial } from '../store/app'
import AppBar from '../components/AppBar.vue'
import FilePicker from '../components/FilePicker.vue'

const canGen = computed(() => state.hasImg && state.title.trim().length > 0)
const picker = ref(null)

function onPicked({ dataUrl }) {
  state.imgDataUrl = dataUrl
  state.hasImg = true
  toast('产品图已上传')
}

function onErr(msg) { toast(msg) }

function reset() {
  resetMaterial()
  toast('已恢复模板默认内容')
}

function generate() {
  if (!state.hasImg) { toast('请先上传产品图'); return }
  if (!state.title.trim()) { toast('请填写视频大标题'); return }
  if (state.credits <= 0) { toast('今日免费额度已用完'); return }
  state.overlay = 'confirm'
}
</script>

<template>
  <section class="page active">
    <AppBar title="替换素材" back-target="templates" action-text="重置" @action="reset" />
    <div class="body">
      <div class="preview">
        <div class="pv">
          <img v-if="state.imgDataUrl" :src="state.imgDataUrl" alt="产品图预览">
          <div class="play"><svg height="24" viewBox="0 0 24 24" width="24"><path d="M9 6L18 12L9 18V6Z" fill="#fff"/></svg></div>
          <div class="dur">0:15</div>
        </div>
        <div class="pmeta"><b>{{ state.tpl.n }}</b><span>{{ state.tpl.d }}</span></div>
      </div>
      <div class="form">
        <div class="item">
          <div class="row">
            <div style="display:flex; gap:12px; align-items:center">
              <div class="thumb">
                <img v-if="state.imgDataUrl" :src="state.imgDataUrl" alt="缩略图">
                <svg v-else height="30" viewBox="0 0 30 30" width="30"><path d="M15 11V19M15 11L11.5 14.5M15 11L18.5 14.5" fill="none" stroke="#B0B3B8" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"/><path d="M9 21H21" fill="none" stroke="#B0B3B8" stroke-linecap="round" stroke-width="1.8"/></svg>
              </div>
              <div><div class="lbl">你的产品图</div><div class="sub">拍照或相册选一张</div></div>
            </div>
            <button class="up" :class="{ gray: state.hasImg }" @click="picker.open()">{{ state.hasImg ? '重新上传' : '上传' }}</button>
          </div>
        </div>
        <div class="item">
          <div class="row"><div class="lbl">视频大标题</div><div class="counter">{{ state.title.length }}/20</div></div>
          <div class="inp"><input v-model="state.title" maxlength="20"></div>
        </div>
        <div class="item">
          <div class="row"><div class="lbl">副标题 / 卖点</div><div class="counter">{{ state.subtitle.length }}/30</div></div>
          <div class="inp"><input v-model="state.subtitle" maxlength="30"></div>
        </div>
        <div class="item">
          <div class="row"><div class="lbl">想让视频说什么（选填）</div><div class="counter">{{ state.speak.length }}/50</div></div>
          <div class="inp" style="height:88px; align-items:flex-start; padding-top:12px"><textarea v-model="state.speak" maxlength="50"></textarea></div>
          <div class="sub" style="margin-top:8px">不填就用模板原配</div>
        </div>
        <div class="item">
          <div class="lbl" style="margin-bottom:12px">你的 Logo（选填）</div>
          <div class="row">
            <button class="up gray" @click="toast('Logo 上传将在下一版开放')">上传 Logo</button>
            <div @click="state.logoOn = !state.logoOn">
              <svg v-if="!state.logoOn" width="44" height="24" viewBox="0 0 44 24"><rect width="44" height="24" rx="12" fill="#DCDFE4"/><circle cx="12" cy="12" r="10" fill="#fff"/></svg>
              <svg v-else width="44" height="24" viewBox="0 0 44 24"><rect width="44" height="24" rx="12" fill="#FF4D1C"/><circle cx="32" cy="12" r="10" fill="#fff"/></svg>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="footer">
      <div>
        <div style="font-size:13px; font-weight:500">预计生成约 2 分钟</div>
        <div class="muted">今天还有 {{ state.credits }} 次免费额度</div>
      </div>
      <button id="genBtn" class="btn-p" :disabled="!canGen" @click="generate">生成视频</button>
    </div>
    <FilePicker ref="picker" accept="image/*" :max-size-m-b="10" @picked="onPicked" @error="onErr" />
  </section>
</template>
