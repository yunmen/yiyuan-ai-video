<template>
  <view class="tool-cost" :aria-busy="loading" aria-live="polite">
    <view class="tool-cost__heading">
      <AppIcon :name="loading ? 'loader' : estimate ? 'coins' : 'alert-circle'" :size="16" color="#B23A2E" :class="{ 'app-spin': loading }" />
      <text>{{ loading ? '正在计算费用…' : (estimate ? `预计消耗 ${estimate.cost} 额度` : '费用暂不可用') }}</text>
      <button v-if="!loading && !estimate" class="tool-cost__link" role="button" tabindex="0" @click="refresh" @keydown.enter.prevent="refresh" @keydown.space.prevent="refresh">重新计算</button>
    </view>
    <template v-if="userStore.isLoggedIn">
      <text class="tool-cost__note">可用 {{ userStore.creditTotal ?? '--' }} 额度 · 失败退回，成功按实际用量结算</text>
      <button v-if="estimate?.enough === false" class="tool-cost__link" role="button" tabindex="0" @click="recharge" @keydown.enter.prevent="recharge" @keydown.space.prevent="recharge">额度不足，去充值</button>
    </template>
    <button v-else class="tool-cost__link" role="button" tabindex="0" @click="login" @keydown.enter.prevent="login" @keydown.space.prevent="login">登录后使用</button>
  </view>
</template>

<script setup>
import { showAppModal } from '@/utils/feedback'
import { ref, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import api from '@/api'
import AppIcon from '@/components/AppIcon.vue'
import { useUserStore } from '@/store/modules/user'
import { currentPagePath, go, toLoginPath } from '@/utils/navigation'

// 报价与余额沿用统一任务接口，展示层不自行推算费用。
const props = defineProps({ params: { type: Object, required: true } })
const userStore = useUserStore()
const estimate = ref(null)
const loading = ref(false)
// 请求序号防止规格快速切换时旧报价覆盖新报价。
let sequence = 0

/** 获取与实扣同源的费用和最新余额，失败不沿用旧报价。 */
async function refresh() {
  const requestId = ++sequence
  loading.value = true
  estimate.value = null
  try {
    const res = await api.task.estimate.post(props.params)
    if (requestId !== sequence) return false
    if (res?.code !== 1 || !res.data) return false
    estimate.value = res.data
    if (res.data.balance) userStore.setCreditTotal(res.data.balance.total)
    return true
  } catch (err) {
    console.error('获取工具费用失败', err)
    return false
  } finally {
    if (requestId === sequence) loading.value = false
  }
}

/** 登录后回到当前工具。 */
function login() {
  go(toLoginPath(currentPagePath()))
}

/** 使用已有充值页补足额度。 */
function recharge() {
  go('/pages/recharge/index')
}

/** 提交前重新核价，未登录、无报价或余额不足均不提交。 */
async function ensure() {
  if (!userStore.isLoggedIn) {
    login()
    return false
  }
  if (!await refresh()) {
    uni.showToast({ title: '无法确认费用，请稍后重试', icon: 'none' })
    return false
  }
  if (estimate.value.enough === false) {
    showAppModal({
      title: '额度不足',
      content: `本次需要 ${estimate.value.cost} 额度，可用 ${estimate.value.balance?.total ?? 0} 额度`,
      confirmText: '去充值',
      success: (res) => { if (res.confirm) recharge() },
    })
    return false
  }
  return true
}

watch(() => [props.params, userStore.token], refresh, { deep: true, immediate: true })
onShow(refresh)
defineExpose({ ensure, refresh })
</script>

<style lang="scss" scoped>
.tool-cost {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  margin: 12px 0;
  padding: 12px;
  width: 100%;
  border-radius: 18px;
  background: var(--paper-100);
  font-size: 12px;
  color: var(--ink-500);
  text-align: center;
  &__heading { display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 7px; color: var(--ink-700); font-weight: 500; }
  &__note { display: block; font-size: 11px; line-height: 1.8; }
  &__link { display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 6px 14px; margin: 0; border-radius: 999px; background: var(--paper-card); color: var(--brand-primary); font-size: 12px; line-height: 1.5; }
}
</style>
