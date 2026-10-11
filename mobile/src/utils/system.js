/**
 * 跨端窗口 / 导航栏尺寸工具。
 *
 * 微信小程序右上角悬浮着不可移除的胶囊按钮（···  ○），自定义导航栏必须：
 * 1. 内容栏高度与胶囊上下对称，视觉才不失衡；
 * 2. 右侧操作区为胶囊让出空间，否则图标会被胶囊盖住。
 * H5 / App 没有胶囊，沿用固定 52px 内容栏。
 */

let cachedMetrics = null

/** 安全读取系统信息（同步），失败回退默认值。 */
export function getSystemInfo() {
  try {
    return uni.getSystemInfoSync() || {}
  } catch (err) {
    console.error('获取系统信息失败，使用默认值')
    return {}
  }
}

/** 状态栏高度（px）；H5 无状态栏，回退 20 保持现有视觉。 */
export function getStatusBarHeight() {
  return getSystemInfo().statusBarHeight || 20
}

/**
 * 自定义导航栏布局指标。
 * @returns {{statusBarHeight:number, barHeight:number, paddingRight:number}}
 *   statusBarHeight 状态栏占位；barHeight 内容栏高度；paddingRight 右侧（胶囊）避让宽度
 */
export function getNavBarMetrics() {
  if (cachedMetrics) return cachedMetrics

  const statusBarHeight = getStatusBarHeight()
  const fallback = { statusBarHeight, barHeight: 52, paddingRight: 16 }

  // #ifdef MP-WEIXIN
  try {
    const sys = getSystemInfo()
    const rect = uni.getMenuButtonBoundingClientRect()
    if (rect && rect.height && rect.top) {
      // 胶囊与状态栏之间的上下间距对称，内容栏高度 = 间距 ×2 + 胶囊高度
      const gap = rect.top - statusBarHeight
      const barHeight = Math.max(44, gap * 2 + rect.height)
      // 右内边距：屏宽 - 胶囊左缘，再留 8px 呼吸位
      const paddingRight = (sys.windowWidth || 375) - rect.left + 8
      cachedMetrics = { statusBarHeight, barHeight, paddingRight }
      return cachedMetrics
    }
  } catch (err) {
    console.error('获取胶囊按钮布局失败，导航栏使用默认高度')
  }
  // #endif

  cachedMetrics = fallback
  return cachedMetrics
}
