<script>
import { useUserStore } from '@/store/modules/user'
import { refreshCurrentUserProfile } from '@/utils/session'

export default {
  onLaunch() {
    const userStore = useUserStore()
    // 先用本地缓存渲染首屏，再后台刷新资料与额度；接口失败不阻断进入首页。
    refreshCurrentUserProfile(userStore)
  },
}
</script>

<style lang="scss">
/* ============================================================
   全局样式：水墨宣纸设计令牌 + 跨页面复用原子类
   取道家「大音希声，大象无形」之意：以宣纸为本、以墨为字、以朱砂点睛，
   重留白、轻装饰、细墨线分隔。同时声明在 page 与 :root 上，兼容 H5 与小程序端。
   ============================================================ */
page,
:root {
  /* 墨（文字与深色基底） */
  --ink-900: #1f1d1a;
  --ink-700: #3a342c;
  --ink-500: #6b6357;
  --ink-300: #9c9488;

  /* 宣纸（背景） */
  --paper-50: #fbf8f2;
  --paper-100: #f5f0e6;
  --paper-200: #ebe4d5;
  --paper-card: #fffdf9;

  /* 墨线（描边） */
  --line-1: #e7e0d1;
  --line-2: #d5cbb6;
  --line-3: #b7ab92;

  /* 品牌主色：朱砂印红 */
  --brand-primary: #b23a2e;
  --brand-primary-hover: #9a3026;
  --brand-primary-active: #832720;
  --brand-secondary: #8a5a3b;
  --brand-primary-light: #f8eae6;
  --brand-primary-lighter: #fcf4f1;

  /* 渐变 */
  --grad-brand: linear-gradient(135deg, #b23a2e 0%, #8e2c22 100%);
  --grad-brand-soft: linear-gradient(135deg, rgba(178, 58, 46, 0.08) 0%, rgba(138, 90, 59, 0.08) 100%);
  --grad-hero: linear-gradient(168deg, #2a2621 0%, #1e1b17 52%, #17150f 100%);
  --grad-card: linear-gradient(135deg, rgba(178, 58, 46, 0.05) 0%, rgba(138, 90, 59, 0.05) 100%);
  --grad-hot: linear-gradient(135deg, #c0392b 0%, #b98236 100%);

  /* 状态色 */
  --state-success: #4b7a5a;
  --state-success-light: #ebf2ec;
  --state-warning: #b98236;
  --state-warning-light: #f8f0df;
  --state-error: #b23a2e;
  --state-error-light: #f8eae6;
  --state-info: #3e6b7a;
  --state-info-light: #e7f0f3;

  /* 中性色 */
  --text-primary: #1f1d1a;
  --text-secondary: #3a342c;
  --text-tertiary: #6b6357;
  --text-muted: #9c9488;
  --text-white: #ffffff;
  --bg-page: #fbf8f2;
  --bg-card: #fffdf9;
  --bg-hover: #f5f0e6;
  --bg-active: #ebe4d5;
  --border-light: #e7e0d1;
  --border-medium: #d5cbb6;
  --border-strong: #b7ab92;

  /* 圆角 / 阴影 */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --radius-xl: 10px;
  --radius-full: 9999px;
  --shadow-sm: 0 1px 2px rgba(31, 29, 26, 0.04), 0 1px 3px rgba(31, 29, 26, 0.05);
  --shadow-md: 0 4px 10px -2px rgba(31, 29, 26, 0.06), 0 2px 5px -2px rgba(31, 29, 26, 0.04);
  --shadow-lg: 0 10px 24px -6px rgba(31, 29, 26, 0.1), 0 4px 8px -4px rgba(31, 29, 26, 0.05);
  --shadow-brand: 0 4px 14px rgba(178, 58, 46, 0.2);
  --shadow-brand-lg: 0 8px 24px rgba(178, 58, 46, 0.28);

  /* 布局 */
  --header-h: 52px;
  --nav-h: 64px;
  --page-max: 480px;
  --page-gutter: 16px;

  /* 字体 */
  --font-sans: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', Arial, sans-serif;
  --font-serif: 'Songti SC', 'STSong', 'Noto Serif SC', 'Source Han Serif SC', 'SimSun',
    Georgia, serif;

  /* 动效 */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --transition-fast: 150ms cubic-bezier(0.16, 1, 0.3, 1);
  --transition-base: 200ms cubic-bezier(0.16, 1, 0.3, 1);
  --transition-slow: 300ms cubic-bezier(0.16, 1, 0.3, 1);
}

/* #ifdef H5 */
html,
body,
page {
  background: #fbf8f2;
  color: #1f1d1a;
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.6;
  -webkit-text-size-adjust: 100%;
  text-size-adjust: 100%;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  font-synthesis: none;
}

button,
input,
textarea,
select {
  margin: 0;
  font: inherit;
  color: inherit;
  line-height: inherit;
  -webkit-appearance: none;
  appearance: none;
}

view,
text,
button,
input,
textarea,
image {
  box-sizing: border-box;
}
/* #endif */

/* #ifdef MP-WEIXIN || APP-PLUS */
/* 小程序端组件样式不推荐标签选择器，且不识别 html/body；只需 page 基态（view 默认 border-box） */
page {
  background: #fbf8f2;
  color: #1f1d1a;
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.6;
}
/* #endif */

/* ============================================================
   页面容器：480px 居中，宣纸质地，底部避让自定义导航条
   ============================================================ */
.app-page {
  max-width: var(--page-max);
  margin: 0 auto;
  /* 100vh 兜底：小程序旧内核不识别 dvh，会忽略后一条并保留 vh */
  min-height: 100vh;
  min-height: 100dvh;
  background-color: var(--bg-page);
  /* 极淡的宣纸颗粒，近看才有质感，远看仍是一片干净的白 */
  background-image: radial-gradient(rgba(31, 29, 26, 0.028) 1px, transparent 1px);
  background-size: 22px 22px;
  position: relative;
  overflow-x: hidden;
  padding-bottom: calc(var(--nav-h) + constant(safe-area-inset-bottom));
  padding-bottom: calc(var(--nav-h) + env(safe-area-inset-bottom));
}

/* 无底部导航的页面（登录/注册等） */
.app-page--plain {
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
}

/* 顶部安全区占位（状态栏） */
.app-statusbar {
  width: 100%;
  background: transparent;
}

/* ============================================================
   文本工具类
   ============================================================ */
.app-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 宋体（明朝体）标题：带文人气，用于大标题与重点数字 */
.app-serif {
  font-family: var(--font-serif);
  letter-spacing: 0.04em;
}

/* ============================================================
   通用卡片 / 区块
   ============================================================ */
.app-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-sm);
}

.app-section-title {
  font-family: var(--font-serif);
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--text-primary);
}

.app-block-title {
  font-family: var(--font-serif);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--text-primary);
}

.app-muted {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* 墨线分隔：一横一线，取「一笔带过」 */
.app-divider {
  height: 1px;
  background: var(--border-light);
}

/* 朱砂印章：点睛元素，用于强调「已成/已验」等关键状态 */
.app-seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--brand-primary);
  color: var(--text-white);
  font-family: var(--font-serif);
  font-weight: 700;
  border-radius: 4px;
  box-shadow: var(--shadow-brand);
  line-height: 1;
}

/* ============================================================
   品牌按钮：朱砂实色，克制不喧哗
   ============================================================ */
.app-btn-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: var(--grad-brand);
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.04em;
  border-radius: var(--radius-full);
  box-shadow: var(--shadow-brand);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  border: none;
  line-height: 1.4;
}

.app-btn-brand:active {
  transform: scale(0.98);
  box-shadow: var(--shadow-brand-lg);
}

.app-btn-brand[disabled] {
  opacity: 0.5;
}

/* 白底 / 描边次要按钮 */
.app-btn-ghost {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
  border: 1.5px solid var(--border-light);
  border-radius: var(--radius-full);
  line-height: 1.4;
}

/* ============================================================
   芯片（单选标签）
   ============================================================ */
.app-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  border-radius: var(--radius-full);
  font-size: 13px;
  font-weight: 500;
  border: 1.5px solid var(--border-light);
  background: var(--bg-card);
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.app-chip--active {
  border-color: var(--brand-primary);
  background: var(--brand-primary-light);
  color: var(--brand-primary);
  font-weight: 600;
}

/* ============================================================
   表单
   ============================================================ */
.app-field {
  width: 100%;
  border: 1.5px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  font-size: 14px;
  color: var(--text-primary);
  background: var(--bg-page);
  transition: all var(--transition-fast);
  font-family: inherit;
}

.app-field--focus {
  border-color: var(--brand-primary);
  background: #ffffff;
}

.app-placeholder {
  color: var(--text-muted);
}

/* 设置项行 */
.app-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-light);
}

.app-row:last-child {
  border-bottom: none;
}

.app-row__label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.app-row__value {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-tertiary);
}

/* ============================================================
   动效（尊重系统「减少动态效果」偏好）
   ============================================================ */
@keyframes app-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes app-ping {
  75%,
  100% {
    transform: scale(2);
    opacity: 0;
  }
}

@keyframes app-shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(400%);
  }
}

@keyframes app-glow {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(178, 58, 46, 0.45);
  }
  50% {
    box-shadow: 0 0 18px 5px rgba(178, 58, 46, 0.12);
  }
}

.app-spin {
  animation: app-spin 1s linear infinite;
}

/* #ifdef H5 */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
/* #endif */
</style>
