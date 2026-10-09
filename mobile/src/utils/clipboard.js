/**
 * 剪贴板工具：复制文本到系统剪贴板。
 * 基于 uni.setClipboardData，支持 H5 / 小程序 / App，统一返回是否成功。
 */
export function copyText(text) {
  return new Promise((resolve) => {
    uni.setClipboardData({
      data: typeof text === 'string' ? text : String(text ?? ''),
      success: () => resolve(true),
      fail: () => resolve(false),
    })
  })
}