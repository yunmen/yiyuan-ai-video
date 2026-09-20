/**
 * 视频工具:从本地视频抽取关键帧,供「上传参考做」作为参考素材复用。
 *
 * 说明:参考视频无法直接投喂给生成模型,这里抽帧成多张图片,
 * 再由素材页作为 materials 提交 —— 后端按素材数量自动选择生成模式
 * (1 张走图生视频 i2v,多张走参考生视频 r2v),无需后端改动。
 */

// 抽出的参考帧 URL 暂存键与有效期(跨页面一次性传递,Upload 页取用后立即清除)
const REF_FRAMES_KEY = 'yy_ref_frames'
const REF_FRAMES_TTL = 30 * 60 * 1000

/**
 * 暂存参考视频抽出的画面 URL 列表(供「替换素材」页预填为素材)
 * @param {string[]} urls 画面图片地址列表
 */
export function setRefFrames(urls) {
  if (!Array.isArray(urls) || !urls.length) return
  try {
    sessionStorage.setItem(REF_FRAMES_KEY, JSON.stringify({ urls, ts: Date.now() }))
  } catch (e) {
    // 隐私模式/存储受限:静默降级,不影响上传主流程
  }
}

/**
 * 取出并清除参考画面 URL 列表(一次性使用,超时或异常返回空数组)
 * @returns {string[]}
 */
export function takeRefFrames() {
  try {
    const raw = sessionStorage.getItem(REF_FRAMES_KEY)
    sessionStorage.removeItem(REF_FRAMES_KEY)
    if (!raw) return []
    const { urls, ts } = JSON.parse(raw)
    if (!Array.isArray(urls) || Date.now() - ts >= REF_FRAMES_TTL) return []
    return urls.filter(Boolean)
  } catch (e) {
    return []
  }
}

// ==================== 内部实现 ====================

const LOAD_TIMEOUT = 8000
const SEEK_TIMEOUT = 5000

/** 等待媒体事件,带超时兜底 */
function waitEvent(el, event, timeout, errMsg) {
  return new Promise((resolve, reject) => {
    let done = false
    const finish = (err) => {
      if (done) return
      done = true
      clearTimeout(timer)
      el.removeEventListener(event, onEvent)
      el.removeEventListener('error', onError)
      err ? reject(err) : resolve()
    }
    const onEvent = () => finish(null)
    const onError = () => finish(new Error(errMsg))
    const timer = setTimeout(() => finish(new Error(errMsg)), timeout)
    el.addEventListener(event, onEvent, { once: true })
    el.addEventListener('error', onError, { once: true })
  })
}

/** 跳转到指定时间点(某些浏览器在当前时间相同时不触发 seeked,故加超时) */
function seekTo(video, time) {
  return new Promise((resolve, reject) => {
    let done = false
    const finish = (err) => {
      if (done) return
      done = true
      clearTimeout(timer)
      video.removeEventListener('seeked', onSeeked)
      video.removeEventListener('error', onError)
      err ? reject(err) : resolve()
    }
    const onSeeked = () => finish(null)
    const onError = () => finish(new Error('视频跳帧失败'))
    const timer = setTimeout(() => finish(new Error('视频跳帧超时')), SEEK_TIMEOUT)
    video.addEventListener('seeked', onSeeked, { once: true })
    video.addEventListener('error', onError, { once: true })
    video.currentTime = time
  })
}

/** 把当前帧画到 canvas 并导出 JPEG */
function grabFrame(video, maxWidth, quality) {
  return new Promise((resolve, reject) => {
    const w = video.videoWidth
    const h = video.videoHeight
    if (!w || !h) return reject(new Error('无法读取视频尺寸'))
    const scale = Math.min(1, maxWidth / w)
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(w * scale)
    canvas.height = Math.round(h * scale)
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height)
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error('画面导出失败'))),
      'image/jpeg',
      quality
    )
  })
}

/** 采样时间点:count=1 取靠前位置避免片头黑帧;多帧则在中间 80% 区间均匀分布 */
function samplePoints(duration, count, at) {
  if (count <= 1) {
    const max = duration > 0 ? Math.max(0.05, duration - 0.05) : 0.05
    return [Math.max(0.05, Math.min(at, max))]
  }
  if (!duration || duration <= 0) return Array.from({ length: count }, () => 0.05)
  const start = duration * 0.1
  const end = duration * 0.9
  const step = (end - start) / (count - 1)
  return Array.from({ length: count }, (_, i) => start + step * i)
}

/**
 * 抽取视频多帧为 JPEG Blob 列表
 * @param {File} file 本地视频文件
 * @param {Object} [opts]
 * @param {number} [opts.count=3] 抽取帧数
 * @param {number} [opts.at=0.1] count=1 时的抽帧时间点(秒)
 * @param {number} [opts.maxWidth=1280] 输出最大宽度,超出则等比缩放(控制上传体积)
 * @param {number} [opts.quality=0.9] JPEG 质量
 * @returns {Promise<Blob[]>}
 */
export async function extractFrames(file, opts = {}) {
  const { count = 3, at = 0.1, maxWidth = 1280, quality = 0.9 } = opts
  const objectUrl = URL.createObjectURL(file)
  const video = document.createElement('video')
  video.preload = 'auto'
  video.muted = true
  video.playsInline = true
  video.src = objectUrl

  try {
    await waitEvent(video, 'loadeddata', LOAD_TIMEOUT, '视频加载超时,请换一个文件试试')
    const blobs = []
    for (const time of samplePoints(video.duration || 0, count, at)) {
      await seekTo(video, time)
      blobs.push(await grabFrame(video, maxWidth, quality))
    }
    if (!blobs.length) throw new Error('未提取到有效画面')
    return blobs
  } finally {
    URL.revokeObjectURL(objectUrl)
    video.removeAttribute('src')
  }
}

/**
 * 抽取视频首帧为 JPEG Blob(单帧场景的便捷方法)
 * @returns {Promise<Blob>}
 */
export function extractFirstFrame(file, opts = {}) {
  return extractFrames(file, { ...opts, count: 1 }).then((blobs) => blobs[0])
}
