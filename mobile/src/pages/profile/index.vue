<template>
  <view class="app-page profile">
    <AppNavBar title="个人中心" :auto-back="false" />

    <view class="profile__body">
      <view class="profile__identity">
        <view class="profile__avatar" :class="{ 'profile__avatar--logged': isLoggedIn }">
          <image
            v-if="avatarUrl && !avatarFailed"
            class="profile__avatar-image"
            alt="个人头像"
            :src="avatarUrl"
            mode="aspectFill"
            @error="avatarFailed = true"
          />
          <text v-else>{{ avatarChar }}</text>
        </view>
        <view class="profile__identity-main">
          <text class="profile__name">{{ displayName }}</text>
          <text class="profile__account">{{ accountText }}</text>
        </view>
        <view
          v-if="!isLoggedIn"
          class="profile__login"
          role="button"
          aria-label="立即登录"
          @click="goLogin"
         tabindex="0" @keydown.enter.stop.prevent="goLogin" @keydown.space.stop.prevent="goLogin">
          <text>立即登录</text>
          <AppIcon name="chevron-right" :size="16" color="#B23A2E" />
        </view>
      </view>

      <view v-if="isLoggedIn" class="profile__credit-card">
        <view class="profile__credit-head">
          <view class="profile__credit-label">
            <AppIcon name="coins" :size="16" color="#B23A2E" :stroke-width="2.2" />
            <text>剩余额度</text>
          </view>
          <text class="profile__credit-link" role="button" @click="goRecharge" tabindex="0" @keydown.enter.stop.prevent="goRecharge" @keydown.space.stop.prevent="goRecharge">充值</text>
        </view>
        <view class="profile__credit-value">
          <text>{{ creditText }}</text>
          <text class="profile__credit-unit">额度</text>
        </view>
        <text class="profile__credit-note">用于视频复刻、数字人口播和文案生成</text>
      </view>

      <view v-else class="profile__welcome">
        <view class="profile__welcome-icon">
          <AppIcon name="user" :size="22" color="#B23A2E" :stroke-width="2" />
        </view>
        <view class="profile__welcome-main">
          <text class="profile__welcome-title">登录后管理你的创作</text>
          <text class="profile__welcome-desc">作品、额度和数字人形象都会同步保存</text>
        </view>
      </view>

      <view class="profile__section">
        <text class="profile__section-title">常用服务</text>
        <view class="profile__menu">
          <button v-for="item in SERVICE_OPTIONS" :key="item.path" class="profile__menu-item profile__service" role="button" tabindex="0" @click="openService(item.path)" @keydown.enter.prevent="openService(item.path)" @keydown.space.prevent="openService(item.path)">
            <view class="profile__menu-icon" :class="`profile__menu-icon--${item.tone}`"><AppIcon :name="item.icon" :size="19" :color="item.color" /></view>
            <view class="profile__menu-main"><text>{{ item.title }}</text><text>{{ item.desc }}</text></view>
            <AppIcon name="chevron-right" :size="18" color="#B7AB92" />
          </button>
          <view class="profile__menu-item" role="button" @click="goDigital" tabindex="0" @keydown.enter.stop.prevent="goDigital" @keydown.space.stop.prevent="goDigital">
            <view class="profile__menu-icon profile__menu-icon--green"><AppIcon name="user" :size="19" color="#4B7A5A" /></view>
            <view class="profile__menu-main"><text>数字人形象</text><text>管理平台形象和我的形象</text></view>
            <AppIcon name="chevron-right" :size="18" color="#B7AB92" />
          </view>
          <view v-if="isLoggedIn" class="profile__menu-item" role="button" @click="handleLogout" tabindex="0" @keydown.enter.stop.prevent="handleLogout" @keydown.space.stop.prevent="handleLogout">
            <view class="profile__menu-icon profile__menu-icon--gray"><AppIcon name="log-out" :size="19" color="#6B6357" /></view>
            <view class="profile__menu-main"><text>退出登录</text><text>退出当前千溪账号</text></view>
            <AppIcon name="chevron-right" :size="18" color="#B7AB92" />
          </view>
        </view>
      </view>

      <text class="profile__version">千溪 · AI 创作工具</text>
    </view>

    <AppTabBar active="profile" />
  </view>
</template>

<script setup>
import { showAppModal } from '@/utils/feedback'
import { computed, ref, watch } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useUserStore } from '@/store/modules/user'
import { refreshCurrentUserProfile } from '@/utils/session'
import { go, toLoginPath, currentPagePath } from '@/utils/navigation'
import api from '@/api'
import AppIcon from '@/components/AppIcon.vue'
import AppNavBar from '@/components/AppNavBar.vue'
import AppTabBar from '@/components/AppTabBar.vue'

/** 常用服务统一描述和导航，未登录时携带目标页回跳。 */
const SERVICE_OPTIONS = [
  { title: '账号设置', desc: '昵称、用户名、密码与头像', icon: 'settings', tone: 'gray', color: '#6B6357', path: '/pages/account-settings/index' },
  { title: '我的素材', desc: '找回上传过的图片与视频', icon: 'image', tone: 'green', color: '#4B7A5A', path: '/pages/materials/index' },
  { title: '邀请好友', desc: '分享邀请码，和好友一起获额度', icon: 'share', tone: 'amber', color: '#9A7138', path: '/pages/invitation/index' },
  { title: '消耗记录', desc: '查看生成扣款与失败退款', icon: 'clock', tone: 'red', color: '#B23A2E', path: '/pages/credit-logs/index' },
]

/** 已登录进入服务，否则登录后回到所选服务。 */
function openService(path) {
  go(userStore.isLoggedIn ? path : toLoginPath(path))
}

const userStore = useUserStore()
const isLoggedIn = computed(() => userStore.isLoggedIn)
const userInfo = computed(() => userStore.userInfo || {})
const displayName = computed(() => userInfo.value.nickname || userInfo.value.name || '千溪用户')
const accountText = computed(() => userInfo.value.phone || userInfo.value.account || (isLoggedIn.value ? '已登录' : '登录后同步作品'))
const avatarUrl = computed(() => userInfo.value.avatar || '')
const avatarFailed = ref(false)
const avatarChar = computed(() => displayName.value.slice(0, 1))

watch(avatarUrl, () => {
  avatarFailed.value = false
})
const creditText = computed(() => userStore.creditTotal === null ? '--' : String(userStore.creditTotal))

onShow(() => {
  if (userStore.token) refreshCurrentUserProfile(userStore)
})

function goLogin() {
  go(toLoginPath(currentPagePath()))
}

function goDigital() {
  go('/pages/digital/index')
}

function goRecharge() {
  go('/pages/recharge/index')
}

function handleLogout() {
  showAppModal({
    title: '退出登录',
    content: '退出后仍可重新登录查看作品，确定退出吗？',
    confirmColor: '#B23A2E',
    success: async ({ confirm }) => {
      if (!confirm) return
      try {
        await api.account.logout.post({}, { suppressGlobalError: true })
      } catch (err) {
        console.error('退出登录请求失败', err)
      } finally {
        userStore.logout()
        uni.showToast({ title: '已退出登录', icon: 'none' })
      }
    },
  })
}
</script>

<style lang="scss" scoped>
.profile__service { width: 100%; text-align: left; background: transparent; line-height: 1.5; border-radius: 0; margin: 0; color: inherit; font: inherit; }
.profile__service::after { border: none; }
.profile__service:focus-visible { outline: 2px solid var(--brand-primary); outline-offset: -3px; }
.profile {
  background: var(--bg-page);
}

.profile__body {
  padding: 14px var(--page-gutter) 28px;
}

.profile__identity {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 100px;
}

.profile__avatar {
  width: 64px;
  height: 64px;
  flex: 0 0 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 5px solid var(--paper-100);
  border-radius: 23px;
  background: var(--paper-card);
  color: var(--brand-primary);
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 700;
}

.profile__avatar--logged {
  background: var(--brand-primary-light);
  border-color: rgba(178, 58, 46, 0.28);
}

.profile__avatar-image {
  width: 100%;
  height: 100%;
  border-radius: 18px;
}

.profile__identity-main {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.profile__name {
  overflow: hidden;
  color: var(--ink-900);
  font-size: 24px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-serif);
}

.profile__account {
  overflow: hidden;
  color: var(--text-tertiary);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile__login {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  padding: 10px 12px;
  border: none;
  border-radius: var(--radius-full);
  color: var(--brand-primary);
  font-size: 13px;
  font-weight: 600;
  background: var(--brand-primary-light);
  min-height: 44px;
}

.profile__credit-card {
  margin-top: 24px;
  padding: 20px;
  border: 5px solid var(--paper-100);
  border-radius: 24px;
  background: var(--paper-card);
  color: var(--ink-900);
  box-shadow: var(--shadow-sm);
}

.profile__credit-head,
.profile__credit-label {
  display: flex;
  align-items: center;
}

.profile__credit-head {
  justify-content: space-between;
}

.profile__credit-label {
  gap: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.profile__credit-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 8px 14px;
  border: 1px solid rgba(178, 58, 46, 0.3);
  border-radius: var(--radius-full);
  color: var(--brand-primary);
  font-size: 12px;
}

.profile__credit-value {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 10px;
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
}

.profile__credit-unit {
  font-size: 12px;
  font-weight: 400;
  opacity: 0.82;
}

.profile__credit-note {
  display: block;
  margin-top: 9px;
  color: var(--text-tertiary);
  font-size: 11px;
}

.profile__welcome {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 24px;
  padding: 18px 12px;
  border: 5px solid var(--paper-100);
  border-radius: 24px;
  background: var(--paper-card);
  box-shadow: var(--shadow-sm);
}

.profile__welcome-icon,
.profile__menu-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  border-radius: 14px;
}

.profile__welcome-icon {
  width: 38px;
  height: 38px;
  border-radius: 14px;
  background: var(--brand-primary-light);
}

.profile__welcome-main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.profile__welcome-title {
  color: var(--ink-900);
  font-size: 14px;
  font-weight: 600;
}

.profile__welcome-desc {
  color: var(--text-tertiary);
  font-size: 11px;
}

.profile__section {
  margin-top: 22px;
}

.profile__section-title {
  display: block;
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.profile__menu {
  overflow: hidden;
  border: 5px solid var(--paper-100);
  border-radius: 24px;
  background: var(--paper-card);
  box-shadow: var(--shadow-sm);
}

.profile__menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 76px;
  padding: 14px;
  border-bottom: 1px solid var(--line-1);
}

.profile__menu-item:last-child {
  border-bottom: none;
}

.profile__menu-item:active {
  background: var(--paper-100);
}

.profile__menu-icon {
  width: 36px;
  height: 36px;
  border-radius: 5px;
}

.profile__menu-icon--red { background: var(--brand-primary-light); }
.profile__menu-icon--amber { background: #f5eee5; }
.profile__menu-icon--green { background: var(--state-success-light); }
.profile__menu-icon--gray { background: var(--paper-200); }

.profile__menu-main {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}

.profile__menu-main text:first-child {
  color: var(--ink-900);
  font-size: 14px;
  font-weight: 600;
}

.profile__menu-main text:last-child {
  overflow: hidden;
  color: var(--text-tertiary);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile__version {
  display: block;
  margin-top: 40px;
  color: var(--text-muted);
  font-size: 11px;
  text-align: center;
  letter-spacing: 2px;
}

@media screen and (max-width: 360px) {
  .profile__body {
    padding-left: 12px;
    padding-right: 12px;
  }

  .profile__name {
    font-size: 17px;
  }

  .profile__login {
    padding-left: 8px;
    padding-right: 8px;
    font-size: 12px;
  }
}
</style>
