import config from '@/config'
import commonApi from '@/api/model/common'
import { getStorage } from '@/utils/storage'
import { requireLogin } from '@/utils/navigation'

/** H5 优先签名直传；签名不可用或非 H5 平台使用后端 multipart 中转。 */
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

// #ifdef H5
/** 读取选择器的原始文件；旧图片调用方只传 blob 地址时，按实际 MIME 补充文件名。 */
async function readUploadFile(filePath, options) {
  let file = options.file
  if (!(file instanceof Blob)) {
    const response = await fetch(filePath)
    if (!response.ok) throw new Error('读取本地素材失败，请重新选择')
    file = await response.blob()
  }
  // blob 临时地址没有扩展名，不能直接作为签名文件名。
  const mimeExtensions = {
    'image/jpeg': 'jpg', 'image/png': 'png', 'image/gif': 'gif',
    'image/webp': 'webp', 'image/bmp': 'bmp', 'video/mp4': 'mp4',
    'video/quicktime': 'mov', 'video/x-m4v': 'm4v', 'video/webm': 'webm',
  }
  const filename = options.filename || file.name
    || (mimeExtensions[file.type] ? `素材.${mimeExtensions[file.type]}` : '')
  if (!file.size) throw new Error('不能上传空文件，请重新选择')
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
    throw new Error(`文件不能超过 ${MAX_UPLOAD_MB}MB`)
  }
  return { file, filename }
}

/** 使用独立 XHR PUT 原始二进制，不附加业务 Token，不在失败后重复中转。 */
function putSignedFile(sign, file, options) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', sign.uploadUrl)
    xhr.timeout = config.UPLOAD_TIMEOUT
    if (file.type) xhr.setRequestHeader('Content-Type', file.type)
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && typeof options.onProgress === 'function') {
        // 100% 留给存储服务确认成功，避免把发送结束误当作上传成功。
        options.onProgress(Math.min(99, Math.round(event.loaded / event.total * 100)))
      }
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        if (typeof options.onProgress === 'function') options.onProgress(100)
        resolve({ url: sign.url, filename: sign.filename, size: file.size })
      } else {
        reject(new Error(`素材直传失败（HTTP ${xhr.status}），请重试`))
      }
    }
    xhr.onerror = () => reject(new Error('素材直传失败，请检查网络或对象存储跨域配置'))
    xhr.ontimeout = () => reject(new Error('上传超时，请切换稳定网络或压缩视频后重试'))
    xhr.onabort = () => reject(new Error('素材上传已取消'))
    xhr.send(file)
  })
}
// #endif

/**
 * 上传单个文件，返回可供生成接口使用的 URL、文件名及字节数。
 * @param {string} filePath 本地临时文件路径
 * @param {{ file?: Blob, filename?: string, onProgress?: (percent:number)=>void }} options 原始文件与进度回调（0-100）
 * @returns {Promise<{url:string, filename:string, size:number}>}
 */
export async function uploadMedia(filePath, options = {}) {
  if (!requireLogin()) throw new Error('请先登录后上传素材')
  // #ifdef H5
  const { file, filename } = await readUploadFile(filePath, options)
  let sign
  if (filename) {
    try {
      const body = await commonApi.uploadSign.post({ filename }, { suppressBusinessError: true, suppressGlobalError: true })
      if (body?.code === 1 && body.data?.uploadUrl && body.data?.url) sign = body.data
      else if (body?.code !== 0) throw new Error('获取上传签名失败')
    } catch (err) {
      // 登录失效、限流或权限拒绝不得通过中转接口继续尝试。
      if (err.code === 9 || [401, 403, 429].includes(err.dataStatus)) throw err
      console.warn('上传签名不可用，改用后端中转上传')
    }
  }
  if (sign) {
    const uploaded = await putSignedFile(sign, file, options)
    // 只有服务端确认文件存在后才视为成功，避免列表出现空素材。
    const confirmed = await commonApi.uploadConfirm.post({ url: uploaded.url })
    if (confirmed?.code !== 1) throw new Error(confirmed?.message || '上传完成确认失败，请重试')
    return uploaded
  }
  options = { ...options, file }
  // #endif
  return uploadViaBackend(filePath, options)
}

/** 非 H5 或签名不可用时，以 multipart 中转并保持原有响应和进度契约。 */
function uploadViaBackend(filePath, options) {
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
    /** 将平台超时转换为可操作的中文提示，其余失败保留原始原因。 */
    const handleFail = (err) => {
      const message = err?.errMsg || '上传失败，请检查网络后重试'
      reject(new Error(/timeout/i.test(message)
        ? '上传超时，请切换稳定网络或压缩视频后重试'
        : message))
    }

    task = uni.uploadFile({
      url: UPLOAD_URL,
      filePath,
      // #ifdef H5
      file: options.file,
      // #endif
      name: 'file',
      header,
      timeout: config.UPLOAD_TIMEOUT,
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
