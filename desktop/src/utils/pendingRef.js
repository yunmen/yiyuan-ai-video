// 跳转「视频复刻」前的对标视频中转:
// 模板成片地址(OSS 链接)不能拼在 URL query 里 —— 会完整暴露存储桶地址且被浏览器记录。
// 改走 sessionStorage 一次性中转:写入后导航,复刻页挂载时取走并立即删除。
const KEY = 'studio:pending_ref'

// 写入待带入的对标视频信息:{ url, title }
export function setPendingRef(payload) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(payload || {}))
  } catch (e) { /* 存储不可用时静默:复刻页走正常上传流程 */ }
}

// 取走并清除待带入的对标视频信息;无数据返回 null
export function takePendingRef() {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return null
    sessionStorage.removeItem(KEY)
    return JSON.parse(raw)
  } catch (e) {
    return null
  }
}
