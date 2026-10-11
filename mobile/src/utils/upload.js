import config from '@/config'
import { getStorage } from '@/utils/storage'

/**
 * 素材上传（对应后端 POST /v1/base/common/upload/file）。
 *
 * 采用后端代理上传（multipart，字段名 file，单文件上限 50MB），三端一致且可获取进度；
 * 后端会优先转存对象存储，未启用时回落本地磁盘，返回 { url, filename, size }。
 * 后端返回的 url 为可直接透传给生成接口的绝对地址。
 */
const UPLOAD_URL = `${config.API_URL}/v1/base/common/upload/file`

/** 解析 uni.uploadFile 的字符串响应体，兼容后端直接返回错误页的情况。 */
function parseBody(raw) {
  if (raw && typeof raw === 'object') return raw
  try {
    return JSON.parse(String(raw || ''))
  } catch (err) {
    console.error('解析上传响应失败')
    return null
  }
}

/**
 * 上传单个文件。
 * @param {string} filePath 本地临时文件路径（uni.chooseVideo / uni.chooseImage 返回值）
 * @param {{ onProgress?: (percent:number)=>void }} options 进度回调（0-100）
 * @returns {Promise<{url:string, filename:string, size:number}>}
 */
export function uploadMedia(filePath, options = {}) {
  return new Promise((resolve, reject) => {
    const header = { ...config.HEADERS }
    const token = getStorage(config.TOKEN_NAME)
    if (token) header[config.TOKEN_NAME] = config.TOKEN_PREFIX + token

    let task = null
    const handleSuccess = (res) => {
      const body = parseBody(res.data)
      if (!body) {
        reject(new Error('上传失败，请稍后重试'))
        return
      }
      if (body.code === 1 && body.data && body.data.url) {
        resolve(body.data)
        return
      }
      reject(new Error(body.message || '上传失败，请稍后重试'))
    }
    const handleFail = (err) => reject(new Error(err?.errMsg || '上传失败，请检查网络后重试'))

    task = uni.uploadFile({
      url: UPLOAD_URL,
      filePath,
      name: 'file',
      header,
      success: handleSuccess,
      fail: handleFail,
    })

    if (task && typeof task.onProgressUpdate === 'function' && typeof options.onProgress === 'function') {
      task.onProgressUpdate((res) => options.onProgress(Math.round(res.progress || 0)))
    }
  })
}

/** 校验本地视频大小（后端上限 50MB，提前拦截避免白等一次上传）。 */
export const MAX_UPLOAD_MB = 50

/** 视频扩展名白名单（与后端 ALLOWED_EXTENSIONS 的视频子集一致）。 */
export const VIDEO_EXTENSIONS = ['mp4', 'mov', 'm4v', 'webm']

/** 图片扩展名白名单（与后端 ALLOWED_EXTENSIONS 的图片子集一致）。 */
export const IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']

/** 从地址中取小写扩展名，取不到返回空串。 */
export function extensionOf(value) {
  const text = String(value || '').split('?')[0]
  const dot = text.lastIndexOf('.')
  if (dot < 0) return ''
  return text.slice(dot + 1).toLowerCase()
}

/** 是否为视频地址（用于把素材分流进 materials 的参考视频位）。 */
export function isVideoUrl(value) {
  return VIDEO_EXTENSIONS.includes(extensionOf(value))
}
