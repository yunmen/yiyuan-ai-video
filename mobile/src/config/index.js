const isDev = import.meta.env.DEV
const isProxy = import.meta.env.VITE_APP_PROXY === 'true'

/**
 * 接口基地址。
 * H5：dev + proxy 时走 /api（vite 代理 rewrite 到后端 /api/user）；生产取 VITE_APP_API_BASEURL。
 * 小程序/App：不存在 dev-server 代理，uni.request 只接受完整 URL，必须使用绝对地址。
 *   - 开发默认指向本机后端，配合微信开发者工具「不校验合法域名」（manifest 已关 urlCheck）
 *   - 生产必须在 .env.production 配置 VITE_APP_MP_API_BASEURL（https 域名，并加入小程序后台合法域名）
 */
let apiUrl = import.meta.env.VITE_APP_API_BASEURL || '/api/user'
// #ifdef H5
apiUrl = isDev && isProxy ? '/api' : (import.meta.env.VITE_APP_API_BASEURL || '/api/user')
// #endif
// #ifdef MP-WEIXIN || APP-PLUS
apiUrl = import.meta.env.VITE_APP_MP_API_BASEURL
  || (isDev ? 'http://127.0.0.1:8801/api/user' : 'https://api.example.com/api/user')
if (!import.meta.env.VITE_APP_MP_API_BASEURL && !isDev) {
  console.warn('[config] 未配置 VITE_APP_MP_API_BASEURL，小程序生产构建使用了占位域名，请在 .env.production 中配置真实后端地址')
}
// #endif

const DEFAULT_CONFIG = {
  // 应用标题
  APP_NAME: import.meta.env.VITE_APP_TITLE || '千溪',

  // 版本号
  APP_VER: '1.0.0',

  // 接口地址（平台差异见文件顶部说明）
  API_URL: apiUrl,

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
