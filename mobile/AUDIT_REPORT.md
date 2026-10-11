# mobile 端代码审计报告

> 审计日期：2026-08-26  
> 审计范围：`/home/ubuntu/pro/ai-creator/mobile/src` 全部源码  
> 执行命令：请在 `mobile` 目录下执行 `npm run build:h5`

---

## 1. 审计结论

本次审计共发现 **16 项问题**，**已全部修复完成**，并通过 `npm run build:h5` 构建验证。

### 1.1 已修复问题

| 编号 | 严重程度 | 文件位置 | 问题 | 修复方式 |
|------|----------|----------|------|----------|
| 1 | Critical | `mobile/src/pages/vip/index.vue` | 未导入支付工具导致运行时错误 | 补充 `openWechatPayment` 等 import |
| 2 | Critical | `mobile/src/utils/image.js` | 缺省封面调用外部图片生成服务 | 改为本地 SVG Data URI 占位图 |
| 3 | High | `mobile/src/pages/console/tool.vue` | 富文本直接渲染后端 HTML，存在 XSS | 新增 `sanitizeArticleHtml()` 过滤危险标签和事件属性 |
| 4 | High | `mobile/src/pages/profile/subscribe.vue` | 支付轮询使用 `setInterval` 导致并发堆积 | 改为 `setTimeout` 递归 + `pollingInFlight` 锁 |
| 5 | High | `mobile/src/utils/payment.js` | 二维码生成失败时暴露 `code_url` | 失败时不展示/复制 `code_url`，仅提示重新下单或联系客服 |
| 6 | Medium | `mobile/src/pages/profile/subscribe.vue` | `closeQrModal` 不停止轮询 | 关闭弹窗时调用 `stopPolling()` 和 `clearPendingOrderNo()` |
| 7 | High | `mobile/src/utils/payment.js` | `qrcode` 在小程序环境不支持 | H5 使用 `qrcode`，小程序/App 提示到 H5 完成支付 |
| 8 | Medium | `mobile/src` 多处 | 多处空 `catch {}` 静默吞异常 | 补充 `console.error` 和中文上下文 |
| 9 | Medium | `mobile/src/pages/console/drama.vue` | `onLoad` 与 `onShow` 双重加载 | 增加 `initialLoaded` 标志避免重复请求 |
| 10 | Medium | `mobile/src/pages/opportunity/index.vue`、`mine.vue` | 列表仅 `onLoad` 加载，登录返回后不刷新 | 增加 `onShow` 刷新 |
| 11 | Medium | `mobile/src/pages/console/tool.vue` | 上传代码重复，blob URL 未释放 | 统一释放 blob URL：上传失败、删除媒体、切换工具、页面卸载 |
| 12 | Medium | `mobile/src/pages/dealer/index.vue` | 错误处理不完善 | `catch` 中补充 `console.error` 和中文 Toast 提示 |
| 13 | Medium | `mobile/src/utils/request.js` | 网络失败缺少兜底 | `uniRequest` 包在 `try/catch` 中统一抛出包含 errMsg 的 Error |
| 14 | Medium | `mobile/src/utils/request.js` | 并发 401 多次 reLaunch | 新增全局跳转锁 `isRedirectingToLogin` |
| 15 | Medium | `mobile/src/utils/request.js` | 业务失败不阻断 | `code === 0` 时默认抛出业务错误，支持 `suppressBusinessError` 兼容旧代码 |
| 16 | Medium | `mobile/src/utils/payment.js` | pending order 明文存储 | 存储 `{orderNo, userId, expireAt}`，读取时校验归属和过期时间 |
| 17 | Low | `mobile/src/components/AppNavBar.vue` | `setTimeout` 未在卸载时清理 | 迁移到 `<script setup>`，使用 `onBeforeUnmount` 清理 |
| 18 | Low | `mobile/src/pages/console/tool.vue`、`console/index.vue` 等 | 部分 `v-for` 缺少稳定 `:key` | 使用业务唯一标识作为 key |
| 19 | Low | `mobile/src/pages/login/index.vue` | `redirect` 原值传递，仅在跳转前清洗 | `onLoad` 中立即清洗并赋值 |
| 20 | Info | `mobile/src/components/AppImage.vue`、`AppEmpty.vue`、`AppNavBar.vue` | 公共组件仍使用 Options API | 迁移到 `<script setup>` |

---

## 2. 验证命令

请在 `mobile` 目录下执行以下命令验证构建：

```bash
cd /home/ubuntu/pro/ai-creator/mobile
npm run build:h5
```

预期结果：构建成功退出，无错误。
