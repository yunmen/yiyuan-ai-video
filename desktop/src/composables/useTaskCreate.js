import { ref } from 'vue'
import { useRouter } from 'vue-router'

// 建单(后端同步做素材识别 + 提示词组装)最长可达 120s,期间若只显示「提交中」
// 用户会以为程序卡住;用轮换文案告知「正在做什么」,让等待过程始终有反馈。
const SUBMIT_HINTS = [
  '正在识别你的素材…',
  '正在为你组装生成提示词…',
  '正在估算时长与算力…',
  '马上开始生成，请稍候…',
]

// 创建生成任务后的统一动作:成功拿到 task_id 即提示并跳转到生成页。
// Creator / Digital 等多页面的提交成功分支结构一致(建单扣额度 → 跳 /generate/:id),
// 抽到此层避免重复实现。Upload 因含支付分支可保留自有逻辑,也可按需复用本方法。
export function useTaskCreate() {
  const router = useRouter()
  // 建单过程中轮换展示的提示文案(由 createAndNavigate 在其执行期间驱动)
  const submitHint = ref(SUBMIT_HINTS[0])
  let hintTimer = null
  let hintIdx = 0

  function startHint() {
    hintIdx = 0
    submitHint.value = SUBMIT_HINTS[0]
    if (hintTimer) clearInterval(hintTimer)
    // 每 1.5s 轮换一条,覆盖建单的同步等待期
    hintTimer = setInterval(() => {
      hintIdx = (hintIdx + 1) % SUBMIT_HINTS.length
      submitHint.value = SUBMIT_HINTS[hintIdx]
    }, 1500)
  }

  function stopHint() {
    if (hintTimer) { clearInterval(hintTimer); hintTimer = null }
  }

  // createFn: 返回 Promise<{ code, data, message }>,由调用方封装具体的建单请求;
  // opts: { message, replace } —— message 为成功提示,replace 为 true 时用 router.replace 跳转。
  // 返回成功时的 data(含 id),失败或异常返回 null。
  async function createAndNavigate(createFn, opts = {}) {
    // 仅在建单请求执行期间轮换提示;无论成败都停止,避免离开页面后定时器泄漏
    startHint()
    let res
    try {
      res = await createFn()
    } catch (e) {
      return null
    } finally {
      stopHint()
    }
    if (res?.code === 1 && res.data?.id) {
      if (opts.message) window.$message?.success(opts.message)
      const target = `/generate/${res.data.id}`
      if (opts.replace) router.replace(target)
      else router.push(target)
      return res.data
    }
    return null
  }

  return { createAndNavigate, submitHint }
}
