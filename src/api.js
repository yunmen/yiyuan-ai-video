/**
 * 用户端接口封装(原型 H5)
 *
 * 约定同 desktop/admin:同源 `/api` 由网关(Caddy)反代到 backend 的 /api/user。
 * 原型环境(未接后端)调用失败时,由调用方回退本地示例数据。
 */

const BASE = '/api/v1'

async function post(path, data = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export const digitalApi = {
  /** 数字人列表(仅返回已上架) */
  list: (data) => post('/digital/list', data),
  /** 数字人详情 */
  detail: (data) => post('/digital/detail', data)
}
