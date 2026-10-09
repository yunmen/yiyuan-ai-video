/**
 * 账号相关的展示与校验工具。
 */

/** 校验登录名是否符合后端账号格式约束（登录用，兼容历史非手机号账号）。 */
export function validateAccount(value) {
  const account = String(value || '').trim()
  if (!account) return '请输入登录名'
  return /^[A-Za-z0-9._@-]{6,20}$/.test(account)
    ? ''
    : '登录名需为6-20位，仅支持英文字母、数字和 . _ @ -'
}

/** 校验密码是否满足后端允许的长度范围。 */
export function validatePassword(value) {
  const password = String(value || '')
  if (!password) return '请输入密码'
  return password.length >= 6 && password.length <= 32
    ? ''
    : '密码长度需为6-32位'
}

/** 校验注册账号是否为 11 位中国大陆手机号（注册用，仅格式校验，不做短信验证）。 */
export function validatePhone(value) {
  const phone = String(value || '').trim()
  if (!phone) return '请输入手机号'
  return /^1[3-9]\d{9}$/.test(phone)
    ? ''
    : '请输入 11 位手机号'
}

/**
 * 将原始用户 ID 格式化为带前缀的展示形态。
 * 同一 ID 始终生成相同结果，便于用户识别与复制。
 * @param {string|number} id - 原始用户 ID
 * @returns {string} 例如 42 → No.000042
 */
export function formatUserId(id) {
  const value = String(id ?? '').trim()
  if (!value) return 'No.000000'
  return `No.${value.padStart(6, '0')}`
}
