<template>
  <view class="app-page app-page--plain auth">
    <AppNavBar title="登录" :auto-back="false" />

    <view class="auth__body">
      <view class="auth__hero">
        <view class="auth__logo">
          <text class="auth__logo-char">溪</text>
        </view>
        <text class="auth__title">欢迎回来</text>
        <text class="auth__sub">登录后额度与作品会同步到你的账号</text>
      </view>

      <!-- 登录方式切换：验证码为默认，避免用户忘记密码时卡住 -->
      <view class="auth__segment">
        <view
          v-for="tab in MODE_OPTIONS"
          :key="tab.key"
          class="auth__seg"
          :class="{ 'auth__seg--active': mode === tab.key }"
          role="button"
          :aria-label="tab.label"
          @click="switchMode(tab.key)"
         tabindex="0" @keydown.enter.stop.prevent="switchMode(tab.key)" @keydown.space.stop.prevent="switchMode(tab.key)" :aria-pressed="mode === tab.key">
          <text>{{ tab.label }}</text>
        </view>
      </view>

      <view class="app-card auth__card">
        <!-- 验证码登录 -->
        <template v-if="mode === 'code'">
          <view class="auth__field">
            <text class="auth__field-label">手机号</text>
            <AppField
              v-model="phone"
              class="app-field"
              type="tel"
              maxlength="11"
              placeholder="请输入 11 位手机号"
              placeholder-class="app-placeholder"
              @input="clearError" aria-label="手机号"/>
          </view>

          <view class="auth__field">
            <text class="auth__field-label">验证码</text>
            <view class="auth__code-row">
              <AppField
                v-model="code"
                class="app-field auth__code-input"
                type="number"
                maxlength="6"
                placeholder="请输入 6 位验证码"
                placeholder-class="app-placeholder"
                @input="clearError" aria-label="验证码"/>
              <text
                class="auth__code-btn"
                :class="{ 'auth__code-btn--disabled': counting || sendingCode }"
                role="button"
                @click="handleSendCode"
               tabindex="0" @keydown.enter.stop.prevent="handleSendCode" @keydown.space.stop.prevent="handleSendCode">{{ codeBtnText }}</text>
            </view>
          </view>
        </template>

        <!-- 密码登录 -->
        <template v-else>
          <view class="auth__field">
            <text class="auth__field-label">登录名</text>
            <AppField
              v-model="account"
              class="app-field"
              name="username"
              autocomplete="username"
              maxlength="20"
              placeholder="请输入登录名"
              placeholder-class="app-placeholder"
              @input="clearError" aria-label="用户名"/>
          </view>

          <view class="auth__field">
            <text class="auth__field-label">密码</text>
            <view class="auth__password">
              <AppField
                v-model="password"
                class="app-field auth__password-input"
                name="password"
                autocomplete="current-password"
                :password="!passwordVisible"
                maxlength="32"
                placeholder="请输入密码"
                placeholder-class="app-placeholder"
                @input="clearError" aria-label="密码"/>
              <text
                class="auth__password-toggle"
                role="button"
                :aria-label="passwordVisible ? '隐藏密码' : '显示密码'"
                @click="passwordVisible = !passwordVisible"
               tabindex="0" @keydown.enter.stop.prevent="passwordVisible = !passwordVisible" @keydown.space.stop.prevent="passwordVisible = !passwordVisible">{{ passwordVisible ? '隐藏' : '显示' }}</text>
            </view>
          </view>
        </template>

        <view v-if="mode === 'code'" class="auth__field">
          <text class="auth__field-label">邀请码（新用户选填）</text>
          <AppField v-model="inviteCode" class="app-field" aria-label="邀请码（新用户选填）" maxlength="8" placeholder="首次登录注册时填写好友邀请码" placeholder-class="app-placeholder" @input="clearError" />
        </view>
        <view v-if="submitError" class="auth__error">{{ submitError }}</view>

        <view
          class="app-btn-brand auth__submit"
          :class="{ 'auth__submit--loading': loading }"
          role="button"
          aria-label="登录"
          @click="handleSubmit"
         tabindex="0" @keydown.enter.stop.prevent="handleSubmit" @keydown.space.stop.prevent="handleSubmit" :aria-busy="loading" :aria-disabled="loading">
          <AppIcon v-if="loading" name="loader" :size="18" color="#FFFFFF" :stroke-width="2.5" class="app-spin" />
          <text>{{ loading ? '登录中…' : '登录' }}</text>
        </view>

        <view class="auth__extra">
          <text class="auth__extra-text">还没有账号？</text>
          <text class="auth__extra-link" role="button" @click="goRegister" tabindex="0" @keydown.enter.stop.prevent="goRegister" @keydown.space.stop.prevent="goRegister">立即注册</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import AppNavBar from '@/components/AppNavBar.vue'
import AppField from '@/components/AppField.vue'
import api from '@/api'
import { useUserStore } from '@/store/modules/user'
import { validateAccount, validatePassword, validatePhone } from '@/utils/account'
import { getSafeInternalRedirect, go, goReplace } from '@/utils/navigation'
import { refreshCurrentUserProfile } from '@/utils/session'

/**
 * 登录页（验证码登录 / 密码登录）。
 *
 * 两种方式共用同一套登录态写入与回跳逻辑；后端只签发单个 token，没有续期机制，
 * 因此这里只处理 token 与 info，不做任何续期。
 */

const MODE_OPTIONS = [
  { key: 'code', label: '验证码登录' },
  { key: 'password', label: '密码登录' },
]

/** 重发倒计时秒数，与后端 60s 发送间隔一致 */
const COUNTDOWN_SECONDS = 60

const userStore = useUserStore()

const mode = ref('code')
const phone = ref('')
const code = ref('')
/** 验证码首次登录自动注册时提交，老用户登录不会获得注册奖励。 */
const inviteCode = ref('')
const account = ref('')
const password = ref('')
const passwordVisible = ref(false)
const loading = ref(false)
const sendingCode = ref(false)
const countdown = ref(0)
const submitError = ref('')

let redirect = '/pages/home/index'
let countdownTimer = null

const counting = computed(() => countdown.value > 0)
const codeBtnText = computed(() => (counting.value ? `${countdown.value}s 后重发` : '获取验证码'))

onLoad((options) => {
  // 先清洗回跳地址，后续 login/register 的所有使用点都是站内安全路径
  const raw = options && options.redirect ? String(options.redirect) : '/pages/home/index'
  redirect = getSafeInternalRedirect(raw)
  inviteCode.value = String(options?.invite_code || '').trim().toUpperCase().slice(0, 8)
  // 已登录直接跳走，避免停留在登录页还能退回登录态
  if (userStore.isLoggedIn) {
    goReplace(redirect)
  }
})

function clearError() {
  submitError.value = ''
}

function switchMode(key) {
  if (mode.value === key) return
  mode.value = key
  submitError.value = ''
}

function toast(title) {
  uni.showToast({ title, icon: 'none' })
}

function startCountdown() {
  countdown.value = COUNTDOWN_SECONDS
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      clearInterval(countdownTimer)
      countdownTimer = null
      countdown.value = 0
    }
  }, 1000)
}

/** 发送验证码：mock 渠道会把验证码放在 data.code 里回显，方便没有短信通道时联调 */
async function handleSendCode() {
  if (counting.value || sendingCode.value) return

  const phoneError = validatePhone(phone.value)
  if (phoneError) {
    submitError.value = phoneError
    return
  }

  sendingCode.value = true
  submitError.value = ''
  try {
    const res = await api.account.smsSend.post(
      { phone: phone.value.trim() },
      { suppressGlobalError: true }
    )
    if (!res || res.code !== 1) {
      submitError.value = res?.message || '验证码发送失败，请稍后重试'
      return
    }
    startCountdown()
    const devCode = res.data?.code
    if (devCode) {
      code.value = String(devCode)
      toast('模拟验证码已自动填入')
    } else {
      toast('验证码已发送')
    }
  } catch (err) {
    console.error('发送验证码失败', err)
    submitError.value = err?.data?.message || err?.message || '验证码发送失败，请稍后重试'
  } finally {
    sendingCode.value = false
  }
}

/** 按当前方式提交登录 */
async function handleSubmit() {
  if (loading.value) return
  submitError.value = ''

  if (mode.value === 'code') {
    const phoneError = validatePhone(phone.value)
    if (phoneError) {
      submitError.value = phoneError
      return
    }
    if (!code.value.trim()) {
      submitError.value = '请输入验证码'
      return
    }
  } else {
    const accountError = validateAccount(account.value)
    const passwordError = validatePassword(password.value)
    if (accountError || passwordError) {
      submitError.value = accountError || passwordError
      return
    }
  }

  loading.value = true
  try {
    const res = mode.value === 'code'
      ? await api.account.loginByCode.post(
          { phone: phone.value.trim(), code: code.value.trim(), invite_code: inviteCode.value.trim().toUpperCase() || undefined },
          { suppressGlobalError: true, suppressGlobalAuthError: true }
        )
      : await api.account.login.post(
          { account: account.value.trim(), password: password.value },
          { suppressGlobalError: true, suppressGlobalAuthError: true }
        )

    if (!res || res.code !== 1) {
      submitError.value = res?.message || '登录失败，请稍后重试'
      return
    }

    const token = res.data?.token
    if (!token) {
      submitError.value = '登录失败，请稍后重试'
      return
    }

    userStore.setToken(token)
    userStore.setUserInfo(res.data?.info)
    await refreshCurrentUserProfile(userStore)
    uni.showToast({ title: '登录成功', icon: 'success' })
    setTimeout(() => {
      goReplace(getSafeInternalRedirect(redirect))
    }, 400)
  } catch (err) {
    console.error('登录失败', err)
    submitError.value = err?.data?.message || err?.message || '登录失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function goRegister() {
  go({ path: '/pages/register/index', query: { redirect } })
}

onUnload(() => {
  // 离开页面停掉倒计时，避免残留定时器继续改状态
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = null
})
</script>

<style lang="scss" scoped>
.auth__body {
  min-height: calc(100vh - 52px);
  padding: 32px 18px 40px;
  background:
    linear-gradient(rgba(177, 45, 38, 0.035) 1px, transparent 1px),
    var(--bg-page);
  background-size: 100% 32px;
}

/* ============ 头部 ============ */
.auth__hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 24px;
}

.auth__logo {
  width: 64px;
  height: 64px;
  border-radius: 20px;
  background: var(--brand-primary);
  box-shadow: var(--shadow-brand);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.auth__logo-char {
  font-family: var(--font-serif);
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
  color: #ffffff;
}

.auth__title {
  font-family: var(--font-serif);
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--text-primary);
}

.auth__sub {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-tertiary);
  text-align: center;
}

/* ============ 方式切换 ============ */
.auth__segment {
  display: flex;
  padding: 3px;
  background: var(--bg-hover);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.auth__seg {
  flex: 1;
  padding: 10px 0;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-tertiary);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);

  &--active {
    background: var(--bg-card);
    color: var(--brand-primary);
    box-shadow: var(--shadow-sm);
  }
}

/* ============ 表单 ============ */
.auth__card {
  padding: 24px 18px;
  background: var(--paper-card);
  border: 5px solid var(--paper-100);
  border-radius: 24px;
  box-shadow: var(--shadow-sm);
  position: relative;

  &::before,
  &::after {
    display: none;
    content: '';
    position: absolute;
    top: 16px;
    bottom: 16px;
    width: 1px;
    background: rgba(177, 45, 38, 0.08);
  }

  &::before { left: 7px; }
  &::after { right: 7px; }
}

.auth__field {
  margin-bottom: 16px;
}

/* uni-input 默认高度不足以容纳表单内边距，需给内部输入区保留可点击高度。 */
.auth__field .app-field {
  box-sizing: border-box;
  height: 48px;
}

.auth__field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.auth__code-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.auth__code-input {
  flex: 1;
  min-width: 0;
}

.auth__code-btn {
  min-height: 44px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  padding: 0 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--brand-primary);

  &--disabled {
    color: var(--text-muted);
  }
}

.auth__password {
  position: relative;
  display: flex;
  align-items: center;
}

.auth__password-input {
  padding-right: 56px;
}

.auth__password-toggle {
  position: absolute;
  right: 6px;
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 500;
  color: var(--brand-primary);
}

.auth__error {
  background: rgba(177, 45, 38, 0.07);
  border-left: 3px solid var(--state-error);
  color: var(--state-error);
  font-size: 13px;
  line-height: 1.5;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.auth__submit {
  height: 48px;
  font-size: 15px;

  &--loading {
    opacity: 0.8;
  }
}

.auth__extra {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 16px;
  font-size: 13px;
}

.auth__extra-text {
  color: var(--text-tertiary);
}

.auth__extra-link {
  color: var(--brand-primary);
  font-weight: 600;
}
</style>
