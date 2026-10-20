<template>
  <AccountServiceShell title="消耗记录" heading="每一份额度，都有去向" subtitle="查看生成扣款、失败退款和其他额度变动。">
    <view class="service-filters"><button v-for="item in FILTERS" :key="item.key" class="service-filter" :class="{ 'service-filter--active': filter === item.key }" role="button" tabindex="0" :aria-pressed="filter === item.key" @click="selectFilter(item.key)" @keydown.enter.prevent="selectFilter(item.key)" @keydown.space.prevent="selectFilter(item.key)">{{ item.label }}</button></view>
    <view v-if="rows.length" class="service-card log-list">
      <view v-for="item in rows" :key="item.id" class="log-row">
        <view class="log-icon" :class="{ 'log-icon--positive': item.change > 0 }"><AppIcon :name="item.change > 0 ? 'rotate-ccw' : 'coins'" :size="20" :color="item.change > 0 ? '#4B7A5A' : '#8A5A3B'" /></view>
        <view class="log-main"><text class="log-title">{{ item.type_label || '额度变动' }}</text><text class="log-remark">{{ item.remark || '额度变动已入账' }}</text><text class="log-time">{{ item.create_time }}</text><button v-if="item.task_id" class="log-task" role="button" tabindex="0" @click="openTask(item.task_id)" @keydown.enter.prevent="openTask(item.task_id)" @keydown.space.prevent="openTask(item.task_id)">查看关联任务 <text>↗</text></button></view>
        <view class="log-amount"><text :class="{ 'log-amount--positive': item.change > 0 }">{{ item.change > 0 ? '+' : '' }}{{ item.change }}</text><text>余额 {{ item.balance }}</text></view>
      </view>
    </view>
    <text v-if="error" class="service-error" role="alert">{{ error }}</text>
    <ServiceButton v-if="error" text="重新加载" secondary @click="retry" />
    <view v-if="loading" class="service-status">正在读取额度流水…</view>
    <AppEmpty v-else-if="!rows.length && !error" icon="clock" title="这里还没有额度记录" desc="生成扣款和任务失败退款都会记录在这里。" />
    <ServiceButton v-if="rows.length < total && !loading && !error" text="加载更多记录" secondary @click="loadMore" />
    <text v-if="rows.length" class="service-note log-note">{{ rows.length >= total ? '已展示全部记录。' : '' }}额度为创作次数，任务失败返还以实际入账为准。</text>
  </AccountServiceShell>
</template>
<script setup>
import AccountServiceShell from '@/components/AccountServiceShell.vue'
import AppEmpty from '@/components/AppEmpty.vue'
import AppIcon from '@/components/AppIcon.vue'
import ServiceButton from '@/components/ServiceButton.vue'
import api from '@/api'
import { go } from '@/utils/navigation'
import { useAccountList } from '@/composables/useAccountList'

/** 类型与后端流水枚举保持一致；全部含充值、奖励和结算返还。 */
const FILTERS = [{ key: 'all', label: '全部' }, { key: 'consume', label: '生成扣款' }, { key: 'refund', label: '失败退款' }, { key: 'settle', label: '结算返还' }]
const { rows, total, loading, error, filter, selectFilter, loadMore, retry } = useAccountList(fetchLogs)
/** 使用用户端流水接口，身份由后端鉴权确定，前端不提交 user_id。 */
function fetchLogs({ filter, ...paging }) { return api.account.creditsLogs.post({ ...paging, ...(filter === 'all' ? {} : { type: filter }) }, { suppressGlobalError: true }) }
/** 打开与真实流水关联的任务详情。 */
function openTask(id) { go({ path: '/pages/task-detail/index', query: { id } }) }
</script>
<style lang="scss" scoped>
@import '@/styles/account-services.scss';
.log-list { padding: 2px 14px; }
.log-row { display: flex; align-items: flex-start; gap: 11px; padding: 22px 0; }
.log-row + .log-row { box-shadow: 0 -1px 0 var(--line-1); }
.log-icon { display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; flex-shrink: 0; border-radius: 13px; background: #f2ede4; }
.log-icon--positive { background: #ebf2ec; }
.log-main { display: flex; flex: 1; min-width: 0; flex-direction: column; gap: 6px; }
.log-title { font-size: 14px; color: var(--ink-900); }
.log-remark { color: var(--ink-500); font-size: 11px; overflow-wrap: anywhere; line-height: 1.7; }
.log-time { color: var(--ink-500); font-size: 10px; }
.log-task { margin: 3px 0 -8px; padding: 8px 0; text-align: left; color: var(--brand-primary); font-size: 11px; line-height: 1.6; background: transparent; }
.log-task::after { border: none; }
.log-amount { display: flex; flex-shrink: 0; flex-direction: column; align-items: flex-end; gap: 8px; color: var(--ink-900); font-size: 20px; }
.log-amount--positive { color: #4b7a5a; }
.log-amount text:last-child { color: var(--ink-500); font-size: 10px; }
.log-note { text-align: center; }
</style>
