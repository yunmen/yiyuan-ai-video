<template>
  <AccountServiceShell :title="selectionMode ? (selectionKind === 'image' ? '选择替换图片' : '选择视频素材') : '我的素材'" :heading="selectionMode ? (selectionKind === 'image' ? `选择${roleLabel(selectionRole)}参考图` : '从素材库选择对标视频') : '灵感，随时找回'" subtitle="图片与视频由系统识别；人物、场景、商品用途由你标记。">
    <view v-if="!selectionMode" class="service-filters"><button v-for="item in FILTERS" :key="item.key" class="service-filter" :class="{ 'service-filter--active': filter === item.key }" role="button" tabindex="0" :aria-pressed="filter === item.key" @click="selectFilter(item.key)" @keydown.enter.prevent="selectFilter(item.key)" @keydown.space.prevent="selectFilter(item.key)">{{ item.label }}</button></view>

    <text v-if="uploadMessage" class="service-note" role="status">{{ uploadMessage }}</text>
    <text v-if="uploadError" class="service-error" role="alert">{{ uploadError }}</text>
    <text class="service-note">共 {{ total }} 份素材 · 仅展示已确认上传成功的记录</text>
    <button class="material-sync" role="button" tabindex="0" :disabled="syncing" @click="recoverMaterials" @keydown.enter.prevent="recoverMaterials" @keydown.space.prevent="recoverMaterials">{{ syncing ? '正在找回历史素材…' : (syncCursor ? '继续找回历史素材' : '找回历史素材') }}</button>
    <text v-if="syncMessage" class="service-note" role="status">{{ syncMessage }}</text>
    <view class="material-grid">
      <button class="material material--add" aria-label="上传素材" :disabled="uploading || !!pendingMaterial" @click="uploadMaterial">
        <text class="material__plus" aria-hidden="true">＋</text>
        <text>{{ uploading ? `正在上传 ${uploadProgress}%` : '上传素材' }}</text>
        <text class="material__meta">{{ selectionMode ? (selectionKind === 'image' ? '上传后选择图片' : '选择视频文件') : '图片 / 视频' }}</text>
      </button>
      <button v-for="item in rows" :key="item.id" class="material" role="button" tabindex="0" :aria-label="`${selectionMode ? '选择' : '预览'}${item.filename}`" @click="preview(item)" @keydown.enter.prevent="preview(item)" @keydown.space.prevent="preview(item)">
        <view class="material__preview">
          <image v-if="item.kind === 'image' && !failedImages[item.id]" :src="item.url" mode="aspectFill" class="material__image" :alt="item.filename" @error="failedImages[item.id] = true" />
          <AppIcon v-else :name="item.kind === 'video' ? 'play' : 'image-off'" :size="30" color="#8A5A3B" />
          <text class="material__badge">{{ item.needs_confirmation ? '待标识 · 点击选择类型' : item.kind === 'video' ? '视频' : item.kind === 'image' ? '图片' : '待标识' }}</text>
        </view>
        <view class="material__info"><text class="material__name">{{ item.filename }}</text><text class="material__meta">{{ formatSize(item.size) }} · {{ item.create_time?.slice(0,10) }}</text><text role="button" tabindex="0" @click.stop="editRole(item)" @keydown.enter.stop.prevent="editRole(item)" @keydown.space.stop.prevent="editRole(item)">{{ roleLabel(item.role) }} · 标记用途</text></view>
      </button>
    </view>
    <text v-if="error" class="service-error" role="alert">{{ error }}</text>
    <ServiceButton v-if="error" text="重新加载" secondary @click="retry" />
    <view v-if="loading" class="service-status">正在整理你的素材…</view>
    <AppEmpty v-else-if="!rows.length && !error" icon="image" :title="selectionMode ? (selectionKind === 'image' ? '暂无已上传的图片' : '暂无已上传的视频') : '素材从第一次上传开始'" desc="点击加号上传，系统自动识别图片或视频；无法确定时再由你标识。" :action-text="selectionMode ? '返回创作' : '去创作'" @action="leaveEmptyLibrary" />
    <ServiceButton v-if="rows.length < total && !loading && !error" text="加载更多素材" secondary @click="loadMore" />
    <text v-if="rows.length && rows.length >= total" class="service-note material-end">已经看到全部素材了</text>
    <view v-if="pendingMaterial" class="material-overlay" role="dialog" aria-label="标识素材类型" aria-modal="true">
      <view class="material-dialog material-type">
        <text class="material-type__title">请标识素材类型</text>
        <text class="service-note">{{ pendingMaterial.filename }}</text>
        <text class="service-note">{{ pendingMaterial.classification_reason === 'conflict' ? '文件类型信息存在冲突，请确认实际类型。' : '系统无法确定类型，请选择图片或视频。' }}标识不会转换文件格式。</text>
        <ServiceButton text="标识为图片" :disabled="marking" @click="markMaterial('image')" />
        <ServiceButton text="标识为视频" secondary :disabled="marking" @click="markMaterial('video')" />
        <text v-if="marking" class="service-note" role="status">正在保存标识…</text>
        <text v-if="markError" class="service-error" role="alert">{{ markError }}</text>
        <ServiceButton text="稍后标识" secondary :disabled="marking" @click="pendingMaterial = null" />
      </view>
    </view>
    <view v-if="roleMaterial" class="material-overlay" role="dialog" aria-label="标记素材用途" aria-modal="true">
      <view class="material-dialog material-type">
        <text class="material-type__title">由你标记素材用途</text>
        <text class="service-note">{{ roleMaterial.filename }}</text>
        <text v-if="selectAfterRole" class="service-note">当前替换需要{{ roleLabel(selectionRole) }}参考图，请确认用途后选择。</text>
        <ServiceButton v-for="item in ROLES" :key="item.key" :text="`标记为${item.label}`" :disabled="roleSaving" @click="saveRole(item.key)" />
        <ServiceButton v-if="!selectAfterRole" text="清除用途标记" secondary :disabled="roleSaving" @click="saveRole(null)" />
        <text v-if="roleError" class="service-error" role="alert">{{ roleError }}</text>
        <ServiceButton text="取消" secondary :disabled="roleSaving" @click="roleMaterial = null" />
      </view>
    </view>
    <view v-if="activeVideo" class="material-overlay" @click.self="activeVideo = ''">
      <view class="material-dialog"><video :src="activeVideo" controls :autoplay="false" class="material-video" /><ServiceButton text="关闭预览" secondary @click="activeVideo = ''" /></view>
    </view>
  </AccountServiceShell>
</template>
<script setup>
import { getCurrentInstance, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import AccountServiceShell from '@/components/AccountServiceShell.vue'
import AppEmpty from '@/components/AppEmpty.vue'
import AppIcon from '@/components/AppIcon.vue'
import ServiceButton from '@/components/ServiceButton.vue'
import api from '@/api'
import { go, requireLogin } from '@/utils/navigation'
import { chooseMaterialFile } from '@/utils/media'
import { MAX_UPLOAD_MB, uploadMedia } from '@/utils/upload'
import { useAccountList } from '@/composables/useAccountList'

/** 素材类型与预览状态，视频按需加载避免列表同时请求大文件。 */
const FILTERS = [{ key: 'all', label: '全部素材' }, { key: 'image', label: '图片' }, { key: 'video', label: '视频' }, { key: 'pending', label: '待标识' }]
const selectionMode = ref(false), selectionKind = ref('video'), selectionRole = ref('')
const roleMaterial = ref(null), roleSaving = ref(false), roleError = ref(''), selectAfterRole = ref(false)
const ROLES = [{ key: 'person', label: '人物' }, { key: 'scene', label: '场景' }, { key: 'product', label: '商品' }]
function roleLabel(role) { return ROLES.find((item) => item.key === role)?.label || '未标用途' }
const uploading = ref(false), uploadProgress = ref(0), uploadError = ref(''), uploadMessage = ref('')
const pendingMaterial = ref(null), marking = ref(false), markError = ref('')
const pageInstance = getCurrentInstance()
const activeVideo = ref(''), failedImages = reactive({})

onLoad((options) => {
  selectionMode.value = options?.mode === 'select' && ['image', 'video'].includes(options?.kind)
  selectionKind.value = options?.kind === 'image' ? 'image' : 'video'
  selectionRole.value = ROLES.some((item) => item.key === options?.role) ? options.role : ''
  if (selectionMode.value) filter.value = selectionKind.value
})
const syncing = ref(false), syncCursor = ref(0), syncMessage = ref('')
const { rows, total, loading, error, filter, selectFilter, loadMore, refresh, retry } = useAccountList(fetchMaterials)
/** 集中 API 分页读取当前筛选下的本人素材。 */
function fetchMaterials({ filter, ...paging }) { return api.common.materials.post({ ...paging, kind: filter }, { suppressGlobalError: true }) }
async function uploadMaterial() {
  if (uploading.value || pendingMaterial.value || !requireLogin()) return
  uploading.value = true
  uploadProgress.value = 0
  uploadError.value = ''
  uploadMessage.value = ''
  try {
    const meta = await chooseMaterialFile(selectionMode.value && selectionKind.value === 'video')
    if (meta.size > MAX_UPLOAD_MB * 1024 * 1024) throw new Error(`素材不能超过 ${MAX_UPLOAD_MB}MB`)
    const data = await uploadMedia(meta.path, {
      file: meta.file,
      filename: meta.name,
      onProgress: (percent) => { uploadProgress.value = percent },
    })
    if (!data?.url) throw new Error('上传未返回素材地址，请重试')
    markError.value = ''
    if (data.needs_confirmation || !['image', 'video'].includes(data.kind)) {
      pendingMaterial.value = { ...data, filename: meta.name || data.filename || '素材' }
      if (!selectionMode.value) filter.value = 'all'
    } else {
      if (!selectionMode.value) filter.value = data.kind
      uploadMessage.value = `上传成功，已自动识别为${data.kind === 'video' ? '视频' : '图片'}。`
    }
    await refresh()
  } catch (err) {
    if (err?.message !== 'CANCEL') uploadError.value = err?.message || '上传失败，请稍后重试'
  } finally {
    uploading.value = false
  }
}

async function markMaterial(kind) {
  if (!pendingMaterial.value || marking.value) return
  marking.value = true
  markError.value = ''
  try {
    const res = await api.common.materialType.post({ url: pendingMaterial.value.url, kind }, { suppressGlobalError: true })
    if (res?.code !== 1) throw new Error(res?.message || '标识保存失败，请重试')
    pendingMaterial.value = null
    if (!selectionMode.value) filter.value = kind
    await refresh()
    uploadMessage.value = '素材标识已保存，可点击素材预览或选择。'
  } catch (err) {
    markError.value = err?.message || '标识保存失败，请重试，无需重新上传'
  } finally {
    marking.value = false
  }
}

/** 老版本直传记录由后端逐批确认存在后入列表，失败记录明确反馈并允许稍后重试。 */
async function recoverMaterials() {
  if (syncing.value) return
  syncing.value = true
  syncMessage.value = ''
  try {
    const res = await api.common.materialsSync.post({ cursor: syncCursor.value }, { suppressGlobalError: true, timeout: 60000 })
    if (res?.code !== 1) throw new Error(res?.message || '找回失败，请稍后重试')
    syncCursor.value = res.data.has_more ? res.data.next_cursor : 0
    syncMessage.value = `本次找回 ${res.data.confirmed} 份素材。${res.data.unavailable ? `${res.data.unavailable} 份文件暂不可用，可稍后重试。` : ''}${res.data.has_more ? '还有历史记录，可继续找回。' : '已检查完全部历史记录。'}`
    await refresh()
  } catch (err) { syncMessage.value = err?.message || '找回失败，请稍后重试' }
  finally { syncing.value = false }
}
/** 选择模式回传视频并返回原工作室，普通模式仍预览素材。 */
function preview(item) {
  if (item.needs_confirmation || !['image', 'video'].includes(item.kind)) {
    pendingMaterial.value = item
    markError.value = ''
    return
  }
  if (selectionMode.value) {
    if (item.kind !== selectionKind.value || !item.url) return
    if (selectionRole.value && item.role !== selectionRole.value) {
      editRole(item, true)
      return
    }
    const channel = pageInstance?.proxy?.getOpenerEventChannel?.()
    if (!channel) {
      uni.showToast({ title: '选择入口已失效，请返回创作页重试', icon: 'none' })
      return
    }
    channel.emit('materialSelected', item)
    uni.navigateBack()
    return
  }
  if (item.kind === 'video') activeVideo.value = item.url
  else uni.previewImage({ urls: rows.value.filter((row) => row.kind === 'image').map((row) => row.url), current: item.url, fail: () => uni.showToast({ title: '无法预览图片，请稍后重试', icon: 'none' }) })
}
function editRole(item, select = false) {
  roleMaterial.value = item
  roleError.value = ''
  selectAfterRole.value = select
}
async function saveRole(role) {
  if (!roleMaterial.value || roleSaving.value) return
  if (selectAfterRole.value && role !== selectionRole.value) {
    roleError.value = `当前需要${roleLabel(selectionRole.value)}图片，请选择对应用途或取消。`
    return
  }
  roleSaving.value = true
  roleError.value = ''
  try {
    const item = roleMaterial.value
    const res = await api.common.materialRole.post({ url: item.url, role }, { suppressGlobalError: true })
    if (res?.code !== 1) throw new Error(res?.message || '用途保存失败，请重试')
    item.role = res.data.role
    const select = selectAfterRole.value
    roleMaterial.value = null
    if (select) preview(item)
  } catch (err) { roleError.value = err?.message || '用途保存失败，请重试' }
  finally { roleSaving.value = false }
}

/** 选择模式直接返回，普通素材库仍可跳转创作入口。 */
function leaveEmptyLibrary() {
  if (selectionMode.value) uni.navigateBack()
  else go('/pages/studio/index')
}
/** 字节数格式化为便于理解的大小，不把历史未知大小显示成空文件。 */
function formatSize(value) { const size = Number(value || 0); return size ? (size < 1048576 ? `${Math.max(1,Math.round(size/1024))} KB` : `${(size/1048576).toFixed(1)} MB`) : '大小未记录' }
</script>
<style lang="scss" scoped>
@import '@/styles/account-services.scss';
.material--add { display: flex; min-height: 196px; flex-direction: column; align-items: center; justify-content: center; gap: 8px; border: 1px dashed var(--brand-primary); color: var(--brand-primary); text-align: center; }
.material__plus { font-size: 52px; font-weight: 300; line-height: 1; }
.material-type { display: flex; flex-direction: column; gap: 12px; }
.material-type__title { font-size: 18px; color: var(--ink-900); }
.material-sync { display: inline-block; padding: 8px 0; margin: 0 0 6px; background: transparent; color: var(--brand-primary); font-size: 12px; line-height: 1.6; }
.material-sync::after { border: none; }
.material-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 12px; margin: 18px 0 24px; }
.material { min-width: 0; padding: 5px; margin: 0; background: var(--paper-100); border-radius: 22px; line-height: 1.5; text-align: left; }
.material::after { border: none; }
.material__preview { position: relative; height: 136px; border-radius: 17px 17px 10px 10px; overflow: hidden; background: #e7e1d5; display: flex; align-items: center; justify-content: center; }
.material__image { width: 100%; height: 100%; }
.material__badge { position: absolute; left: 8px; bottom: 8px; padding: 2px 8px; border-radius: 999px; background: var(--paper-card); color: var(--ink-700); font-size: 10px; }
.material__info { display: flex; flex-direction: column; gap: 6px; padding: 12px 9px; background: var(--paper-card); border-radius: 10px 10px 17px 17px; }
.material__name { color: var(--ink-900); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.material__meta { color: var(--ink-500); font-size: 10px; }
.material-end { text-align: center; }
.material-overlay { position: fixed; inset: 0; z-index: var(--z-overlay); background: rgba(37,36,31,0.8); display: flex; align-items: center; justify-content: center; padding: 20px; }
.material-dialog { width: 100%; max-width: 440px; padding: 12px; border-radius: 24px; background: var(--paper-card); }
.material-video { width: 100%; height: 260px; margin-bottom: 16px; }
</style>
