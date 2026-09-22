/**
 * 视频工具:从本地视频抽取关键帧,供「上传参考做」作为参考素材复用。
 *
 * 说明:提交给后端的是「参考视频地址 + 抽帧图片」两部分 ——
 *   ① 参考视频本身(已上传到服务器的地址)让模型能学到原片的运镜、节奏与转场,
 *      后端据此走**视频编辑**(gen_mode=v2v);
 *   ② 抽帧图片作为参考画面随 materials 下发(i2v/r2v 的素材语义)。
 * 若只传图片,后端只能退化成"抽帧近似",丢掉运动信息,故两者都要带上。
 */

// 抽出的参考帧 URL 暂存键与有效期(跨页面一次性传递,Upload 页取用后立即清除)
const REF_FRAMES_KEY = 'yy_ref_frames'
const REF_FRAMES_TTL = 30 * 60 * 1000

/**
 * 暂存参考视频信息(抽出的画面 + 上传后的原视频地址),供素材页预填与预览
 * @param {string[]} urls 画面图片地址列表
 * @param {string} [videoUrl] 上传后的参考视频地址(素材页预览优先播放它,而不是模板示例视频)
 */
export function setRefFrames(urls, videoUrl = '') {
  const frames = Array.isArray(urls) ? urls.filter(Boolean) : []
  if (!frames.length && !videoUrl) return
  try {
    sessionStorage.setItem(REF_FRAMES_KEY, JSON.stringify({ urls: frames, videoUrl, ts: Date.now() }))
  } catch (e) {
    // 隐私模式/存储受限:静默降级,不影响上传主流程
  }
}

/**
 * 读取参考视频信息(只读,不消费)
 *
 * 为什么不再"读走即删":页面刷新、开发时热更新、路由回退都会让组件重新挂载,
 * 一次性消费会让用户上传完什么都没做、素材就凭空消失。
 * 清除改由调用方在「生成成功 / 用户主动清除 / 换成别的素材」时调 clearRefSource。
 *
 * @returns {{frames: string[], videoUrl: string}}
 */
export function takeRefSource() {
  const empty = { frames: [], videoUrl: '' }
  try {
    const raw = sessionStorage.getItem(REF_FRAMES_KEY)
    if (!raw) return empty
    const { urls, videoUrl, ts } = JSON.parse(raw)
    if (Date.now() - ts >= REF_FRAMES_TTL) return empty
    return { frames: Array.isArray(urls) ? urls.filter(Boolean) : [], videoUrl: videoUrl || '' }
  } catch (e) {
    return empty
  }
}

/** 清除参考视频信息(生成成功、用户主动清除或换成别的素材时调用) */
export function clearRefSource() {
  try {
    sessionStorage.removeItem(REF_FRAMES_KEY)
  } catch (e) {
    // 隐私模式/存储受限:忽略
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
