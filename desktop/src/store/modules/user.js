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
  // 登录成功后的跳转目标:仅当「未登录点入了需要登录的页面」时由调用方指定;
  // 为空则登录后停留在当前页(如在工作台登录后继续创作),不再强制跳「我的作品」。
  const loginRedirect = ref('')
  // 剩余额度:全局唯一来源,避免顶部额度与页面卡片各拉各的导致展示不一致
  const creditTotal = ref(null)

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

  // 打开登录弹窗;redirect 为登录成功后要去的路径(可为空)
  const openLogin = (redirect = '') => {
    loginRedirect.value = redirect || ''
    loginVisible.value = true
  }
  const closeLogin = () => { loginVisible.value = false }
  // 登录成功后取走跳转目标并清空,避免残留影响下次登录
  const consumeLoginRedirect = () => {
    const target = loginRedirect.value
    loginRedirect.value = ''
    return target
  }

  const setCreditTotal = (value) => { creditTotal.value = value }

  const logout = () => {
    token.value = ''
    userInfo.value = null
    creditTotal.value = null
    localStorage.removeItem(tokenKey)
    localStorage.removeItem(userKey)
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    loginVisible,
    creditTotal,
    setToken,
    setUserInfo,
    setCreditTotal,
    openLogin,
    closeLogin,
    consumeLoginRedirect,
    logout
  }
})
