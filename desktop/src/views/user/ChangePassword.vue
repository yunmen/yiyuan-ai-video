<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import api from '@/api'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)

// 验证码注册的用户没有密码,此时走「设置密码」(无需原密码)
const hasPassword = computed(() => userStore.userInfo?.has_password !== false)

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

async function onSubmit() {
  if (hasPassword.value && !form.old_password) return window.$message?.warning('请输入原密码')
  if (form.new_password.length < 6) return window.$message?.warning('新密码至少 6 位')
  if (form.new_password !== form.confirm_password) return window.$message?.warning('两次输入的新密码不一致')
  if (hasPassword.value && form.old_password === form.new_password) return window.$message?.warning('新密码不能与原密码相同')

  loading.value = true
  try {
    if (hasPassword.value) {
      await api.account.changePassword.post({
        old_password: form.old_password,
        new_password: form.new_password
      })
    } else {
      await api.account.setPassword.post({ password: form.new_password })
    }
    window.$message?.success(hasPassword.value ? '密码修改成功，请重新登录' : '密码设置成功，请重新登录')
    userStore.logout()
    router.push('/home')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="pwd-page">
    <div class="wrap">
      <div class="g-card">
        <div v-if="hasPassword" class="f-item">
          <div class="f-label">原密码</div>
          <input v-model="form.old_password" type="password" class="f-input" placeholder="请输入原密码" maxlength="32" />
        </div>
        <div class="f-item">
          <div class="f-label">新密码</div>
          <input v-model="form.new_password" type="password" class="f-input" placeholder="6-32 位新密码" maxlength="32" />
        </div>
        <div class="f-item">
          <div class="f-label">确认新密码</div>
          <input v-model="form.confirm_password" type="password" class="f-input" placeholder="再次输入新密码" maxlength="32" />
        </div>
      </div>
      <div class="tip">
        {{ hasPassword ? '修改成功后需要重新登录' : '当前账号为验证码登录，设置密码后即可用密码登录' }}
      </div>
      <button class="submit-btn" :disabled="loading" @click="onSubmit">
        {{ loading ? '提交中...' : (hasPassword ? '确认修改' : '设置密码') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.pwd-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); padding-bottom: 80px; }
.wrap { max-width: 560px; margin: 0 auto; padding: 20px; }

.g-card { background: #fff; border-radius: var(--radius); box-shadow: var(--shadow-sm); overflow: hidden; }
.f-item { padding: 14px 16px; }
.f-item + .f-item { border-top: 1px solid var(--line); }
.f-label { font-size: 13px; color: var(--weak); margin-bottom: 8px; }
.f-input {
  width: 100%; border: none; outline: none; background: transparent;
  font-size: 15px; padding: 0;
}
.f-input::placeholder { color: #C9CCD1; }

.tip { font-size: 12px; color: var(--weak); margin: 12px 4px 0; }

.submit-btn {
  width: 100%; height: 48px; border-radius: 24px; border: none;
  background: linear-gradient(135deg, var(--brand-400) 0%, var(--brand) 100%);
  color: #fff; font-weight: 500; font-size: 15px;
  cursor: pointer; margin-top: 24px;
}
.submit-btn:disabled { opacity: .6; cursor: not-allowed; }
</style>
