/** 原生交互使用同一组品牌颜色；小程序保持平台弹窗、选择器与输入能力。 */
const CONFIRM_COLOR = '#B23A2E'
const TEXT_COLOR = '#48463F'
const MUTED_COLOR = '#77746B'

/** 透传 uni.showModal 的参数、回调与返回值，仅补齐品牌确认色和取消色。 */
export function showAppModal(options) {
  return uni.showModal({ confirmColor: CONFIRM_COLOR, cancelColor: MUTED_COLOR, ...options })
}

/** 透传 uni.showActionSheet 的选项与事件，平台菜单文字沿用深墨色。 */
export function showAppActionSheet(options) {
  return uni.showActionSheet({ itemColor: TEXT_COLOR, ...options })
}
