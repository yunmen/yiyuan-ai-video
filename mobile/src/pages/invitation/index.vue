<template>
  <AccountServiceShell title="邀请好友" heading="好灵感，值得分享" subtitle="邀请一位新朋友，一起开启下一次创作。">
    <view v-if="loading" class="service-status">正在准备你的专属邀请码…</view>
    <text v-if="error" class="service-error" role="alert">{{ error }}</text>
    <ServiceButton v-if="error" text="重新获取邀请码" secondary @click="loadInvitation" />
    <template v-if="invitation">
      <view class="service-card invite-card">
        <view class="invite-seal"><AppIcon name="share" :size="27" color="#B23A2E" /></view>
        <text class="invite-card__label">你的专属邀请码</text>
        <text class="invite-code" selectable>{{ invitation.code }}</text>
        <text v-if="invitation.reward_amount > 0" class="invite-reward">注册成功，你和好友各得 <text>{{ invitation.reward_amount }}</text> 额度</text>
        <text v-else class="service-note">邀请奖励暂未开启，仍可分享邀请码。</text>
        <ServiceButton text="复制邀请码" @click="copyCode" />
        <text class="service-note">分享给好友，注册时填写即可</text>
      </view>
      <view class="invite-stats"><view><text>{{ invitation.invited_count }}</text><text>成功邀请 / 人</text></view><view><text>{{ invitation.earned_credits }}</text><text>累计获得 / 额度</text></view></view>
      <view class="service-card">
        <text class="service-section-title">三步，一起创作</text>
        <view v-for="(step,index) in STEPS" :key="step.title" class="invite-step"><text class="invite-step__number">0{{ index + 1 }}</text><view><text>{{ step.title }}</text><text>{{ step.desc }}</text></view></view>
        <text class="service-note">仅限新用户注册时填写一次。奖励自动进入双方永久额度，可在消耗记录中查看。实际奖励以注册成功时的规则为准。</text>
      </view>
    </template>
  </AccountServiceShell>
</template>
<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import AccountServiceShell from '@/components/AccountServiceShell.vue'
import AppIcon from '@/components/AppIcon.vue'
import ServiceButton from '@/components/ServiceButton.vue'
import { requireLogin } from '@/utils/navigation'
import { copyText } from '@/utils/clipboard'
import api from '@/api'

/** 只展示服务端发放规则，不在前端计算或写入邀请奖励。 */
const invitation = ref(null), loading = ref(false), error = ref('')
const STEPS = [{ title: '复制你的邀请码', desc: '把专属邀请码发给想邀请的朋友。' }, { title: '好友注册时填写', desc: '账号密码注册和首次验证码登录均可填写。' }, { title: '双方额度自动到账', desc: '好友成功注册后，你们一起获得创作额度。' }]
/** 每次返回页面刷新累计实际奖励；失败保留已有邀请码以便继续分享。 */
async function loadInvitation() {
  if (!requireLogin() || loading.value) return
  loading.value = true
  error.value = ''
  try {
    const res = await api.account.invitation.post({}, { suppressGlobalError: true })
    if (res?.code !== 1) throw new Error(res?.message || '获取邀请码失败')
    invitation.value = res.data
  } catch (err) { error.value = err?.message || '获取邀请码失败，请重试' }
  finally { loading.value = false }
}
/** 使用已有跨端剪贴板能力分享，复制失败提供明确反馈。 */
async function copyCode() {
  if (!invitation.value?.code) return
  const success = await copyText(invitation.value.code)
  uni.showToast({ title: success ? '邀请码已复制，发给好友吧' : '复制失败，请长按邀请码复制', icon: 'none' })
}
onShow(loadInvitation)
</script>
<style lang="scss" scoped>
@import '@/styles/account-services.scss';
.invite-card { text-align: center; padding: 28px 20px 20px; }
.invite-seal { display: flex; align-items: center; justify-content: center; width: 60px; height: 60px; margin: 0 auto 20px; border-radius: 20px; background: var(--brand-primary-light); }
.invite-card__label { display: block; font-size: 12px; color: var(--ink-500); }
.invite-code { display: block; margin: 14px 0 18px; font: 700 32px/1.4 var(--font-serif); letter-spacing: 0.1em; color: var(--ink-900); }
.invite-reward { display: block; color: var(--ink-700); font-size: 13px; line-height: 1.8; margin-bottom: 24px; }
.invite-reward text { color: var(--brand-primary); font-weight: 700; }
.invite-stats { display: flex; margin: 28px 0; }
.invite-stats > view { flex: 1; display: flex; align-items: center; flex-direction: column; gap: 8px; }
.invite-stats > view + view { box-shadow: -1px 0 0 var(--line-1); }
.invite-stats text:first-child { font: 700 30px var(--font-serif); color: var(--ink-900); }
.invite-stats text:last-child { color: var(--ink-500); font-size: 11px; }
.invite-step { display: flex; gap: 14px; margin: 22px 0; }
.invite-step__number { color: var(--brand-primary); font: 22px var(--font-serif); }
.invite-step > view { display: flex; flex: 1; flex-direction: column; gap: 5px; font-size: 14px; color: var(--ink-900); }
.invite-step > view text:last-child { color: var(--ink-500); font-size: 12px; line-height: 1.7; }
</style>
