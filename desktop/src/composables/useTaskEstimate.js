import { ref, computed } from 'vue'
import api from '@/api'
import { formatDuration } from '@/utils/format'

// 生成任务花费预估:多页面(Upload 视频 / Creator 图文音 / Digital 数字人)共用的
// 「消耗次数 + 预计耗时」逻辑。后端 EstimateSchema 与建单扣减同源,
// 预估失败不阻断提交(以下单时后端计算结果为准),故这里静默处理异常。
export function useTaskEstimate() {
  const estCost = ref(null)
  const estSeconds = ref(0)
  // 后端回传的可选规格(画幅/清晰度/时长档位等),与 TASK_PROFILES / gen_rules 同源,
  // 前端据此渲染真实选项,不再各自写死(数字人时长档位也取自这里,避免 UI 显示与实际吸附档不符)。
  const estOptions = ref(null)

  // 通用文案:消耗额度 + 预计耗时(时长统一用 formatDuration,超过 1 分钟显示"X 分 Y 秒")
  const estText = computed(() => {
    const parts = [`消耗 ${estCost.value ?? 1} 次额度`]
    const s = estSeconds.value
    if (s) parts.push(`预计 ${formatDuration(s)}`)
    return parts.join(' · ')
  })

  // 拉取一次预估;成功时回填并返回完整 data,便于调用方读取规格选项等额外字段
  async function refresh(type, extra = {}) {
    try {
      const res = await api.task.estimate.post({ type, ...extra })
      if (res.code === 1 && res.data) {
        estCost.value = res.data.cost
        estSeconds.value = res.data.estimate_seconds || 0
        estOptions.value = res.data.options || null
        return res.data
      }
    } catch (e) {
      // 估值失败静默,不阻断下单
    }
    return null
  }

  return { estCost, estSeconds, estText, estOptions, refresh }
}
