<script>
import { useUserStore } from '@/store/modules/user'
import { refreshCurrentUserProfile } from '@/utils/session'

export default {
  /** 启动时先使用本地账号缓存，后台刷新资料与额度，避免阻塞首屏。 */
  onLaunch() {
    // 用户资料由现有会话层管理，不在视觉层重复实现鉴权。
    const userStore = useUserStore()
    refreshCurrentUserProfile(userStore)
  },
}
</script>

<style lang="scss">
/* 纸白影像工作室：以下 CSS 令牌与 uni.scss 的同名变量逐项对应。 */
page,
:root {
  --ink-900: #25241f;
  --ink-700: #48463f;
  --ink-500: #77746b;
  --ink-300: #969187;
  --paper-50: #f8f7f3;
  --paper-100: #efede7;
  --paper-200: #e6e2d9;
  --paper-card: #fffefa;
  --line-1: rgba(74, 65, 47, 0.08);
  --line-2: rgba(74, 65, 47, 0.15);
  --line-3: rgba(74, 65, 47, 0.25);
  --brand-primary: #b23a2e;
  --brand-primary-hover: #9a3026;
  --brand-primary-active: #832720;
  --brand-secondary: #8a5a3b;
  --brand-primary-light: #f8ece7;
  --brand-primary-lighter: #fcf5f1;
  --grad-brand: linear-gradient(135deg, #b23a2e 0%, #8e2c22 100%);
  --grad-brand-soft: linear-gradient(135deg, rgba(178, 58, 46, 0.08) 0%, rgba(138, 90, 59, 0.08) 100%);
  --grad-hero: linear-gradient(168deg, #2a2621 0%, #1e1b17 52%, #17150f 100%);
  --grad-card: linear-gradient(135deg, rgba(178, 58, 46, 0.05) 0%, rgba(138, 90, 59, 0.05) 100%);
  --grad-hot: linear-gradient(135deg, #c0392b 0%, #b98236 100%);
  --state-success: #4b7a5a;
  --state-success-light: #ebf2ec;
  --state-warning: #b98236;
  --state-warning-light: #f8f0df;
  --state-error: #b23a2e;
  --state-error-light: #f8ece7;
  --state-info: #3e6b7a;
  --state-info-light: #e7f0f3;
  --text-primary: #25241f;
  --text-secondary: #48463f;
  --text-tertiary: #77746b;
  --text-muted: #969187;
  --text-white: #ffffff;
  --bg-page: #f8f7f3;
  --bg-card: #fffefa;
  --bg-hover: #efede7;
  --bg-active: #e6e2d9;
  --border-light: rgba(74, 65, 47, 0.08);
  --border-medium: rgba(74, 65, 47, 0.15);
  --border-strong: rgba(74, 65, 47, 0.25);
  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 20px;
  --radius-xl: 28px;
  --radius-full: 9999px;
  --shadow-sm: 0 1px 2px rgba(31, 29, 26, 0.04), 0 1px 3px rgba(31, 29, 26, 0.05);
  --shadow-md: 0 4px 10px -2px rgba(31, 29, 26, 0.06), 0 2px 5px -2px rgba(31, 29, 26, 0.04);
  --shadow-lg: 0 10px 24px -6px rgba(31, 29, 26, 0.1), 0 4px 8px -4px rgba(31, 29, 26, 0.05);
  --shadow-brand: 0 4px 14px rgba(178, 58, 46, 0.2);
  --shadow-brand-lg: 0 8px 24px rgba(178, 58, 46, 0.28);
  --s-1: 4px;
  --s-2: 8px;
  --s-3: 12px;
  --s-4: 16px;
  --s-5: 20px;
  --s-6: 24px;
  --s-8: 32px;
  --s-10: 40px;
  --s-12: 48px;
  --text-xs: 12px;
  --text-sm: 13px;
  --text-base: 14px;
  --text-lg: 16px;
  --text-xl: 18px;
  --text-2xl: 20px;
  --text-3xl: 24px;
  --text-4xl: 28px;
  --text-5xl: 32px;
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
  --font-extrabold: 800;
  --header-h: 52px;
  --nav-h: 84px;
  --page-max: 480px;
  --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
  --transition-fast: 150ms cubic-bezier(0.22, 1, 0.36, 1);
  --transition-base: 200ms cubic-bezier(0.22, 1, 0.36, 1);
  --transition-slow: 300ms cubic-bezier(0.22, 1, 0.36, 1);
  --font-sans: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', sans-serif;
  --font-serif: 'Songti SC', 'STSong', 'Noto Serif SC', 'Source Han Serif SC', 'SimSun', Georgia, serif;
  --page-gutter: 20px;
  /* 统一层级：悬浮导航、吸顶标题、底部操作、弹层。 */
  --z-header: 20;
  --z-tabbar: 30;
  --z-action: 25;
  --z-overlay: 200;
}

/* #ifdef H5 */
html, body, page {
  background: var(--bg-page);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.6;
  -webkit-text-size-adjust: 100%;
  text-size-adjust: 100%;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
button, input, textarea, select { margin: 0; font: inherit; color: inherit; }
view, text, button, input, textarea, image { box-sizing: border-box; }
/* 原生按钮与表单保留可见的键盘焦点，避免只提供鼠标反馈。 */
[role='button']:focus-visible, button:focus-visible, input:focus-visible, textarea:focus-visible {
  outline: 2px solid var(--brand-primary);
  outline-offset: 4px;
}
[role='button'] { cursor: pointer; -webkit-tap-highlight-color: transparent; }
/* #endif */

/* #ifdef MP-WEIXIN || APP-PLUS */
page { background: var(--bg-page); color: var(--text-primary); font-family: var(--font-sans); font-size: 14px; line-height: 1.6; }
/* #endif */

/* 各端统一盒模型，纸色托盘边框与安全区内边距均计入控件尺寸。 */
view, text, button, input, textarea, image, video, scroll-view, picker { box-sizing: border-box; }
button::after { border: none; }
[role='button'][aria-disabled='true'] { opacity: 0.55; }
[role='button']:active { -webkit-tap-highlight-color: transparent; }

.app-page {
  max-width: var(--page-max);
  margin: 0 auto;
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--bg-page);
  position: relative;
  overflow-x: hidden;
  padding-bottom: calc(var(--nav-h) + 24px + env(safe-area-inset-bottom));
}
.app-page--plain { padding-bottom: calc(24px + env(safe-area-inset-bottom)); }
.app-statusbar { width: 100%; background: transparent; }
.app-truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.app-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.app-serif { font-family: var(--font-serif); letter-spacing: 0.02em; }

/* 通过内侧高光与纸色外托盘形成双层结构，不使用沉重的投影。 */
.app-card {
  background: var(--bg-card);
  border: 6px solid var(--paper-100);
  border-radius: var(--radius-xl);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9), var(--shadow-sm);
}
.app-section-title { font-family: var(--font-serif); font-size: 23px; font-weight: 700; color: var(--text-primary); }
.app-block-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.app-muted { font-size: 12px; color: var(--text-tertiary); }
.app-divider { height: 1px; background: var(--border-light); }
.app-seal { display: inline-flex; align-items: center; justify-content: center; background: var(--brand-primary); color: white; font-family: var(--font-serif); border-radius: 8px; }

.app-btn-brand, .app-btn-ghost {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  min-height: 48px; padding: 12px 20px; border-radius: var(--radius-full);
  font-size: 14px; font-weight: 600; line-height: 1.4;
  transition: transform var(--transition-fast), opacity var(--transition-fast);
}
.app-btn-brand { background: var(--grad-brand); color: white; border: none; box-shadow: var(--shadow-brand); }
.app-btn-ghost { background: var(--bg-card); color: var(--text-secondary); border: 1px solid var(--border-medium); }
.app-btn-brand:active, .app-btn-ghost:active { transform: scale(0.98); }
.app-btn-brand[disabled], .app-btn-brand[aria-disabled='true'] { opacity: 0.5; }
.app-cta-icon { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 50%; background: rgba(255, 255, 255, 0.16); }

.app-chip {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  min-height: 44px; padding: 10px 16px; border-radius: var(--radius-full);
  font-size: 13px; border: 1px solid var(--border-light);
  background: var(--bg-card); color: var(--text-secondary);
  transition: transform var(--transition-fast);
}
.app-chip:active { transform: scale(0.97); }
.app-chip--active { border-color: rgba(178, 58, 46, 0.25); background: var(--brand-primary-light); color: var(--brand-primary); font-weight: 600; }
.app-field {
  width: 100%; border: 1px solid var(--border-light); border-radius: var(--radius-md);
  min-height: 48px; padding: 13px 14px; font-size: 14px; color: var(--text-primary);
  background: var(--bg-page); font-family: inherit;
}
.app-field--focus { border-color: var(--brand-primary); background: var(--bg-card); }
.app-placeholder { color: var(--text-muted); }
.app-row { display: flex; align-items: center; justify-content: space-between; padding: 16px 0; border-bottom: 1px solid var(--border-light); }
.app-row:last-child { border-bottom: none; }
.app-row__label, .app-row__value { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.app-row__label { color: var(--text-secondary); }
.app-row__value { color: var(--text-tertiary); }

/* 工具页共用说明区，避免每个页面重复定义同一套标题与间距。 */
.tool-intro { padding: 22px var(--page-gutter) 24px; }
.tool-intro__title { display: block; font: 600 25px/1.5 var(--font-serif); color: var(--text-primary); }
.tool-intro__desc { display: block; margin-top: 8px; font-size: 12px; line-height: 1.8; color: var(--text-tertiary); }
@media (max-width: 360px) { .tool-intro__title { font-size: 22px; } }

/* 仅动画化透明度和位移，不为滚动容器增加模糊与持续重绘。 */
@keyframes app-enter { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
@keyframes app-spin { to { transform: rotate(360deg); } }
@keyframes app-ping { 75%, 100% { transform: scale(2); opacity: 0; } }
@keyframes app-shimmer { from { transform: translateX(-100%); } to { transform: translateX(400%); } }
@keyframes app-breathe { 0%, 100% { opacity: 1; } 50% { opacity: 0.65; } }
.app-spin { animation: app-spin 1s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
.app-enter { animation: app-enter 800ms var(--ease-out) both; }

/* #ifdef H5 */
/* 保留 uni 原生弹窗行为，同时将费用确认、作品搜索和选项选择应用纸白视觉。 */
.uni-modal {
  width: calc(100% - 40px); max-width: 360px; box-sizing: border-box;
  background: var(--paper-card); color: var(--ink-900);
  border: 6px solid var(--paper-100); border-radius: 28px;
  box-shadow: var(--shadow-lg);
}
.uni-modal__hd { padding: 24px 20px 8px; }
.uni-modal__title { font: 600 22px/1.5 var(--font-serif); }
.uni-modal__bd { padding: 12px 20px 24px; font-size: 14px; line-height: 1.8; color: var(--ink-500); overflow-wrap: anywhere; }
.uni-modal__textarea { margin: 12px 16px 24px; padding: 12px; border-radius: 14px; background: var(--paper-50); color: var(--ink-900); font-size: 16px; }
.uni-modal__ft { display: flex; gap: 8px; padding: 0 16px 16px; }
.uni-modal__ft::after, .uni-modal__btn::after { display: none; }
.uni-modal__btn { flex: 1; border-radius: 999px; min-height: 48px; font-size: 14px; line-height: 48px; }
.uni-modal__btn_default { background: var(--paper-100); color: var(--ink-700) !important; }
.uni-modal__btn_primary { background: var(--brand-primary); color: #fff !important; }
/* 原生控件样式按需载入；提高选择器精度，确保宽屏和深色系统设置下也沿用当前纸白设计。 */
:root .uni-actionsheet, :root .uni-picker-container .uni-picker-custom { box-sizing: border-box; }
:root .uni-actionsheet { max-width: var(--page-max); left: 50%; right: auto; top: auto; bottom: 0; width: 100%; margin-left: 0; padding: 6px 6px calc(6px + env(safe-area-inset-bottom)); border-radius: 28px 28px 0 0; background: var(--paper-100); transform: translate(-50%, 100%); opacity: 1; transition: transform var(--transition-slow), visibility var(--transition-slow); overflow: hidden; }
:root .uni-actionsheet.uni-actionsheet_toggle { transform: translate(-50%, 0); }
:root .uni-actionsheet__menu { max-height: 70vh; overflow-y: auto; border-radius: 22px 22px 12px 12px; box-shadow: none; }
:root .uni-actionsheet__menu, :root .uni-actionsheet__action, :root .uni-actionsheet__cell { background: var(--paper-card); color: var(--ink-700) !important; }
:root .uni-actionsheet__action { display: block; border-radius: 12px; }
:root .uni-actionsheet__title { background: var(--paper-card); color: var(--ink-500); }
:root .uni-actionsheet__cell { min-height: 52px; font-size: 15px; }
:root .uni-actionsheet__cell:before { border-color: var(--line-1); }
:root .uni-actionsheet__cell:active { background: var(--paper-100); }
/* uni H5 实际使用 uni-picker-custom，并分别呈现手机滚轮和宽屏选项列表。 */
:root .uni-picker-container .uni-picker-custom { background: var(--paper-card); border: 6px solid var(--paper-100); border-radius: 28px; box-shadow: var(--shadow-lg); overflow: hidden; transition: transform var(--transition-slow), opacity var(--transition-slow), visibility var(--transition-slow); }
:root .uni-picker-container .uni-picker-header { background: var(--paper-100); }
:root .uni-picker-container .uni-picker-content, :root .uni-picker-container .uni-picker-select { background: var(--paper-card); }
:root .uni-picker-container .uni-picker-item { color: var(--ink-700); }
:root .uni-picker-container .uni-picker-item.selected { color: var(--brand-primary); background: var(--brand-primary-light); }
:root .uni-picker-container .uni-picker-action.uni-picker-action-cancel { color: var(--ink-500); }
:root .uni-picker-container .uni-picker-action.uni-picker-action-confirm { color: var(--brand-primary); }
:root .uni-picker-container .uni-picker-header:after { border-color: var(--line-1); }
:root .uni-picker-container .uni-picker-view-mask { background-image: linear-gradient(180deg, rgba(255,254,250,0.95), rgba(255,254,250,0.6)), linear-gradient(0deg, rgba(255,254,250,0.95), rgba(255,254,250,0.6)); }
:root .uni-picker-container .uni-picker-view-indicator:before, :root .uni-picker-container .uni-picker-view-indicator:after { border-color: var(--line-1); }
@media (max-width: 499px) {
  :root .uni-picker-container .uni-picker-custom { left: 50%; max-width: var(--page-max); transform: translate(-50%, 100%); border-radius: 28px 28px 0 0; padding-bottom: env(safe-area-inset-bottom); }
  :root .uni-picker-container .uni-picker-custom.uni-picker-toggle { transform: translate(-50%, 0); }
}
/* iOS 聚焦小字号输入会放大页面；真实输入节点至少 16px，外部标签保持原有层级。 */
/* 显式命中 uni 的内部类，避免其默认 font: inherit 覆盖字号下限。 */
uni-input .uni-input-input, uni-textarea .uni-textarea-textarea { font-size: 16px; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }
}
/* #endif */
</style>
