const isDev = import.meta.env.DEV
const isProxy = import.meta.env.VITE_APP_PROXY === 'true'

const DEFAULT_CONFIG = {
  // 应用标题
  APP_NAME: import.meta.env.VITE_APP_TITLE || '一源',

  // 版本号
  APP_VER: '1.0.0',

  // 接口地址。dev+proxy 时走 /api → vite 代理到后端 /api/user；生产直接 /api/user
  API_URL: isDev && isProxy ? '/api' : (import.meta.env.VITE_APP_API_BASEURL || '/api/user'),

  // 请求超时
  TIMEOUT: 10000,

  // Token 头名
  TOKEN_NAME: 'Authorization',

  // Token 前缀
  TOKEN_PREFIX: 'Bearer ',

  // 追加其他头
  HEADERS: {},

  // 请求是否开启缓存
  REQUEST_CACHE: false,

  // 用户信息本地存储键名
  USER_INFO_KEY: 'userInfo',
}

export default DEFAULT_CONFIG