<template>
  <view class="app-page app-page--plain recharge">
    <AppNavBar title="额度充值" />

    <view class="recharge__body">
      <!-- 未登录：额度与账号绑定，先引导登录，不发起任何接口请求 -->
      <view v-if="!loggedIn" class="app-card recharge__login">
        <text class="recharge__login-title">登录后即可充值额度</text>
        <text class="recharge__login-desc">额度与账号绑定，登录后才能查看余额并购买套餐</text>
        <view class="app-btn-brand recharge__login-btn" role="button" @click="goLogin" tabindex="0" @keydown.enter.stop.prevent="goLogin" @keydown.space.stop.prevent="goLogin">
          <text>去登录</text>
        </view>
      </view>

      <template v-else>
        <!-- 额度卡片：数字全部来自 /account/credits -->
        <view class="recharge__card">
          <view class="recharge__card-row">
            <AppIcon name="coins" :size="16" color="rgba(255,255,255,0.85)" :stroke-width="2.5" />
            <text class="recharge__card-label">剩余额度</text>
          </view>
          <text class="recharge__card-value">
            {{ creditTotalText }}<text class="recharge__card-unit"> 额度</text>
          </text>
          <text v-if="creditSubText" class="recharge__card-sub">{{ creditSubText }}</text>
        </view>

        <!-- 套餐列表（单选，默认第一项） -->
        <text class="app-block-title recharge__title">选择套餐</text>

        <view v-if="packagesLoading" class="recharge__placeholder">
          <text class="app-muted">套餐加载中…</text>
        </view>

        <AppEmpty v-else-if="packagesError" title="套餐加载失败" :desc="packagesError" icon="alert-circle" action-text="重新加载" @action="loadPackages" />

        <template v-else-if="packages.length">
          <view
            v-for="item in packages"
            :key="item.id"
            class="recharge__pkg"
            :class="{ 'recharge__pkg--active': isSelected(item) }"
            role="button"
            :aria-label="item.name"
            @click="selectedId = item.id"
           tabindex="0" @keydown.enter.stop.prevent="selectedId = item.id" @keydown.space.stop.prevent="selectedId = item.id" :aria-pressed="isSelected(item)">
            <view class="recharge__pkg-main">
              <view class="recharge__pkg-head">
                <text class="recharge__pkg-name">{{ item.name }}</text>
                <text v-if="item.tag" class="recharge__pkg-tag">{{ item.tag }}</text>
              </view>
              <text v-if="item.sub_title" class="recharge__pkg-sub app-truncate">{{ item.sub_title }}</text>
              <text class="recharge__pkg-credits">{{ item.credits }} 额度</text>
            </view>
            <text class="recharge__pkg-price">¥{{ item.price }}</text>
          </view>
        </template>

        <AppEmpty v-else title="暂无可购买套餐" desc="套餐上架后即可在这里购买" icon="coins" />

        <!-- 立即充值：mock 支付会直接确认，真实支付则轮询订单状态 -->
        <view
          class="app-btn-brand recharge__pay"
          :class="{ 'recharge__pay--loading': paying }"
          role="button"
          aria-label="立即充值"
          :aria-disabled="paying || !selectedPackage || packagesLoading || !!packagesError"
          @click="handleRecharge"
         tabindex="0" @keydown.enter.stop.prevent="handleRecharge" @keydown.space.stop.prevent="handleRecharge">
          <AppIcon
            :name="paying ? 'loader' : 'zap'"
            :size="18"
            color="#FFFFFF"
            :stroke-width="2.5"
            :class="paying ? 'app-spin' : ''"
          />
          <text>{{ paying ? (payingStatus || '处理中…') : '立即充值' }}</text>
        </view>

        <!-- 充值记录：不新开路由，就地展开 -->
        <view class="recharge__link-row" role="button" @click="loadOrders" tabindex="0" @keydown.enter.stop.prevent="loadOrders" @keydown.space.stop.prevent="loadOrders">
          <text class="recharge__link">{{ ordersLoading ? '加载中…' : '查看充值记录' }}</text>
        </view>

        <view v-if="ordersLoaded" class="app-card recharge__orders">
          <text class="app-block-title">充值记录</text>
          <view v-if="!orders.length" class="recharge__orders-empty">
            <text class="app-muted">暂无充值记录</text>
          </view>
          <view v-for="order in orders" :key="order.order_no" class="recharge__order">
            <view class="recharge__order-main">
              <text class="recharge__order-name app-truncate">{{ order.package_name || '额度充值' }}</text>
              <text class="recharge__order-no">{{ order.order_no }}</text>
            </view>
            <view class="recharge__order-side">
              <text class="recharge__order-amount">¥{{ order.amount }}</text>
              <text class="recharge__order-status">{{ orderStatusText(order.status) }}</text>
              <text class="recharge__order-time">{{ order.pay_time || order.create_time }}</text>
            </view>
          </view>
        </view>
      </template>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { onUnload } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import AppNavBar from '@/components/AppNavBar.vue'
import AppEmpty from '@/components/AppEmpty.vue'
import api from '@/api'
import { useUserStore } from '@/store/modules/user'
import { currentPagePath, go, toLoginPath } from '@/utils/navigation'
import { refreshCurrentUserProfile } from '@/utils/session'

/**
 * 额度充值。
 *
 * 首页额度条与「我的作品」的充值入口都指向本页，因此必须真实可用：
 * 余额取 /v1/account/credits，套餐取 /v1/payment/package/list，下单走 /v1/payment/order/recharge。
 * mock 支付模式后端直接返回 mock=true，前端调用 mock/confirm 完成到账；真实微信支付则轮询订单状态。
 */

/** 订单状态文案与后端 OrderStatusEnum 一一对应 */
const ORDER_STATUS_TEXT = {
  1: '待支付',
  2: '已支付',
  3: '已交付',
  4: '已取消',
  5: '退款中',
  6: '已退款',
}

const PAY_POLL_INTERVAL = 3000
const PAY_TIMEOUT = 180000

const userStore = useUserStore()

const credits = ref(null)
const packages = ref([])
const selectedId = ref(null)
const packagesLoading = ref(false)
// 将请求失败与真实无套餐区分，并提供同页重试入口。
const packagesError = ref('')
const paying = ref(false)
const payingStatus = ref('')
const orders = ref([])
const ordersLoading = ref(false)
const ordersLoaded = ref(false)

let statusTimer = null

const loggedIn = computed(() => userStore.isLoggedIn)

const selectedPackage = computed(
  () => packages.value.find((item) => String(item.id) === String(selectedId.value)) || null
)

/** 拿不到的字段一律显示占位符，绝不编造数字 */
function metric(value) {
  return value === undefined || value === null ? '--' : String(value)
}

const creditTotalText = computed(() => metric(credits.value?.total))

const creditSubText = computed(() => {
  const data = credits.value
  if (!data) return ''
  return `今日已用 ${metric(data.today_used)} · 免费额度 ${metric(data.daily_free)}`
})

function orderStatusText(status) {
  return ORDER_STATUS_TEXT[Number(status)] || '未知状态'
}

function isSelected(item) {
  return String(item.id) === String(selectedId.value)
}

function toast(title) {
  uni.showToast({ title, icon: 'none' })
}

function goLogin() {
  // 统一走安全登录跳转，登录成功后回到本页继续充值
  go(toLoginPath(currentPagePath()))
}

async function loadCredits() {
  try {
    const res = await api.account.credits.post(
      {},
      { suppressGlobalError: true, suppressGlobalAuthError: true }
    )
    if (res && res.code === 1 && res.data) {
      credits.value = res.data
      userStore.setCreditTotal(res.data.total)
    }
  } catch (err) {
    console.error('加载剩余额度失败', err)
  }
}

/** 读取真实套餐并保留有效选择，读取失败时停止展示可购买状态。 */
async function loadPackages() {
  packagesLoading.value = true
  packagesError.value = ''
  try {
    const res = await api.payment.packageList.post({}, { suppressGlobalError: true })
    if (res?.code !== 1 || !Array.isArray(res.data)) throw new Error(res?.message || '暂时无法读取套餐')
    const list = res.data
    packages.value = list
    // 默认选中第一个套餐；刷新后若原选项仍在则保持不变
    if (list.length && !list.some((item) => String(item.id) === String(selectedId.value))) {
      selectedId.value = list[0].id
    }
  } catch (err) {
    console.error('加载充值套餐失败', err)
    packages.value = []
    selectedId.value = null
    packagesError.value = err?.message || '请检查网络后重试'
  } finally {
    packagesLoading.value = false
  }
}

async function loadOrders() {
  if (ordersLoading.value) return
  ordersLoading.value = true
  try {
    const res = await api.payment.orderList.post(
      { pageNum: 1, pageSize: 20 },
      { suppressGlobalError: true, suppressGlobalAuthError: true }
    )
    orders.value = res && res.code === 1 && Array.isArray(res.data) ? res.data : []
    ordersLoaded.value = true
  } catch (err) {
    console.error('加载充值记录失败', err)
    toast('充值记录加载失败')
  } finally {
    ordersLoading.value = false
  }
}

/** 到账后的统一收尾：刷新余额与用户资料，并同步已展开的充值记录 */
async function finishRecharge() {
  payingStatus.value = ''
  uni.showToast({ title: '充值成功', icon: 'success' })
  await Promise.all([loadCredits(), refreshCurrentUserProfile(userStore)])
  if (ordersLoaded.value) loadOrders()
}

async function confirmMockPayment(orderNo) {
  const res = await api.payment.orderMockConfirm.post(
    { order_no: orderNo },
    { suppressGlobalError: true }
  )
  if (!res || res.code !== 1) {
    toast(res?.message || '支付确认失败，请稍后重试')
    return
  }
  await finishRecharge()
}

/**
 * 轮询订单状态直到到账：已支付/已交付视为成功，取消/退款终止等待，超时返回 false。
 */
function waitForPayment(orderNo) {
  return new Promise((resolve) => {
    const startedAt = Date.now()
    statusTimer = setInterval(async () => {
      if (Date.now() - startedAt > PAY_TIMEOUT) {
        clearInterval(statusTimer)
        statusTimer = null
        resolve(false)
        return
      }
      try {
        const res = await api.payment.orderStatus.post(
          { order_no: orderNo },
          { suppressGlobalError: true }
        )
        const data = res && res.code === 1 ? res.data : null
        if (!data) return
        const status = Number(data.status)
        payingStatus.value = `等待支付…（${orderStatusText(status)}）`
        if (status === 2 || status === 3) {
          clearInterval(statusTimer)
          statusTimer = null
          resolve(true)
        } else if (status === 4 || status === 6) {
          clearInterval(statusTimer)
          statusTimer = null
          resolve(false)
        }
      } catch (err) {
        // 单次查询失败不终止轮询，等待下一次重试
        console.error('轮询订单状态失败，将继续重试', err)
      }
    }, PAY_POLL_INTERVAL)
  })
}

/** 有有效套餐且页面未在加载时才允许建单，重复操作沿用原有提交锁。 */
async function handleRecharge() {
  if (paying.value || packagesLoading.value || packagesError.value) return

  const pkg = selectedPackage.value
  if (!pkg) {
    toast('请先选择充值套餐')
    return
  }

  paying.value = true
  payingStatus.value = '正在创建订单…'
  try {
    const res = await api.payment.orderRecharge.post(
      { package_id: pkg.id, device: 'mobile' },
      { suppressGlobalError: true }
    )
    const data = res && res.code === 1 ? res.data : null
    const orderNo = data?.order_no
    if (!orderNo) {
      payingStatus.value = ''
      toast(res?.message || '下单失败，请稍后重试')
      return
    }

    if (data.mock === true) {
      await confirmMockPayment(orderNo)
      return
    }

    payingStatus.value = '等待支付…'
    const paid = await waitForPayment(orderNo)
    if (paid) {
      await finishRecharge()
    } else {
      payingStatus.value = ''
      toast('支付未完成，可稍后在充值记录中查看')
    }
  } catch (err) {
    // 套餐已下架等业务失败由后端给出可执行文案，原样透传
    console.error('创建充值订单失败', err)
    payingStatus.value = ''
    toast(err?.data?.message || err?.message || '下单失败，请稍后重试')
  } finally {
    paying.value = false
  }
}

onMounted(() => {
  // 未登录时只展示登录引导，不发起任何接口请求
  if (!loggedIn.value) return
  loadCredits()
  loadPackages()
})

onUnload(() => {
  // 离开页面停掉订单轮询，避免回调打到已销毁的页面
  if (statusTimer) clearInterval(statusTimer)
  statusTimer = null
})
</script>

<style lang="scss" scoped>
.recharge__body {
  min-height: calc(100vh - 52px);
  padding: 24px 18px 40px;
  background:
    linear-gradient(rgba(177, 45, 38, 0.03) 1px, transparent 1px),
    var(--bg-page);
  background-size: 100% 32px;
}

/* ============ 未登录引导 ============ */
.recharge__login {
  padding: 32px 20px;
  display: flex;
  background: var(--paper-card);
  border: 5px solid var(--paper-100);
  border-radius: 24px;
  box-shadow: var(--shadow-sm);
  flex-direction: column;
  align-items: center;
}

.recharge__login-title {
  font-size: 23px;
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-serif);
}

.recharge__login-desc {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-tertiary);
  text-align: center;
}

.recharge__login-btn {
  width: 100%;
  height: 48px;
  margin-top: 20px;
  font-size: 15px;
}

/* ============ 额度卡片 ============ */
.recharge__card {
  position: relative;
  overflow: hidden;
  border-radius: 24px;
  padding: 22px 20px;
  background: var(--grad-hero);
  border: 5px solid var(--paper-200);
  box-shadow: var(--shadow-sm);
  margin-bottom: 20px;

  &::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 150px;
    height: 150px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.12);
  }
}

.recharge__card-row {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 6px;
}

.recharge__card-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
}

.recharge__card-value {
  position: relative;
  z-index: 1;
  display: block;
  margin-top: 8px;
  font-size: 32px;
  font-weight: 700;
  line-height: 1.2;
  color: #ffffff;
}

.recharge__card-unit {
  font-size: 14px;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.8);
}

.recharge__card-sub {
  position: relative;
  z-index: 1;
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
}

/* ============ 套餐 ============ */
.recharge__title {
  display: block;
  margin-bottom: 12px;
  font-family: var(--font-serif);
  letter-spacing: 0.08em;
  color: var(--text-primary);
}

.recharge__placeholder {
  padding: 24px 0;
  text-align: center;
}

.recharge__pkg {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
  margin-bottom: 10px;
  background: rgba(255, 253, 248, 0.96);
  border: 1px solid var(--border-light);
  border-radius: 20px;
  box-shadow: 0 6px 16px rgba(93, 55, 36, 0.05);
  transition: all var(--transition-fast);

  min-height: 98px;

  &--active {
    border-color: var(--brand-primary);
    background: rgba(177, 45, 38, 0.06);
    box-shadow: inset 3px 0 0 var(--brand-primary), 0 6px 16px rgba(93, 55, 36, 0.06);
  }
}

.recharge__pkg-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.recharge__pkg-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.recharge__pkg-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.recharge__pkg-tag {
  flex-shrink: 0;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 600;
  color: #ffffff;
  background: var(--grad-brand);
  border-radius: var(--radius-full);
}

.recharge__pkg-sub {
  font-size: 12px;
  color: var(--text-tertiary);
}

.recharge__pkg-credits {
  font-size: 12px;
  font-weight: 500;
  color: var(--brand-primary);
}

.recharge__pkg-price {
  flex-shrink: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

/* ============ 支付按钮 / 记录入口 ============ */
.recharge__pay {
  height: 50px;
  font-size: 15px;
  margin-top: 18px;
  border-radius: var(--radius-full);
  box-shadow: 0 8px 18px rgba(177, 45, 38, 0.2);

  &--loading {
    opacity: 0.8;
  }
}

.recharge__link-row {
  display: flex;
  justify-content: center;
  padding: 12px 0 4px;
}

.recharge__link {
  font-size: 13px;
  font-weight: 500;
  color: var(--brand-primary);
}

/* ============ 充值记录 ============ */
.recharge__orders {
  margin-top: 12px;
  padding: 18px 16px;
  background: var(--paper-card);
  border: 6px solid var(--paper-100);
  border-radius: 26px;
}

.recharge__orders-empty {
  padding: 16px 0 4px;
  text-align: center;
}

.recharge__order {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-light);

  &:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }
}

.recharge__order-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.recharge__order-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.recharge__order-no {
  font-size: 11px;
  color: var(--text-tertiary);
  overflow-wrap: anywhere;
}

.recharge__order-side {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.recharge__order-amount {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.recharge__order-status {
  font-size: 12px;
  color: var(--brand-primary);
}

.recharge__order-time {
  font-size: 11px;
  color: var(--text-muted);
}
</style>
