<template>
  <AccountServiceShell title="我的素材" heading="灵感，随时找回" subtitle="上传过的图片与视频，留在这里继续陪你创作。">
    <view class="service-filters"><button v-for="item in FILTERS" :key="item.key" class="service-filter" :class="{ 'service-filter--active': filter === item.key }" role="button" tabindex="0" :aria-pressed="filter === item.key" @click="selectFilter(item.key)" @keydown.enter.prevent="selectFilter(item.key)" @keydown.space.prevent="selectFilter(item.key)">{{ item.label }}</button></view>
    <text class="service-note">共 {{ total }} 份素材 · 仅展示已确认上传成功的记录</text>
    <button class="material-sync" role="button" tabindex="0" :disabled="syncing" @click="recoverMaterials" @keydown.enter.prevent="recoverMaterials" @keydown.space.prevent="recoverMaterials">{{ syncing ? '正在找回历史素材…' : (syncCursor ? '继续找回历史素材' : '找回历史素材') }}</button>
    <text v-if="syncMessage" class="service-note" role="status">{{ syncMessage }}</text>
    <view v-if="rows.length" class="material-grid">
      <button v-for="item in rows" :key="item.id" class="material" role="button" tabindex="0" :aria-label="`预览${item.filename}`" @click="preview(item)" @keydown.enter.prevent="preview(item)" @keydown.space.prevent="preview(item)">
        <view class="material__preview">
          <image v-if="item.kind === 'image' && !failedImages[item.id]" :src="item.url" mode="aspectFill" class="material__image" :alt="item.filename" @error="failedImages[item.id] = true" />
          <AppIcon v-else :name="item.kind === 'video' ? 'play' : 'image-off'" :size="30" color="#8A5A3B" />
          <text class="material__badge">{{ item.kind === 'video' ? '视频' : '图片' }}</text>
        </view>
        <view class="material__info"><text class="material__name">{{ item.filename }}</text><text class="material__meta">{{ formatSize(item.size) }} · {{ item.create_time?.slice(0,10) }}</text></view>
      </button>
    </view>
    <text v-if="error" class="service-error" role="alert">{{ error }}</text>
    <ServiceButton v-if="error" text="重新加载" secondary @click="retry" />
    <view v-if="loading" class="service-status">正在整理你的素材…</view>
    <AppEmpty v-else-if="!rows.length && !error" icon="image" title="素材从第一次上传开始" desc="在创作中上传的图片和视频会自动保存在这里。" action-text="去创作" @action="go('/pages/studio/index')" />
    <ServiceButton v-if="rows.length < total && !loading && !error" text="加载更多素材" secondary @click="loadMore" />
    <text v-if="rows.length && rows.length >= total" class="service-note material-end">已经看到全部素材了</text>
    <view v-if="activeVideo" class="material-overlay" @click.self="activeVideo = ''">
      <view class="material-dialog"><video :src="activeVideo" controls :autoplay="false" class="material-video" /><ServiceButton text="关闭预览" secondary @click="activeVideo = ''" /></view>
    </view>
  </AccountServiceShell>
</template>
<script setup>
import { reactive, ref } from 'vue'
import AccountServiceShell from '@/components/AccountServiceShell.vue'
import AppEmpty from '@/components/AppEmpty.vue'
import AppIcon from '@/components/AppIcon.vue'
import ServiceButton from '@/components/ServiceButton.vue'
import api from '@/api'
import { go } from '@/utils/navigation'
import { useAccountList } from '@/composables/useAccountList'

/** 素材类型与预览状态，视频按需加载避免列表同时请求大文件。 */
const FILTERS = [{ key: 'all', label: '全部素材' }, { key: 'image', label: '图片' }, { key: 'video', label: '视频' }]
const activeVideo = ref(''), failedImages = reactive({})
const syncing = ref(false), syncCursor = ref(0), syncMessage = ref('')
const { rows, total, loading, error, filter, selectFilter, loadMore, refresh, retry } = useAccountList(fetchMaterials)
/** 集中 API 分页读取当前筛选下的本人素材。 */
function fetchMaterials({ filter, ...paging }) { return api.common.materials.post({ ...paging, kind: filter }, { suppressGlobalError: true }) }
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
/** 图片用平台预览，视频使用跨端 video 组件。 */
function preview(item) {
  if (item.kind === 'video') activeVideo.value = item.url
  else uni.previewImage({ urls: rows.value.filter((row) => row.kind === 'image').map((row) => row.url), current: item.url, fail: () => uni.showToast({ title: '无法预览图片，请稍后重试', icon: 'none' }) })
}
/** 字节数格式化为便于理解的大小，不把历史未知大小显示成空文件。 */
function formatSize(value) { const size = Number(value || 0); return size ? (size < 1048576 ? `${Math.max(1,Math.round(size/1024))} KB` : `${(size/1048576).toFixed(1)} MB`) : '大小未记录' }
</script>
<style lang="scss" scoped>
@import '@/styles/account-services.scss';
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
