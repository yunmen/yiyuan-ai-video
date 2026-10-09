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
   全局样式：设计系统令牌 + 跨页面复用原子类
   令牌取值与设计稿《一源 AI 视频 · 移动端设计系统》完全一致。
   同时声明在 page 与 :root 上，兼容 H5 与小程序端。
   ============================================================ */
page,
:root {
  /* 品牌主色：深空蓝 → 极光紫 */
  --brand-primary: #4f46e5;
  --brand-primary-hover: #4338ca;
  --brand-primary-active: #3730a3;
  --brand-secondary: #7c3aed;
  --brand-primary-light: #eef2ff;
  --brand-primary-lighter: #f5f3ff;

  /* 渐变 */
  --grad-brand: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  --grad-brand-soft: linear-gradient(135deg, rgba(79, 70, 229, 0.08) 0%, rgba(124, 58, 237, 0.08) 100%);
  --grad-hero: linear-gradient(180deg, #1e1b4b 0%, #312e81 50%, #4c1d95 100%);
  --grad-card: linear-gradient(135deg, rgba(79, 70, 229, 0.06) 0%, rgba(124, 58, 237, 0.06) 100%);
  --grad-hot: linear-gradient(135deg, #ef4444 0%, #f59e0b 100%);

  /* 状态色 */
  --state-success: #10b981;
  --state-success-light: #ecfdf5;
  --state-warning: #f59e0b;
  --state-warning-light: #fffbeb;
  --state-error: #ef4444;
  --state-error-light: #fef2f2;
  --state-info: #3b82f6;
  --state-info-light: #eff6ff;

  /* 中性色 */
  --text-primary: #0f172a;
  --text-secondary: #334155;
  --text-tertiary: #64748b;
  --text-muted: #94a3b8;
  --text-white: #ffffff;
  --bg-page: #f8fafc;
  --bg-card: #ffffff;
  --bg-hover: #f1f5f9;
  --bg-active: #e2e8f0;
  --border-light: #e2e8f0;
  --border-medium: #cbd5e1;
  --border-strong: #94a3b8;

  /* 圆角 / 阴影 */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-full: 9999px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06);
  --shadow-md: 0 4px 8px -2px rgba(15, 23, 42, 0.06), 0 2px 4px -2px rgba(15, 23, 42, 0.04);
  --shadow-lg: 0 10px 16px -4px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.04);
  --shadow-brand: 0 4px 14px rgba(79, 70, 229, 0.25);
  --shadow-brand-lg: 0 8px 24px rgba(79, 70, 229, 0.35);

  /* 布局 */
  --header-h: 56px;
  --nav-h: 60px;
  --page-max: 480px;

  /* 动效 */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --transition-fast: 150ms cubic-bezier(0.16, 1, 0.3, 1);
  --transition-base: 200ms cubic-bezier(0.16, 1, 0.3, 1);
  --transition-slow: 300ms cubic-bezier(0.16, 1, 0.3, 1);
}

page {
  background: #f8fafc;
  color: #0f172a;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  font-size: 14px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

view,
text,
button,
input,
textarea,
image {
  box-sizing: border-box;
}

/* ============================================================
   页面容器：480px 居中，宽屏两侧留白，底部避让自定义导航条
   ============================================================ */
.app-page {
  max-width: var(--page-max);
  margin: 0 auto;
  min-height: 100vh;
  background: var(--bg-page);
  position: relative;
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
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.app-block-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.app-muted {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* ============================================================
   品牌按钮
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
    box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.5);
  }
  50% {
    box-shadow: 0 0 18px 5px rgba(139, 92, 246, 0.12);
  }
}

.app-spin {
  animation: app-spin 1s linear infinite;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
