import { defineStore } from 'pinia'
import config from '@/config'
import { getStorage, setStorage, removeStorage } from '@/utils/storage'

// --- 用户认证 Store（只负责状态管理，不调 API）---
// 后端只签发单个 token，没有 refresh_token / 有效期字段，登录态以 token 为唯一条件。
export const useUserStore = defineStore('user', {
  state: () => {
    const token = getStorage(config.TOKEN_NAME, '')
    let userInfo = null
    const raw = getStorage(config.USER_INFO_KEY, '')
    if (raw) {
      try { userInfo = JSON.parse(raw) } catch (err) { console.error('解析本地用户信息失败'); userInfo = null }
    }
    return {
      token,
      userInfo,
      // 总额度（可用 + 免费 + 每日赠送），未刷新时为 null
      creditTotal: null,
    }
  },

  getters: {
    // Token 是登录态的唯一必要条件，资料可在首屏挂载后异步刷新。
    isLoggedIn: (state) => !!state.token,
  },

  actions: {
    /** 保存 token */
    setToken(token) {
      if (!token) return
      setStorage(config.TOKEN_NAME, token)
      this.token = token
    },

    /** 保存用户信息 */
    setUserInfo(info) {
      if (!info) return
      setStorage(config.USER_INFO_KEY, JSON.stringify(info))
      this.userInfo = info
    },

    /** 保存总额度 */
    setCreditTotal(value) {
      this.creditTotal = value
    },

    /** 登出，清除本地状态 */
    logout() {
      removeStorage(config.TOKEN_NAME)
      removeStorage(config.USER_INFO_KEY)
      this.token = ''
      this.userInfo = null
      this.creditTotal = null
    },

    /** 从本地存储重新读取 token 与用户信息（跨页同步时用） */
    syncFromStorage() {
      const t = getStorage(config.TOKEN_NAME, '')
      if (t) this.token = t
      const raw = getStorage(config.USER_INFO_KEY, '')
      if (raw) {
        try { this.userInfo = JSON.parse(raw) } catch (err) { console.error('解析本地用户信息失败'); this.userInfo = null }
      }
    },
  },
})
