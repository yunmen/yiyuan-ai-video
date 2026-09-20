<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import api from '@/api'

const router = useRouter()
const userStore = useUserStore()

// 验证码注册的用户尚未设置密码,文案区分「设置密码 / 修改密码」
const hasPassword = computed(() => userStore.userInfo?.has_password !== false)

// 通知开关(本地存储,无需后端)
const LS_NOTIFY = 'yy_notify'
const notify = reactive(JSON.parse(localStorage.getItem(LS_NOTIFY) || '{"gen":true,"promo":true,"sys":false}'))

function toggleNotify(key) {
  notify[key] = !notify[key]
  localStorage.setItem(LS_NOTIFY, JSON.stringify(notify))
  window.$message?.success(`${labelOf(key)}已${notify[key] ? '开启' : '关闭'}`)
}

function labelOf(key) {
  return { gen: '生成完成通知', promo: '活动优惠通知', sys: '系统公告' }[key]
}

// 协议弹窗
const doc = ref(null) // 'agreement' | 'privacy' | null
const docs = {
  agreement: {
    title: '用户协议',
    body: '欢迎使用一源 AI 视频。使用本服务即表示你同意：1）你上传的素材拥有合法使用权；2）生成的内容仅用于正当营销用途；3）不得用于违法违规场景；4）服务按"现状"提供，AI 生成结果可能存在偏差。'
  },
  privacy: {
    title: '隐私政策',
    body: '我们仅收集为提供服务所必需的信息：1）手机号用于登录验证；2）你上传的图片/视频仅用于本次生成，处理完成后自动删除；3）所有数据传输均加密；4）你可在设置中随时清除本地缓存。'
  }
}

function clearCache() {
  window.$dialog?.warning({
    title: '清除缓存',
    content: '将清除本地缓存数据(不影响云端作品)，确定继续吗？',
    positiveText: '清除',
    negativeText: '取消',
    onPositiveClick: () => {
      localStorage.removeItem('yy_notify')
      sessionStorage.clear()
      window.$message?.success('缓存已清除')
    }
  })
}

function checkUpdate() {
  window.$message?.info('已是最新版本 V1.0')
}

function onLogout() {
  window.$dialog?.warning({
    title: '退出登录',
    content: '确定退出当前账号吗？',
    positiveText: '退出',
    negativeText: '取消',
    onPositiveClick: async () => {
      try { await api.account.logout.post() } catch (e) { /* 忽略 */ }
      userStore.logout()
      window.$message?.success('已退出登录')
      router.push('/home')
    }
  })
}
</script>

<template>
  <div class="settings-page">
    <div class="wrap">
      <!-- 账号 -->
      <div class="g-title">账号</div>
      <div class="g-card">
        <div class="set-item" @click="router.push('/change-password')">
          {{ hasPassword ? '修改密码' : '设置密码' }}
          <svg width="20" height="20" viewBox="0 0 20 20"><path d="M7.5 4L13.5 10L7.5 16" fill="none" stroke="#C9CCD1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
      </div>

      <!-- 通知 -->
      <div class="g-title">通知</div>
      <div class="g-card">
        <div class="set-item">
          生成完成通知
          <n-switch :value="notify.gen" @update:value="toggleNotify('gen')" />
        </div>
        <div class="set-item">
          活动优惠通知
          <n-switch :value="notify.promo" @update:value="toggleNotify('promo')" />
        </div>
        <div class="set-item">
          系统公告
          <n-switch :value="notify.sys" @update:value="toggleNotify('sys')" />
        </div>
      </div>

      <!-- 通用 -->
      <div class="g-title">通用</div>
      <div class="g-card">
        <div class="set-item" @click="clearCache">
          清除缓存
          <svg width="20" height="20" viewBox="0 0 20 20"><path d="M7.5 4L13.5 10L7.5 16" fill="none" stroke="#C9CCD1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div class="set-item" @click="checkUpdate">
          检查更新
          <span class="s-sub">V1.0
            <svg width="20" height="20" viewBox="0 0 20 20"><path d="M7.5 4L13.5 10L7.5 16" fill="none" stroke="#C9CCD1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>
      </div>

      <!-- 协议 -->
      <div class="g-title">协议</div>
      <div class="g-card">
        <div class="set-item" @click="doc = 'agreement'">
          用户协议
          <svg width="20" height="20" viewBox="0 0 20 20"><path d="M7.5 4L13.5 10L7.5 16" fill="none" stroke="#C9CCD1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div class="set-item" @click="doc = 'privacy'">
          隐私政策
          <svg width="20" height="20" viewBox="0 0 20 20"><path d="M7.5 4L13.5 10L7.5 16" fill="none" stroke="#C9CCD1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
      </div>

      <button class="logout-btn" @click="onLogout">退出登录</button>
      <div class="version">一源 AI 视频 V1.0</div>
    </div>

    <!-- 协议弹窗 -->
    <n-modal v-model:show="doc" preset="dialog" :title="doc ? docs[doc].title : ''" style="max-width: 420px" :on-after-leave="() => doc = null">
      <p v-if="doc" style="margin:0; line-height:1.8; font-size:13px; color:var(--body-c)">{{ docs[doc].body }}</p>
      <template #action>
        <n-button type="primary" @click="doc = null">我知道了</n-button>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.settings-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); padding-bottom: 80px; }
.wrap { max-width: 560px; margin: 0 auto; padding: 20px; display: flex; flex-direction: column; }

.g-title { font-size: 13px; color: var(--weak); margin: 16px 4px 8px; }
.g-card { background: #fff; border-radius: var(--radius); box-shadow: var(--shadow-sm); overflow: hidden; }
.set-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px; height: 52px; font-size: 15px; cursor: pointer;
  transition: background .15s;
}
.set-item:hover { background: #FAFAFB; }
.set-item + .set-item { border-top: 1px solid var(--line); }
.s-sub { display: flex; align-items: center; gap: 6px; color: var(--weak); font-size: 13px; }

.logout-btn {
  height: 48px; border-radius: 24px; background: #fff; border: 1px solid var(--line);
  color: var(--brand); font-weight: 600; font-size: 15px;
  cursor: pointer; margin-top: 24px;
}
.logout-btn:hover { border-color: var(--brand); }
.version { text-align: center; font-size: 12px; color: var(--weak); margin-top: 16px; }

@media (min-width: 768px) {
  .wrap { max-width: 720px; padding: 24px; }
}
</style>
