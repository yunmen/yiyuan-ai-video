<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const tabs = [
  {
    key: 'replicate',
    label: '视频复刻',
    desc: '上传对标视频或选平台模板',
    sub: '换产品 · 换人物 · 换场景',
    to: '/studio/replicate',
    accent: '#FF4D1C',
    icon: `<svg viewBox="0 0 48 48" fill="none"><rect x="4" y="4" width="40" height="40" rx="12" fill="#FFF0EA"/><rect x="10" y="14" width="22" height="18" rx="4" fill="none" stroke="#FF4D1C" stroke-width="2.2"/><path d="M32 19L40 15V33L32 29V19Z" fill="none" stroke="#FF4D1C" stroke-width="2.2" stroke-linejoin="round"/></svg>`
  },
  {
    key: 'storyboard',
    label: '九宫格出片',
    desc: '只需商品信息，自动出强 Hook',
    sub: 'AI脚本 · 分镜图 · 自动成片',
    to: '/studio/storyboard',
    accent: '#3A7BE8',
    icon: `<svg viewBox="0 0 48 48" fill="none"><rect x="4" y="4" width="40" height="40" rx="12" fill="#EAF2FF"/><rect x="10" y="10" width="8" height="8" rx="2" fill="none" stroke="#3A7BE8" stroke-width="2"/><rect x="20" y="10" width="8" height="8" rx="2" fill="none" stroke="#3A7BE8" stroke-width="2"/><rect x="30" y="10" width="8" height="8" rx="2" fill="none" stroke="#3A7BE8" stroke-width="2"/><rect x="10" y="20" width="8" height="8" rx="2" fill="none" stroke="#3A7BE8" stroke-width="2"/><rect x="20" y="20" width="8" height="8" rx="2" fill="none" stroke="#3A7BE8" stroke-width="2"/><rect x="30" y="20" width="8" height="8" rx="2" fill="none" stroke="#3A7BE8" stroke-width="2"/><rect x="10" y="30" width="24" height="8" rx="2" fill="none" stroke="#3A7BE8" stroke-width="2"/></svg>`
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
    <div class="studio-wrap">
      <!-- 顶部标题区 -->
      <div class="studio-hero">
        <h1>🎬 创作工作台</h1>
        <p>选择一种创作方式。所有方式都支持「创意档位 / 开头钩子 / 专家模式」高级设置。</p>
      </div>

      <!-- 方式选择卡 -->
      <div class="studio-tabs">
        <div
          v-for="t in tabs"
          :key="t.key"
          :class="['stab', { on: active === t.key }]"
          @click="router.push(t.to)"
        >
          <div class="stab-accent" :style="{ background: t.accent }"></div>
          <div class="stab-inner">
            <div class="stab-header">
              <div class="stab-icon" v-html="t.icon"></div>
              <div class="stab-info">
                <b>{{ t.label }}</b>
                <span class="stab-sub">{{ t.desc }}</span>
              </div>
            </div>
            <div class="stab-foot">
              <span>{{ t.sub }}</span>
              <svg width="16" height="16" viewBox="0 0 16 16"><path d="M5 3L11 8L5 13" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </div>
          </div>
        </div>
      </div>

      <!-- 内容区 -->
      <div class="studio-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style scoped>
.studio {
  min-height: calc(100vh - var(--header-h));
  background: var(--bg);
  padding: var(--s-5) var(--s-4) 80px;
}
.studio-wrap {
  max-width: 720px;
  margin: 0 auto;
}

/* Hero */
.studio-hero {
  text-align: center;
  margin-bottom: var(--s-5);
}
.studio-hero h1 {
  font-size: 24px;
  font-weight: 800;
  margin: 0 0 var(--s-2);
  color: var(--ink);
}
.studio-hero p {
  font-size: 13px;
  color: var(--weak);
  margin: 0;
  line-height: 1.7;
}

/* Tabs */
.studio-tabs {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--s-3);
  margin-bottom: var(--s-5);
}
.stab {
  position: relative;
  background: #fff;
  border: 1.5px solid var(--line);
  border-radius: var(--radius-lg);
  cursor: pointer;
  overflow: hidden;
  transition: all .2s var(--ease-out);
}
.stab:hover {
  border-color: var(--brand);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}
.stab.on {
  border-color: var(--brand);
  box-shadow: var(--shadow-brand);
  background: var(--brand-bg);
}
.stab.on .stab-accent { opacity: 1; }
.stab-accent {
  position: absolute;
  top: 0; left: 0;
  width: 4px; height: 100%;
  opacity: .5;
  transition: opacity .2s;
}
.stab-inner {
  padding: var(--s-4);
  display: flex;
  flex-direction: column;
  gap: var(--s-3);
}
.stab-header {
  display: flex;
  align-items: center;
  gap: var(--s-3);
}
.stab-icon {
  width: 44px; height: 44px;
  flex-shrink: 0;
}
.stab-icon svg { width: 100%; height: 100%; }
.stab-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stab-info b {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
}
.stab.on .stab-info b {
  color: var(--brand);
}
.stab-sub {
  font-size: 12px;
  color: var(--body-2);
}
.stab-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--s-2);
  border-top: 1px solid var(--line-2);
  font-size: 11px;
  color: var(--weak);
}
.stab.on .stab-foot {
  color: var(--brand);
}

.studio-content {
  /* 子页面自己的样式 */
}

@media (max-width: 768px) {
  .studio {
    padding: var(--s-4) var(--s-3) 60px;
  }
  .studio-hero h1 { font-size: 20px; }
  .studio-tabs {
    display: flex;
    gap: var(--s-2);
  }
  .stab-inner {
    padding: var(--s-3);
  }
  .stab-icon { width: 36px; height: 36px; }
  .stab-header { flex-direction: row; }
  .stab-info b { font-size: 14px; }
  .stab-sub,
  .stab-foot span { display: none; }
}

@media (min-width: 768px) {
  .studio-tabs {
    gap: var(--s-4);
  }
  .stab-inner {
    padding: var(--s-5);
  }
}
</style>
