<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import api from '@/api'

const router = useRouter()
const userStore = useUserStore()

const saving = ref(false)
const editVisible = ref(false)
const editForm = reactive({ nickname: '', avatar: '' })
const credit = ref(null)
const signData = ref(null)
const signing = ref(false)

const menus = [
  { key: 'works', label: '我的作品', desc: '查看与管理已生成的视频', path: '/works' },
  { key: 'balance', label: '账户余额', desc: '额度明细与充值', path: '/balance' },
  { key: 'orders', label: '我的订单', desc: '支付订单与退款记录', path: '/orders' },
  { key: 'support', label: '联系客服', desc: '在线客服与常见问题', path: '/support' },
  { key: 'setting', label: '设置', desc: '通知、缓存与协议', path: '/settings' },
]

const balanceText = computed(() => credit.value === null ? '查看额度' : `剩余 ${credit.value.total} 次`)

async function onLogout() {
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

function openEdit() {
  editForm.nickname = userStore.userInfo?.nickname || ''
  editForm.avatar = userStore.userInfo?.avatar || ''
  editVisible.value = true
}

async function saveProfile() {
  saving.value = true
  try {
    const res = await api.account.update.post({
      nickname: editForm.nickname,
      avatar: editForm.avatar
    })
    if (res.code === 1) {
      userStore.setUserInfo(res.data)
      window.$message?.success('保存成功')
      editVisible.value = false
    }
  } catch (e) { /* 拦截器已提示 */ }
  saving.value = false
}

async function loadCredits() {
  if (!userStore.isLoggedIn) { credit.value = null; userStore.setCreditTotal(null); return }
  try {
    const res = await api.account.credits.post()
    if (res.code === 1) {
      credit.value = res.data
      userStore.setCreditTotal(res.data.total)
    }
  } catch (e) { credit.value = null }
}

async function loadSign() {
  if (!userStore.isLoggedIn) { signData.value = null; return }
  try {
    const res = await api.account.signStatus.post()
    if (res.code === 1) signData.value = res.data
  } catch (e) { signData.value = null }
}

async function doSign() {
  if (!userStore.isLoggedIn) { userStore.openLogin(); return }
  if (signData.value?.signed || signing.value) return
  signing.value = true
  try {
    const res = await api.account.sign.post()
    if (res.code === 1) {
      signData.value = { ...(signData.value || {}), signed: true, streak: res.data.streak, credits: res.data.credits }
      window.$message?.success(res.message || '签到成功')
      loadCredits()
    }
  } catch (e) { /* 拦截器已提示 */ }
  signing.value = false
}

function go(path) {
  if (!userStore.isLoggedIn) { userStore.openLogin(); return }
  router.push(path)
}

// 未登录先弹登录框,登录成功后再加载(避免关掉弹窗后停留空数据)
watch(() => userStore.isLoggedIn, (val) => {
  if (val) { loadCredits(); loadSign() }
}, { immediate: true })

onMounted(() => {
  if (!userStore.isLoggedIn) userStore.openLogin()
})
</script>

<template>
  <div class="me-page">
    <div class="wrap">
      <!-- 用户概览 -->
      <aside class="col-side">
        <div class="profile card">
          <div class="av">{{ (userStore.userInfo?.nickname || '用').slice(0, 1) }}</div>
          <div class="uinfo">
            <div class="uname">{{ userStore.userInfo?.nickname || '未登录' }}</div>
            <div class="uacct">{{ userStore.userInfo?.account || '登录后体验完整功能' }}</div>
          </div>
          <button class="edit-btn" @click="openEdit">编辑资料</button>
        </div>

        <div class="credit card" @click="go('/balance')">
          <div class="c-label">账户余额</div>
          <div class="c-num">{{ credit === null ? '--' : credit.total }}<small>次</small></div>
          <div class="c-sub" v-if="credit">
            免费 {{ credit.free_credits }} · 付费 {{ credit.credits }} · 今日已用 {{ credit.today_used }}
          </div>
          <div class="c-sub" v-else>登录后查看额度明细</div>
          <div class="c-btn">去充值</div>
        </div>

        <div class="signin card" :class="{ done: signData?.signed }" @click="doSign">
          <div class="s-left">
            <div class="s-title">每日签到</div>
            <div class="s-sub" v-if="signData">
              <template v-if="signData.signed">今日已签 · 连续 {{ signData.streak }} 天</template>
              <template v-else>签到得 {{ signData.daily_credits }} 次额度</template>
            </div>
            <div class="s-sub" v-else>登录后领取每日额度</div>
          </div>
          <div class="s-btn" :class="{ done: signData?.signed }">
            {{ signData?.signed ? '已签到' : (signing ? '签到中' : '签到') }}
          </div>
        </div>
      </aside>

      <!-- 菜单 -->
      <section class="col-main">
        <div class="menus card">
          <div v-for="(m, i) in menus" :key="m.key" class="menu" :class="{ 'no-border': i === menus.length - 1 }" @click="go(m.path)">
            <div class="m-left">
              <span class="m-name">{{ m.label }}</span>
              <span class="m-desc">{{ m.desc }}</span>
            </div>
            <span class="menu-right">
              <template v-if="m.key === 'balance'">{{ balanceText }}</template>
              <svg width="18" height="18" viewBox="0 0 20 20"><path d="M7.5 4L13.5 10L7.5 16" fill="none" stroke="#C9CCD1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </span>
          </div>
        </div>
        <button class="logout" @click="onLogout">退出登录</button>
      </section>
    </div>

    <!-- 编辑资料 -->
    <n-modal v-model:show="editVisible" title="编辑资料" preset="dialog" style="max-width: 380px">
      <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 8px">
        <n-input v-model:value="editForm.nickname" placeholder="昵称" maxlength="20" />
        <n-input v-model:value="editForm.avatar" placeholder="头像 URL" />
      </div>
      <template #action>
        <n-button @click="editVisible = false">取消</n-button>
        <n-button type="primary" :loading="saving" @click="saveProfile">保存</n-button>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.me-page { min-height: calc(100vh - var(--header-h)); background: var(--bg); padding-bottom: 80px; }
.wrap {
  max-width: 560px;
  margin: 0 auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card { background: #fff; border-radius: var(--radius); box-shadow: var(--shadow-sm); }
.col-side, .col-main { display: flex; flex-direction: column; gap: 16px; min-width: 0; }

.profile { padding: 20px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.av {
  width: 56px; height: 56px; border-radius: 50%;
  background: linear-gradient(135deg, #FFD0BC, #FF8A3D);
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; color: #fff; font-weight: 700;
  flex-shrink: 0;
}
.uinfo { flex: 1; min-width: 0; }
.uname { font-size: 17px; font-weight: 700; }
.uacct { font-size: 12px; color: var(--weak); margin-top: 4px; }
.edit-btn {
  height: 32px; padding: 0 14px; border-radius: 16px;
  border: 1px solid var(--line); background: #fff;
  color: var(--body-c); font-size: 13px; cursor: pointer;
}
.edit-btn:hover { color: var(--brand); border-color: var(--brand); }

.credit {
  padding: 20px;
  background: linear-gradient(135deg, #FF6A3D, #FF4D1C);
  color: #fff;
  cursor: pointer;
}
.c-label { font-size: 13px; opacity: .85; }
.c-num { font-size: 34px; font-weight: 700; margin-top: 4px; line-height: 1.1; }
.c-num small { font-size: 14px; font-weight: 400; margin-left: 4px; }
.c-sub { font-size: 12px; opacity: .88; margin-top: 6px; }
.c-btn {
  display: inline-block;
  margin-top: 14px;
  padding: 0 18px;
  height: 32px;
  line-height: 32px;
  border-radius: 16px;
  background: rgba(255, 255, 255, .22);
  font-size: 13px;
  font-weight: 600;
}

.signin {
  padding: 18px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: linear-gradient(135deg, #FFF4E6, #FFE2C2);
  cursor: pointer;
}
.signin.done { background: #F4F5F7; cursor: default; }
.s-title { font-size: 15px; font-weight: 700; color: #6B3B12; }
.signin.done .s-title { color: var(--weak); }
.s-sub { font-size: 12px; color: #9A6B3A; margin-top: 4px; }
.signin.done .s-sub { color: var(--weak); }
.s-btn {
  flex-shrink: 0;
  height: 34px;
  padding: 0 18px;
  border-radius: 17px;
  background: linear-gradient(135deg, #FF8A3D, #FF4D1C);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
}
.s-btn.done { background: #D8DADF; color: #fff; }

.menus { padding: 4px 0; }
.menu {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 14px 16px; cursor: pointer;
  transition: background .15s;
}
.menu:hover { background: #FAFAFB; }
.menu + .menu { border-top: 1px solid var(--line); }
.m-left { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.m-name { font-size: 15px; }
.m-desc { font-size: 12px; color: var(--weak); }
.menu-right { display: flex; align-items: center; gap: 6px; color: var(--weak); font-size: 13px; flex-shrink: 0; }
.logout {
  height: 46px; border-radius: 23px; background: #fff; border: 1px solid var(--line);
  display: flex; align-items: center; justify-content: center;
  color: var(--brand); font-weight: 600; font-size: 15px;
  cursor: pointer;
}
.logout:hover { border-color: var(--brand); }

@media (min-width: 900px) {
  .wrap {
    max-width: var(--page-max);
    padding: 24px;
    display: grid;
    grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
    gap: 20px;
    align-items: start;
  }
}
</style>
