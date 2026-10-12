import config from '@/config'
import { useUserStore } from '@/store/modules/user'
import { getStorage, removeStorage } from '@/utils/storage'
import { getSafeInternalRedirect, toLoginPath } from '@/utils/navigation'

/**
 * 移动端统一请求封装（基于 uni.request）。
 * 统一附加 Token、绕过 GET 缓存、处理业务状态码与鉴权失效跳转。
 * 业务判断：后端成功 code=1，业务失败 code=0，鉴权失败 code=9。
 * 说明：后端只签发单个 token，没有续期流程；鉴权失效一律清理登录态并跳转登录页。
 * 说明：会员订阅已不再作为功能门禁，功能不可用只可能是积分不足。
 */

/** 全局跳转登录锁，防止多个并发 401 请求重复触发 uni.reLaunch。 */
let isRedirectingToLogin = false

/** 尝试获取登录跳转锁，避免并发请求重复跳转登录页。 */
function acquireLoginRedirectLock() {
  if (isRedirectingToLogin) return false
  isRedirectingToLogin = true
  return true
}

/** 释放登录跳转锁。 */
function releaseLoginRedirectLock() {
  isRedirectingToLogin = false
}

/** 清理失效身份，避免其他业务继续把用户视为已登录。 */
function clearAuthentication() {
  try {
    useUserStore().logout()
  } catch (err) {
    console.error('清理登录态失败')
    removeStorage(config.TOKEN_NAME)
    removeStorage(config.USER_INFO_KEY)
  }
}

/** 读取请求实际携带的 Token，用于识别已经过期的旧会话响应。 */
function getRequestToken(header) {
  const authorization = header?.[config.TOKEN_NAME]
  if (typeof authorization !== 'string') return ''
  return authorization.startsWith(config.TOKEN_PREFIX)
    ? authorization.slice(config.TOKEN_PREFIX.length)
    : authorization
}

/** 仅允许当前会话的鉴权失败清理身份，旧请求不得影响刚完成的新登录。 */
function isCurrentSessionRequest(requestToken) {
  if (!requestToken) return true
  const currentToken = useUserStore().token
  return !currentToken || requestToken === currentToken
}

/** 处理身份失效，并保留清理身份前的站内目标。 */
function handleAuthenticationExpired(currentPage) {
  const target = getSafeInternalRedirect(currentPage)
  clearAuthentication()
  return target
}

/** 优先提取后端返回的业务错误，避免只向用户展示 HTTP 状态文本。 */
function getResponseErrorMessage(error) {
  const data = error?.data
  return data?.message || data?.msg || data?.detail || error?.errMsg || error?.message
}

/** 构建带自定义配置的 uni.request Option，返回 Promise<完整响应体>。 */
function uniRequest(url, method, data, configOption = {}) {
  return new Promise((resolve, reject) => {
    uni.request({
      url,
      method,
      data,
      // 单请求可通过 configOption.timeout 覆盖全局默认 10s 超时（同步长任务如策略研究需放宽）；
      // 下方展开的 configOption.unireq 若含 timeout 仍可二次覆盖，保持既有兼容。
      timeout: configOption.timeout || config.TIMEOUT,
      header: configOption.header || {},
      ...configOption.unireq,
      success: (res) => {
        // 仅当到达 HTTP 层才算完成，业务状态码在下方统一处理
        resolve({ statusCode: res.statusCode, data: res.data, config: configOption })
      },
      fail: (err) => {
        reject({ data: null, errMsg: err.errMsg || '请求服务器无响应！', config: configOption })
      },
    })
  })
}

/** 附带 Token 与防缓存参数后的完整 URL。 */
function buildUrl(url) {
  let finalUrl = url
  if (!config.REQUEST_CACHE && !finalUrl.includes('?')) {
    finalUrl += `${finalUrl.includes('?') ? '&' : '?'}_=${Date.now()}`
  }
  return finalUrl
}

/**
 * 核心请求执行：附加 Token、按业务状态码分发、鉴权失效清理登录态并跳转登录页。
 */
async function request(url, method, data = {}, configOption = {}) {
  let token = getStorage(config.TOKEN_NAME)
  const header = {
    ...config.HEADERS,
    ...(configOption.header || {}),
  }
  if (token) header[config.TOKEN_NAME] = config.TOKEN_PREFIX + token
  if (!config.REQUEST_CACHE && method === 'GET') {
    data = { ...(data || {}), _: Date.now() }
  }

  // 记录当前页面路径，用于鉴权失效后的回跳
  let currentPage = ''
  try {
    const pages = getCurrentPages()
    const page = pages && pages.length ? pages[pages.length - 1] : null
    currentPage = page ? `/${page.route}` : ''
  } catch (err) {
    console.error('获取当前页面路径失败')
    currentPage = ''
  }

  let res
  try {
    res = await uniRequest(buildUrl(url), method, data, { ...configOption, header })
  } catch (error) {
    // 网络请求失败时统一抛出包含原始 errMsg 的 Error，方便调用方展示或继续处理
    const errMsg = error?.errMsg || '请求服务器无响应！'
    throw new Error(errMsg)
  }
  const body = res.data

  // HTTP 层错误
  if (!res.statusCode || res.statusCode < 200 || res.statusCode >= 300) {
    const message = getResponseErrorMessage(res)
    if (configOption.suppressGlobalError && res.statusCode !== 401) {
      throw Object.assign(new Error(message || `HTTP ${res.statusCode}`), { data: res.data, dataStatus: res.statusCode })
    }
    return handleHttpError(res.statusCode, message, header, configOption, currentPage)
  }

  // 业务状态码：0 业务失败 / 9 鉴权失效 / 其他按成功返回完整响应
  if (body && body.code === 0) {
    try { uni.showToast({ title: body.message || body.msg || '操作失败', icon: 'none' }) } catch (err) { console.error('业务失败提示弹窗失败') }
    // 默认抛出业务错误，让调用方通过 try/catch 处理；旧代码可传 suppressBusinessError: true 保持兼容。
    if (!configOption.suppressBusinessError) {
      throw Object.assign(new Error(body.message || body.msg || '操作失败'), { code: 0, data: body.data })
    }
  }

  if (body && body.code === 9) {
    const message = body.message || body.msg || '登录已过期'
    const authError = Object.assign(new Error(message), { code: 9, dataStatus: 401 })
    if (configOption.suppressGlobalAuthError) throw authError
    const requestToken = getRequestToken(header)
    if (!isCurrentSessionRequest(requestToken)) throw authError

    // 获取跳转锁，防止并发 401 触发多次 uni.reLaunch
    if (!acquireLoginRedirectLock()) throw authError
    const target = handleAuthenticationExpired(currentPage)
    try { uni.showToast({ title: message, icon: 'none' }) } catch (err) { console.error('登录过期提示弹窗失败') }
    uni.reLaunch({
      url: toLoginPath(target),
      success: releaseLoginRedirectLock,
      fail: releaseLoginRedirectLock,
    })
    // 兜底：若 success/fail 未正常回调，3 秒后自动释放锁
    setTimeout(releaseLoginRedirectLock, 3000)
    throw authError
  }

  return body
}

/** HTTP 错误分发（404/500/403/401/400 等）。 */
function handleHttpError(statusCode, message, requestHeader, configOption, currentPage) {
  const msg = message || ''
  if (statusCode === 403) {
    // 会员订阅已不再作为功能门禁，403 只可能来自其它权限校验，不再引导订阅页
    if (!configOption.suppressForbiddenRedirect) {
      try {
        uni.showToast({ title: msg || '暂无权限访问该资源', icon: 'none' })
      } catch (err) { console.error('无权限提示弹窗失败') }
    }
  } else if (statusCode === 401) {
    const requestToken = getRequestToken(requestHeader)
    if (!isCurrentSessionRequest(requestToken)) {
      throw Object.assign(new Error(msg || '登录已过期'), { data: null, dataStatus: 401 })
    }
    // 获取跳转锁，防止并发 401 触发多次 uni.reLaunch
    if (!acquireLoginRedirectLock()) {
      throw Object.assign(new Error(msg || '登录已过期'), { data: null, dataStatus: 401 })
    }
    const target = handleAuthenticationExpired(currentPage)
    uni.reLaunch({
      url: toLoginPath(target),
      success: releaseLoginRedirectLock,
      fail: releaseLoginRedirectLock,
    })
    // 兜底：若 success/fail 未正常回调，3 秒后自动释放锁
    setTimeout(releaseLoginRedirectLock, 3000)
  } else {
    const titles = {
      404: msg || '正在请求不存在的服务器记录！',
      500: msg || '服务器发生错误！',
      400: msg || '提交的数据不符合要求，请检查后重试。',
      422: msg || '提交的数据不符合要求，请检查后重试。',
    }
    try {
      uni.showToast({ title: titles[statusCode] || msg || `HTTP ${statusCode}`, icon: 'none' })
    } catch (err) { console.error('HTTP 错误提示弹窗失败') }
  }
  throw Object.assign(new Error(msg || `HTTP ${statusCode}`), { data: null, dataStatus: statusCode, suppressed: true })
}

const http = {
  get(url, params = {}, configOption = {}) {
    return request(url, 'GET', params, configOption)
  },
  post(url, data = {}, configOption = {}) {
    return request(url, 'POST', data, configOption)
  },
  put(url, data = {}, configOption = {}) {
    return request(url, 'PUT', data, configOption)
  },
  /**
   * 流式接口（SSE）。
   * H5 平台使用 fetch + ReadableStream 逐块聚合后端 chunk 正文；其余平台退化为普通 POST。
   * @returns {Promise<{code: number, data: {content: string}}>} SSE 结束时返回聚合正文；HTTP 错误抛出带 message 的 Error。
   */
  stream(url, data = {}, configOption = {}) {
    // 仅 H5 环境存在 fetch/ReadableStream；其他平台（小程序/App）保持原退化逻辑
    if (typeof window === 'undefined' || typeof window.fetch !== 'function') {
      return request(url, 'POST', data, configOption)
    }
    // 将 uni.request 回调形态的 async 超时配置转成毫秒
    const timeout = configOption.timeout || config.TIMEOUT
    return new Promise((resolve, reject) => {
      const controller = typeof AbortController !== 'undefined' ? new AbortController() : null
      const timer = controller && timeout ? setTimeout(() => controller.abort(), timeout) : null
      const header = { ...config.HEADERS, ...(configOption.header || {}) }
      const token = getStorage(config.TOKEN_NAME)
      if (token) header[config.TOKEN_NAME] = config.TOKEN_PREFIX + token
      // 关闭浏览器自动缓存，服务端黑名单已一并附加 _= 防缓存参数
      header['Cache-Control'] = 'no-cache'
      // 必须显式声明 JSON：fetch 对字符串 body 默认会发 text/plain，FastAPI 会当作字符串校验失败
      if (!header['Content-Type']) header['Content-Type'] = 'application/json'

      fetch(buildUrl(url), {
        method: 'POST',
        headers: header,
        body: JSON.stringify(data),
        signal: controller ? controller.signal : undefined,
      })
        .then(async (response) => {
          if (timer) clearTimeout(timer)
          // HTTP 层错误：优先读取后端返回的业务错误信息
          if (!response.ok) {
            let message = `HTTP ${response.status}`
            try {
              const text = await response.text()
              const parsed = JSON.parse(text)
              message = parsed.message || parsed.msg || parsed.detail || message
            } catch (err) {
              console.error('解析错误响应体失败')
              /* 忽略非 JSON 错误体，使用默认 HTTP 文案 */
            }
            throw Object.assign(new Error(message), { data: null, dataStatus: response.status })
          }
          // 逐块读取 SSE，聚合 chunk 正文；error 事件与 [DONE] 终止
          const reader = response.body && typeof response.body.getReader === 'function'
            ? response.body.getReader()
            : null
          if (!reader) {
            throw new Error('当前环境不支持流式读取')
          }
          const decoder = new TextDecoder()
          let buffer = ''
          let content = ''
          let streamError = ''
          let metaId = ''
          let metaTaskId = ''
          let finished = false
          while (!finished) {
            const { value, done } = await reader.read()
            if (done) break
            buffer += decoder.decode(value || new Uint8Array(), { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''
            for (const line of lines) {
              if (!line.startsWith('data: ')) continue
              const payload = line.slice(6)
              if (payload === '[DONE]') { finished = true; break }
              try {
                const parsed = JSON.parse(payload)
                if (parsed.chunk) content += parsed.chunk
                else if (parsed.error) streamError = parsed.error
                else {
                  // 透传 meta 帧（id/task_id），供「重新生成」原地覆盖使用
                  if (parsed.id) metaId = parsed.id
                  if (parsed.task_id) metaTaskId = parsed.task_id
                }
              } catch (err) {
                console.error('解析 SSE 辅助数据帧失败')
                /* 忽略无法解析的辅助数据帧 */
              }
            }
          }
          if (streamError) throw new Error(streamError)
          resolve({ code: 1, data: { content, id: metaId, task_id: metaTaskId } })
        })
        .catch((err) => {
          if (timer) clearTimeout(timer)
          // 统一错误对象形态，便于调用方展示 message
          reject(Object.assign(err instanceof Error ? err : new Error(err?.message || '请求失败'), { data: null }))
        })
    })
  },
  request,
}

export default http