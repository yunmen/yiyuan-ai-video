<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import QRCode from 'qrcode'
import { useUserStore } from '@/store/modules/user'
import api from '@/api'

const userStore = useUserStore()

const balance = ref({ free_credits: 0, credits: 0, total: 0, daily_free: 3, today_used: 0 })
const logs = ref([])
const total = ref(0)
const loading = ref(false)
const query = reactive({ pageNum: 1, pageSize: 10 })

// 充值套餐(来自后台配置)
const packages = ref([])
const selected = ref(null)
const currentPkg = computed(() => packages.value.find(p => p.id === selected.value) || null)

// 支付弹窗
const payVisible = ref(false)
const paying = ref(false)
const confirming = ref(false)
const payInfo = reactive({ order_no: '', amount: '', code_url: '', mock: false })
const qrData = ref('')
let pollTimer = null

async function loadPackages() {
  try {
    const res = await api.payment.packageList.post()
    if (res.code === 1) {
      packages.value = res.data || []
      if (packages.value.length && !selected.value) {
        const hot = packages.value.find(p => p.tag)
        selected.value = (hot || packages.value[0]).id
      }
    }
  } catch (e) { /* 拦截器已提示 */ }
}

async function loadBalance() {
  try {
    const res = await api.account.credits.post()
    if (res.code === 1) balance.value = res.data
  } catch (e) { /* 拦截器已提示 */ }
}

// 每日签到
const signInfo = ref(null)
const signing = ref(false)

async function loadSign() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await api.account.signStatus.post()
    if (res.code === 1) signInfo.value = res.data
  } catch (e) { /* 拦截器已提示 */ }
}

async function doSign() {
  if (!userStore.isLoggedIn) { userStore.openLogin(); return }
  signing.value = true
  try {
    const res = await api.account.sign.post()
    if (res.code === 1) {
      window.$message?.success(`签到成功，获得 ${res.data.credits} 次额度`)
      await loadSign()
      await loadBalance()
      query.pageNum = 1
      await loadLogs()
    }
  } catch (e) { /* 拦截器已提示 */ }
  signing.value = false
}

async function loadLogs() {
  loading.value = true
  try {
    const res = await api.account.creditsLogs.post({ ...query })
    if (res.code === 1) {
      logs.value = res.data || []
      total.value = res.total || 0
    }
  } catch (e) { /* 拦截器已提示 */ }
  loading.value = false
}

function onPageChange(page) {
  query.pageNum = page
  loadLogs()
}

function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function checkStatus(silent = true) {
  try {
    const res = await api.payment.orderStatus.post({ order_no: payInfo.order_no })
    if (res.code === 1 && res.data && res.data.status === 3) {
      stopPoll()
      payVisible.value = false
      window.$message?.success('充值成功，额度已到账')
      await loadBalance()
      query.pageNum = 1
      await loadLogs()
      return true
    }
    if (!silent && res.code !== 1) stopPoll()
  } catch (e) { /* 忽略轮询异常 */ }
  return false
}

function startPoll() {
  stopPoll()
  let times = 0
  pollTimer = setInterval(async () => {
    times += 1
    const done = await checkStatus()
    if (done || times >= 90) {
      stopPoll()
      if (!done) window.$message?.warning('暂未查询到支付结果，请稍后刷新额度')
    }
  }, 2000)
}

async function recharge() {
  if (!currentPkg.value) { window.$message?.info('请先选择充值套餐'); return }
  if (!userStore.isLoggedIn) { userStore.openLogin(); return }
  paying.value = true
  try {
    const res = await api.payment.recharge.post({ package_id: currentPkg.value.id, device: 'desktop' })
    if (res.code === 1) {
      const data = res.data
      Object.assign(payInfo, {
        order_no: data.order_no,
        amount: data.amount,
        code_url: data.code_url,
        mock: !!data.mock,
      })
      qrData.value = data.code_url && !data.mock ? await QRCode.toDataURL(data.code_url) : ''
      payVisible.value = true
      startPoll()
    }
  } catch (e) { /* 拦截器已提示 */ }
  paying.value = false
}

async function mockPay() {
  confirming.value = true
  try {
    const res = await api.payment.mockConfirm.post({ order_no: payInfo.order_no })
    if (res.code === 1) await checkStatus(false)
  } catch (e) { /* 拦截器已提示 */ }
  confirming.value = false
}

function unitPrice(p) {
  const price = Number(p.price || 0)
  return price && p.credits ? (price / p.credits).toFixed(2) : '0.00'
}

onMounted(() => {
  if (!userStore.isLoggedIn) {
    userStore.openLogin()
    return
  }
  loadBalance()
  loadLogs()
  loadPackages()
  loadSign()
})

onBeforeUnmount(stopPoll)
</script>

<template>
  <div class="balance-page">
    <div class="wrap">
      <div class="col-main">
        <!-- 每日签到 -->
        <div class="sign-card">
          <div class="s-left">
            <div class="s-title">每日签到</div>
            <div class="s-sub">
              {{ signInfo ? (signInfo.signed ? `今日已签到 · 连续 ${signInfo.streak} 天` : `连续签到 ${signInfo.streak} 天 · 今日可领 ${signInfo.daily_credits} 次`) : '签到领取免费额度' }}
            </div>
          </div>
          <button class="btn-sign" :class="{ done: signInfo?.signed }" :disabled="signing || signInfo?.signed" @click="doSign">
            {{ signInfo?.signed ? '已签到' : (signing ? '签到中…' : `签到 +${signInfo ? signInfo.daily_credits : 1}`) }}
          </button>
        </div>

        <!-- 余额卡 -->
        <div class="balance-card">
          <div class="bc-top">
            <div>
              <div class="label">剩余额度</div>
              <div class="num">{{ balance.total }}<small>次</small></div>
            </div>
            <div class="bc-split">
              <div><b>{{ balance.free_credits }}</b><span>免费额度</span></div>
              <div><b>{{ balance.credits }}</b><span>付费额度</span></div>
              <div><b>{{ balance.today_used }}</b><span>今日已用</span></div>
            </div>
          </div>
          <div class="rule">每日 0 点重置 {{ balance.daily_free }} 次免费额度 · 生成 1 条作品消耗 1 次 · 额度用尽可充值继续使用</div>
        </div>

        <!-- 充值套餐 -->
        <div class="panel">
          <div class="panel-head">
            <h3>充值套餐</h3>
            <span class="panel-sub">付费额度永久有效，优先于免费额度消耗</span>
          </div>
          <n-spin :show="!packages.length">
            <div class="pkg-grid">
              <div
                v-for="p in packages"
                :key="p.id"
                class="pkg-item"
                :class="{ on: selected === p.id }"
                @click="selected = p.id"
              >
                <div v-if="p.tag" class="tag">{{ p.tag }}</div>
                <div class="p-name">{{ p.name }}</div>
                <div class="p-times">{{ p.credits }}<small>次</small></div>
                <div class="p-desc">{{ p.sub_title || '即充即用' }}</div>
                <div class="p-price">¥{{ p.price }}<small>约 {{ unitPrice(p) }} 元/次</small></div>
              </div>
              <div v-if="!packages.length" class="pkg-empty">暂无可用套餐</div>
            </div>
          </n-spin>
          <div class="pkg-footer">
            <div>
              <div class="f-title">{{ currentPkg ? `${currentPkg.name} · ${currentPkg.credits} 次` : '请选择套餐' }}</div>
              <div class="f-sub">支付成功后额度实时到账</div>
            </div>
            <button class="btn-p" :disabled="!currentPkg || paying" @click="recharge">
              {{ paying ? '下单中…' : `立即充值 ${currentPkg ? '¥' + currentPkg.price : ''}` }}
            </button>
          </div>
        </div>
      </div>

      <!-- 额度流水 -->
      <div class="col-side">
        <div class="panel record">
          <div class="panel-head">
            <h3>额度明细</h3>
          </div>
          <n-spin :show="loading">
            <div v-if="!logs.length && !loading" class="empty">暂无额度变动记录</div>
            <div v-for="r in logs" :key="r.id" class="r-item">
              <div class="r-left">
                <div class="r-name">{{ r.type_label }}<span v-if="r.remark" class="r-remark"> · {{ r.remark }}</span></div>
                <div class="r-time">{{ r.create_time }} · 余额 {{ r.balance }} 次</div>
              </div>
              <div class="r-val" :class="r.change < 0 ? 'minus' : 'plus'">{{ r.change > 0 ? '+' : '' }}{{ r.change }}</div>
            </div>
          </n-spin>
          <div v-if="total > query.pageSize" class="pager">
            <n-pagination v-model:page="query.pageNum" :item-count="total" :page-size="query.pageSize" @update:page="onPageChange" />
          </div>
        </div>
      </div>
    </div>

    <!-- 支付弹窗 -->
    <n-modal v-model:show="payVisible" preset="card" style="max-width: 380px" title="扫码支付" @after-leave="stopPoll">
      <div class="pay-box">
        <div class="pay-amount">¥{{ payInfo.amount }}</div>
        <template v-if="payInfo.mock">
          <div class="pay-tip">当前为开发环境模拟支付，点击下方按钮确认付款</div>
          <button class="btn-p block" :disabled="confirming" @click="mockPay">{{ confirming ? '确认中…' : '模拟支付成功' }}</button>
        </template>
        <template v-else>
          <img v-if="qrData" :src="qrData" class="pay-qr" alt="支付二维码" />
          <div class="pay-tip">请使用微信扫码支付，支付完成后自动到账</div>
        </template>
        <div class="pay-order">订单号 {{ payInfo.order_no }}</div>
      </div>
    </n-modal>
  </div>
</template>

<style scoped>
.balance-page { background: var(--bg); min-height: calc(100vh - 64px); }
.wrap {
  max-width: 560px;
  margin: 0 auto;
  padding: 16px 16px 80px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.col-main, .col-side { display: flex; flex-direction: column; gap: 16px; min-width: 0; }

/* 每日签到 */
.sign-card {
  background: #fff;
  border-radius: var(--radius);
  padding: 14px 16px;
  box-shadow: var(--shadow-sm);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.s-title { font-size: 15px; font-weight: 600; }
.s-sub { font-size: 12px; color: var(--weak); margin-top: 4px; }
.btn-sign {
  height: 38px; padding: 0 20px; border: none; border-radius: 19px;
  background: var(--brand); color: #fff; font-size: 14px; font-weight: 600;
  cursor: pointer; white-space: nowrap;
}
.btn-sign:hover:not(:disabled) { background: #FF6A3D; }
.btn-sign:disabled { background: #FFD3C2; cursor: not-allowed; }
.btn-sign.done { background: var(--bg); color: var(--weak); }

/* 余额卡 */
.balance-card {
  background: linear-gradient(135deg, #FF6A3D, #FF4D1C);
  border-radius: 16px;
  padding: 24px 20px;
  color: #fff;
}
.bc-top { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.balance-card .label { font-size: 13px; opacity: .85; }
.balance-card .num { font-size: 40px; font-weight: 700; margin-top: 6px; line-height: 1.1; }
.balance-card .num small { font-size: 14px; font-weight: 400; margin-left: 4px; }
.bc-split { display: flex; gap: 18px; }
.bc-split div { display: flex; flex-direction: column; align-items: center; }
.bc-split b { font-size: 18px; font-weight: 700; }
.bc-split span { font-size: 11px; opacity: .8; margin-top: 2px; }
.balance-card .rule { font-size: 11px; opacity: .78; margin-top: 16px; line-height: 1.7; }

/* 通用面板 */
.panel { background: #fff; border-radius: 14px; padding: 18px 16px; }
.panel-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.panel-head h3 { margin: 0; font-size: 16px; font-weight: 600; }
.panel-sub { font-size: 12px; color: var(--weak); }

/* 套餐 */
.pkg-grid { display: grid; grid-template-columns: 1fr; gap: 10px; }
.pkg-item {
  position: relative;
  border: 1.5px solid var(--line);
  border-radius: 12px;
  padding: 14px 16px;
  cursor: pointer;
  transition: border-color .15s, box-shadow .15s, transform .15s;
}
.pkg-item:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(255, 77, 28, .10); }
.pkg-item.on { border-color: #FF4D1C; background: #FFF8F5; }
.p-name { font-size: 15px; font-weight: 600; }
.p-times { font-size: 24px; font-weight: 700; color: #FF4D1C; margin-top: 2px; }
.p-times small { font-size: 12px; font-weight: 400; margin-left: 3px; }
.p-desc { font-size: 12px; color: var(--weak); margin-top: 2px; }
.p-price { font-size: 14px; font-weight: 600; margin-top: 8px; }
.p-price small { font-size: 11px; font-weight: 400; color: var(--weak); margin-left: 6px; }
.pkg-item .tag {
  position: absolute; top: -1px; right: 12px;
  background: #FF4D1C; color: #fff; font-size: 10px;
  padding: 1px 8px; border-radius: 0 0 6px 6px;
}
.pkg-empty { text-align: center; color: var(--weak); font-size: 13px; padding: 24px 0; }

.pkg-footer {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  border-top: 1px solid var(--line);
  margin-top: 14px; padding-top: 14px;
}
.f-title { font-size: 14px; font-weight: 600; }
.f-sub { font-size: 12px; color: var(--weak); margin-top: 2px; }
.btn-p {
  height: 40px; padding: 0 24px; border: none; border-radius: 20px;
  background: #FF4D1C; color: #fff; font-size: 14px; font-weight: 600;
  cursor: pointer; white-space: nowrap; transition: background .15s;
}
.btn-p:hover:not(:disabled) { background: #FF6A3D; }
.btn-p:disabled { background: #FFD3C2; cursor: not-allowed; }
.btn-p.block { display: block; width: 100%; }

/* 流水 */
.r-item {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 12px 0; border-bottom: 1px solid var(--line);
}
.r-item:last-child { border-bottom: none; }
.r-left { min-width: 0; }
.r-name { font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.r-remark { font-size: 12px; color: var(--weak); }
.r-time { font-size: 12px; color: var(--weak); margin-top: 4px; }
.r-val { font-size: 16px; font-weight: 700; flex: 0 0 auto; }
.r-val.plus { color: #18A058; }
.r-val.minus { color: #FF4D1C; }
.empty { text-align: center; color: var(--weak); font-size: 13px; padding: 30px 0; }
.pager { display: flex; justify-content: center; margin-top: 12px; }

/* 支付弹窗 */
.pay-box { display: flex; flex-direction: column; align-items: center; gap: 12px; }
.pay-amount { font-size: 28px; font-weight: 700; color: #FF4D1C; }
.pay-qr { width: 200px; height: 200px; border-radius: 10px; border: 1px solid var(--line); }
.pay-tip { font-size: 13px; color: var(--body-c); text-align: center; }
.pay-order { font-size: 11px; color: var(--weak); word-break: break-all; text-align: center; }

/* 桌面端 */
@media (min-width: 900px) {
  .wrap {
    max-width: 1160px;
    padding: 24px;
    display: grid;
    grid-template-columns: minmax(0, 1.6fr) minmax(320px, 1fr);
    gap: 20px;
    align-items: start;
  }
  .balance-card { padding: 28px 26px; }
  .panel { padding: 20px; border-radius: 16px; }
  .pkg-grid { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; }
}
</style>
