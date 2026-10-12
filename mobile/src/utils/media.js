/**
 * 跨端本地视频选择。
 *
 * 微信小程序自基础库 2.21.0 起废弃 uni.chooseVideo，推荐 uni.chooseMedia；
 * 两者返回结构不同（chooseMedia 的文件信息在 tempFiles[0]，且自带 duration）。
 * H5/App 继续使用 uni.chooseVideo；H5 不回传 duration 时用 video 元素探测。
 */

/** 从路径中取文件名（小程序临时路径如 wxfile://tmp/xxx.mp4 也能取到末段）。 */
function fileNameOf(path) {
  const text = String(path || '').split('?')[0]
  const slash = Math.max(text.lastIndexOf('/'), text.lastIndexOf('\\'))
  const name = slash >= 0 ? text.slice(slash + 1) : text
  return name || 'video.mp4'
}

/** H5：挂载 video 元素探测本地视频时长，失败 / 非 H5 环境返回 0。 */
function probeVideoSeconds(src) {
  return new Promise((resolve) => {
    if (typeof document === 'undefined' || !src) {
      resolve(0)
      return
    }
    const el = document.createElement('video')
    el.preload = 'metadata'
    el.muted = true
    const done = (value) => resolve(Number(value) || 0)
    el.onloadedmetadata = () => done(el.duration)
    el.onerror = () => done(0)
    el.src = src
    setTimeout(() => done(0), 8000)
  })
}

/**
 * 打开视频选择器（相册 / 拍摄）。
 * @returns {Promise<{path:string, name:string, size:number, duration:number, file?: Blob}>} H5 保留原始文件供直传。
 *   用户取消时 reject(new Error('CANCEL'))，调用方可静默忽略。
 */
export function chooseVideoFile() {
  return new Promise((resolve, reject) => {
    const cancel = () => reject(new Error('CANCEL'))

    // #ifdef MP-WEIXIN
    uni.chooseMedia({
      count: 1,
      mediaType: ['video'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const file = res && res.tempFiles && res.tempFiles[0]
        const path = file && file.tempFilePath
        if (!path) {
          reject(new Error('未获取到选中视频'))
          return
        }
        resolve({
          path,
          name: fileNameOf(path),
          size: Number(file.size || 0),
          duration: Math.round(Number(file.duration || 0)),
        })
      },
      fail: (err) => {
        if (/cancel/i.test(String(err && err.errMsg))) cancel()
        else reject(err instanceof Error ? err : new Error((err && err.errMsg) || '选择视频失败'))
      },
    })
    // #endif

    // #ifndef MP-WEIXIN
    uni.chooseVideo({
      sourceType: ['album', 'camera'],
      success: async (res) => {
        const tempFile = res && res.tempFile
        const path = (res && (res.tempFilePath || (res.tempFilePaths && res.tempFilePaths[0]))) || ''
        if (!path) {
          reject(new Error('未获取到选中视频'))
          return
        }
        const name = (tempFile && tempFile.name) || (res && res.name) || fileNameOf(path)
        const size = Number((tempFile && tempFile.size) || (res && res.size) || 0)
        let duration = Number((res && res.duration) || 0)
        if (!duration) duration = await probeVideoSeconds(path)
        resolve({ path, name, size, duration: Math.round(duration), file: tempFile })
      },
      fail: (err) => {
        if (/cancel/i.test(String(err && err.errMsg))) cancel()
        else reject(err instanceof Error ? err : new Error((err && err.errMsg) || '选择视频失败'))
      },
    })
    // #endif
  })
}
