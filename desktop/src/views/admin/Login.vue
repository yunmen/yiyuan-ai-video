<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createDiscreteApi } from 'naive-ui'
import adminApi, { ADMIN_TOKEN_KEY, ADMIN_INFO_KEY } from '@/api/admin'

const router = useRouter()
const { notification } = createDiscreteApi(['notification'])

const formRef = ref(null)
const loading = ref(false)
const form = reactive({
  account: '',
  password: ''
})

const rules = {
  account: [{ required: true, message: '请输入管理员账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = () => {
  formRef.value?.validate(async (errors) => {
    if (errors) return
    loading.value = true
    try {
      const res = await adminApi.login({ account: form.account, password: form.password })
      if (res.code === 1 && res.data?.token) {
        localStorage.setItem(ADMIN_TOKEN_KEY, res.data.token)
        localStorage.setItem(ADMIN_INFO_KEY, JSON.stringify(res.data.info || {}))
        notification.success({ title: '登录成功', duration: 2000, content: `欢迎回来,${res.data.info?.nickname || '管理员'}` })
        router.replace('/admin/template')
      }
    } finally {
      loading.value = false
    }
  })
}
</script>

<template>
  <div class="admin-login">
    <n-card class="login-card" :bordered="false">
      <div class="login-brand">
        <span class="login-brand-dot"></span>
        <span class="login-brand-name">一源AI 管理后台</span>
      </div>
      <p class="login-sub">请使用管理员账号登录</p>
      <n-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="handleLogin">
        <n-form-item path="account" :show-label="false">
          <n-input v-model:value="form.account" placeholder="管理员账号" />
        </n-form-item>
        <n-form-item path="password" :show-label="false">
          <n-input
            v-model:value="form.password"
            type="password"
            show-password-on="click"
            placeholder="密码"
          />
        </n-form-item>
        <n-button
          type="primary"
          block
          size="large"
          :loading="loading"
          class="login-btn"
          @click="handleLogin"
        >
          登 录
        </n-button>
      </n-form>
    </n-card>
  </div>
</template>

<style scoped>
.admin-login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #10151F;
}
.login-card {
  width: 380px;
  border-radius: 12px;
  padding: 12px 8px;
}
.login-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 8px;
}
.login-brand-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--brand);
}
.login-brand-name {
  font-size: 20px;
  font-weight: 700;
  color: var(--ink);
}
.login-sub {
  text-align: center;
  color: var(--weak);
  font-size: 13px;
  margin: 0 0 24px;
}
.login-btn {
  --n-color: var(--brand) !important;
  --n-color-hover: #e6451a !important;
  --n-color-pressed: #cc3e17 !important;
  --n-color-focus: var(--brand) !important;
  --n-ripple-color: var(--brand) !important;
  --n-border: 1px solid var(--brand) !important;
  --n-border-hover: 1px solid var(--brand) !important;
  --n-border-pressed: 1px solid var(--brand) !important;
  --n-border-focus: 1px solid var(--brand) !important;
}
</style>
