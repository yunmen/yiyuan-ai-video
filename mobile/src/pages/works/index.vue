<template>
  <view class="app-page works">
    <AppNavBar title="我的作品" align="left" :auto-back="false">
      <template #right>
        <view class="works__search" role="button" aria-label="按作品编号搜索" @click="openSearch">
          <AppIcon name="search" :size="20" color="#3A342C" />
        </view>
      </template>
    </AppNavBar>

    <view class="works__body">
      <!-- 额度条：与 /account/credits 同源，未登录时引导登录 -->
      <view class="balance">
        <view class="balance__left">
          <view class="balance__icon">
            <AppIcon name="zap" :size="20" color="#FFFFFF" />
          </view>
          <view class="balance__info">
            <text class="balance__label">剩余额度</text>
            <text class="balance__value">
              {{ balanceText }}
              <text v-if="balanceReady" class="balance__unit">次</text>
            </text>
          </view>
        </view>
        <view class="balance__btn" role="button" @click="goRecharge">
          <text>{{ isLoggedIn ? '充值' : '去登录' }}</text>
        </view>
      </view>

      <!-- 搜索条件提示（按作品编号搜索时出现） -->
      <view v-if="taskNo" class="works__search-tip">
        <text class="works__search-tip-text">编号包含「{{ taskNo }}」</text>
        <view class="works__search-clear" role="button" @click="clearSearch">
          <AppIcon name="close" :size="14" color="#B23A2E" :stroke-width="2.5" />
        </view>
      </view>

      <view class="works__section-title">
        <view>
          <text class="works__eyebrow">朱印状态</text>
          <text class="works__title">结果中心</text>
        </view>
        <text class="works__section-note">按生成进度整理</text>
      </view>

      <view class="filters">
        <view
          v-for="tab in filterTabs"
          :key="tab.key"
          class="filters__tab"
          :class="{ 'filters__tab--active': filter === tab.key }"
          role="button"
          @click="switchFilter(tab.key)"
        >
          <text>{{ tab.label }}</text>
        </view>
      </view>

      <!-- 未登录 -->
      <AppEmpty
        v-if="!isLoggedIn"
        title="登录后查看作品"
        desc="登录即可查看生成进度与历史成片"
        icon="film"
        action-text="去登录"
        @action="goLogin"
      />

      <template v-else>
        <!-- 骨架 -->
        <view v-if="loading && !works.length" class="masonry">
          <view v-for="n in 4" :key="n" class="masonry__item">
            <view class="work work--skeleton">
              <view class="work__thumb work__thumb--skeleton" />
              <view class="work__body">
                <view class="skeleton-line" />
                <view class="skeleton-line skeleton-line--short" />
              </view>
            </view>
          </view>
        </view>

        <!-- 作品瀑布流 -->
        <view v-else-if="visibleWorks.length" class="masonry">
          <view v-for="item in visibleWorks" :key="item.id" class="masonry__item">
            <view class="work" role="button" @click="openActions(item)">
              <view class="work__thumb" :style="{ paddingTop: thumbPadding(item) }">
                <image
                  v-if="workCover(item)"
                  class="work__img"
                  :src="workCover(item)"
                  mode="aspectFill"
                />
                <view v-else class="work__img work__img--fallback">
                  <AppIcon
                    :name="statusOf(item).key === 'failed' ? 'image-off' : 'film'"
                    :size="36"
                    color="#D5CBB6"
                    :stroke-width="1.5"
                  />
                </view>

                <view v-if="statusOf(item).key === 'processing'" class="work__gen">
                  <view class="gen-ring">
                    <view class="gen-ring__track" />
                    <view class="gen-ring__spin gen-ring__spin--outer" />
                    <view class="gen-ring__spin gen-ring__spin--inner" />
                    <text class="gen-ring__value">{{ normalizeProgress(item.progress) }}%</text>
                  </view>
                  <text class="work__gen-phase">{{ workStageText(item.progress) }}</text>
                  <view class="gen-bar">
                    <view
                      class="gen-bar__fill"
                      :style="{ width: normalizeProgress(item.progress) + '%' }"
                    />
                  </view>
                </view>

                <view v-if="statusOf(item).key === 'processing'" class="work__pulse">
                  <view class="work__pulse-dot" />
                </view>

                <text
                  class="work__status"
                  :class="'work__status--' + statusOf(item).key"
                >
                  {{ statusOf(item).label }}
                </text>

                <text class="work__duration">{{ formatDuration(workDuration(item)) }}</text>
              </view>

              <view class="work__body">
                <text class="work__title app-clamp-2">{{ displayTitle(item) }}</text>
                <view class="work__foot">
                  <text class="work__meta">{{ metaText(item) }}</text>
                  <text class="work__action-hint">{{ statusOf(item).key === 'completed' ? '播放 / 详情' : '更多' }}</text>
                  <view class="work__more" role="button" aria-label="更多操作">
                    <AppIcon name="more-horizontal" :size="16" color="#9C9488" />
                  </view>
                </view>
              </view>
            </view>
          </view>
        </view>

        <!-- 空态 -->
        <AppEmpty
          v-else
          :title="taskNo ? '没有匹配的作品' : '暂无作品'"
          :desc="taskNo ? '换个作品编号试试' : '去创作一个属于你的 AI 视频吧'"
          icon="film"
          action-text="立即创作"
          @action="goStudio"
        />
      </template>

      <view v-if="loading && works.length" class="works__loading">
        <AppIcon name="loader" :size="16" color="#9C9488" class="app-spin" />
        <text>加载中…</text>
      </view>
    </view>

    <!-- 成片播放浮层（H5/小程序均可用，避免为播放单独开页面）。
         关闭按钮用 cover-view：小程序 video 为原生组件，普通 view 在未启用同层渲染时盖不住 -->
    <view v-if="playingUrl" class="player" @click="closePlayer">
      <video
        class="player__video"
        :src="playingUrl"
        :autoplay="true"
        :controls="true"
        object-fit="contain"
        @click.stop
      >
        <cover-view class="player__close" @click.stop="closePlayer">✕</cover-view>
      </video>
    </view>

    <AppTabBar active="works" />
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onPullDownRefresh, onShow, onUnload } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import AppNavBar from '@/components/AppNavBar.vue'
import AppTabBar from '@/components/AppTabBar.vue'
import AppEmpty from '@/components/AppEmpty.vue'
import api from '@/api'
import { useGenConfig } from '@/composables/useGenConfig'
import { useUserStore } from '@/store/modules/user'
import { currentPagePath, go, toLoginPath } from '@/utils/navigation'
import {
  formatDateTime,
  formatDuration,
  isWorkTask,
  normalizeProgress,
  workCover,
  workDuration,
  workFailReason,
  workRemainingText,
  workStageText,
  workStatus,
  workTitle,
  workTypeLabel,
} from '@/utils/task'

const userStore = useUserStore()
const { loadGenConfig, creativeLevels, defaultCreativeLevel, hookBoosts } = useGenConfig()

const isLoggedIn = computed(() => userStore.isLoggedIn)
const balanceReady = computed(() => typeof userStore.creditTotal === 'number')
const balanceText = computed(() => (balanceReady.value ? String(userStore.creditTotal) : '--'))

/** 状态筛选：与后端 QuerySchema.status 一一对应（空 = 全部）。 */
const filterTabs = [
  { key: 'all', label: '全部', status: '' },
  { key: 'processing', label: '生成中', status: 'processing' },
  { key: 'completed', label: '已完成', status: 'success' },
  { key: 'failed', label: '失败', status: 'failed' },
]

const filter = ref('all')
const taskNo = ref('')
const works = ref([])
const loading = ref(false)
const playingUrl = ref('')

/** 后端已按状态过滤；这里再剔除对标拆解这类内部任务（只做分析、不产出成片）。 */
const visibleWorks = computed(() => works.value.filter(isWorkTask))

const statusOf = (item) => workStatus(item.status)

/** 作品标题：模板标题/备注优先；生成中的任务补上类型，避免多条「AI 作品」重名。 */
function displayTitle(item) {
  const title = workTitle(item)
  return statusOf(item).key === 'processing' ? `${title}（${workTypeLabel(item)}）` : title
}

/** 卡片主信息行：生成中看预计剩余，失败看原因，其余展示创建时间。 */
function metaText(item) {
  const status = statusOf(item)
  if (status.key === 'processing') return workRemainingText(item)
  if (status.key === 'failed') return workFailReason(item)
  return formatDateTime(item.create_time)
}

/**
 * 缩略图撑高比例（padding-top 百分比，相对容器宽度）：用任务真实画幅（gen_ratio）
 * 驱动瀑布流错落，缺失时回退 3:4。不用 aspect-ratio，旧版小程序内核不支持会导致封面塌陷。
 */
function thumbPadding(item) {
  const ratio = String(item?.gen_ratio || '').trim()
  const match = ratio.match(/^(\d+)\s*[:/]\s*(\d+)$/)
  if (!match) return '133.3333%'
  const w = Number(match[1])
  const h = Number(match[2])
  if (!w || !h) return '133.3333%'
  return `${(h / w) * 100}%`
}

/** 拉取额度（与首页/充值页同一数据源）。 */
async function loadCredits() {
  if (!isLoggedIn.value) return
  try {
    const res = await api.account.credits.post({}, { suppressGlobalError: true, suppressGlobalAuthError: true })
    if (res && res.code === 1 && res.data) userStore.setCreditTotal(res.data.total)
  } catch (err) {
    console.error('加载剩余额度失败', err)
  }
}

/** 拉取作品列表（按当前筛选与编号搜索）。 */
async function loadWorks() {
  if (!isLoggedIn.value) {
    works.value = []
    return
  }
  loading.value = true
  try {
    const active = filterTabs.find((tab) => tab.key === filter.value)
    const payload = { pageNum: 1, pageSize: 30 }
    if (active && active.status) payload.status = active.status
    if (taskNo.value) payload.task_no = taskNo.value
    const res = await api.task.list.post(payload, { suppressGlobalError: true })
    works.value = res && res.code === 1 && Array.isArray(res.data) ? res.data : []
  } catch (err) {
    console.error('加载作品列表失败', err)
    works.value = []
  } finally {
    loading.value = false
  }
}

/**
 * 进度轮询：仅当列表里存在生成中的任务时开启，全部完成后自动停止，
 * 页面卸载时清理，避免离开页面后仍在请求。
 */
let pollTimer = null
function syncPolling() {
  const hasProcessing = works.value.some((item) => statusOf(item).key === 'processing')
  if (hasProcessing && !pollTimer) {
    pollTimer = setInterval(() => {
      loadWorks()
    }, 5000)
    return
  }
  if (!hasProcessing && pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function switchFilter(key) {
  if (filter.value === key) return
  filter.value = key
  loadWorks().then(syncPolling)
}

function openSearch() {
  uni.showModal({
    title: '搜索作品',
    editable: true,
    placeholderText: '输入作品编号（如 GY2026…）',
    success: (res) => {
      if (!res.confirm) return
      taskNo.value = String(res.content || '').trim()
      loadWorks().then(syncPolling)
    },
  })
}

function clearSearch() {
  taskNo.value = ''
  loadWorks().then(syncPolling)
}

function goLogin() {
  go(toLoginPath(currentPagePath()))
}

function goRecharge() {
  if (!isLoggedIn.value) {
    goLogin()
    return
  }
  go('/pages/recharge/index')
}

function goStudio() {
  go('/pages/studio/index')
}

/**
 * 作品操作：全部走真实后端接口（重新生成 / 删除），已完成作品支持页内播放成片。
 * 不新增详情页，避免偏离设计稿的信息架构。
 */
function openActions(item) {
  const status = statusOf(item)
  const actions = []
  if (status.key === 'completed' && item.result_video) actions.push({ label: '播放成片', key: 'play' })
  if (status.key === 'completed' && item.type === 'video') actions.push({ label: '查看分镜', key: 'shots' })
  if (status.key !== 'processing') actions.push({ label: '重新生成', key: 'regenerate' })
  actions.push({ label: '删除作品', key: 'delete' })

  uni.showActionSheet({
    itemList: actions.map((action) => action.label),
    success: (res) => {
      const action = actions[res.tapIndex]
      if (!action) return
      if (action.key === 'play') playingUrl.value = item.result_video
      if (action.key === 'shots') go({ path: '/pages/task-detail/index', query: { id: item.id } })
      if (action.key === 'regenerate') regenerate(item)
      if (action.key === 'delete') confirmDelete(item)
    },
  })
}

function optionLabel(option) {
  return option?.desc ? `${option.label}（${option.desc}）` : option?.label || option?.key || ''
}

function pickRegenerateOption(title, options, current) {
  return new Promise((resolve) => {
    uni.showActionSheet({
      title,
      itemList: options.map(optionLabel),
      success: (res) => resolve(options[res.tapIndex]?.key || current),
      fail: () => resolve(null),
    })
  })
}

async function regenerate(item) {
  await loadGenConfig()
  const creativeLevel = await pickRegenerateOption('选择创意档位', creativeLevels.value, defaultCreativeLevel.value)
  if (!creativeLevel) return
  const hookBoost = await pickRegenerateOption('选择开头钩子', hookBoosts.value, 'normal')
  if (!hookBoost) return
  try {
    const res = await api.task.regenerate.post(
      { id: item.id, creative_level: creativeLevel, hook_boost: hookBoost },
      { suppressGlobalError: true },
    )
    if (res && res.code === 1) {
      uni.showToast({ title: '已重新提交生成', icon: 'success' })
      await loadWorks()
      syncPolling()
    }
  } catch (err) {
    console.error('重新生成失败', err)
    uni.showToast({ title: err?.data?.message || err?.message || '重新生成失败', icon: 'none' })
  }
}

function confirmDelete(item) {
  uni.showModal({
    title: '删除作品',
    content: '删除后不可恢复，确定删除这条作品吗？',
    confirmText: '删除',
    confirmColor: '#B23A2E',
    success: async (res) => {
      if (!res.confirm) return
      try {
        const result = await api.task.delete.post({ id: item.id }, { suppressGlobalError: true })
        if (result && result.code === 1) {
          uni.showToast({ title: '已删除', icon: 'success' })
          works.value = works.value.filter((work) => work.id !== item.id)
        }
      } catch (err) {
        console.error('删除作品失败', err)
        uni.showToast({ title: err?.data?.message || err?.message || '删除失败', icon: 'none' })
      }
    },
  })
}

function closePlayer() {
  playingUrl.value = ''
}

onShow(() => {
  loadCredits()
  loadWorks().then(syncPolling)
})

onPullDownRefresh(async () => {
  try {
    await Promise.all([loadCredits(), loadWorks()])
    syncPolling()
  } finally {
    uni.stopPullDownRefresh()
  }
})

onUnload(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style lang="scss" scoped>
.works {
  &__search {
    width: 36px;
    height: 36px;
    margin-right: -8px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: background var(--transition-fast);
  }

  &__search:active {
    background: var(--bg-hover);
  }

  &__body {
    padding: 12px var(--page-gutter) 24px;
  }

  &__section-title {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    margin: 6px 0 14px;
    padding-left: 10px;
    border-left: 3px solid var(--brand-primary);
  }

  &__eyebrow {
    display: block;
    margin-bottom: 4px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.16em;
    color: var(--brand-primary);
  }

  &__title {
    display: block;
    font-family: var(--font-serif);
    font-size: 21px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--text-primary);
  }

  &__section-note {
    padding-bottom: 2px;
    font-size: 11px;
    color: var(--text-tertiary);
  }

  &__search-tip {
    display: flex;
    width: fit-content;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    margin-bottom: 12px;
    border-radius: var(--radius-full);
    background: var(--brand-primary-light);

    &-text {
      font-size: 12px;
      color: var(--brand-primary);
    }
  }

  &__search-clear {
    display: flex;
    align-items: center;
  }

  &__loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 16px 0;
    font-size: 12px;
    color: var(--text-muted);
  }
}

/* ============ 额度条 ============ */
.balance {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  margin-bottom: 18px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);

  &__left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  &__icon {
    width: 34px;
    height: 34px;
    border: 1px solid var(--border-medium);
    border-radius: var(--radius-md);
    background: var(--brand-primary-light);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  &__info {
    display: flex;
    flex-direction: column;
  }

  &__label {
    font-size: 12px;
    color: var(--text-tertiary);
  }

  &__value {
    margin-top: 2px;
    font-size: 18px;
    font-weight: 700;
    color: var(--text-primary);
  }

  &__unit {
    font-size: 14px;
    font-weight: 400;
    color: var(--text-muted);
  }

  &__btn {
    padding: 7px 13px;
    border: 1px solid var(--border-medium);
    border-radius: var(--radius-md);
    background: transparent;
    color: var(--brand-primary);
    font-size: 13px;
    font-weight: 600;
  }
}

/* ============ 状态筛选 ============ */
.filters {
  display: flex;
  align-items: center;
  gap: 26px;
  margin: 0 -16px 18px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border-medium);
  overflow-x: auto;

  &__tab {
    position: relative;
    padding: 10px 4px;
    font-size: 14px;
    font-weight: 500;
    color: var(--text-tertiary);
    white-space: nowrap;
    transition: color var(--transition-fast);

    &--active {
      color: var(--text-primary);
      font-weight: 600;
    }

    &--active::after {
      content: '';
      position: absolute;
      bottom: -1px;
      left: 0;
      width: 100%;
      height: 2px;
      background: var(--brand-primary);
    }
  }
}

/* ============ 瀑布流 ============ */
.masonry {
  column-count: 2;
  column-gap: 12px;

  &__item {
    break-inside: avoid;
    margin-bottom: 12px;
  }
}

.work {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(31, 29, 26, 0.03);

  &--skeleton {
    border-color: var(--border-light);
  }

  &__thumb {
    position: relative;
    width: 100%;
    background: var(--grad-brand-soft);
    overflow: hidden;

    &--skeleton {
      /* 与默认 3:4 封面一致的撑高，兼容不支持 aspect-ratio 的旧内核 */
      padding-top: 133.3333%;
      background: var(--bg-hover);
    }
  }

  &__img {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: block;

    &--fallback {
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--bg-hover);
    }
  }

  /* 状态角标 */
  &__status {
    position: absolute;
    top: 8px;
    left: 8px;
    z-index: 2;
    padding: 3px 8px;
    border-radius: var(--radius-full);
    font-size: 11px;
    font-weight: 500;

    &--processing {
      background: rgba(62, 107, 122, 0.1);
      color: var(--state-info);
    }

    &--completed {
      background: rgba(75, 122, 90, 0.1);
      color: var(--state-success);
    }

    &--failed {
      background: rgba(178, 58, 46, 0.1);
      color: var(--state-error);
    }
  }

  /* 时长 */
  &__duration {
    position: absolute;
    right: 8px;
    bottom: 8px;
    z-index: 2;
    padding: 2px 6px;
    border-radius: 4px;
    background: rgba(0, 0, 0, 0.65);
    color: #ffffff;
    font-size: 11px;
  }

  /* 生成中遮罩 */
  &__gen {
    position: absolute;
    inset: 0;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(31, 29, 26, 0.56);
  }

  &__gen-phase {
    margin-top: 10px;
    margin-bottom: 10px;
    font-size: 12px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.9);
  }

  &__pulse {
    position: absolute;
    top: 8px;
    right: 8px;
    z-index: 2;
    width: 10px;
    height: 10px;
  }

  &__pulse-dot {
    width: 8px;
    height: 8px;
    margin-left: auto;
    border-radius: 50%;
    background: #B98236;
    opacity: 0.85;
  }

  &__body {
    padding: 12px 12px 13px;
    border-top: 1px solid rgba(231, 224, 209, 0.72);
  }

  &__title {
    display: block;
    font-family: var(--font-serif);
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: var(--text-primary);
    margin-bottom: 7px;
  }

  &__foot {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  &__meta {
    flex: 1;
    min-width: 0;
    font-size: 12px;
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__action-hint {
    margin-left: 8px;
    font-size: 10px;
    color: var(--brand-primary);
    white-space: nowrap;
  }

  &__more {
    width: 28px;
    height: 28px;
    margin-right: -4px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
  }
}

/* ============ 进度环 / 进度条 ============ */
.gen-ring {
  position: relative;
  width: 56px;
  height: 56px;
  animation: none;

  &__track,
  &__spin {
    position: absolute;
    border-radius: 50%;
    border: 2px solid transparent;
  }

  &__track {
    inset: 0;
    border-color: rgba(255, 255, 255, 0.15);
  }

  &__spin--outer {
    inset: 0;
    border-top-color: #ffffff;
    border-right-color: #ffffff;
    animation: none;
  }

  &__spin--inner {
    inset: 5px;
    border-bottom-color: #E0AFA6;
    border-left-color: #E0AFA6;
    animation: none;
  }

  &__value {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    color: #ffffff;
    font-variant-numeric: tabular-nums;
  }
}

.gen-bar {
  position: relative;
  width: 72%;
  height: 6px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.2);
  overflow: hidden;

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.5), transparent);
    animation: app-shimmer 1.8s ease-in-out infinite;
  }

  &__fill {
    height: 100%;
    border-radius: var(--radius-full);
    background: var(--grad-brand);
    background: #D19A4A;
    transition: width 0.7s cubic-bezier(0.4, 0, 0.2, 1);
  }
}

/* ============ 骨架 ============ */
.skeleton-line {
  height: 12px;
  border-radius: 6px;
  background: var(--bg-hover);

  &--short {
    width: 60%;
    margin-top: 8px;
  }
}

/* ============ 成片播放浮层 ============ */
.player {
  position: fixed;
  inset: 0;
  z-index: 300;
  background: rgba(31, 29, 26, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;

  &__video {
    width: 100%;
    height: 70vh;
    border-radius: var(--radius-lg);
    background: #1F1D1A;
  }

  &__close {
    /* cover-view 仅支持基础样式，用 text-align + line-height 居中，不用 flex */
    position: absolute;
    top: 12px;
    right: 12px;
    z-index: 10;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: rgba(0, 0, 0, 0.45);
    color: #ffffff;
    font-size: 16px;
    line-height: 36px;
    text-align: center;
  }
}
</style>
