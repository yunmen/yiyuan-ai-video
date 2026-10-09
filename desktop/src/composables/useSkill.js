import { ref, onBeforeUnmount } from 'vue'
import api from '@/api'

// 内容生成统一调用组合式:收口「下发 → 轮询至 done/not_found → 返回产物」。
// 页面只关心 runCopy / runImagePrompt / runVoice / runPipeline + result/loading,
// 不重复写轮询逻辑;内部技能名与编排对前端透明,对外接口均为中性产品功能名(/content/*)。
export function useSkill() {
  const loading = ref(false)
  const result = ref(null)   // 标准产物 content(ToolResult.content)
  const meta = ref(null)     // 标准产物 metadata(含 plan/handoff/ok)
  const error = ref('')
  const status = ref('')     // pending | done | not_found
  // 质量门禁透传:meta.quality ∈ ok | degraded | failed(由 worker 编排器聚合,见 docs/skill_agent_workflow_analysis.md)
  const quality = ref('')
  const qualityWarn = ref('')

  let timer = null

  function stop() {
    if (timer) { clearInterval(timer); timer = null }
  }

  // 把编排器返回的质量标记转成用户可读提示;degraded=部分兜底生成,failed=整体失败
  function applyQuality(metaObj) {
    const q = (metaObj && metaObj.quality) || ''
    quality.value = q
    if (q === 'degraded') {
      qualityWarn.value = '部分内容由兜底模板生成,质量可能不完整,建议人工复核或重新生成'
    } else if (q === 'failed') {
      qualityWarn.value = '内容生成链路失败,请稍后重试'
    } else {
      qualityWarn.value = ''
    }
  }

  // 轮询异步产物直到 done / not_found / 超时;只按 task_id,不含技能名
  function poll(taskId, { interval = 2000, timeout = 120000 } = {}) {
    return new Promise((resolve) => {
      const started = Date.now()
      const tick = async () => {
        try {
          // 结果路由仅按 task_id 取产物(后端忽略技能名),不把技能名写进 URL
          const res = await api.content.result.post({ task_id: taskId })
          if (res?.code !== 1) {
            status.value = 'not_found'
            resolve({ status: 'not_found', data: null })
            return
          }
          const st = res.data?.status
          status.value = st
          if (st === 'done') {
            stop()
            const data = res.data?.result || {}
            result.value = data.content ?? null
            meta.value = data.metadata ?? null
            applyQuality(meta.value)
            resolve({ status: 'done', data })
            return
          }
          if (st === 'not_found') {
            stop()
            resolve({ status: 'not_found', data: null })
            return
          }
          // pending:继续轮询,但超过总超时则放弃(避免页面永久卡住)
          if (Date.now() - started > timeout) {
            stop()
            resolve({ status: 'timeout', data: null })
          }
        } catch (e) {
          // 网络抖动:继续轮询,超时由上面统一判定
        }
      }
      stop()
      tick()
      timer = setInterval(tick, interval)
    })
  }

  // 通用:调用某个内容功能(feature 对应 api.content.<key>)并轮询产物。
  // 注意:后端各 /content/* 的 body 约定为 { instruction, params }(instruction 自然语言指令,
  // params 为结构化参数);本组合式对调用方屏蔽该形态——调用方只传"功能参数 payload",
  // 这里统一包成 { instruction: '', params: payload } 下发,避免直接平铺导致 params 丢失。
  async function runFeature(key, payload = {}) {
    loading.value = true
    error.value = ''
    result.value = null
    meta.value = null
    try {
      const res = await api.content[key].post({ instruction: '', params: payload })
      if (res?.code !== 1 || !res.data?.task_id) {
        error.value = res?.message || '调用失败'
        return { status: 'error', data: null }
      }
      return await poll(res.data.task_id)
    } catch (e) {
      error.value = e?.message || '调用异常'
      return { status: 'error', data: null }
    } finally {
      loading.value = false
    }
  }

  // 生成/润色带货文案(映射服务端 text-generation 技能)
  async function runCopy(payload = {}) { return runFeature('copy', payload) }
  // 生成中文图片提示词(映射服务端 image-generation 技能)
  async function runImagePrompt(payload = {}) { return runFeature('imagePrompt', payload) }
  // 语音合成(映射服务端 audio-synthesis 技能)
  async function runVoice(payload = {}) { return runFeature('voice', payload) }
  // 长文去 AI 味改写(映射服务端 text-rewrite 技能)
  async function runRewrite(payload = {}) { return runFeature('rewrite', payload) }
  // 批量翻译(映射服务端 text-translate 技能,供模板多语言变体本地化)
  async function runTranslate(payload = {}) { return runFeature('translate', payload) }

  // 内容准备流水线(目标 → 多步骤内容生成)并轮询黑板产物(映射服务端 video-replicate-prep 等计划)
  async function runPipeline(goal, planMeta = {}, plan = null) {
    loading.value = true
    error.value = ''
    result.value = null
    meta.value = null
    try {
      const res = await api.content.prepare.post({ goal, meta: planMeta, plan })
      if (res?.code !== 1 || !res.data?.task_id) {
        error.value = res?.message || '内容准备失败'
        return { status: 'error', data: null }
      }
      return await poll(res.data.task_id)
    } catch (e) {
      error.value = e?.message || '内容准备异常'
      return { status: 'error', data: null }
    } finally {
      loading.value = false
    }
  }

  onBeforeUnmount(stop)

  return { loading, result, meta, error, status, quality, qualityWarn, runCopy, runImagePrompt, runVoice, runRewrite, runTranslate, runPipeline, poll, stop }
}
