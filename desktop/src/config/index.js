const isDev = import.meta.env.DEV
const isProxy = import.meta.env.VITE_APP_PROXY === 'true'

const DEFAULT_CONFIG = {
  //标题
	APP_NAME: import.meta.env.VITE_APP_TITLE,

  // 版本号
  APP_VER: "1.0.0",

  // 接口地址
  API_URL: isDev && isProxy ? "/api" : (import.meta.env.VITE_APP_API_BASEURL || "/api"),

  // 请求超时
  TIMEOUT: 10000,

  // TokenName
  TOKEN_NAME: "Authorization",

  // Token前缀
  TOKEN_PREFIX: "Bearer ",

  // 追加其他头
  HEADERS: {},

  // 请求是否开启缓存
  REQUEST_CACHE: false,
}

export default DEFAULT_CONFIG
