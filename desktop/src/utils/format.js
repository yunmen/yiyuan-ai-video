/**
 * 秒数 → 友好时长文案(统一桌面端"预计耗时/剩余时间"展示,避免各处副本漂移):
 *  - 不足 1 分钟:        "X 秒"
 *  - 达到/超过 1 分钟:   "X 分 Y 秒"
 *  - 0 / 负数 / 非法:    返回 fallback(默认空串)
 *
 * @param {number|string} sec  时长(秒)
 * @param {object} [opts]
 * @param {boolean} [opts.approx=false]  是否加"约"字(估算/轮询值用 true,确定值用 false)
 * @param {string}  [opts.fallback='']  非法/0 时的回退文案
 * @returns {string}
 */
export function formatDuration(sec, opts = {}) {
  const { approx = false, fallback = '' } = opts
  const n = Math.max(0, Math.floor(Number(sec) || 0))
  if (n <= 0) return fallback
  const m = Math.floor(n / 60)
  const s = n % 60
  const p = approx ? '约 ' : ''
  return m > 0 ? `${p}${m} 分 ${s} 秒` : `${p}${s} 秒`
}
