<template>
  <AccountServiceShell title="账号设置" heading="让大家认识你" subtitle="完善个人资料，也照顾好账号的安全。">
    <text v-if="loadError" class="service-error" role="alert">{{ loadError }}</text>
    <ServiceButton v-if="loadError" text="重新加载资料" secondary @click="loadProfile" />
    <view v-if="fetching" class="service-status">正在读取账号资料…</view>
    <template v-else-if="ready">
      <view class="service-card">
        <button class="settings-avatar" role="button" tabindex="0" aria-label="更换头像" :disabled="uploading || saving" @click="chooseAvatar" @keydown.enter.prevent="chooseAvatar" @keydown.space.prevent="chooseAvatar">
          <image v-if="form.avatar && !avatarFailed" :src="form.avatar" mode="aspectFill" class="settings-avatar__image" alt="当前头像" @error="avatarFailed = true" />
          <text v-else class="settings-avatar__fallback">{{ form.nickname.slice(0,1) || '溪' }}</text>
          <view class="settings-avatar__text"><text>{{ uploading ? '正在上传头像…' : '更换头像' }}</text><text>选择一张你喜欢的照片</text></view>
          <AppIcon name="edit" :size="18" />
        </button>
        <view class="service-field"><text class="service-label">昵称</text><AppField v-model="form.nickname" class="app-field" aria-label="昵称" maxlength="30" placeholder="请输入昵称" /></view>
        <view class="service-field"><text class="service-label">用户名</text><AppField v-model="form.account" class="app-field" aria-label="用户名" maxlength="20" placeholder="6–20 位字母、数字或 . _ @ -" /><text class="service-note">用于密码登录。修改用户名后需重新登录。</text></view>
        <text v-if="phone" class="service-note">已绑定手机号：{{ phone }}（更改用户名后仍可验证码登录）</text>
        <text v-if="profileError" class="service-error" role="alert">{{ profileError }}</text>
        <ServiceButton text="保存个人资料" loading-text="正在保存…" :loading="saving" :disabled="uploading" @click="saveProfile" />
      </view>
      <view class="service-card">
        <text class="service-section-title">{{ hasPassword ? '修改密码' : '设置登录密码' }}</text>
        <view v-if="hasPassword" class="service-field"><text class="service-label">当前密码</text><AppField v-model="passwordForm.old" class="app-field" aria-label="当前密码" password maxlength="32" placeholder="请输入当前密码" /></view>
        <view class="service-field"><text class="service-label">新密码</text><AppField v-model="passwordForm.next" class="app-field" aria-label="新密码" password maxlength="32" placeholder="请输入 6–32 位新密码" /></view>
        <view class="service-field"><text class="service-label">确认新密码</text><AppField v-model="passwordForm.confirm" class="app-field" aria-label="确认新密码" password maxlength="32" placeholder="请再次输入新密码" /></view>
        <text v-if="passwordError" class="service-error" role="alert">{{ passwordError }}</text>
        <ServiceButton :text="hasPassword ? '确认修改密码' : '设置密码'" loading-text="正在保存…" :loading="changingPassword" :disabled="saving" secondary @click="savePassword" />
      </view>
    </template>
  </AccountServiceShell>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import AccountServiceShell from '@/components/AccountServiceShell.vue'
import AppField from '@/components/AppField.vue'
import ServiceButton from '@/components/ServiceButton.vue'
import AppIcon from '@/components/AppIcon.vue'
import api from '@/api'
import { useUserStore } from '@/store/modules/user'
import { requireLogin, goReplace, toLoginPath } from '@/utils/navigation'
import { validateAccount, validatePassword } from '@/utils/account'
import { uploadMedia } from '@/utils/upload'

/** 资料、密码各自维护提交锁，读到真实资料前禁止写入。 */
const userStore = useUserStore()
const form = reactive({ nickname: '', account: '', avatar: '' })
const passwordForm = reactive({ old: '', next: '', confirm: '' })
const phone = ref(''), hasPassword = ref(false), avatarFailed = ref(false)
const ready = ref(false), fetching = ref(false), uploading = ref(false), saving = ref(false), changingPassword = ref(false)
const loadError = ref(''), profileError = ref(''), passwordError = ref('')

/** 首次打开加载资料，返回相册时保留正在编辑的表单。 */
async function loadProfile() {
  if (!requireLogin() || fetching.value || ready.value) return
  fetching.value = true
  loadError.value = ''
  try {
    const res = await api.account.info.post({}, { suppressGlobalError: true })
    if (res?.code !== 1) throw new Error(res?.message || '读取资料失败')
    Object.assign(form, { nickname: res.data.nickname || '', account: res.data.account || '', avatar: res.data.avatar || '' })
    phone.value = res.data.phone || ''
    hasPassword.value = Boolean(res.data.has_password)
    userStore.setUserInfo(res.data)
    ready.value = true
  } catch (err) { loadError.value = err?.message || '读取资料失败，请重试' }
  finally { fetching.value = false }
}
onShow(loadProfile)

/** 只选择一张图片，取消不提示；上传成功后再进入待保存资料。 */
function chooseAvatar() {
  if (uploading.value || saving.value) return
  uni.chooseImage({ count: 1, sizeType: ['compressed'], success: async (result) => {
    uploading.value = true
    profileError.value = ''
    try {
      const file = result.tempFiles?.[0]
      const uploaded = await uploadMedia(result.tempFilePaths[0], { file: file?.file || file, filename: file?.name })
      form.avatar = uploaded.url
      avatarFailed.value = false
    } catch (err) { profileError.value = err?.message || '头像上传失败，请重试' }
    finally { uploading.value = false }
  }, fail: (err) => { if (!/cancel/i.test(err?.errMsg || '')) profileError.value = '无法打开相册，请检查权限后重试' } })
}

/** 修改登录凭据后清理本地会话，回到登录页并带上设置页回跳地址。 */
function reauthenticate(message) {
  userStore.logout()
  uni.showToast({ title: message, icon: 'none' })
  goReplace(toLoginPath('/pages/account-settings/index'))
}

/** 保存昵称、用户名和已上传头像，用户名变更遵循后端重新鉴权指示。 */
async function saveProfile() {
  if (saving.value || uploading.value || changingPassword.value) return
  profileError.value = validateAccount(form.account) || (!form.nickname.trim() ? '请输入昵称' : '')
  if (profileError.value) return
  saving.value = true
  try {
    const res = await api.account.update.post({ account: form.account.trim(), nickname: form.nickname.trim(), avatar: form.avatar }, { suppressGlobalError: true })
    if (res?.code !== 1) throw new Error(res?.message || '保存失败，请重试')
    if (res.data.reauth_required) { reauthenticate('用户名已更新，请重新登录'); return }
    userStore.setUserInfo(res.data)
    uni.showToast({ title: '个人资料已保存', icon: 'success' })
  } catch (err) { profileError.value = err?.message || '保存失败，请重试' }
  finally { saving.value = false }
}

/** 已有密码必须提交原密码；验证码注册用户首次设置不走修改接口。 */
async function savePassword() {
  if (changingPassword.value || saving.value) return
  passwordError.value = (hasPassword.value && !passwordForm.old ? '请输入当前密码' : '') || validatePassword(passwordForm.next)
  if (!passwordError.value && passwordForm.next !== passwordForm.confirm) passwordError.value = '两次输入的新密码不一致'
  if (passwordError.value) return
  changingPassword.value = true
  try {
    const res = hasPassword.value
      ? await api.account.changePassword.post({ old_password: passwordForm.old, new_password: passwordForm.next }, { suppressGlobalError: true })
      : await api.account.setPassword.post({ password: passwordForm.next }, { suppressGlobalError: true })
    if (res?.code !== 1) throw new Error(res?.message || '密码保存失败')
    if (hasPassword.value) { reauthenticate('密码已修改，请重新登录'); return }
    hasPassword.value = true
    userStore.setUserInfo({ ...userStore.userInfo, has_password: true })
    Object.assign(passwordForm, { old: '', next: '', confirm: '' })
    uni.showToast({ title: '登录密码已设置', icon: 'success' })
  } catch (err) { passwordError.value = err?.message || '密码保存失败，请重试' }
  finally { changingPassword.value = false }
}
</script>

<style lang="scss" scoped>
@import '@/styles/account-services.scss';
.settings-avatar { display: flex; align-items: center; gap: 14px; width: 100%; margin: 0 0 26px; padding: 0; background: transparent; text-align: left; line-height: 1.6; }
.settings-avatar::after { border: none; }
.settings-avatar__image, .settings-avatar__fallback { width: 58px; height: 58px; flex-shrink: 0; border-radius: 20px; }
.settings-avatar__fallback { display: flex; align-items: center; justify-content: center; background: var(--paper-100); color: var(--brand-primary); font: 700 26px var(--font-serif); }
.settings-avatar__text { display: flex; flex-direction: column; flex: 1; gap: 4px; font-size: 14px; color: var(--ink-900); }
.settings-avatar__text text:last-child { font-size: 11px; color: var(--ink-500); }
</style>
