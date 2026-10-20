<template>
  <view class="app-page app-page--plain reg">
    <AppNavBar title="注册" />

    <view class="reg__body">
      <view class="reg__hero">
        <view class="reg__logo">
          <text class="reg__logo-char">溪</text>
        </view>
        <text class="reg__title">创建账号</text>
        <text class="reg__sub">注册后即可用 AI 复刻视频、生成口播与文案</text>
      </view>

      <view class="app-card reg__card">
        <view class="reg__field">
          <text class="reg__field-label">登录名</text>
          <AppField
            v-model="account"
            class="app-field"
            name="username"
            autocomplete="username"
            maxlength="20"
            placeholder="6-20 位，支持字母、数字和 . _ @ -"
            placeholder-class="app-placeholder"
            @input="clearError" aria-label="用户名"/>
        </view>

        <view class="reg__field">
          <text class="reg__field-label">密码</text>
          <view class="reg__password">
            <AppField
              v-model="password"
              class="app-field reg__password-input"
              name="password"
              autocomplete="new-password"
              :password="!passwordVisible"
              maxlength="32"
              placeholder="请输入 6-32 位密码"
              placeholder-class="app-placeholder"
              @input="clearError" aria-label="密码"/>
            <text
              class="reg__password-toggle"
              role="button"
              :aria-label="passwordVisible ? '隐藏密码' : '显示密码'"
              @click="passwordVisible = !passwordVisible"
             tabindex="0" @keydown.enter.stop.prevent="passwordVisible = !passwordVisible" @keydown.space.stop.prevent="passwordVisible = !passwordVisible">{{ passwordVisible ? '隐藏' : '显示' }}</text>
          </view>
        </view>

        <view class="reg__field">
          <text class="reg__field-label">确认密码</text>
          <view class="reg__password">
            <AppField
              v-model="confirmPassword"
              class="app-field reg__password-input"
              name="confirmPassword"
              autocomplete="new-password"
              :password="!confirmVisible"
              maxlength="32"
              placeholder="请再次输入密码"
              placeholder-class="app-placeholder"
              @input="clearError" aria-label="确认密码"/>
            <text
              class="reg__password-toggle"
              role="button"
              :aria-label="confirmVisible ? '隐藏确认密码' : '显示确认密码'"
              @click="confirmVisible = !confirmVisible"
             tabindex="0" @keydown.enter.stop.prevent="confirmVisible = !confirmVisible" @keydown.space.stop.prevent="confirmVisible = !confirmVisible">{{ confirmVisible ? '隐藏' : '显示' }}</text>
          </view>
        </view>

        <view class="reg__field">
          <text class="reg__field-label">昵称（选填）</text>
          <AppField
            v-model="nickname"
            class="app-field"
            maxlength="30"
            placeholder="不填则使用系统默认昵称"
            placeholder-class="app-placeholder"
            @input="clearError" aria-label="昵称"/>
        </view>

        <view class="reg__field">
          <text class="reg__field-label">邀请码（选填）</text>
          <AppField v-model="inviteCode" class="app-field" aria-label="邀请码（选填）" maxlength="8" placeholder="填写好友的 8 位邀请码" placeholder-class="app-placeholder" @input="clearError" />
        </view>
        <view v-if="submitError" class="reg__error">{{ submitError }}</view>

        <view
          class="app-btn-brand reg__submit"
          :class="{ 'reg__submit--loading': loading }"
          role="button"
          aria-label="注册"
          @click="handleRegister"
         tabindex="0" @keydown.enter.stop.prevent="handleRegister" @keydown.space.stop.prevent="handleRegister" :aria-busy="loading" :aria-disabled="loading">
          <AppIcon v-if="loading" name="loader" :size="18" color="#FFFFFF" :stroke-width="2.5" class="app-spin" />
          <text>{{ loading ? '注册中…' : '注册' }}</text>
        </view>

        <view class="reg__extra">
          <text class="reg__extra-text">已有账号？</text>
          <text class="reg__extra-link" role="button" @click="goLogin" tabindex="0" @keydown.enter.stop.prevent="goLogin" @keydown.space.stop.prevent="goLogin">立即登录</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import AppNavBar from '@/components/AppNavBar.vue'
import AppField from '@/components/AppField.vue'
import api from '@/api'
import { useUserStore } from '@/store/modules/user'
import { validateAccount, validatePassword } from '@/utils/account'
import { getSafeInternalRedirect, go, goReplace } from '@/utils/navigation'
import { refreshCurrentUserProfile } from '@/utils/session'

/**
 * 注册页。
 *
 * 后端注册接口只创建账号、不返回 token（后端只签发单个 token，无续期机制），
 * 因此注册成功后立刻用同一组账号密码登录一次，把登录态补齐再回跳来源页。
 */

const userStore = useUserStore()

const account = ref('')
const password = ref('')
const confirmPassword = ref('')
const nickname = ref('')
/** 注册时一次性提交的邀请码，已有账号不可补领。 */
const inviteCode = ref('')
const passwordVisible = ref(false)
const confirmVisible = ref(false)
const loading = ref(false)
const submitError = ref('')

let redirect = '/pages/home/index'

onLoad((options) => {
  const raw = options && options.redirect ? String(options.redirect) : '/pages/home/index'
  redirect = getSafeInternalRedirect(raw)
  inviteCode.value = String(options?.invite_code || '').trim().toUpperCase().slice(0, 8)
})

/** 编辑输入时清理上次的校验反馈。 */
function clearError() {
  submitError.value = ''
}

function toast(title) {
  uni.showToast({ title, icon: 'none' })
}

/** 注册成功后自动登录；任一步失败都退回登录页让用户手动登录 */
async function autoLogin() {
  try {
    const res = await api.account.login.post(
      { account: account.value.trim(), password: password.value },
      { suppressGlobalError: true, suppressGlobalAuthError: true }
    )
    const token = res && res.code === 1 ? res.data?.token : null
    if (!token) return false
    userStore.setToken(token)
    userStore.setUserInfo(res.data?.info)
    await refreshCurrentUserProfile(userStore)
    return true
  } catch (err) {
    console.error('注册后自动登录失败，将引导用户手动登录', err)
    return false
  }
}

/** 校验注册表单并连同可选邀请码提交，成功后自动登录。 */
async function handleRegister() {
  if (loading.value) return
  submitError.value = ''

  const accountError = validateAccount(account.value)
  const passwordError = validatePassword(password.value)
  if (accountError || passwordError) {
    submitError.value = accountError || passwordError
    return
  }
  if (password.value !== confirmPassword.value) {
    submitError.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  try {
    const res = await api.account.register.post(
      {
        account: account.value.trim(),
        password: password.value,
        nickname: nickname.value.trim(),
        invite_code: inviteCode.value.trim().toUpperCase() || undefined,
      },
      { suppressGlobalError: true, suppressGlobalAuthError: true }
    )
    if (!res || res.code !== 1) {
      submitError.value = res?.message || '注册失败，请稍后重试'
      return
    }

    uni.showToast({ title: '注册成功', icon: 'success' })

    const logged = await autoLogin()
    if (!logged) {
      // 没拿到登录态不能停在注册页（返回按钮已被隐藏），直接去登录页
      toast('注册成功，请登录')
      setTimeout(() => {
        goReplace('/pages/login/index')
      }, 400)
      return
    }

    setTimeout(() => {
      goReplace(getSafeInternalRedirect(redirect))
    }, 400)
  } catch (err) {
    // 账号已存在等业务失败由后端给出可执行文案，原样展示
    console.error('注册失败', err)
    submitError.value = err?.data?.message || err?.message || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function goLogin() {
  go({ path: '/pages/login/index', query: { redirect } })
}
</script>

<style lang="scss" scoped>
.reg__body {
  min-height: calc(100vh - 52px);
  padding: 32px 18px 40px;
  background:
    linear-gradient(rgba(177, 45, 38, 0.035) 1px, transparent 1px),
    var(--bg-page);
  background-size: 100% 32px;
}

/* ============ 头部 ============ */
.reg__hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 24px;
}

.reg__logo {
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

.reg__logo-char {
  font-family: var(--font-serif);
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
  color: #ffffff;
}

.reg__title {
  font-family: var(--font-serif);
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--text-primary);
}

.reg__sub {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-tertiary);
  text-align: center;
}

/* ============ 表单 ============ */
.reg__card {
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

.reg__field {
  margin-bottom: 16px;
}

.reg__field-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.reg__password {
  position: relative;
  display: flex;
  align-items: center;
}

.reg__password-input {
  padding-right: 56px;
}

.reg__password-toggle {
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

.reg__error {
  background: rgba(177, 45, 38, 0.07);
  border-left: 3px solid var(--state-error);
  color: var(--state-error);
  font-size: 13px;
  line-height: 1.5;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.reg__submit {
  height: 48px;
  font-size: 15px;

  &--loading {
    opacity: 0.8;
  }
}

.reg__extra {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 16px;
  font-size: 13px;
}

.reg__extra-text {
  color: var(--text-tertiary);
}

.reg__extra-link {
  color: var(--brand-primary);
  font-weight: 600;
}
</style>
