<template>
  <view class="app-page home">
    <view class="home__status" :style="{ height: statusBarHeight + 'px' }" />
    <view class="home__header" :style="heroBarStyle">
      <view class="home__brand">
        <view class="home__logo"><text>溪</text></view>
        <view class="home__brand-copy"><text class="home__brand-name">千溪</text><text class="home__brand-caption">AI 影像工作室</text></view>
      </view>
      <button tabindex="0" role="button" class="home__quota" @click="handleQuotaTap" @keydown.enter.prevent="handleQuotaTap" @keydown.space.prevent="handleQuotaTap"><AppIcon name="sparkles" :size="14" color="#B23A2E" /><text>{{ quotaText }}</text></button>
    </view>

    <view class="home__intro app-enter">
      <view class="home__eyebrow"><view class="home__dot" /><text>让每一个想法，都有画面</text></view>
      <view class="home__headline"><text>让灵感，</text><text>自成<text class="home__headline-accent">一片。</text></text></view>
      <text class="home__description">一条参考视频，或几张商品图。<text class="home__description-line">把接下来的创作，交给千溪 AI。</text></text>
    </view>

    <!-- 沿用本地品牌水墨图；明确标注视觉示意，避免误认为可播放的成片。 -->
    <view class="home__art-shell app-enter">
      <view class="home__art">
        <image class="home__art-image" src="/static/hero-ink.jpg" mode="aspectFill" alt="水墨山峦与溪水，千溪品牌视觉示意" />
        <view class="home__art-top"><text class="home__art-label">千溪 · 灵感视界</text><text class="home__art-index">〇 一</text></view>
        <view class="home__art-caption"><text class="home__art-verse">万千灵感，汇于一溪。</text><text class="home__art-note">品牌视觉示意</text></view>
      </view>
      <view class="home__art-meta"><view class="home__art-meta-item"><AppIcon name="layers" :size="14" color="#77746B" /><text>从素材到原创</text></view><text>{{ defaultResolution }} 画质可选</text></view>
    </view>

    <view class="home__action app-enter">
      <button tabindex="0" role="button" class="home__cta app-btn-brand" @click="goStudio" @keydown.enter.prevent="goStudio" @keydown.space.prevent="goStudio"><text>开始我的创作</text><view class="app-cta-icon"><AppIcon name="arrow-right" :size="18" color="#FFFFFF" /></view></button>
      <text class="home__action-note">{{ noteFreeText }} · 按步骤轻松上手</text>
    </view>

    <view class="home__steps">
      <view v-for="(step, index) in steps" :key="step.title" class="home__step"><text class="home__step-no">0{{ index + 1 }}</text><text class="home__step-title">{{ step.title }}</text><text class="home__step-desc">{{ step.desc }}</text></view>
    </view>

    <view class="home__section">
      <view class="home__section-head"><view><text class="home__kicker">灵感不设限</text><text class="app-section-title">你的创作，更多可能</text></view><text class="home__section-index">01 / 工具</text></view>
      <view class="home__tools">
        <button tabindex="0" role="button" v-for="entry in entries" :key="entry.key" class="home__tool" @click="openEntry(entry)" @keydown.enter.prevent="openEntry(entry)" @keydown.space.prevent="openEntry(entry)">
          <view class="home__tool-inner"><view class="home__tool-top"><view class="home__tool-icon" :style="{ background: entry.iconBg }"><AppIcon :name="entry.icon" :size="23" :color="entry.iconColor" /></view><AppIcon name="arrow-up-right" :size="16" color="#969187" /></view><text class="home__tool-title">{{ entry.title }}</text><text class="home__tool-desc">{{ entry.desc }}</text></view>
        </button>
      </view>
    </view>

    <view class="home__section">
      <view class="home__section-head"><view><text class="home__kicker">从一个好点子开始</text><text class="app-section-title">创作灵感库</text></view><button tabindex="0" role="button" v-if="templates.length > 4" class="home__more" @click="toggleAllTemplates" @keydown.enter.prevent="toggleAllTemplates" @keydown.space.prevent="toggleAllTemplates">{{ showAllTemplates ? '收起' : '查看全部' }}<AppIcon name="chevron-right" :size="14" color="#77746B" /></button></view>
      <view v-if="templatesLoading" class="home__templates" aria-label="模板加载中">
        <view v-for="n in 4" :key="n" class="home__template home__template--skeleton"><view class="home__skeleton-cover" /><view class="home__skeleton-line" /></view>
      </view>
      <view v-else-if="templatesError" class="home__empty" aria-live="polite"><view class="home__empty-icon"><AppIcon name="alert-circle" :size="24" color="#B23A2E" /></view><text class="home__empty-title">灵感库暂时无法加载</text><text class="home__empty-desc">{{ templatesError }}</text><button tabindex="0" role="button" class="home__empty-link" @click="loadTemplates" @keydown.enter.prevent="loadTemplates" @keydown.space.prevent="loadTemplates">重新加载<AppIcon name="refresh-cw" :size="14" color="#B23A2E" /></button></view>
      <view v-else-if="visibleTemplates.length" class="home__templates">
        <button tabindex="0" role="button" v-for="item in visibleTemplates" :key="item.id" class="home__template" @click="useTemplate(item)" @keydown.enter.prevent="useTemplate(item)" @keydown.space.prevent="useTemplate(item)"><view class="home__template-cover"><image v-if="item.cover" class="home__template-img" :src="item.cover" mode="aspectFill" :alt="item.title" /><view v-else class="home__template-fallback"><AppIcon name="film" :size="30" color="#8A5A3B" /></view><text v-if="templateBadge(item)" class="home__template-badge">{{ templateBadge(item) }}</text><text class="home__template-duration">{{ item.duration }}s</text></view><text class="home__template-title app-truncate">{{ item.title }}</text><view class="home__template-meta"><text>{{ item.category || '通用' }}</text><text>{{ formatCount(item.use_count) }} 次使用</text></view></button>
      </view>
      <view v-else class="home__empty"><view class="home__empty-icon"><AppIcon name="image" :size="24" color="#8A5A3B" /></view><text class="home__empty-title">好灵感，正在路上</text><text class="home__empty-desc">模板整理中，你也可以直接上传素材开始创作。</text><button tabindex="0" role="button" class="home__empty-link" @click="goStudio" @keydown.enter.prevent="goStudio" @keydown.space.prevent="goStudio">用自己的素材创作<AppIcon name="arrow-right" :size="14" color="#B23A2E" /></button></view>
    </view>
    <view class="home__footer"><text>千溪</text><text>让创作，自然发生。</text></view>
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

// 账号与额度继续由共享 Store 管理。
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
const noteFreeText = computed(() => '支持本地上传与视频直链')

// 工具入口仅映射已实现的页面，不增加演示功能。
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

// 首页为流程说明，不将尚未执行的步骤标记为已完成。
const steps = [
  { title: '上传素材', desc: '视频或商品图片' },
  { title: '交给 AI', desc: '自动拆解与创作' },
  { title: '收获成片', desc: '在作品页查看' },
]

// 模板始终读取后台上架数据，为空时提供真实空态。
const templates = ref([])
const templatesLoading = ref(false)
// 请求失败单独展示恢复入口，不把网络错误描述为模板整理中。
const templatesError = ref('')
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
  templatesError.value = ''
  try {
    let res = await api.template.recommend.post({}, { suppressGlobalError: true })
    if (res?.code !== 1 || !Array.isArray(res.data)) throw new Error(res?.message || '请检查网络后重试')
    let list = res.data
    if (!list.length) {
      res = await api.template.list.post(
        { pageNum: 1, pageSize: 8, sort_type: 1 },
        { suppressGlobalError: true }
      )
      if (res?.code !== 1 || !Array.isArray(res.data)) throw new Error(res?.message || '请检查网络后重试')
      list = res.data
    }
    templates.value = list
  } catch (err) {
    console.error('加载热门模板失败', err)
    templates.value = []
    templatesError.value = err?.message || '请检查网络后重试'
  } finally {
    templatesLoading.value = false
  }
}

/** 切换模板展开状态，保留当前页面位置。 */
function toggleAllTemplates() {
  showAllTemplates.value = !showAllTemplates.value
}

/** 未登录时所有创作入口先引导登录，登录后回到首页继续。 */
function requireLogin() {
  if (userStore.isLoggedIn) return true
  go(toLoginPath(currentPagePath()))
  return false
}

/** 打开所选工具，登录要求由工具页统一处理。 */
function openEntry(entry) {
  go(entry.path)
}

/** 进入视频创作工作台。 */
function goStudio() {
  go('/pages/studio/index')
}

/** 携带真实模板编号进入工作台。 */
function useTemplate(item) {
  go({ path: '/pages/studio/index', query: { template_id: item.id } })
}

/** 额度入口登录后进入充值页。 */
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

/** 刷新生成配置、真实模板与账号额度。 */
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
.home { padding-left: var(--page-gutter); padding-right: var(--page-gutter); }
.home__header { display: flex; align-items: center; justify-content: space-between; min-height: 60px; gap: 12px; }
.home__brand { display: flex; align-items: center; gap: 10px; }
.home__logo { display: flex; align-items: center; justify-content: center; width: 38px; height: 38px; border-radius: 12px; color: #fffefa; background: var(--brand-primary); box-shadow: inset 0 1px 0 rgba(255,255,255,.25); font: 24px var(--font-serif); }
.home__brand-copy { display: flex; flex-direction: column; gap: 1px; }
.home__brand-name { font: 700 20px var(--font-serif); letter-spacing: 3px; line-height: 1.3; }
.home__brand-caption { font-size: 10px; color: var(--text-tertiary); letter-spacing: 1px; }
.home__quota { margin: 0; padding: 0 12px; min-height: 44px; display: flex; align-items: center; gap: 6px; background: var(--paper-card); border-radius: 99px; box-shadow: var(--shadow-sm); font-size: 12px; color: var(--text-secondary); line-height: 1.4; }
.home button::after { border: none; }
.home__intro { padding: 30px 3px 24px; }
.home__eyebrow { display: flex; align-items: center; gap: 7px; font-size: 11px; letter-spacing: 2px; color: var(--text-tertiary); }
.home__dot { width: 5px; height: 5px; background: var(--brand-primary); border-radius: 50%; }
.home__headline { display: flex; flex-direction: column; margin-top: 16px; font: 500 42px/1.28 var(--font-serif); letter-spacing: 2px; }
.home__headline-accent { color: var(--brand-primary); }
.home__description { display: block; margin-top: 14px; font-size: 13px; line-height: 1.9; color: var(--text-tertiary); }
.home__description-line { display: block; }
.home__art-shell { padding: 6px; border-radius: 24px; background: var(--paper-100); box-shadow: var(--shadow-sm); animation-delay: 80ms; }
.home__art { height: 186px; position: relative; border-radius: 18px; overflow: hidden; background: #eae6dc; }
.home__art-image { width: 100%; height: 100%; display: block; }
.home__art-top { position: absolute; inset: 16px 16px auto; display: flex; align-items: center; justify-content: space-between; color: #5e584c; }
.home__art-label { font-size: 10px; letter-spacing: 2px; }
.home__art-index { font: 13px var(--font-serif); }
.home__art-caption { position: absolute; inset: auto 16px 13px; display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.home__art-verse { font: 15px var(--font-serif); color: #4d493e; letter-spacing: 1px; }
.home__art-note { font-size: 9px; color: #716b60; }
.home__art-meta { padding: 11px 8px 6px; display: flex; justify-content: space-between; align-items: center; color: var(--text-tertiary); font-size: 10px; }
.home__art-meta-item { display: flex; align-items: center; gap: 6px; }
.home__action { margin-top: 20px; animation-delay: 160ms; }
.home__cta { width: 100%; height: 54px; padding: 7px 10px 7px 24px; justify-content: space-between; font-size: 15px; letter-spacing: 1px; }
.home__cta .app-cta-icon { width: 38px; height: 38px; transition: transform var(--transition-base); }
.home__cta:active .app-cta-icon { transform: translateX(2px); }
.home__action-note { display: block; text-align: center; margin-top: 10px; font-size: 10px; color: var(--text-tertiary); }
.home__steps { margin-top: 28px; padding: 18px 0; display: flex; border-top: 1px solid var(--line-1); border-bottom: 1px solid var(--line-1); }
.home__step { flex: 1; display: flex; flex-direction: column; padding-left: 14px; border-left: 1px solid var(--line-1); }
.home__step:first-child { padding-left: 2px; border-left: none; }
.home__step-no { font: 15px var(--font-serif); color: var(--brand-secondary); }
.home__step-title { margin-top: 7px; font-size: 13px; font-weight: 600; }
.home__step-desc { margin-top: 3px; font-size: 10px; color: var(--text-tertiary); }
.home__section { margin-top: 34px; }
.home__section-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 10px; margin-bottom: 18px; }
.home__section-head > view { display: flex; flex-direction: column; gap: 5px; }
.home__kicker { color: var(--text-tertiary); font-size: 10px; letter-spacing: 1.5px; }
.home__section-index { padding-bottom: 4px; color: var(--text-muted); font-size: 9px; white-space: nowrap; }
.home__tools { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.home__tool { margin: 0; padding: 5px; text-align: left; border-radius: 22px; background: var(--paper-100); line-height: 1.5; transition: transform var(--transition-base); }
.home__tool:active { transform: scale(.975); }
.home__tool-inner { padding: 14px 11px; border-radius: 17px; background: var(--paper-card); box-shadow: inset 0 1px 0 #fff; }
.home__tool-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.home__tool-icon { width: 40px; height: 40px; border-radius: 13px; display: flex; align-items: center; justify-content: center; }
.home__tool-title { display: block; font-size: 15px; font-weight: 600; }
.home__tool-desc { display: block; margin-top: 5px; font-size: 10px; color: var(--text-tertiary); }
.home__more { display: flex; align-items: center; padding: 8px 0 4px 8px; min-height: 44px; font-size: 11px; margin: 0; background: transparent; color: var(--text-tertiary); gap: 4px; line-height: 1.5; }
.home__templates { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px 12px; }
.home__template { min-width: 0; padding: 5px 5px 12px; margin: 0; text-align: left; background: var(--paper-card); border-radius: 20px; line-height: 1.5; }
.home__template-cover { position: relative; height: 180px; border-radius: 15px; overflow: hidden; background: var(--paper-100); }
.home__template-img, .home__template-fallback { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
.home__template-badge { position: absolute; top: 8px; left: 8px; border-radius: 99px; padding: 4px 8px; background: var(--paper-card); font-size: 10px; }
.home__template-duration { position: absolute; bottom: 8px; right: 8px; padding: 2px 7px; border-radius: 99px; background: rgba(37,36,31,.65); color: white; font-size: 10px; }
.home__template-title { display: block; padding: 11px 6px 0; font-size: 13px; font-weight: 600; }
.home__template-meta { display: flex; justify-content: space-between; padding: 5px 6px 0; color: var(--text-tertiary); font-size: 9px; }
.home__skeleton-cover { height: 180px; border-radius: 15px; background: var(--paper-100); }
.home__skeleton-line { height: 10px; width: 68%; margin: 14px 6px 0; border-radius: 5px; background: var(--paper-100); }
.home__empty { display: flex; flex-direction: column; align-items: center; padding: 30px 16px 20px; border: 6px solid var(--paper-100); border-radius: 24px; background: var(--paper-card); }
.home__empty-icon { width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; border-radius: 17px; background: var(--paper-100); }
.home__empty-title { margin-top: 14px; font-size: 15px; font-weight: 600; }
.home__empty-desc { margin-top: 7px; text-align: center; font-size: 11px; color: var(--text-tertiary); line-height: 1.8; }
.home__empty-link { display: flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px; margin: 9px 0 0; background: transparent; color: var(--brand-primary); font-size: 12px; }
.home__footer { display: flex; align-items: center; justify-content: space-between; padding: 32px 4px 12px; color: var(--text-muted); font-size: 10px; }
.home__footer > text:first-child { font: 17px var(--font-serif); letter-spacing: 4px; }
@media (max-width: 360px) { .home__headline { font-size: 38px; } .home__tool-desc { font-size: 9px; } .app-section-title { font-size: 21px; } }
</style>
