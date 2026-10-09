<template>
  <view class="app-page home">
    <!-- hero 渐变头图：状态栏 + 品牌行 + 主 CTA -->
    <view class="hero">
      <view class="hero__statusbar" :style="{ height: statusBarHeight + 'px' }" />

      <view class="hero__bar">
        <view class="hero__brand">
          <view class="hero__logo">
            <AppIcon name="video-camera" :size="20" color="#FFFFFF" :stroke-width="2.5" />
          </view>
          <text class="hero__brand-name">一源AI</text>
        </view>
        <view class="hero__quota" role="button" @click="handleQuotaTap">
          <AppIcon name="star" :size="12" color="#FFFFFF" :stroke-width="2.5" />
          <text>{{ quotaText }}</text>
        </view>
      </view>

      <view class="hero__body">
        <view class="hero__intro">
          <text class="hero__title">别人的爆款视频</text>
          <text class="hero__title">1 分钟改成你的</text>
          <text class="hero__sub">不用拍、不用剪、不用写文案 · 上传一条对标视频，AI 自动生成原创带货片</text>
        </view>

        <view class="hero__media">
          <image class="hero__media-img" src="/static/hero-main.jpg" mode="aspectFill" />
          <view class="hero__media-mask" />
          <view class="hero__media-foot">
            <view class="hero__creators">
              <view class="hero__avatars">
                <view class="hero__avatar hero__avatar--1" />
                <view class="hero__avatar hero__avatar--2" />
                <view class="hero__avatar hero__avatar--3" />
              </view>
              <text class="hero__media-text">AI 自动拆解复刻</text>
            </view>
            <view class="hero__rating">
              <AppIcon name="star" :size="11" color="#FFFFFF" :stroke-width="2.5" />
              <text class="hero__media-text">输出 {{ defaultResolution }}</text>
            </view>
          </view>
        </view>

        <view class="hero__cta app-btn-brand" role="button" @click="goStudio">
          <text class="hero__cta-text">立即生成</text>
          <AppIcon name="arrow-right" :size="18" color="#FFFFFF" :stroke-width="2.5" />
          <view class="hero__cta-shine" />
        </view>

        <view class="hero__notes">
          <view class="hero__note">
            <AppIcon name="check" :size="12" color="rgba(255,255,255,0.5)" :stroke-width="2.5" />
            <text>手机号验证码登录</text>
          </view>
          <text class="hero__note-dot">·</text>
          <view class="hero__note">
            <AppIcon name="check" :size="12" color="rgba(255,255,255,0.5)" :stroke-width="2.5" />
            <text>生成失败自动返还</text>
          </view>
          <text class="hero__note-dot">·</text>
          <view class="hero__note hero__note--amber">
            <AppIcon name="sparkles" :size="12" color="#FCD34D" :stroke-width="2.5" />
            <text>{{ noteFreeText }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 功能入口 -->
    <view class="section">
      <view class="entry-grid">
        <view
          v-for="entry in entries"
          :key="entry.key"
          class="entry-card"
          role="button"
          @click="openEntry(entry)"
        >
          <view class="entry-card__icon" :style="{ background: entry.iconBg }">
            <AppIcon :name="entry.icon" :size="24" :color="entry.iconColor" />
          </view>
          <text class="entry-card__title">{{ entry.title }}</text>
          <text class="entry-card__desc">{{ entry.desc }}</text>
        </view>
      </view>
    </view>

    <!-- 三步流程 -->
    <view class="section">
      <text class="app-section-title">三步生成爆款视频</text>
      <view class="steps">
        <view v-for="(step, index) in steps" :key="step.title" class="steps__item">
          <view v-if="index < steps.length - 1" class="steps__line" />
          <view class="steps__circle" :class="{ 'steps__circle--done': step.done }">
            <AppIcon
              v-if="step.done"
              name="check"
              :size="24"
              color="#FFFFFF"
              :stroke-width="2.5"
            />
            <text v-else>{{ index + 1 }}</text>
          </view>
          <text class="steps__title">{{ step.title }}</text>
          <text class="steps__desc">{{ step.desc }}</text>
        </view>
      </view>

      <view class="steps__media">
        <image class="steps__media-img" src="/static/hero-main.jpg" mode="aspectFill" />
      </view>
    </view>

    <!-- 热门模板 -->
    <view class="section">
      <view class="tpl-head">
        <text class="app-section-title">热门模板</text>
        <view v-if="templates.length > 4" class="tpl-head__more" role="button" @click="toggleAllTemplates">
          <text>{{ showAllTemplates ? '收起' : '查看全部' }}</text>
          <AppIcon
            name="chevron-right"
            :size="14"
            color="#4F46E5"
            :stroke-width="2.5"
            :class="showAllTemplates ? 'tpl-head__arrow--up' : ''"
          />
        </view>
      </view>

      <view v-if="templatesLoading" class="tpl-grid">
        <view v-for="n in 4" :key="n" class="tpl-card tpl-card--skeleton">
          <view class="tpl-card__thumb tpl-card__thumb--skeleton" />
          <view class="tpl-card__body">
            <view class="tpl-skeleton-line" />
            <view class="tpl-skeleton-line tpl-skeleton-line--short" />
          </view>
        </view>
      </view>

      <view v-else-if="visibleTemplates.length" class="tpl-grid">
        <view
          v-for="item in visibleTemplates"
          :key="item.id"
          class="tpl-card"
          role="button"
          @click="useTemplate(item)"
        >
          <view class="tpl-card__thumb">
            <text v-if="templateBadge(item)" class="tpl-card__badge">{{ templateBadge(item) }}</text>
            <image v-if="item.cover" class="tpl-card__img" :src="item.cover" mode="aspectFill" />
            <view v-else class="tpl-card__img tpl-card__img--fallback">
              <AppIcon name="film" :size="28" color="#A5B4FC" :stroke-width="2" />
            </view>
            <view class="tpl-card__usage">
              <view class="tpl-card__usage-item">
                <AppIcon name="eye" :size="10" color="#FFFFFF" :stroke-width="2.5" />
                <text>{{ formatCount(item.use_count) }}</text>
              </view>
              <text>{{ item.duration }}s</text>
            </view>
          </view>
          <view class="tpl-card__body">
            <text class="tpl-card__title app-truncate">{{ item.title }}</text>
            <text class="tpl-card__sub app-truncate">{{ item.category || '通用' }}</text>
          </view>
        </view>
      </view>

      <view v-else class="tpl-empty">
        <text class="tpl-empty__text">模板正在准备中，先直接上传素材开工</text>
      </view>
    </view>

    <AppTabBar active="home" />
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onPullDownRefresh, onShow } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import AppTabBar from '@/components/AppTabBar.vue'
import api from '@/api'
import { useUserStore } from '@/store/modules/user'
import { useGenConfig } from '@/composables/useGenConfig'
import { currentPagePath, go, toLoginPath } from '@/utils/navigation'
import { refreshCurrentUserProfile } from '@/utils/session'
import { formatCount } from '@/utils/task'

const userStore = useUserStore()
const { loadGenConfig, defaultResolution } = useGenConfig()

const statusBarHeight = ref(20)
try {
  const sys = uni.getSystemInfoSync()
  statusBarHeight.value = sys.statusBarHeight || 20
} catch (err) {
  console.error('获取系统状态栏高度失败，使用默认值')
}

/** 已登录展示真实剩余额度，未登录引导登录（额度条与后端 /account/credits 同源）。 */
const quotaText = computed(() => {
  if (!userStore.isLoggedIn) return '登录领额度'
  const total = userStore.creditTotal
  return total === null || total === undefined ? '额度' : `${total} 额度`
})

/** 底部小字：突出一个实用卖点，不虚构数字。 */
const noteFreeText = computed(() => '支持手机本地上传 / 视频直链')

const entries = [
  {
    key: 'studio',
    title: '创作工作台',
    desc: '视频复刻 · 九宫格出片',
    icon: 'layers',
    iconColor: '#4F46E5',
    iconBg: 'linear-gradient(135deg, rgba(79,70,229,0.08) 0%, rgba(124,58,237,0.08) 100%)',
    path: '/pages/studio/index',
  },
  {
    key: 'digital',
    title: '数字人口播',
    desc: '真人形象 · 智能播报',
    icon: 'user',
    iconColor: '#7C3AED',
    iconBg: 'linear-gradient(135deg, rgba(124,58,237,0.1) 0%, rgba(236,72,153,0.1) 100%)',
    path: '/pages/digital/index',
  },
  {
    key: 'render',
    title: '视频换口播',
    desc: '一键替换 · 多语言支持',
    icon: 'volume',
    iconColor: '#3B82F6',
    iconBg: 'linear-gradient(135deg, rgba(59,130,246,0.1) 0%, rgba(79,70,229,0.1) 100%)',
    path: '/pages/render/index',
  },
  {
    key: 'aiflavor',
    title: '文案去味',
    desc: 'AI优化 · 爆款文案',
    icon: 'edit',
    iconColor: '#10B981',
    iconBg: 'linear-gradient(135deg, rgba(16,185,129,0.1) 0%, rgba(59,130,246,0.1) 100%)',
    path: '/pages/aiflavor/index',
  },
  {
    key: 'grid',
    title: '九宫格成片',
    desc: '提示词/照片→九宫格',
    icon: 'image',
    iconColor: '#F59E0B',
    iconBg: 'linear-gradient(135deg, rgba(245,158,11,0.1) 0%, rgba(79,70,229,0.1) 100%)',
    path: '/pages/grid/index',
  },
]

const steps = [
  { title: '选方式', desc: '复刻/九宫格' },
  { title: '传素材', desc: '视频/商品图' },
  { title: 'AI出片', desc: '一键生成', done: true },
]

const templates = ref([])
const templatesLoading = ref(false)
const showAllTemplates = ref(false)
const visibleTemplates = computed(() =>
  showAllTemplates.value ? templates.value : templates.value.slice(0, 4)
)

/** 模板角标：优先沿用运营打的标签，其次标记后台推荐位，不做无依据的"爆款"判定。 */
function templateBadge(item) {
  const tag = Array.isArray(item?.tags) ? item.tags.find((t) => String(t || '').trim()) : ''
  if (tag) return String(tag).trim()
  return item?.recommend ? '推荐' : ''
}

/** 加载热门模板：优先推荐位，为空时回退按热度排序的上架模板。 */
async function loadTemplates() {
  templatesLoading.value = true
  try {
    let res = await api.template.recommend.post({}, { suppressGlobalError: true })
    let list = res && res.code === 1 && Array.isArray(res.data) ? res.data : []
    if (!list.length) {
      res = await api.template.list.post(
        { pageNum: 1, pageSize: 8, sort_type: 1 },
        { suppressGlobalError: true }
      )
      list = res && res.code === 1 && Array.isArray(res.data) ? res.data : []
    }
    templates.value = list
  } catch (err) {
    console.error('加载热门模板失败', err)
    templates.value = []
  } finally {
    templatesLoading.value = false
  }
}

function toggleAllTemplates() {
  showAllTemplates.value = !showAllTemplates.value
}

/** 未登录时所有创作入口先引导登录，登录后回到首页继续。 */
function requireLogin() {
  if (userStore.isLoggedIn) return true
  go(toLoginPath(currentPagePath()))
  return false
}

function openEntry(entry) {
  go(entry.path)
}

function goStudio() {
  go('/pages/studio/index')
}

function useTemplate(item) {
  go({ path: '/pages/studio/index', query: { template_id: item.id } })
}

function handleQuotaTap() {
  if (!requireLogin()) return
  go('/pages/recharge/index')
}

/** 拉取最新额度：登录后额度条与底部横幅都以真实数据为准。 */
async function loadCredits() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await api.account.credits.post({}, { suppressGlobalError: true, suppressGlobalAuthError: true })
    if (res && res.code === 1 && res.data) {
      userStore.setCreditTotal(res.data.total)
      userStore.setUserInfo({ ...(userStore.userInfo || {}), ...res.data })
    }
  } catch (err) {
    console.error('加载剩余额度失败', err)
  }
}

async function refreshAll() {
  await loadGenConfig()
  await Promise.all([loadTemplates(), loadCredits()])
}

onShow(() => {
  refreshAll()
})

onPullDownRefresh(async () => {
  try {
    await refreshCurrentUserProfile(userStore)
    await refreshAll()
  } finally {
    uni.stopPullDownRefresh()
  }
})
</script>

<style lang="scss" scoped>
/* ============ hero ============ */
.hero {
  position: relative;
  overflow: hidden;
  background: var(--grad-hero);
  padding-bottom: 32px;

  &__statusbar {
    width: 100%;
  }

  &::before,
  &::after {
    content: '';
    position: absolute;
    border-radius: 50%;
    pointer-events: none;
  }

  &::before {
    top: -50%;
    right: -20%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(124, 58, 237, 0.4) 0%, transparent 70%);
  }

  &::after {
    bottom: -30%;
    left: -10%;
    width: 250px;
    height: 250px;
    background: radial-gradient(circle, rgba(79, 70, 229, 0.3) 0%, transparent 70%);
  }

  &__bar {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 20px;
  }

  &__brand {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__logo {
    width: 32px;
    height: 32px;
    border-radius: var(--radius-sm);
    background: rgba(255, 255, 255, 0.2);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  &__brand-name {
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
  }

  &__quota {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border-radius: var(--radius-full);
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: #ffffff;
    font-size: 12px;
  }

  &__body {
    position: relative;
    z-index: 1;
    padding: 16px 20px 0;
  }

  &__pill-wrap {
    display: flex;
    justify-content: center;
    margin-bottom: 16px;
  }

  &__pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: var(--radius-full);
    background: linear-gradient(90deg, rgba(245, 158, 11, 0.2) 0%, rgba(244, 63, 94, 0.2) 100%);
    border: 1px solid rgba(251, 191, 36, 0.3);
  }

  &__pill-text {
    font-size: 12px;
    font-weight: 500;
    color: #fde68a;
  }

  &__intro {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 20px;
  }

  &__title {
    font-size: 24px;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.25;
  }

  &__sub {
    margin-top: 8px;
    font-size: 14px;
    line-height: 1.6;
    color: rgba(255, 255, 255, 0.7);
    text-align: center;
  }

  &__media {
    position: relative;
    border-radius: var(--radius-lg);
    overflow: hidden;
    margin-bottom: 20px;
    box-shadow: 0 24px 48px rgba(15, 23, 42, 0.32);
  }

  &__media-img {
    width: 100%;
    height: 176px;
    display: block;
  }

  &__media-mask {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(0, 0, 0, 0) 55%, rgba(0, 0, 0, 0.45) 100%);
    pointer-events: none;
  }

  &__media-foot {
    position: absolute;
    left: 12px;
    right: 12px;
    bottom: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  &__creators {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  &__avatars {
    display: flex;
  }

  &__avatar {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid rgba(255, 255, 255, 0.6);

    &--1 {
      background: #f472b6;
    }

    &--2 {
      background: #60a5fa;
      margin-left: -6px;
    }

    &--3 {
      background: #fbbf24;
      margin-left: -6px;
    }
  }

  &__rating {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  &__media-text {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.8);
  }

  &__cta {
    position: relative;
    overflow: hidden;
    height: 56px;
    padding: 0 20px;
    font-size: 16px;
  }

  &__cta-text {
    position: relative;
    z-index: 1;
  }

  &__cta-shine {
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transform: translateX(-100%);
    transition: transform 700ms var(--ease-out);
  }

  &__cta:active &__cta-shine {
    transform: translateX(100%);
  }

  &__notes {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-top: 10px;
  }

  &__note {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);

    &--amber {
      color: #fcd34d;
      font-weight: 500;
    }
  }

  &__note-dot {
    color: rgba(255, 255, 255, 0.3);
    font-size: 12px;
  }
}

/* ============ 通用区块 ============ */
.section {
  padding: 16px 20px;
}

/* ============ 功能入口 ============ */
.entry-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.entry-card {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: 16px;
  display: flex;
  flex-direction: column;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);

  &:active {
    transform: scale(0.98);
    box-shadow: var(--shadow-md);
  }

  &__icon {
    width: 48px;
    height: 48px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 12px;
  }

  &__title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
  }

  &__desc {
    font-size: 12px;
    color: var(--text-tertiary);
  }
}

/* ============ 三步流程 ============ */
.steps {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-top: 20px;

  &__item {
    flex: 1;
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  &__line {
    position: absolute;
    top: 28px;
    left: 60%;
    width: 80%;
    height: 2px;
    opacity: 0.4;
    background: linear-gradient(90deg, var(--brand-primary-light), var(--brand-secondary));
  }

  &__circle {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: var(--bg-card);
    border: 2px solid var(--brand-primary-light);
    box-shadow: var(--shadow-sm);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 700;
    color: var(--brand-primary);

    &--done {
      background: var(--grad-brand);
      border-color: transparent;
      color: #ffffff;
    }
  }

  &__title {
    margin-top: 12px;
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary);
  }

  &__desc {
    margin-top: 4px;
    font-size: 12px;
    color: var(--text-tertiary);
  }

  &__media {
    margin-top: 24px;
    border-radius: var(--radius-md);
    overflow: hidden;
    box-shadow: var(--shadow-md);
  }

  &__media-img {
    width: 100%;
    height: 128px;
    display: block;
  }
}

/* ============ 热门模板 ============ */
.tpl-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  &__more {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 14px;
    font-weight: 500;
    color: var(--brand-primary);
  }

  &__arrow--up {
    transform: rotate(-90deg);
  }
}

.tpl-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.tpl-card {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-fast);

  &:active {
    transform: scale(0.98);
  }

  &__thumb {
    position: relative;
    aspect-ratio: 9 / 16;
    background: var(--grad-brand-soft);
    overflow: hidden;

    &--skeleton {
      background: var(--bg-hover);
    }
  }

  &__img {
    width: 100%;
    height: 100%;
    display: block;

    &--fallback {
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--grad-brand-soft);
    }
  }

  &__badge {
    position: absolute;
    top: 8px;
    left: 8px;
    z-index: 1;
    padding: 2px 8px;
    border-radius: var(--radius-full);
    background: var(--grad-hot);
    color: #ffffff;
    font-size: 10px;
    font-weight: 600;
  }

  &__usage {
    position: absolute;
    left: 8px;
    right: 8px;
    bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 4px 8px;
    border-radius: var(--radius-sm);
    background: rgba(0, 0, 0, 0.5);
    color: #ffffff;
    font-size: 10px;
  }

  &__usage-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  &__body {
    padding: 12px;
  }

  &__title {
    display: block;
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary);
  }

  &__sub {
    display: block;
    margin-top: 2px;
    font-size: 12px;
    color: var(--text-tertiary);
  }
}

.tpl-skeleton-line {
  height: 12px;
  border-radius: 6px;
  background: var(--bg-hover);

  &--short {
    width: 60%;
    margin-top: 8px;
  }
}

.tpl-empty {
  padding: 24px;
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  border: 1px dashed var(--border-medium);
  text-align: center;

  &__text {
    font-size: 13px;
    color: var(--text-tertiary);
  }
}

/* ============ 底部横幅 ============ */
.banner {
  position: relative;
  overflow: hidden;
  background: var(--grad-brand);
  border-radius: var(--radius-xl);
  padding: 20px;

  &::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 150px;
    height: 150px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
  }

  &__content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }

  &__title {
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
  }

  &__desc {
    margin-top: 4px;
    margin-bottom: 16px;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.8);
  }

  &__btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 10px 20px;
    border-radius: var(--radius-full);
    background: #ffffff;
    color: var(--brand-primary);
    font-size: 14px;
    font-weight: 600;
    box-shadow: var(--shadow-lg);
  }
}
</style>
