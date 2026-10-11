import { ref } from 'vue'
import api from '@/api'

/** 串行轮询内容准备任务；取消时立即结束等待，旧请求不得覆盖新任务。 */
export function useContentPrepare() {
  const loading = ref(false)
  let sequence = 0
  let cancelWait = null

  /** 取消本地轮询，不撤销服务端任务，也不允许其结果继续回写。 */
  function stop() {
    sequence += 1
    loading.value = false
    if (cancelWait) cancelWait()
    cancelWait = null
  }

  /** 下发复刻准备上下文，返回经过质量检查的三段文案；失败明确抛出中文错误。 */
  async function run(goal, meta) {
    stop()
    const current = sequence
    loading.value = true
    const deadline = Date.now() + 180000
    const cancelled = new Promise((_, reject) => {
      cancelWait = () => reject(Object.assign(new Error('文案准备已取消'), { cancelled: true }))
    })
    /** 为每次请求及等待设置剩余时间上限，网络异常也不能无限轮询。 */
    async function bounded(promise) {
      let timer
      try {
        return await Promise.race([
          promise,
          cancelled,
          new Promise((_, reject) => {
            timer = setTimeout(() => reject(new Error('文案准备超时，请重试')), Math.max(1, deadline - Date.now()))
          }),
        ])
      } finally {
        clearTimeout(timer)
      }
    }
    try {
      const response = await bounded(api.content.prepare.post({ goal, meta }, { suppressGlobalError: true }))
      if (response?.code !== 1 || !response.data?.task_id) throw new Error(response?.message || '文案任务创建失败')
      while (Date.now() < deadline) {
        const result = await bounded(api.content.result.post({ task_id: response.data.task_id }, { suppressGlobalError: true }))
        if (current !== sequence) throw Object.assign(new Error('文案准备已取消'), { cancelled: true })
        if (result?.code !== 1) throw new Error(result?.message || '获取文案失败')
        const data = result.data
        if (data?.status === 'done') {
          const copy = data.result?.content?.copy
          if (data.result?.metadata?.ok === false || data.result?.metadata?.quality === 'failed') throw new Error('文案准备失败，请重试')
          if (!copy || !copy.title?.trim() || !copy.subtitle?.trim() || (!copy.script?.trim() && !copy.no_narration)) throw new Error('未生成有效文案，请重试')
          if (copy.fallback || (meta.images?.length && !copy.vision)) throw new Error('素材识别服务暂不可用，未采用通用模板，请重试或手动填写文案')
          return { title: copy.title, subtitle: copy.subtitle, script: copy.script || '', noNarration: !!copy.no_narration, speechBudget: copy.speech_budget }
        }
        if (data?.status !== 'pending') throw new Error('文案任务已失效，请重试')
        await bounded(new Promise((resolve) => setTimeout(resolve, 1500)))
      }
      throw new Error('文案准备超时，请重试')
    } finally {
      if (current === sequence) {
        loading.value = false
        cancelWait = null
      }
    }
  }

  return { loading, run, stop }
}
