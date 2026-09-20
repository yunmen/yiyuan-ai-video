<script setup>
import { ref } from 'vue'
import { state, toast } from '../store/app'

const phone = ref('')
const codeBtn = ref('获取验证码')
const counting = ref(false)

function close() { state.overlay = null }

function sendCode() {
  if (counting.value) return
  let n = 59
  counting.value = true
  codeBtn.value = n + 's'
  const iv = setInterval(() => {
    n--
    codeBtn.value = n + 's'
    if (n <= 0) {
      clearInterval(iv)
      codeBtn.value = '获取验证码'
      counting.value = false
    }
  }, 1000)
  toast('验证码已发送（演示版：任意 4 位）')
}

function doLogin() {
  if (phone.value.length < 11) { toast('请输入 11 位手机号'); return }
  state.logged = true
  state.overlay = null
  toast('登录成功，欢迎回来')
}

function confirmGenerate() {
  if (state.credits <= 0) {
    toast('今日免费额度已用完')
    return
  }
  // 扣减额度并跳转到生成页（生成器在那里启动）
  state.credits--
  state.overlay = null
  state.stack = []
  state.dir = 'slide-in'
  state.cur = 'generating'
  state.gen = { running: false, p: 0, stepIdx: 0, left: false, workId: null }
}
</script>

<template>
  <div class="overlay" :class="{ on: state.overlay }" @click.self="close">
    <!-- 登录 / 注册 -->
    <div v-if="state.overlay === 'login'" class="modal">
      <h3>登录 / 注册</h3>
      <div class="inp"><input v-model="phone" maxlength="11" placeholder="请输入手机号"></div>
      <div style="display:flex; gap:8px">
        <div class="inp" style="flex:1"><input placeholder="验证码"></div>
        <div class="btn-p" style="width:106px; height:46px; font-size:13px; border-radius:10px; background:var(--brand-bg); color:var(--brand)" @click="sendCode">{{ codeBtn }}</div>
      </div>
      <div class="btn-p" @click="doLogin">登录 / 注册</div>
      <p class="agree">登录即表示同意用户协议和隐私政策</p>
    </div>
    <!-- 生成确认 -->
    <div v-else-if="state.overlay === 'confirm'" class="modal">
      <h3>确认开始生成？</h3>
      <p class="muted" style="margin:0; text-align:center; line-height:1.7">将用你填写的素材替换模板内容，<br>生成大约需要 2 分钟。</p>
      <div style="display:flex; gap:10px">
        <div class="btn-s" style="flex:1; font-size:15px" @click="close">再看看</div>
        <div class="btn-p" style="flex:1; font-size:15px" @click="confirmGenerate">开始生成</div>
      </div>
    </div>
  </div>
</template>
