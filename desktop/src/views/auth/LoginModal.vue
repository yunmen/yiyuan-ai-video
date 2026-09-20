<script setup>
import { ref, reactive, computed, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import api from '@/api'

const router = useRouter()
const userStore = useUserStore()

// code=验证码登录(首次登录自动注册) password=密码登录
const tab = ref('code')
const loading = ref(false)
const form = reactive({ phone: '', code: '', account: '', password: '' })

// 验证码倒计时
const countdown = ref(0)
const sending = ref(false)
let timer = null

const phoneValid = computed(() => /^1[3-9]\d{9}$/.test(form.phone))

function startCountdown(seconds) {
  countdown.value = seconds
  stopCountdown()
  timer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) stopCountdown()
  }, 1000)
}

function stopCountdown() {
  if (timer) { clearInterval(timer); timer = null }
  if (countdown.value <= 0) countdown.value = 0
}

async function sendCode() {
  if (!phoneValid.value) { window.$message?.warning('请输入正确的手机号'); return }
  sending.value = true
  try {
    const res = await api.account.smsSend.post({ phone: form.phone })
    if (res.code === 1) {
      window.$message?.success('验证码已发送')
      // 开发环境 mock 渠道直接回显验证码,方便联调
      if (res.data?.code) {
        form.code = res.data.code
        window.$message?.info(`开发环境验证码：${res.data.code}`)
      }
      startCountdown(res.data?.interval || 60)
    }
  } catch (e) { /* 拦截器已提示 */ }
  sending.value = false
}

async function loginByCode() {
  if (!phoneValid.value) { window.$message?.warning('请输入正确的手机号'); return }
  if (!form.code) { window.$message?.warning('请输入验证码'); return }
  loading.value = true
  try {
    const res = await api.account.loginByCode.post({ phone: form.phone, code: form.code })
    if (res.code === 1) onSuccess(res.data)
  } catch (e) { /* 拦截器已提示 */ }
  loading.value = false
}

async function loginByPassword() {
  if (!form.account || !form.password) { window.$message?.warning('请输入账号和密码'); return }
  loading.value = true
  try {
    const res = await api.account.login.post({ account: form.account, password: form.password })
    if (res.code === 1) onSuccess(res.data)
  } catch (e) { /* 拦截器已提示 */ }
  loading.value = false
}

function onSuccess(data) {
  userStore.setToken(data.token)
  userStore.setUserInfo(data.info)
  window.$message?.success(data.is_new ? '注册成功，已自动登录' : '登录成功')
  userStore.closeLogin()
  form.code = ''
  form.password = ''
  router.push('/works')
}

function submit() {
  if (tab.value === 'code') loginByCode()
  else loginByPassword()
}

function onTabChange(value) {
  if (value === 'password' && form.phone && !form.account) form.account = form.phone
}

onBeforeUnmount(stopCountdown)
</script>

<template>
  <n-modal
    v-model:show="userStore.loginVisible"
    preset="card"
    :title="null"
    style="max-width: 400px; border-radius: 16px"
    :mask-closable="false"
  >
    <h3 class="login-title">登录一源 AI 视频</h3>
    <p class="login-sub">未注册的手机号将自动创建账号</p>

    <n-tabs v-model:value="tab" type="segment" animated @update:value="onTabChange">
      <!-- 验证码登录(推荐/首次登录) -->
      <n-tab-pane name="code" tab="验证码登录">
        <n-form label-placement="top">
          <n-form-item label="手机号">
            <n-input v-model:value="form.phone" placeholder="请输入手机号" maxlength="11" />
          </n-form-item>
          <n-form-item label="验证码">
            <n-input v-model:value="form.code" placeholder="请输入短信验证码" maxlength="8" @keyup.enter="submit" />
          </n-form-item>
          <n-button
            block
            round
            tertiary
            :disabled="!phoneValid || countdown > 0"
            :loading="sending"
            @click="sendCode"
          >
            {{ countdown > 0 ? `${countdown}s 后重发` : '获取验证码' }}
          </n-button>
          <n-button type="primary" block round class="submit-btn" :loading="loading" @click="loginByCode">
            登录 / 注册
          </n-button>
        </n-form>
      </n-tab-pane>

      <!-- 密码登录 -->
      <n-tab-pane name="password" tab="密码登录">
        <n-form label-placement="top">
          <n-form-item label="账号(手机号)">
            <n-input v-model:value="form.account" placeholder="请输入手机号" />
          </n-form-item>
          <n-form-item label="密码">
            <n-input v-model:value="form.password" type="password" placeholder="请输入密码" @keyup.enter="submit" />
          </n-form-item>
          <n-button type="primary" block round class="submit-btn" :loading="loading" @click="loginByPassword">
            登录
          </n-button>
        </n-form>
        <p class="tip">还没有密码？请使用「验证码登录」登录后在设置中创建密码</p>
      </n-tab-pane>
    </n-tabs>

    <p class="agree">登录即表示同意用户协议和隐私政策</p>
  </n-modal>
</template>

<style scoped>
.login-title { margin: 0; text-align: center; font-size: 18px; }
.login-sub { margin: 6px 0 0; text-align: center; font-size: 12px; color: var(--weak); }
.submit-btn { margin-top: 12px; }
.tip { font-size: 12px; color: var(--weak); text-align: center; margin: 12px 0 0; line-height: 1.6; }
.agree { font-size: 11px; color: #9B9B9B; text-align: center; margin: 14px 0 0; }
</style>
