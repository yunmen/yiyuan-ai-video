<script setup>
import { ref } from 'vue'
import { state, toast } from '../store/app'
import AppBar from '../components/AppBar.vue'

const packages = [
  { id: 1, name: '体验包', desc: '适合首次尝试', price: 9.9, times: 10 },
  { id: 2, name: '进阶包', desc: '高频制作首选', price: 29.9, times: 50, hot: true },
  { id: 3, name: '畅享包', desc: '不限量更划算', price: 99, times: 200 }
]
const records = [
  { name: '生成视频消耗', time: '今天 14:22', val: -1 },
  { name: '每日签到奖励', time: '今天 09:00', val: 1 },
  { name: '充值到账', time: '昨天 18:30', val: 50 },
  { name: '生成视频消耗', time: '昨天 10:05', val: -1 }
]
const selected = ref(null)

function recharge() {
  if (!selected.value) { toast('请先选择充值套餐'); return }
  const pkg = packages.find(p => p.id === selected.value)
  toast(`已发起 ${pkg.price} 元支付，充值成功将到账 ${pkg.times} 次`)
}
</script>

<template>
  <section class="page active">
    <AppBar title="账户余额" back-target="me" />
    <div class="body">
      <div class="balance-card">
        <div class="label">剩余免费额度</div>
        <div class="num">{{ state.credits }}<small>次</small></div>
        <div class="rule">每日 0 点重置 3 次免费额度 · 生成 1 条视频消耗 1 次 · 额度用尽可充值继续使用</div>
      </div>

      <div class="pkg">
        <div class="pkg-title">充值套餐</div>
        <div v-for="p in packages" :key="p.id" class="pkg-item" :class="{ on: selected === p.id }" @click="selected = p.id">
          <div>
            <div class="name">{{ p.name }} · {{ p.times }} 次</div>
            <div class="desc">{{ p.desc }}</div>
          </div>
          <div class="price">¥{{ p.price }}<small>/次{{ (p.price / p.times).toFixed(1) }}</small></div>
          <div v-if="p.hot" class="tag">推荐</div>
        </div>
      </div>

      <div class="record">
        <div v-for="(r, i) in records" :key="i" class="r-item">
          <div>
            <div class="r-name">{{ r.name }}</div>
            <div class="r-time">{{ r.time }}</div>
          </div>
          <div class="r-val" :class="r.val < 0 ? 'minus' : 'plus'">{{ r.val > 0 ? '+' : '' }}{{ r.val }}</div>
        </div>
      </div>
    </div>
    <div class="footer">
      <div>
        <div style="font-size:13px; font-weight:500">{{ selected ? packages.find(p => p.id === selected).name : '请选择套餐' }}</div>
        <div class="muted">立即充值，额度实时到账</div>
      </div>
      <button class="btn-p" :disabled="!selected" @click="recharge">立即充值</button>
    </div>
  </section>
</template>
