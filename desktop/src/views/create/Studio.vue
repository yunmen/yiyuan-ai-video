<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

// 创作方式：视频复刻 / 九宫格出片。
// 图标使用设计稿的线性图标（stroke=currentColor，激活态自动跟随品牌色着色）。
const tabs = [
  {
    key: 'replicate',
    label: '视频复刻',
    desc: '对标爆款一键复刻',
    to: '/studio/replicate',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>`
  },
  {
    key: 'storyboard',
    label: '九宫格出片',
    desc: '九张图生成视频',
    to: '/studio/storyboard',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>`
  },
]
const active = computed(() => {
  if (route.path.startsWith('/studio/replicate')) return 'replicate'
  if (route.path.startsWith('/studio/storyboard')) return 'storyboard'
  return 'replicate'
})
</script>

<template>
  <div class="studio">
    <!-- 移动端顶部栏（返回 + 居中标题）；桌面端由全局 AppHeader 承担，此处隐藏 -->
    <div class="page-head">
      <button class="ph-back" aria-label="返回" @click="router.push('/home')">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
      </button>
      <h1 class="ph-title">创作工作台</h1>
      <span class="ph-right"></span>
    </div>

    <div class="studio-wrap">
      <!-- 创作方式选择：2 列卡片（图标 + 标题 + 一行描述），激活态品牌着色 -->
      <div class="mode-tabs">
        <button
          v-for="t in tabs"
          :key="t.key"
          type="button"
          class="mode-tab"
          :class="{ on: active === t.key }"
          @click="router.push(t.to)"
        >
          <span class="mode-icon" v-html="t.icon"></span>
          <span class="mode-title">{{ t.label }}</span>
          <span class="mode-desc">{{ t.desc }}</span>
        </button>
      </div>

      <!-- 内容区：视频复刻 / 九宫格出片表单（子页面自带样式与间距） -->
      <div class="studio-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style scoped>
.studio {
  min-height: 100vh;
  background: var(--bg);
  /* 移动端为底部固定 tabbar 预留空间，避免内容被遮挡 */
  padding-bottom: calc(var(--nav-h) + 24px + env(safe-area-inset-bottom));
}

.studio-wrap {
  max-width: var(--page-max);
  margin: 0 auto;
}

/* 页面自带顶栏仅在移动端展示 */
@media (min-width: 768px) {
  .page-head { display: none; }
}

/* 创作方式选择器：2 列卡片 */
.mode-tabs {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--s-2);
  padding: var(--s-4);
}

.mode-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 12px;
  border: 1.5px solid var(--border-light);
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  font-family: inherit;
  cursor: pointer;
  transition: border-color var(--transition-fast), background var(--transition-fast),
              box-shadow var(--transition-fast), transform var(--transition-fast);
}
.mode-tab:hover {
  border-color: var(--brand);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}
.mode-tab:active { transform: scale(.98); }
.mode-tab.on {
  border-color: var(--brand);
  background: var(--brand-primary-light);
}

/* 图标：圆角方块容器，内置 28px 线性图标 */
.mode-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--line-2);
  color: var(--body-2);
  transition: background var(--transition-fast), color var(--transition-fast), box-shadow var(--transition-fast);
}
.mode-icon svg { width: 28px; height: 28px; }
.mode-tab.on .mode-icon {
  background: var(--bg-card);
  color: var(--brand);
  box-shadow: var(--shadow-xs);
}

.mode-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-3);
  transition: color var(--transition-fast);
}
.mode-tab.on .mode-title {
  color: var(--brand);
  font-weight: 700;
}

.mode-desc {
  font-size: 11px;
  line-height: 1.4;
  text-align: center;
  color: var(--weak);
  transition: color var(--transition-fast);
}
.mode-tab.on .mode-desc { color: var(--brand-400); }

/* 桌面端：内容居中加宽，选择器与下方表单宽度对齐 */
@media (min-width: 768px) {
  .studio { padding-bottom: var(--s-7); }
  .mode-tabs {
    gap: var(--s-4);
    padding: var(--s-5) var(--s-4);
    max-width: 720px;   /* 与子页面表单（.wrap 720px）保持一致，视觉对齐 */
    margin: 0 auto;
  }
  .mode-tab { padding: var(--s-5) var(--s-4); }
}
</style>
