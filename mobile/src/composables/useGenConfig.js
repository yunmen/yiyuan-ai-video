import { computed, ref } from 'vue'
import api from '@/api'

/**
 * 公开业务配置（POST /v1/base/common/gen-config）。
 *
 * 后端把「管理员可配的生成参数」与「代码内置的能力选项」一并下发，前端只渲染不写死，
 * 避免新增档位时要同时改前后端两处（能选却校验不过 / 反之）。
 * 该接口免登录，模块级缓存一次，多个页面共享同一份配置。
 */
const config = ref(null)
const loading = ref(false)
let inflight = null

/** 读取字符串配置项并做 trim，缺失返回空串。 */
function pickString(key) {
  const value = config.value?.[key]
  return value === undefined || value === null ? '' : String(value).trim()
}

/** 读取整数配置项，非法值回退默认。 */
function pickNumber(key, fallback) {
  const num = Number(pickString(key))
  return Number.isFinite(num) && num > 0 ? num : fallback
}

/** 加载一次公开配置（并发调用共享同一请求）。 */
export async function loadGenConfig(force = false) {
  if (config.value && !force) return config.value
  if (inflight) return inflight
  loading.value = true
  inflight = api.common.genConfig
    .post({}, { suppressGlobalError: true, suppressGlobalAuthError: true })
    .then((res) => {
      if (res && res.code === 1 && res.data) config.value = res.data
      return config.value
    })
    .catch((err) => {
      console.error('加载公开业务配置失败，页面使用兜底默认值', err)
      return config.value
    })
    .finally(() => {
      loading.value = false
      inflight = null
    })
  return inflight
}

/** 直接读取原始配置值（未加载时返回 undefined）。 */
export function genConfigValue(key) {
  return config.value?.[key]
}

export function useGenConfig() {
  /** 创意档位：忠实复刻 / 适度改造 / 爆款改写（含推荐位兜底） */
  const creativeLevels = computed(() => {
    const list = config.value?.replicate_creative_levels
    return Array.isArray(list) && list.length
      ? list
      : [
          { key: 'faithful', label: '忠实复刻', desc: '保持原片结构与动作' },
          { key: 'creative', label: '适度改造', desc: '在保留原片风格下做创意增强' },
          { key: 'viral', label: '爆款改写', desc: '按爆款逻辑重塑表演与节奏' },
        ]
  })
  /** 后端推荐默认档位（小白不调参时用的值，与后端兜底同源） */
  const defaultCreativeLevel = computed(
    () => String(config.value?.replicate_defaults?.creative_level || 'creative')
  )
  /** 开头钩子强化档位 */
  const hookBoosts = computed(() => {
    const list = config.value?.replicate_hook_boosts
    return Array.isArray(list) && list.length
      ? list
      : [
          { key: 'normal', label: '正常', desc: '正常开头即可' },
          { key: 'strong', label: '强化开头', desc: '用强钩子抓住前 3 秒' },
          { key: 'off', label: '关闭', desc: '不做特殊处理' },
        ]
  })
  /** 复刻目标形态（短剧 / 口播 / 街采…），空数组表示不指定形态 */
  const replicateFormats = computed(() => {
    const list = config.value?.replicate_formats
    return Array.isArray(list) ? list : []
  })
  /** 替换意图（换人物 / 换商品 / 换场景） */
  const replicateIntents = computed(() => {
    const list = config.value?.replicate_intents
    return Array.isArray(list) ? list : []
  })
  /** 默认画幅 / 清晰度 */
  const defaultRatio = computed(() => pickString('gen.video_ratio') || '9:16')
  const defaultResolution = computed(() => pickString('gen.video_resolution') || '1080P')
  /** 视频编辑（复刻）参考视频时长上限（秒） */
  const maxReferenceSeconds = computed(() => pickNumber('gen.video_edit_max_seconds', 30))
  /** 数字人口播模型；为空表示后端未接入，数字人任务不可用 */
  const digitalModel = computed(() => pickString('gen.digital_model'))

  /** 主角表现（跳舞律动 / 推广种草）：仅在「换人物」时生效，由后端 lead_acts 单一来源下发 */
  const leadActs = computed(() => {
    const list = config.value?.lead_acts
    return Array.isArray(list) && list.length
      ? list
      : [
          { key: 'dance', label: '跳舞律动', desc: '让新主角跟着节奏跳起来' },
          { key: 'pitch', label: '推广种草', desc: '让新主角像主播一样介绍' },
        ]
  })

  return {
    genConfig: config,
    loading,
    loadGenConfig,
    creativeLevels,
    defaultCreativeLevel,
    hookBoosts,
    replicateFormats,
    replicateIntents,
    leadActs,
    defaultRatio,
    defaultResolution,
    maxReferenceSeconds,
    digitalModel,
  }
}
