/**
 * 生成任务的展示工具集（对应后端 GenerateTaskModel / /v1/task/*）。
 *
 * 说明：后端任务状态只有 processing / success / failed 三态（TaskStatusEnum），
 * 进度 progress 由 worker 回调写入；这里把状态、阶段文案、封面、时长、时间等
 * 展示口径集中到一处，避免各页面各写一套导致口径漂移。
 */

/** 状态 → 展示口径（键为后端原始状态）。 */
const STATUS_MAP = {
  processing: { key: 'processing', label: '生成中' },
  pending: { key: 'processing', label: '生成中' },
  success: { key: 'completed', label: '已完成' },
  failed: { key: 'failed', label: '失败' },
}

/** 任务类型 → 中文名。 */
const TYPE_LABELS = {
  video: '视频生成',
  digital: '数字人口播',
  render: '视频换口播',
  image: '图片生成',
  audio: '音频生成',
  text: '文案生成',
  deconstruct: '对标拆解',
}

/**
 * 生成阶段文案。
 * 与设计稿「我的作品」生成中遮罩的四段文案一致（AI 解析素材 → AI 生成分镜 →
 * AI 合成配音中 → AI 渲染画面中），按进度阈值切换。
 */
const PROGRESS_PHASES = [
  { at: 0, text: 'AI 解析素材' },
  { at: 45, text: 'AI 生成分镜' },
  { at: 65, text: 'AI 合成配音中' },
  { at: 85, text: 'AI 渲染画面中' },
]

/** 作品列表不需要展示的内部任务类型（对标拆解只做分析、不产出成片）。 */
const INTERNAL_TYPES = ['deconstruct']

/** 归一化状态，未知状态按「生成中」处理，避免出现空白标签。 */
export function workStatus(status) {
  return STATUS_MAP[String(status || '').toLowerCase()] || STATUS_MAP.processing
}

/** 是否为「我的作品」应展示的任务。 */
export function isWorkTask(item) {
  return !!item && !INTERNAL_TYPES.includes(String(item.type || ''))
}

/** 作品标题：优先模板标题，其次用户备注，最后回退类型名。 */
export function workTitle(item) {
  if (!item) return '未命名作品'
  const title = String(item.template_title || '').trim()
  if (title) return title
  const remark = String(item.remark || '').trim()
  if (remark) return remark
  return TYPE_LABELS[item.type] || 'AI 作品'
}

/** 作品副标题（类型标签）。 */
export function workTypeLabel(item) {
  return TYPE_LABELS[item?.type] || 'AI 作品'
}

/**
 * 作品封面地址。
 * 优先模板封面，其次素材里的静态图片；视频素材与后端返回的相对地址一律丢弃，
 * 交给页面渲染统一的渐变兜底，避免出现裂图。
 */
export function workCover(item) {
  if (!item) return ''
  const candidates = [item.template_cover, item.cover, ...(Array.isArray(item.materials) ? item.materials : [])]
  for (const candidate of candidates) {
    const url = String(candidate || '').trim()
    if (/^https?:\/\//i.test(url) && /\.(png|jpe?g|webp|gif|bmp)(\?|$)/i.test(url)) return url
  }
  return ''
}

/** 成片时长（秒）：worker 上报的真实时长优先，其次建单吸附档位。 */
export function workDuration(item) {
  const seconds = Number(item?.usage?.seconds || item?.gen_duration || 0)
  return Number.isFinite(seconds) && seconds > 0 ? Math.round(seconds) : 0
}

/** 秒 → mm:ss（0 时返回占位符，用于生成中的卡片）。 */
export function formatDuration(seconds) {
  const total = Number(seconds || 0)
  if (!total) return '--:--'
  const minutes = Math.floor(total / 60)
  const rest = Math.floor(total % 60)
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

/** 后端时间串（YYYY-MM-DD HH:mm:ss）→ MM-DD HH:mm。 */
export function formatDateTime(value) {
  const text = String(value || '').trim()
  if (!text) return ''
  const match = text.match(/^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/)
  if (!match) return text
  return `${match[2]}-${match[3]} ${match[4]}:${match[5]}`
}

/** 大数字缩写：12800 → 1.2w，860 → 860。 */
export function formatCount(value) {
  const num = Number(value || 0)
  if (!Number.isFinite(num) || num <= 0) return '0'
  if (num >= 10000) return `${(num / 10000).toFixed(1)}w`
  return String(Math.round(num))
}

/** 进度归一化到 0-99 的整数（生成中最多展示 99%，成功才到 100%）。 */
export function normalizeProgress(value) {
  const num = Number(value || 0)
  if (!Number.isFinite(num) || num <= 0) return 0
  return Math.max(0, Math.min(99, Math.round(num)))
}

/** 进度 → 阶段文案。 */
export function workStageText(progress) {
  const value = Number(progress || 0)
  let text = PROGRESS_PHASES[0].text
  for (const phase of PROGRESS_PHASES) {
    if (value >= phase.at) text = phase.text
  }
  return text
}

/**
 * 生成中的「预计还需」文案。
 * 依据后端 estimate_seconds 的估算口径（视频 = 90s + 时长 × 25s）与任务创建时间推算，
 * 只做展示用途，不作为超时判定 —— 真实进度以 worker 回调为准。
 */
export function workRemainingText(item) {
  if (!item) return ''
  const created = Date.parse(String(item.create_time || '').replace(' ', 'T'))
  if (!Number.isFinite(created)) return '生成中'
  const duration = workDuration(item) || 0
  const estimated = String(item.type) === 'digital' ? 420 : String(item.type) === 'render' ? 600 : 90 + duration * 25
  const elapsed = Math.max(0, (Date.now() - created) / 1000)
  const remain = Math.round((estimated - elapsed) / 60)
  if (remain <= 0) return '即将完成'
  return `预计还需 ${remain} 分钟`
}

/** 失败原因（后端已做用户侧脱敏，缺失时给统一兜底文案）。 */
export function workFailReason(item) {
  return String(item?.fail_reason || '').trim() || '生成失败，可删除后重新发起'
}
