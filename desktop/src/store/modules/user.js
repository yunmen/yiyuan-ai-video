import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const defaultInfo = {
  id: 1,
  phone: '13800000000',
  nickname: '用户',
  avatar: 'https://picsum.photos/200/200?random=55',
  status: 1
}

// 注意:请求拦截器从 localStorage 的 'token' 读取鉴权,这里保持键名一致
const tokenKey = 'token'
const userKey = 'app_user'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem(tokenKey) || '')
  const userInfo = ref(null)
  const loginVisible = ref(false)

  try {
    const saved = localStorage.getItem(userKey)
    if (saved) userInfo.value = JSON.parse(saved)
  } catch {
    userInfo.value = null
  }

  const isLoggedIn = computed(() => !!token.value)

  const setToken = (value) => {
    token.value = value
    localStorage.setItem(tokenKey, value)
  }

  const setUserInfo = (info) => {
    userInfo.value = { ...defaultInfo, ...info }
    localStorage.setItem(userKey, JSON.stringify(userInfo.value))
  }

  const openLogin = () => { loginVisible.value = true }
  const closeLogin = () => { loginVisible.value = false }

  const logout = () => {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem(tokenKey)
    localStorage.removeItem(userKey)
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    loginVisible,
    setToken,
    setUserInfo,
    openLogin,
    closeLogin,
    logout
  }
})
