/**
 * 移动端导航工具。
 * uni-app 使用页面文件路径导航，这里统一封装安全的站内回跳、登录跳转，
 * 并按页面是否为底部 Tab 自动选择 reLaunch / navigateTo / redirectTo。
 */

/** 本项目底部导航的 Tab 页面路径，使用 uni.reLaunch 切换（页面未注册为原生 tabBar）。 */
const TAB_PAGES = [
  '/pages/home/index',
  '/pages/studio/index',
  '/pages/works/index',
]

/**
 * 将查询参数规范为安全的站内回跳地址。
 * 拒绝协议地址、双斜杠、反斜杠和控制字符，避免形成开放重定向。
 */
export function getSafeInternalRedirect(value, fallback = '/pages/home/index') {
  if (Array.isArray(value)) value = value[0]
  if (typeof value !== 'string') return fallback

  const target = value.trim()
  // uni 站内路径以 /pages/ 或 / 开头；拒绝协议、双斜杠、反斜杠与控制字符
  if (
    !target.startsWith('/')
    || target.startsWith('//')
    || target.includes('\\')
    || /[\u0000-\u001F\u007F]/.test(target)
  ) {
    return fallback
  }
  return target
}

/** 是否为底部 Tab 页面。 */
export function isTabPage(path) {
  return TAB_PAGES.includes(path)
}

/**
 * 构造携带安全回跳地址的登录页 URL。
 * @param {string} [target] 原站内目标路径（如 /pages/works/index）
 */
export function toLoginPath(target) {
  const redirect = getSafeInternalRedirect(target)
  return `/pages/login/index?redirect=${encodeURIComponent(redirect)}`
}

/**
 * 统一站内导航入口。
 * @param {object|string} target - 支持字符串路径或 { path, query }，query 会拼为 url 查询串
 */
export function go(target) {
  const { path, query } = typeof target === 'string' ? { path: target, query: {} } : target
  const safePath = getSafeInternalRedirect(path)
  const qs = query
    ? Object.entries(query)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&')
    : ''
  const url = qs ? `${safePath}?${qs}` : safePath

  if (isTabPage(safePath)) {
    // Tab 页走 reLaunch 保持返回栈干净；reLaunch 不能携带查询参数，故忽略 query。
    try {
      uni.reLaunch({ url: safePath })
    } catch (err) {
      console.error('切换 Tab 页面失败，尝试 redirectTo 兜底')
      uni.redirectTo({ url: safePath })
    }
    return safePath
  }

  try {
    uni.navigateTo({ url })
  } catch (err) {
    console.error('页面跳转失败，尝试 redirectTo 兜底')
    uni.redirectTo({ url })
  }
  return url
}

/**
 * 登录/注册成功后用于替换当前页的安全跳转：
 * - Tab 目标：reLaunch 直接替换页面栈，登录/注册页随之移除；
 * - 非 Tab 目标：uni.redirectTo 替换当前登录/注册页，避免登录/注册页残留在
 *   页面栈底部导致返回按钮仍能退回登录/注册页。
 * @param {string|object} target - 与 go() 相同的目标
 */
export function goReplace(target) {
  const { path, query } = typeof target === 'string' ? { path: target, query: {} } : target
  const safePath = getSafeInternalRedirect(path)
  const qs = query
    ? Object.entries(query)
        .filter(([, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&')
    : ''
  const url = qs ? `${safePath}?${qs}` : safePath

  if (isTabPage(safePath)) {
    // Tab 页走 reLaunch，忽略无法携带的 query。
    uni.reLaunch({ url: safePath })
    return safePath
  }
  uni.redirectTo({ url })
  return url
}

/** 当前页面路径（用作登录后的回跳目标）。 */
export function currentPagePath() {
  try {
    const pages = getCurrentPages()
    const page = pages && pages.length ? pages[pages.length - 1] : null
    return page ? `/${page.route}` : '/pages/home/index'
  } catch (err) {
    console.error('获取当前页面路径失败，使用首页兜底')
    return '/pages/home/index'
  }
}
