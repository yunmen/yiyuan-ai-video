import { useRouter } from 'vue-router'

// 创建生成任务后的统一动作:成功拿到 task_id 即提示并跳转到生成页。
// Creator / Digital 等多页面的提交成功分支结构一致(建单扣额度 → 跳 /generate/:id),
// 抽到此层避免重复实现。Upload 因含支付分支可保留自有逻辑,也可按需复用本方法。
export function useTaskCreate() {
  const router = useRouter()

  // createFn: 返回 Promise<{ code, data, message }>,由调用方封装具体的建单请求;
  // opts: { message, replace } —— message 为成功提示,replace 为 true 时用 router.replace 跳转。
  // 返回成功时的 data(含 id),失败或异常返回 null。
  async function createAndNavigate(createFn, opts = {}) {
    let res
    try {
      res = await createFn()
    } catch (e) {
      return null
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

  return { createAndNavigate }
}
