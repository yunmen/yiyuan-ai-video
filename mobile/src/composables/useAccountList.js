import { ref } from 'vue'
import { onShow, onReachBottom, onPullDownRefresh } from '@dcloudio/uni-app'
import { requireLogin } from '@/utils/navigation'

/** 个人列表共用分页；序列号防止切换筛选后旧响应覆盖新列表。 */
export function useAccountList(fetchPage) {
  /** 列表、筛选和请求状态只保留在当前页面，不在不同账号间缓存。 */
  const rows = ref([]), total = ref(0), loading = ref(false), error = ref(''), filter = ref('all')
  let page = 0, requestId = 0

  /** 刷新重置页码；追加失败时保留已有记录，重试仍请求同一页。 */
  async function load(reset = false) {
    if (!reset && (loading.value || rows.value.length >= total.value)) return
    if (!requireLogin()) return
    const current = ++requestId
    const nextPage = reset ? 1 : page + 1
    if (reset) { rows.value = []; total.value = 0; page = 0 }
    loading.value = true
    error.value = ''
    try {
      const response = await fetchPage({ pageNum: nextPage, pageSize: 20, filter: filter.value })
      if (current !== requestId) return
      if (response?.code !== 1) throw new Error(response?.message || '加载失败，请重试')
      rows.value = reset ? (response.data || []) : [...rows.value, ...(response.data || [])]
      total.value = Number(response.total || 0)
      page = nextPage
    } catch (err) {
      if (current === requestId) error.value = err?.message || '加载失败，请稍后重试'
    } finally {
      if (current === requestId) loading.value = false
    }
  }
  /** 切换筛选立即清空旧数据，避免错把旧列表标记为新分类。 */
  function selectFilter(value) { if (filter.value !== value) { filter.value = value; load(true) } }
  /** 触底请求下一页。 */
  function loadMore() { return load(false) }
  /** 首次或下拉重新读取当前筛选。 */
  function refresh() { return load(true) }
  /** 失败首屏重试第一页，追加失败重试当前下一页。 */
  function retry() { return load(page === 0) }
  onShow(refresh)
  onReachBottom(loadMore)
  /** 下拉刷新无论成功失败都关闭平台加载指示。 */
  onPullDownRefresh(async () => { try { await refresh() } finally { uni.stopPullDownRefresh() } })
  return { rows, total, loading, error, filter, selectFilter, loadMore, refresh, retry }
}
