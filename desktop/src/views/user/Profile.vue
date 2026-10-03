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
      try { await api.account.logout.post() } catch (e) { }
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
  } catch (e) { }
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
  } catch (e) { }
  signing.value = false
}

function go(path) {
  if (!userStore.isLoggedIn) { userStore.openLogin(); return }
  router.push(path)
}

watch(() => userStore.isLoggedIn, (val) => {
  if (val) { loadCredits(); loadSign() }
}, { immediate: true })

onMounted(() => {
  if (!userStore.isLoggedIn) userStore.openLogin()
})
</script>

<template>
  <div class="me-page">
    <div class="page-wrap">
      <!-- 用户概览 -->
      <aside class="col-side">
        <!-- 个人信息卡 -->
        <div class="profile card">
          <div class="av-wrap">
            <div class="av">{{ (userStore.userInfo?.nickname || '用').slice(0, 1) }}</div>
          </div>
          <div class="uinfo">
            <div class="uname">{{ userStore.userInfo?.nickname || '未登录' }}</div>
            <div class="uacct">{{ userStore.userInfo?.account || '登录后体验完整功能' }}</div>
          </div>
          <button class="edit-btn" @click="openEdit">
            <svg width="12" height="12" viewBox="0 0 12 12"><path d="M8.5 1.5L10.5 3.5L4.5 9.5H2.5V7.5L8.5 1.5Z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
            编辑资料
          </button>
        </div>

        <!-- 余额卡 -->
        <div class="credit" @click="go('/balance')">
          <div class="credit-bg"></div>
          <div class="credit-content">
            <div class="c-label">账户余额</div>
            <div class="c-num-wrap">
              <div class="c-num">{{ credit === null ? '--' : credit.total }}<small>次</small></div>
              <template v-if="credit">
                <div class="c-detail">
                  <span>免费 {{ credit.free_credits }}</span>
                  <span>·</span>
                  <span>付费 {{ credit.credits }}</span>
                </div>
              </template>
              <template v-else>
                <div class="c-detail muted">登录后查看额度明细</div>
              </template>
            </div>
            <div class="c-btn-row">
              <button class="c-btn">
                去充值
                <svg width="12" height="12" viewBox="0 0 12 12"><path d="M4 2H10V8M10 2L2 10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </button>
              <span class="c-today" v-if="credit">今日已用 {{ credit.today_used }}</span>
            </div>
          </div>
        </div>

        <!-- 签到卡 -->
        <div class="signin" :class="{ done: signData?.signed }" @click="doSign">
          <div class="s-left">
            <div class="s-title">
              <svg width="16" height="16" viewBox="0 0 24 24"><path d="M12 2l2.5 6.5L21 9l-5 4.5L17.5 21 12 17l-5.5 4L8 13.5 3 9l6.5-.5L12 2z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>
              每日签到
            </div>
            <div class="s-sub" v-if="signData">
              <template v-if="signData.signed">已连续签到 {{ signData.streak }} 天</template>
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
              <svg width="16" height="16" viewBox="0 0 20 20"><path d="M7.5 4L13.5 10L7.5 16" fill="none" stroke="#C9CCD1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </span>
          </div>
        </div>
        <button class="logout" @click="onLogout">
          <svg width="14" height="14" viewBox="0 0 14 14"><path d="M6 12H3V2H6M6 7H12M9 4L12 7L9 10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
          退出登录
        </button>
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
.me-page {
  min-height: calc(100vh - var(--header-h));
  background: var(--bg);
  padding-bottom: 80px;
}
.page-wrap {
  max-width: 560px;
  margin: 0 auto;
  padding: var(--s-4);
  display: flex;
  flex-direction: column;
  gap: var(--s-4);
}

.card {
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

/* 个人信息 */
.profile {
  padding: var(--s-5);
  display: flex;
  align-items: center;
  gap: var(--s-4);
  flex-wrap: wrap;
}
.av-wrap {
  position: relative;
  flex-shrink: 0;
}
.av {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: var(--grad-brand);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #fff;
  font-weight: 800;
  box-shadow: var(--shadow-brand);
}
.uinfo { flex: 1; min-width: 0; }
.uname {
  font-size: 18px;
  font-weight: 700;
  color: var(--ink);
}
.uacct {
  font-size: 12px;
  color: var(--weak);
  margin-top: 3px;
}
.edit-btn {
  height: 32px;
  padding: 0 14px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--line);
  background: #fff;
  color: var(--body-c);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all .18s;
}
.edit-btn:hover { color: var(--brand); border-color: var(--brand); background: var(--brand-bg); }

/* 余额卡 */
.credit {
  position: relative;
  padding: var(--s-5);
  background: var(--grad-brand);
  color: #fff;
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  transition: transform .2s, box-shadow .2s;
  box-shadow: var(--shadow-brand);
}
.credit:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-brand-lg);
}
.credit-bg {
  position: absolute;
  top: -40px;
  right: -40px;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: rgba(255, 255, 255, .08);
  pointer-events: none;
}
.credit-content {
  position: relative;
  z-index: 1;
}
.c-label {
  font-size: 12px;
  opacity: .85;
  font-weight: 500;
}
.c-num {
  font-size: 38px;
  font-weight: 800;
  margin-top: 4px;
  line-height: 1;
  letter-spacing: -1px;
}
.c-num small {
  font-size: 14px;
  font-weight: 400;
  margin-left: 4px;
  opacity: .8;
}
.c-detail {
  font-size: 12px;
  opacity: .85;
  margin-top: 8px;
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.c-detail.muted { opacity: .7; }
.c-btn-row {
  margin-top: var(--s-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
}
.c-btn {
  height: 34px;
  padding: 0 16px;
  border: none;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, .22);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  backdrop-filter: blur(4px);
  transition: background .18s;
}
.c-btn:hover { background: rgba(255, 255, 255, .3); }
.c-today {
  font-size: 11px;
  opacity: .7;
}

/* 签到 */
.signin {
  padding: var(--s-4) var(--s-5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
  background: var(--grad-warm);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: transform .18s;
}
.signin:active { transform: scale(.99); }
.signin.done { background: #fff; box-shadow: var(--shadow-sm); cursor: default; }
.s-left { display: flex; flex-direction: column; gap: 3px; }
.s-title {
  font-size: 15px;
  font-weight: 700;
  color: #6B3B12;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.signin.done .s-title { color: var(--weak); }
.s-sub { font-size: 12px; color: #9A6B3A; }
.signin.done .s-sub { color: var(--weak); }
.s-btn {
  flex-shrink: 0;
  height: 36px;
  padding: 0 18px;
  border-radius: var(--radius-pill);
  background: var(--grad-brand);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  box-shadow: var(--shadow-brand);
}
.s-btn.done {
  background: #D8DADF;
  box-shadow: none;
}

/* 菜单 */
.menus {
  padding: 4px 0;
  overflow: hidden;
}
.menu {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
  padding: var(--s-4) var(--s-5);
  cursor: pointer;
  transition: background .15s;
}
.menu:hover { background: var(--bg); }
.menu + .menu { border-top: 1px solid var(--line-2); }
.m-left { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.m-name { font-size: 15px; font-weight: 500; color: var(--ink); }
.m-desc { font-size: 12px; color: var(--weak); }
.menu-right {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--weak);
  font-size: 13px;
  flex-shrink: 0;
}

.logout {
  height: 46px;
  border-radius: var(--radius-pill);
  background: #fff;
  border: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--brand);
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all .18s;
}
.logout:hover {
  border-color: var(--brand);
  background: var(--brand-bg);
}

@media (min-width: 900px) {
  .page-wrap {
    max-width: var(--page-max);
    padding: var(--s-6);
    display: grid;
    grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
    gap: var(--s-5);
    align-items: start;
  }
}
</style>
