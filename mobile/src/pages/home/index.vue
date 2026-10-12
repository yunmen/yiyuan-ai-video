<template>
  <view class="app-page home">
    <!-- hero 渐变头图：状态栏 + 品牌行 + 主 CTA -->
    <view class="hero">
      <view class="hero__statusbar" :style="{ height: statusBarHeight + 'px' }" />

      <view class="hero__bar" :style="heroBarStyle">
        <view class="hero__brand">
          <view class="hero__logo">
            <text class="hero__logo-char">溪</text>
          </view>
          <text class="hero__brand-name">千溪</text>
        </view>
        <view class="hero__quota" role="button" @click="handleQuotaTap">
          <AppIcon name="star" :size="12" color="#B23A2E" :stroke-width="2.5" />
          <text>{{ quotaText }}</text>
        </view>
      </view>

      <view class="hero__seal" aria-hidden="true">千溪</view>
      <view class="hero__body">
        <view class="hero__eyebrow">AI 影像工坊 · 让灵感直接成片</view>
        <view class="hero__intro">
          <text class="hero__title">把灵感，直接变成视频</text>
          <text class="hero__title">从素材到成片只需一步</text>
          <text class="hero__sub">上传一条参考视频或几张商品图，AI 自动拆解、改写并生成你的原创内容</text>
        </view>

        <view class="hero__media">
          <image class="hero__media-img" src="/static/hero-ink.jpg" mode="aspectFill" />
          <view class="hero__media-overlay" />
          <view class="hero__play-badge">
            <AppIcon name="play" :size="14" color="#FFFFFF" :stroke-width="2.5" />
            <text>AI 生成案例</text>
          </view>
          <view class="hero__result-card">
            <text class="hero__result-label">参考素材</text>
            <text class="hero__result-arrow">→</text>
            <text class="hero__result-label hero__result-label--accent">原创成片</text>
          </view>
          <view class="hero__media-foot">
            <view class="hero__chip">
              <AppIcon name="sparkles" :size="11" color="#B23A2E" :stroke-width="2.5" />
              <text class="hero__chip-text">自动拆解画面与文案</text>
            </view>
            <view class="hero__chip">
              <AppIcon name="star" :size="11" color="#B23A2E" :stroke-width="2.5" />
              <text class="hero__chip-text">{{ defaultResolution }}</text>
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
            <AppIcon name="check" :size="12" color="#9C9488" :stroke-width="2.5" />
            <text>手机号验证码登录</text>
          </view>
          <text class="hero__note-dot">·</text>
          <view class="hero__note">
            <AppIcon name="check" :size="12" color="#9C9488" :stroke-width="2.5" />
            <text>生成失败自动返还</text>
          </view>
          <text class="hero__note-dot">·</text>
          <view class="hero__note hero__note--amber">
            <AppIcon name="sparkles" :size="12" color="#B98236" :stroke-width="2.5" />
            <text>{{ noteFreeText }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 首屏新手引导：紧跟主 CTA，解释用户如何从素材走到成片 -->
    <view class="section process-section process-section--first-screen">
      <view class="process-head">
        <view class="sec-head">
          <view class="sec-head__mark" />
          <text class="app-section-title">三步生成爆款视频</text>
        </view>
        <text class="process-head__hint">简单三步，马上出片</text>
      </view>
      <view class="steps">
        <view v-for="(step, index) in steps" :key="step.title" class="steps__item">
          <view v-if="index < steps.length - 1" class="steps__line" />
          <view class="steps__circle" :class="{ 'steps__circle--done': step.done }">
            <AppIcon v-if="step.done" name="check" :size="24" color="#FFFFFF" :stroke-width="2.5" />
            <text v-else>{{ index + 1 }}</text>
          </view>
          <text class="steps__title">{{ step.title }}</text>
          <text class="steps__desc">{{ step.desc }}</text>
        </view>
      </view>
    </view>

    <!-- 快速开始 -->
    <view class="section quick-start-section">
      <view class="section-kicker">
        <text class="section-kicker__eyebrow">QUICK START</text>
        <text class="section-kicker__title">你想先做什么？</text>
      </view>
      <view class="quick-actions">
        <view class="quick-action quick-action--primary" role="button" @click="goStudio">
          <view class="quick-action__copy">
            <text class="quick-action__title">一键复刻视频</text>
            <text class="quick-action__desc">上传参考视频，快速生成原创成片</text>
            <view class="quick-action__link">
              <text>立即开始</text>
              <AppIcon name="arrow-right" :size="14" color="#FFFFFF" :stroke-width="2.5" />
            </view>
          </view>
          <view class="quick-action__visual">
            <AppIcon name="wand" :size="32" color="#FFFFFF" :stroke-width="1.6" />
          </view>
        </view>
        <view class="quick-action quick-action--secondary" role="button" @click="openEntry(entries[0])">
          <view class="quick-action__mini-icon"><AppIcon name="user" :size="20" color="#8A5A3B" /></view>
          <text class="quick-action__title">数字人口播</text>
          <text class="quick-action__desc">不用出镜，也能稳定输出</text>
          <AppIcon class="quick-action__arrow" name="chevron-right" :size="16" color="#B7AB92" />
        </view>
      </view>
    </view>

    <!-- 功能入口 -->
    <view class="section tools-section">
      <view class="section-kicker section-kicker--compact">
        <text class="section-kicker__eyebrow">MORE TOOLS</text>
        <text class="section-kicker__title">更多创作工具</text>
      </view>
      <view class="entry-grid">
        <view
          v-for="entry in entries.slice(1)"
          :key="entry.key"
          class="entry-card"
          role="button"
          @click="openEntry(entry)"
        >
          <view class="entry-card__top">
            <view class="entry-card__icon" :style="{ background: entry.iconBg }">
              <AppIcon :name="entry.icon" :size="22" :color="entry.iconColor" />
            </view>
            <AppIcon name="chevron-right" :size="16" color="#B7AB92" />
          </view>
          <text class="entry-card__title">{{ entry.title }}</text>
          <text class="entry-card__desc">{{ entry.desc }}</text>
        </view>
      </view>
    </view>

    <!-- 热门模板 -->
    <view class="section">
      <view class="tpl-head">
        <view class="sec-head">
          <view class="sec-head__mark" />
          <text class="app-section-title">热门模板</text>
        </view>
        <view v-if="templates.length > 4" class="tpl-head__more" role="button" @click="toggleAllTemplates">
          <text>{{ showAllTemplates ? '收起' : '查看全部' }}</text>
          <AppIcon
            name="chevron-right"
            :size="14"
            color="#B23A2E"
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
              <AppIcon name="film" :size="28" color="#E0AFA6" :stroke-width="2" />
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
import { getStatusBarHeight, getNavBarMetrics } from '@/utils/system'
import { refreshCurrentUserProfile } from '@/utils/session'
import { formatCount } from '@/utils/task'

const userStore = useUserStore()
const { loadGenConfig, defaultResolution } = useGenConfig()

const statusBarHeight = ref(getStatusBarHeight())
// 小程序右上角有系统胶囊：hero 右槽（额度胶囊）必须让出空间，否则被胶囊盖住
const heroBarStyle = ref({})
// #ifdef MP-WEIXIN
heroBarStyle.value = { paddingRight: getNavBarMetrics().paddingRight + 'px' }
// #endif

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
    key: 'digital',
    title: '数字人口播',
    desc: '真人形象 · 智能播报',
    icon: 'user',
    iconColor: '#8A5A3B',
    iconBg: 'linear-gradient(135deg, rgba(138, 90, 59,0.1) 0%, rgba(138, 90, 59,0.1) 100%)',
    path: '/pages/digital/index',
  },
  {
    key: 'render',
    title: '视频换口播',
    desc: '一键替换 · 多语言支持',
    icon: 'volume',
    iconColor: '#3E6B7A',
    iconBg: 'linear-gradient(135deg, rgba(62, 107, 122,0.1) 0%, rgba(178, 58, 46,0.1) 100%)',
    path: '/pages/render/index',
  },
  {
    key: 'aiflavor',
    title: '文案去味',
    desc: 'AI优化 · 爆款文案',
    icon: 'edit',
    iconColor: '#4B7A5A',
    iconBg: 'linear-gradient(135deg, rgba(75, 122, 90,0.1) 0%, rgba(62, 107, 122,0.1) 100%)',
    path: '/pages/aiflavor/index',
  },
  {
    key: 'grid',
    title: '九宫格成片',
    desc: '提示词/照片→九宫格',
    icon: 'image',
    iconColor: '#B98236',
    iconBg: 'linear-gradient(135deg, rgba(185, 130, 54,0.1) 0%, rgba(178, 58, 46,0.1) 100%)',
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
  background:
    radial-gradient(circle at 88% 12%, rgba(178, 58, 46, 0.08) 0, rgba(178, 58, 46, 0) 25%),
    linear-gradient(180deg, #f4eee2 0%, #fbf8f2 100%);
  padding-bottom: 32px;

  &::before {
    content: '';
    position: absolute;
    top: 118px;
    right: -42px;
    width: 210px;
    height: 96px;
    border-top: 1px solid rgba(62, 107, 122, 0.2);
    border-radius: 50%;
    transform: rotate(-16deg);
    pointer-events: none;
  }

  &::after {
    content: '';
    position: absolute;
    left: -58px;
    bottom: 78px;
    width: 180px;
    height: 92px;
    border-bottom: 1px solid rgba(75, 122, 90, 0.18);
    border-radius: 50%;
    transform: rotate(12deg);
    pointer-events: none;
  }

  &__statusbar {
    width: 100%;
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
    border-radius: 6px;
    background: var(--grad-brand);
    box-shadow: 0 2px 8px rgba(178, 58, 46, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  &__logo-char {
    font-family: var(--font-serif);
    font-size: 19px;
    font-weight: 700;
    line-height: 1;
    color: #ffffff;
  }

  &__brand-name {
    font-family: var(--font-serif);
    font-size: 19px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--text-primary);
  }

  /* 额度：纸底墨线小胶囊，取代原深色玻璃态 */
  &__quota {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 5px 11px;
    border-radius: var(--radius-full);
    background: var(--bg-card);
    border: 1px solid var(--border-medium);
    color: var(--text-secondary);
    font-size: 12px;
  }

  &__seal {
    position: absolute;
    top: 92px;
    right: 18px;
    z-index: 0;
    width: 58px;
    height: 58px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px solid rgba(178, 58, 46, 0.58);
    border-radius: 5px;
    color: rgba(178, 58, 46, 0.72);
    font-family: var(--font-serif);
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.14em;
    transform: rotate(8deg);
    opacity: 0.76;
  }

  &__body {
    position: relative;
    z-index: 1;
    padding: 16px 20px 0;
  }

  &__eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    margin-bottom: 10px;
    color: var(--brand-primary);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.16em;

    &::before {
      content: '';
      width: 20px;
      height: 1px;
      background: var(--brand-primary);
      opacity: 0.7;
    }
  }

  &__intro {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    margin-bottom: 18px;
    padding-left: 12px;

    &::before {
      content: '';
      position: absolute;
      top: 4px;
      bottom: 4px;
      left: 0;
      width: 2px;
      border-radius: 2px;
      background: linear-gradient(180deg, var(--brand-primary), rgba(178, 58, 46, 0.12));
    }
  }

  &__title {
    font-family: var(--font-serif);
    font-size: 27px;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: var(--text-primary);
    line-height: 1.4;
  }

  &__sub {
    margin-top: 10px;
    font-size: 13.5px;
    line-height: 1.75;
    color: var(--text-tertiary);
  }

  /* 山水卷轴：纸本留白之上，细墨线一框 */
  &__media {
    position: relative;
    border-radius: var(--radius-lg);
    overflow: hidden;
    margin-bottom: 20px;
    border: 1px solid rgba(62, 107, 122, 0.24);
    box-shadow: 0 10px 24px rgba(62, 107, 122, 0.12), var(--shadow-md);

    &::before {
      content: '';
      position: absolute;
      inset: 8px;
      z-index: 1;
      border: 1px solid rgba(255, 253, 249, 0.45);
      border-radius: calc(var(--radius-lg) - 4px);
      pointer-events: none;
    }
  }

  &__media-img {
    width: 100%;
    height: 176px;
    display: block;
    filter: saturate(0.82) contrast(1.04);
  }

  &__media-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(31, 29, 26, 0.08) 15%, rgba(31, 29, 26, 0.03) 42%, rgba(31, 29, 26, 0.62) 100%);
  }

  &__play-badge {
    position: absolute;
    top: 14px;
    left: 14px;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    border: 1px solid rgba(255, 255, 255, 0.35);
    border-radius: var(--radius-full);
    background: rgba(31, 29, 26, 0.48);
    color: #ffffff;
    font-size: 11px;
    font-weight: 600;
  }

  &__result-card {
    position: absolute;
    top: 48px;
    right: 14px;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 7px 10px;
    border: 1px solid rgba(255, 255, 255, 0.48);
    border-radius: var(--radius-sm);
    background: rgba(255, 253, 249, 0.88);
    box-shadow: 0 5px 14px rgba(31, 29, 26, 0.13);
  }

  &__result-label {
    color: var(--text-secondary);
    font-size: 10px;
    font-weight: 600;

    &--accent {
      color: var(--brand-primary);
    }
  }

  &__result-arrow {
    color: var(--brand-primary);
    font-size: 13px;
    font-weight: 700;
  }

  &__media-foot {
    position: absolute;
    left: 10px;
    right: 10px;
    bottom: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  /* 图上信息改为纸白小胶囊，浅底墨字，不再用深色蒙层 */
  &__chip {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px;
    border-radius: var(--radius-full);
    background: rgba(255, 253, 249, 0.88);
    border: 1px solid var(--border-light);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
  }

  &__chip-text {
    font-size: 11px;
    color: var(--text-secondary);
  }

  &__avatars {
    display: flex;
  }

  &__avatar {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    border: 1.5px solid #fffdf9;

    &--1 {
      background: #b23a2e;
    }

    &--2 {
      background: #8a5a3b;
      margin-left: -6px;
    }

    &--3 {
      background: #3e6b7a;
      margin-left: -6px;
    }
  }

  &__cta {
    position: relative;
    overflow: hidden;
    height: 52px;
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
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.28), transparent);
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
    flex-wrap: wrap;
    gap: 8px 10px;
    margin-top: 14px;
  }

  &__note {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: var(--text-tertiary);

    &--amber {
      color: #b98236;
      font-weight: 500;
    }
  }

  &__note-dot {
    color: var(--border-strong);
    font-size: 12px;
  }
}

/* ============ 快速开始 ============ */
.quick-start-section {
  padding-top: 10px;
  padding-bottom: 8px;
}

.section-kicker {
  display: block;
  margin-bottom: 12px;

  &--compact {
    margin-bottom: 12px;
  }

  &__eyebrow {
    display: block;
    color: var(--brand-primary);
    font-size: 10px;
    font-weight: 700;
    line-height: 1.2;
    letter-spacing: 0.16em;
  }

  &__title {
    display: block;
    margin-top: 4px;
    color: var(--text-primary);
    font-family: var(--font-serif);
    font-size: 19px;
    font-weight: 700;
    letter-spacing: 0.04em;
  }
}

.quick-actions {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 10px;
}

.quick-action {
  position: relative;
  min-height: 144px;
  overflow: hidden;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);

  &:active {
    transform: translateY(1px) scale(0.99);
    box-shadow: var(--shadow-md);
  }

  &--primary {
    display: flex;
    justify-content: space-between;
    padding: 18px 14px 16px 16px;
    background: linear-gradient(135deg, #b23a2e 0%, #8f2f26 100%);
    color: #ffffff;
  }

  &--secondary {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: 16px 14px;
    background: var(--bg-card);
    border: 1px solid var(--border-light);
  }

  &__copy {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }

  &__title {
    display: block;
    font-family: var(--font-serif);
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.04em;
  }

  &__desc {
    display: block;
    max-width: 138px;
    margin-top: 7px;
    min-height: 34px;
    font-size: 11px;
    line-height: 1.55;
    color: rgba(255, 255, 255, 0.78);
  }

  &--secondary &__desc {
    color: var(--text-tertiary);
  }

  &__link {
    display: flex;
    align-items: center;
    gap: 5px;
    margin-top: 14px;
    font-size: 12px;
    font-weight: 600;
  }

  &__visual {
    position: absolute;
    right: -8px;
    bottom: -10px;
    width: 84px;
    height: 84px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
    transform: rotate(-12deg);
  }

  &__mini-icon {
    width: 38px;
    height: 38px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 13px;
    border-radius: var(--radius-md);
    background: rgba(138, 90, 59, 0.1);
  }

  &__arrow {
    position: absolute;
    top: 16px;
    right: 12px;
  }
}

/* ============ 通用区块 ============ */
.section {
  padding: 16px 20px;
}

.process-section {
  padding-top: 10px;
  padding-bottom: 8px;
}

.process-section--first-screen {
  margin: 0 20px;
  padding: 14px 14px 12px;
  border: 1px solid rgba(178, 58, 46, 0.14);
  border-radius: var(--radius-lg);
  background: rgba(255, 252, 246, 0.9);
  box-shadow: 0 4px 16px rgba(94, 65, 39, 0.06);
}

.process-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.process-head__hint {
  flex-shrink: 0;
  color: var(--text-tertiary);
  font-size: 10px;
}

/* 章节标题：朱砂短竖为记，取「点睛」之意 */
.sec-head {
  display: flex;
  align-items: center;
  gap: 10px;

  &__mark {
    width: 3px;
    height: 18px;
    border-radius: 2px;
    flex-shrink: 0;
    background: var(--brand-primary);
  }
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

  &__top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 14px;
  }

  &__icon {
    width: 44px;
    height: 44px;
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  &__title {
    font-family: var(--font-serif);
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.04em;
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
    /* 9:16 撑高：不用 aspect-ratio，旧版小程序内核不支持会导致封面塌陷（skeleton 共用） */
    padding-top: 177.7778%;
    background: var(--grad-brand-soft);
    overflow: hidden;

    &--skeleton {
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
@media screen and (max-width: 480px) {
  .hero {
    padding-bottom: 24px;
  }

  .hero__bar {
    padding: 10px var(--page-gutter);
  }

  .hero__body {
    padding: 12px var(--page-gutter) 0;
  }

  .hero__seal {
    top: 84px;
    right: 16px;
    width: 50px;
    height: 50px;
    font-size: 15px;
  }

  .hero__eyebrow {
    margin-bottom: 8px;
    font-size: 10px;
  }

  .hero__intro {
    margin-bottom: 14px;
  }

  .hero__title {
    font-size: clamp(24px, 7vw, 29px);
    line-height: 1.28;
    letter-spacing: 0.04em;
  }

  .hero__sub {
    margin-top: 8px;
    font-size: 13px;
    line-height: 1.55;
  }

  .hero__media {
    margin-bottom: 14px;
    border-radius: 8px;
  }

  .hero__media-img {
    height: clamp(148px, 43vw, 190px);
  }

  .hero__media-foot {
    left: 8px;
    right: 8px;
    bottom: 8px;
    gap: 6px;
  }

  .hero__chip {
    min-width: 0;
    padding: 4px 7px;
  }

  .hero__chip-text {
    max-width: 118px;
    overflow: hidden;
    font-size: 10px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .hero__cta {
    height: 48px;
    border-radius: 6px;
  }

  .hero__notes {
    margin-top: 10px;
    gap: 4px 7px;
  }

  .hero__note,
  .hero__note-dot {
    font-size: 10px;
  }

  .section {
    padding: 14px var(--page-gutter);
  }

  .entry-grid {
    gap: 8px;
  }

  .entry-card {
    min-height: 112px;
    padding: 12px;
    border-radius: 8px;
  }

  .entry-card__top {
    margin-bottom: 10px;
  }

  .entry-card__icon {
    width: 38px;
    height: 38px;
  }

  .entry-card__title {
    font-size: 15px;
  }

  .steps {
    margin-top: 14px;
  }

  .steps__circle {
    width: 44px;
    height: 44px;
    font-size: 16px;
  }

  .steps__line {
    top: 22px;
  }

  .steps__title {
    margin-top: 8px;
    font-size: 13px;
  }

  .steps__desc {
    font-size: 11px;
    text-align: center;
  }

  .steps__media {
    margin-top: 16px;
  }

  .tpl-grid {
    gap: 8px;
  }

  .tpl-card {
    border-radius: 8px;
  }

  .tpl-card__body {
    padding: 10px;
  }
}

</style>
