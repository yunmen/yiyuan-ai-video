// 后端 /gen-config 选项单一来源:复刻形态 / 替换意图 / 主角表现 / 创意档位 / 开头钩子 / 单价 / 推荐默认值。
// 模块级缓存,避免多页面、多组件重复请求;所有实例共享同一份响应式数据。
import { reactive } from 'vue'
import api from '@/api'

// 默认(后端未升级)时页面退化为“不指定”,与升级前行为一致;列表非空才渲染对应选择区
const state = reactive({
  replicateFormats: [],
  replicateIntents: [],
  leadActs: [],
  creativeLevels: [],
  hookBoosts: [],
  price: '9.90',
  // 推荐默认值(小白不调参时由前端预填,用户不感知):与后端 REPLICATE_DEFAULTS 同源
  defaults: { creative_level: '', hook_boost: '', format: '', lead_act: '', intent: [] },
})

// 后端下发的选项用 value 作键(与 pydantic 字段名一致),前端统一读 key。
// 这里做一次归一化:否则组件里的 find(x => x.key === ...) 永远匹配不上,
// 表现为“选项能渲染但点了不选中 / 说明文字一直是未指定”(实际踩过)。
function normalizeOptions(list) {
  return (Array.isArray(list) ? list : []).map((o) => ({
    key: o.key ?? o.value ?? '',
    label: o.label ?? '',
    desc: o.desc ?? '',
  }))
}

const loaded = { value: false }
let inflight = null

async function load() {
  if (inflight) return inflight
  inflight = (async () => {
    try {
      const res = await api.common.genConfig.post()
      if (res.code === 1 && res.data) {
        const d = res.data
        if (Array.isArray(d.replicate_formats)) state.replicateFormats = normalizeOptions(d.replicate_formats)
        if (Array.isArray(d.replicate_intents)) state.replicateIntents = normalizeOptions(d.replicate_intents)
        if (Array.isArray(d.lead_acts)) state.leadActs = normalizeOptions(d.lead_acts)
        if (Array.isArray(d.replicate_creative_levels)) state.creativeLevels = normalizeOptions(d.replicate_creative_levels)
        if (Array.isArray(d.replicate_hook_boosts)) state.hookBoosts = normalizeOptions(d.replicate_hook_boosts)
        if (d['gen.video_price']) state.price = d['gen.video_price']
        if (d.replicate_defaults) state.defaults = { ...state.defaults, ...d.replicate_defaults }
      }
    } catch (e) {
      // 用默认空列表,不阻断主流程
    }
    loaded.value = true
  })()
  return inflight
}

// 返回响应式配置对象;首次调用即触发一次拉取(多实例共享同一份)
export function useGenConfig() {
  if (!loaded.value) load()
  return state
}
