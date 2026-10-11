# 一源 AI 视频（yiyuan-ai-video）· Code Wiki

> 版本：基于 2026-10 仓库现状整理
> 覆盖范围：整个 monorepo（`mobile` / `backend` / `worker` / `admin` / `desktop` / `devops`），其中 **`mobile/` 移动端与 `backend/` 共享后端为当前维护重点**（`desktop/` 已冻结）
> 阅读对象：新加入的开发者、联调/测试人员、代码评审者

---

## 目录

1. [项目概览](#1-项目概览)
2. [仓库结构与技术栈](#2-仓库结构与技术栈)
3. [系统架构](#3-系统架构)
4. [mobile 移动端详解](#4-mobile-移动端详解)
5. [backend 后端详解](#5-backend-后端详解)
6. [worker AI 生成组件详解](#6-worker-ai-生成组件详解)
7. [admin 管理后台与 desktop 用户端（简述）](#7-admin-管理后台与-desktop-用户端简述)
8. [数据库模型总览](#8-数据库模型总览)
9. [核心业务链路](#9-核心业务链路)
10. [前后端接口契约映射](#10-前后端接口契约映射)
11. [本地开发与运行](#11-本地开发与运行)
12. [构建、部署与运维](#12-构建部署与运维)
13. [测试体系](#13-测试体系)
14. [关键约定与规范](#14-关键约定与规范)
15. [关键文件索引](#15-关键文件索引)

---

## 1. 项目概览

### 1.1 产品定位

面向**本地商家与电商**的 AI 短视频营销内容生成平台（产品名「千溪」移动端）。核心业务：

- **视频复刻**（Replicate）：上传一条对标爆款视频 + 替换素材（人物/商品/场景），AI 逆推分镜并重新成片；
- **九宫格成片**：AI 生成 9 张变体拼图 / 上传 9 张拼合 / 一张九宫格拆分为 9 张；
- **数字人口播**：选择平台或专属数字人形象，输入口播文案生成讲解视频；
- **视频换口播**：上传视频提取原台词 → AI 润色 → 换数字人/场景重新配音出片；
- **文案去味**：长文去除 AI 痕迹改写；
- 以及模板创作、文生/图生视频、图片生成、语音合成（TTS）、背景音乐等基础能力。

配套账号体系：注册登录（账号密码 / 手机验证码）、**免费额度 + 付费额度 + 每日签到**、充值套餐与微信支付订单。

### 1.2 核心业务链路

```
选择模板/上传素材 → 预估消耗 → 创建生成任务（tb_generate_task, processing）
        → 预扣额度 → 下发 ARQ 队列（Redis）
        → worker 消费任务、调用 AI 网关生成、周期回调进度
        → 成功：结果落库 + 按实际用量结算；失败：返还额度 / 订单退款
前端通过 /v1/task/detail 轮询任务状态与结果
```

两个关键架构决策：

| 决策 | 说明 |
| --- | --- |
| **backend 只建单，不生成** | 创建任务记录后下发到 ARQ 队列；真实 AI 调用全部在 worker 中完成 |
| **worker 不直连业务数据库** | 生成结果通过 `notify_url` 回调（`X-Worker-Token` 鉴权）由 backend 落库，worker 可独立部署 |

### 1.3 三端用户形态

| 端 | 使用者 | 状态 |
| --- | --- | --- |
| `mobile/`（uni-app，H5 + 微信小程序） | C 端商家用户 | **当前维护**，设计原则「简单、靠引导直接上手」 |
| `desktop/`（Vue3 + Naive UI 响应式） | C 端用户（桌面/移动浏览器） | **已冻结**，仅保留回归参考 |
| `admin/`（Vue3 + Element Plus / SCUI） | 平台运营管理员 | 正常维护 |

---

## 2. 仓库结构与技术栈

### 2.1 顶层目录

```
yiyuan-ai-video/
├── mobile/          # 移动端（uni-app Vue3 + Vite），本 Wiki 重点
├── backend/         # FastAPI 后端：API、RBAC、计费、支付、任务建单/回调
├── worker/          # ARQ 异步生成组件：消费任务、调用 AI 模型、回调 backend
├── admin/           # SCUI 管理后台（Vue3 + Vite + Element Plus）
├── desktop/         # 已冻结的用户端（Vue3 + Naive UI）
├── devops/          # Docker / Caddy / Nginx / Redis / Postgres 配置与前端构建产物
├── scripts/         # sync-build.mjs：前端构建产物同步到静态托管目录
├── docs/            # ai-gateway-guide.md、release-checklist.md
├── http/            # 接口调试样例（.http）
├── docker-compose.yaml
├── deploy.sh        # Linux 部署脚本
├── AGENTS.md        # 全仓协作规则（架构约束、风格、验证要求）
└── README.md
```

> 另有 `materials/`、`output/`、`sucai/`、`tmp/`、`tts_dump/`、`_design/` 等为素材/产物/设计稿目录，不属于应用代码。

### 2.2 技术栈一览

| 层 | 技术 |
| --- | --- |
| 移动端 | uni-app 3.0（Vue 3.4 `<script setup>`）、Vite 5、Pinia 2、vue-i18n 9、Sass；跨 H5 / 微信小程序 |
| 后端 | FastAPI 0.116、Pydantic 2.11、Tortoise ORM 0.25 + Aerich 迁移、Redis(arq 依赖)、APScheduler、Typer、loguru、JWT(pyjwt)、argon2 |
| 生成组件 | ARQ 0.28（Redis broker）、httpx、OpenAI 兼容 SDK、pydantic-settings |
| 管理后台 | Vue 3.5、Vite、Element Plus 2.14、Pinia、ECharts 6、TinyMCE、xgplayer |
| 用户端(冻结) | Vue 3、Naive UI、Pinia |
| 数据库 | dev：MySQL；prod：PostgreSQL 16；缓存/队列：Redis |
| 对象存储 | 腾讯云 COS（未启用时回退本地磁盘） |
| 支付/短信 | 微信支付 V3（wechatpayv3）；腾讯云短信（开发态 mock） |
| 基础设施 | Docker Compose、Caddy 2（HTTPS/HTTP3/静态托管/反代） |

---

## 3. 系统架构

### 3.1 总体架构图

```
                    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
                    │ mobile(H5/小程序)│  │ admin (SCUI) │  │ desktop(冻结) │
                    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                           │ /api/user/v1/*  │ /api/admin/v1/* │ /api/user/v1/*
                           ▼                 ▼                 ▼
                    ┌─────────────────────────────────────────────────┐
                    │              backend (FastAPI :8801)              │
                    │  Route → Controller → Service → CRUD → Model      │
                    │  JWT 鉴权(Redis 存储) / 统一 code 响应 / 额度计费  │
                    └───────┬───────────────────────────────▲───────────┘
                            │ enqueue_job (ARQ, Redis)       │ POST /callback
                            │ 队列名: generate               │ (X-Worker-Token)
                            ▼                                │
                    ┌─────────────────┐    httpx 回调/断点拉取  │
                    │ worker (ARQ)    │ ───────────────────────┘
                    │ tool→service 编排│
                    └───────┬─────────┘
                            │ OpenAI 兼容协议（含方舟 ark 原生协议）
                            ▼
                    AI 网关/中转站（chat/text/image/video/audio/music/digital/asr）
                            │
                            ▼
              结果转存腾讯云 COS（可选，失败保留模型直链）

        PostgreSQL/MySQL ── backend        Redis ── ARQ 队列 / Token / 锁 / 缓存
```

### 3.2 任务异步模型（建单 → 生成 → 回调）

1. 前端调 `POST /api/user/v1/task/create`（或 image/audio/text/digital/render 等建单接口）；
2. backend 的 `generate_task.Service` 完成：模板/规格校验、成本预估（`cost_rules.estimate_cost`）、登录用户**预扣额度**、写入 `tb_generate_task`（`status=processing`，含 `checkpoint` 断点槽位）；
3. `app/core/task_queue.enqueue_generate_task()` 以**固定 job_id**（`task-{id}`，用于去重/存活探测）下发到 ARQ 队列；
4. worker 的 `process_*` 任务方法被唤起 → 对应 service 编排（分镜/ASR/配音/生成/字幕/BGM/合成/质检）→ 调 tools 访问 AI 网关；期间通过 `plugin/notice.py` 周期回调进度、回写断点；
5. backend `POST /api/user/v1/task/callback`（内部接口）接收：
   - `processing`：更新 `progress` 与 `update_time`（心跳）；
   - `success`：落结果、沉淀分镜实体（`tb_episode`/`tb_shot`）、按实际用量结算返还差额；
   - `failed`：记录 `fail_reason`/`fail_code`、返还额度或触发付费订单自动退款。
6. 前端轮询 `/v1/task/detail`（或 `/v1/content/result` 轻量内容任务）读取最终结果。

### 3.3 可靠性兜底

| 机制 | 位置 | 作用 |
| --- | --- | --- |
| 卡死对账 | `app/core/reconcile.py`（周期 300s） | 超时（`TASK_STUCK_TIMEOUT`，默认 18000s）processing → failed |
| 孤儿回收 | `generate_task.Service.recover_orphan_tasks` | worker 崩溃导致 ARQ job 丢失（默认 600s 无进展）→ 重新入队断点续跑，不重复扣费 |
| 静默预警 | `list_silent_tasks`（默认 600s 无回调） | 只告警不动状态，便于提前排查 |
| 回调重试 | `worker/plugin/notice.py` | httpx 线性退避重试（默认 3 次） |
| 支付单超时 | `payment.Service.reconcile_expired` | 待支付订单（默认 120 分钟）自动取消 |
| 生成瞬时错误重试 | worker `core/retry.py` + ARQ `max_tries=3` | 网关抖动指数退避；网关级故障转移见 `tools/base.py` |

---

## 4. mobile 移动端详解

### 4.1 工程信息

| 项 | 值 |
| --- | --- |
| 框架 | uni-app 3.0（`@dcloudio/*` 3.0.0-4060620250520001）+ Vue 3.4.21，`createSSRApp` 入口 |
| 构建 | Vite 5.2 + `@dcloudio/vite-plugin-uni`，Sass 1.77 |
| 状态/国际化 | Pinia 2.0.36、vue-i18n 9.1.9（当前仅中文 `zh-CN`） |
| 目标平台 | H5（主）、微信小程序（`mp-weixin`）；manifest 中保留 app-plus 配置 |
| 开发端口 | **5174**（见 [vite.config.js](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/vite.config.js)） |
| 路径别名 | `@` → `src/` |
| 样式注入 | `src/uni.scss` 通过 `css.preprocessorOptions.scss.additionalData` 全局自动注入，**禁止页面内 @import** |

npm 脚本（[package.json](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/package.json)）：

| 命令 | 作用 |
| --- | --- |
| `npm run dev:h5` | 启动 H5 开发服务 |
| `npm run dev:mp-weixin` | 微信小程序开发模式 |
| `npm run build:h5` | 构建 H5 到 `dist/build/h5` |
| `npm run build` | 构建 H5 并同步到 `../devops/nginx/data/h5`（供 Nginx 静态托管） |
| `npm run build:mp-weixin` | 构建微信小程序产物 |

### 4.2 环境配置

| 文件 | 关键变量 |
| --- | --- |
| `.env.development` | `VITE_APP_PROXY=true`、`VITE_DEV_BACKEND_TARGET=http://localhost:8801`、`VITE_APP_API_BASEURL=/api` |
| `.env.production` | `VITE_APP_PROXY=false`、`VITE_APP_API_BASEURL=/api/user` |

请求地址解析（[src/config/index.js](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/config/index.js)）：

- 开发态：`API_URL='/api'`，Vite 代理把 **`/api/*` rewrite 为 `/api/user/*`** 转发到 backend 8801；`/shared/*` 不重写直接转发（共享静态资源）；
- 生产态：`API_URL='/api/user'`，由前置网关（Nginx）同源反代。

其他配置：超时 10s、Token 头 `Authorization: Bearer <token>`、本地存储键 `userInfo`。

### 4.3 目录结构

```
mobile/src/
├── main.js                 # createSSRApp：注册 Pinia、i18n
├── App.vue                 # onLaunch 后台刷新用户资料/额度；全局设计令牌与原子类
├── manifest.json           # uni-app 应用配置（H5 history 路由）
├── pages.json              # 12 个页面注册（全部自定义导航 navigationStyle: custom）
├── uni.scss                # 全局 SCSS 变量（水墨宣纸设计系统）
├── config/index.js         # 运行期静态配置（API_URL/Token/超时）
├── api/
│   ├── index.js            # import.meta.glob 自动聚合 model/*.js
│   └── model/              # 9 个按业务域划分的接口模块
├── pages/                  # 12 个页面（见 4.5）
├── components/             # 4 个跨端基础组件
├── composables/            # useGenConfig / useContentPrepare
├── store/modules/user.js   # 唯一 Pinia Store：认证与额度
├── utils/                  # request/storage/navigation/upload/task/account/clipboard/session
├── locales/index.js        # vue-i18n（zh-CN）
└── static/hero-ink.jpg     # 本地静态图
```

### 4.4 启动流程

1. `main.js` 的 `createApp()` 创建 SSR App，安装 Pinia 与 i18n；
2. `App.vue` 的 `onLaunch`：以本地缓存 token/userInfo **立即渲染首屏**，随后调用 `refreshCurrentUserProfile()`（[utils/session.js](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/utils/session.js.js)）后台拉取 `/account/info` 与 `/account/credits`，失败不阻断进入；
3. 页面全部采用**自定义导航栏**（`AppNavBar`）与**自绘底部 Tab**（`AppTabBar`，非原生 tabBar），以保证 H5/小程序视觉一致。

### 4.5 页面清单（pages.json）

| 页面路径 | 名称 | 职责与关键逻辑 |
| --- | --- | --- |
| `pages/home/index` | 首页 | 运营入口聚合：热门模板推荐（`/template/recommend`）、四大能力入口、额度展示、`onShow` 刷新、下拉刷新；未登录引导登录 |
| `pages/studio/index` | 创作工作台 | **核心页（约 1800 行）**：视频复刻 + 九宫格成片。素材选择上传、AI 角色识别、对标视频元素槽位检测绑定、分镜拆解轮询、文案准备流水线、创意档位/钩子/画幅/时长/真人策略/去水印等高级选项、`/task/estimate` 实时预估、建单后轮询进度并跳作品 |
| `pages/grid/index` | 九宫格成片 | 三种模式：AI 生成 9 图拼接 / 上传 9 张拼合 / 上传 1 张拆分；调 `/task/image/create`（`grid`/`split` 字段），轮询后支持保存相册 |
| `pages/works/index` | 我的作品 | `/task/list` 分页、状态筛选与搜索、生成中卡片（进度+阶段文案+剩余时间）轮询、重新生成、删除、视频播放弹层、下拉刷新 |
| `pages/task-detail/index` | 分镜编辑 | `/storyboard/list` 镜头列表、质检分数展示、编辑镜头提示词/台词（`/storyboard/shot/update`）、局部重跑（`/task/regenerate_segment`）后轮询 |
| `pages/digital/index` | 数字人口播 | 平台形象列表 + 我的专属数字人增删改、形象/背景/商品图上传、语速/音色/时长/分辨率/画幅选择、文案 AI 润色、预估、`/task/digital/create` |
| `pages/render/index` | 视频换口播 | 上传视频 → 提取台词（拆解 + ASR 归集）→ 去味润色 → 选数字人/场景 → `/task/render/create` |
| `pages/aiflavor/index` | 文案去味 | `/content/rewrite` 异步改写（强度 1-4、语气），轮询 `/content/result`，一键复制 |
| `pages/recharge/index` | 额度充值 | 套餐列表、下单（`/payment/order/recharge`）、mock 支付确认、订单状态轮询、我的订单列表、支付后刷新额度 |
| `pages/login/index` | 登录 | 账号密码 / 短信验证码双模式、验证码倒计时、登录后按 `redirect` 安全回跳 |
| `pages/register/index` | 注册 | 手机号注册校验、注册成功自动登录并回跳 |
| `pages/profile/index` | 个人中心 | 用户资料（含 `No.000042` 式格式化 ID）、额度、签到入口、数字人/充值/反馈导航、退出登录 |

> 4 个 Tab 页（`TAB_PAGES`，见 [utils/navigation.js](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/utils/navigation.js)）：home / studio / works / profile，切换走 `uni.reLaunch` 清空页面栈。

### 4.6 基础组件

| 组件 | 说明 |
| --- | --- |
| [AppNavBar.vue](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/components/AppNavBar.vue) | 通用顶部导航：自适应状态栏高度、按页面栈显示返回（Tab/登录页除外）、`solid`/`transparent`/`align` 三种形态、标题具名插槽 |
| [AppTabBar.vue](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/components/AppTabBar.vue) | 底部四项导航（首页/创作/作品/我的），选中态朱砂短线 + 品牌色，适配安全区 |
| [AppIcon.vue](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/components/AppIcon.vue) | lucide 风格线性图标：因小程序不支持内联 `<svg>`，将路径数据编码为 **SVG Data URI** 用 `<image>` 渲染，三端一致；支持 name/size/color/strokeWidth |
| `AppEmpty.vue` | 空状态占位 |

### 4.7 状态管理（Pinia）

仅一个 Store：[store/modules/user.js](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/store/modules/user.js)

- State：`token`（登录态唯一判据，后端**不签发 refresh_token**）、`userInfo`、`creditTotal`；
- Getters：`isLoggedIn`；
- Actions：`setToken` / `setUserInfo` / `setCreditTotal` / `logout` / `syncFromStorage`；
- 持久化：通过 `uni.getStorageSync` 系列同步 API（H5 映射 localStorage），存取均 try/catch 兜底。

### 4.8 网络层（重点）

[utils/request.js](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/utils/request.js) 基于 **`uni.request`** 自封装（非 axios），导出 `http.get/post/put/stream/request`。

**统一处理策略：**

1. 自动附加 `Authorization: Bearer <token>`；GET 请求加 `_=时间戳` 绕缓存；
2. 业务状态码（HTTP 200 体内 `code`）：
   - `code=1` 成功，返回完整响应体；
   - `code=0` 业务失败：toast 后端 `message` 并**抛错**（可用 `suppressBusinessError` 关闭）；
   - `code=9` 鉴权失效：清理登录态并 `uni.reLaunch` 到登录页（带安全回跳地址）；
3. HTTP 层错误：401 同鉴权失效处理；403 toast；400/404/422/500 中文文案 toast；
4. **并发 401 防抖**：模块级 `isRedirectingToLogin` 跳转锁 + 3s 兜底释放，防止多个并发请求重复 reLaunch；
5. **会话一致性**：记录请求携带的 token，过期请求的 401 不得清掉刚完成的新登录会话（`isCurrentSessionRequest`）；
6. 单请求可覆盖超时（`timeout`），支持 `suppressGlobalError` / `suppressGlobalAuthError` / `suppressForbiddenRedirect` 等静默选项（后台静默刷新场景使用）。

**SSE 流式接口 `http.stream()`：**

- 仅 H5 使用 `fetch + ReadableStream`，小程序/App 退化为普通 POST；
- 逐行解析 `data: ` 帧，聚合 `chunk` 文本，透传 `error`、`[DONE]` 终止符与 meta 帧（`id`/`task_id`）；
- 显式 `Content-Type: application/json`（避免 fetch 字符串默认 text/plain 导致 FastAPI 校验失败），`AbortController` 控制超时。

### 4.9 API 模块层

[api/index.js](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/api/index.js) 用 `import.meta.glob('./model/*.js', { eager: true })` 自动聚合，页面统一 `import api from '@/api'` 后按 `api.<模块>.<接口名>.post()` 调用。每个接口描述对象含 `url`、中文 `name`、`post(data, cfg)` 方法。

| 模块文件 | 后端前缀 | 主要接口 |
| --- | --- | --- |
| `account.js` | `/v1/account` | register、login、smsSend、loginByCode、setPassword、info、update、changePassword、logout、credits、creditsLogs |
| `task.js` | `/v1/task` | estimate、create、deconstruct、precheck、classifyImages、detectElements、list、detail、delete、regenerate、regenerateSegment、resume、imageCreate、audioCreate、textCreate、digitalCreate、renderCreate |
| `content.js` | `/v1/content` | copy、imagePrompt、voice、prepare、rewrite、translate（均异步返回 `task_id`）、result（轮询） |
| `digital.js` | `/v1/digital` | list、detail、personalCreate/List/Update/Delete |
| `payment.js` | `/v1/payment` | packageList、orderRecharge、orderStatus、orderList、orderMockConfirm |
| `template.js` | `/v1/template` | list、recommend、categoryList、detail |
| `storyboard.js` | `/v1/storyboard` | list、shotUpdate |
| `common.js` | `/v1/base/common` | genConfig（公开业务配置）、uploadFile（multipart 素材上传）、uploadSign（直传预签名） |
| `feedback.js` | `/v1/feedback` | create |

> 完整接口字段契约见 [第 10 节](#10-前后端接口契约映射)。

### 4.10 组合式函数（composables）

| 函数 | 作用 |
| --- | --- |
| [useGenConfig.js](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/composables/useGenConfig.js) | 拉取并**模块级缓存**免登录配置 `/base/common/gen-config`（并发共享同一请求 `inflight`）；下发创意档位（忠实复刻/适度改造/爆款改写）、钩子强化、复刻形态、替换意图、主角表现、默认画幅/清晰度、参考视频时长上限、数字人模型开关等；前端只渲染后端配置，不写死档位 |
| [useContentPrepare.js](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/composables/useContentPrepare.js) | 复刻前置文案准备：下发 `/content/prepare` → 1.5s 间隔轮询 `/content/result`，180s 总超时；含取消（sequence 序号防旧任务回写）、质量校验（必须产出 title/subtitle/script，拒绝 fallback） |

### 4.11 工具集（utils）

| 文件 | 关键导出 |
| --- | --- |
| `request.js` | `http`：见 4.8 |
| `storage.js` | `getStorage/setStorage/removeStorage`（uni 同步存储 + 异常兜底） |
| `navigation.js` | `go/goReplace`（Tab 走 reLaunch、其余 navigateTo/redirectTo 兜底）、`toLoginPath`、`getSafeInternalRedirect`（**防开放重定向**：拒绝协议/双斜杠/反斜杠/控制字符）、`isTabPage`、`currentPagePath` |
| `upload.js` | `uploadMedia(filePath, {onProgress})`（`uni.uploadFile` multipart，字段名 `file`，带进度）、`MAX_UPLOAD_MB=50`、视频/图片扩展名白名单、`isVideoUrl` |
| `task.js` | 任务展示口径统一：`workStatus`（processing/pending→生成中）、`workTitle/workCover/workDuration`、`normalizeProgress`（生成中封顶 99%）、`workStageText`（解析素材→生成分镜→合成配音→渲染画面四阶段）、`workRemainingText`、`workFailReason`、时间/数字格式化 |
| `account.js` | 登录名/密码/手机号校验；`formatUserId`（42 → `No.000042`） |
| `clipboard.js` | `copyText`（uni 剪贴板 Promise 化） |
| `session.js` | `refreshCurrentUserProfile`：静默刷新资料与额度，会话切换时丢弃旧响应 |

### 4.12 设计系统（道家「水墨宣纸」风格）

全局令牌同时声明在 [App.vue](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/App.vue)（CSS 变量，`page` 与 `:root` 双声明兼容小程序）与 [uni.scss](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/uni.scss)（SCSS 变量）：

- **理念**：大音希声，大象无形。以宣纸为本、以墨为字、以朱砂点睛；重留白、轻装饰、细墨线分隔；
- 色板：墨（`--ink-900 #1F1D1A` 等）、宣纸（`--paper-50 #FBF8F2`、卡片 `#FFFDF9`）、墨线、**品牌朱砂 `--brand-primary #B23A2E`**、赭石次强调、苔绿/赭黄等自然状态色；
- 容器：最大宽度 **480px** 居中、极淡宣纸颗粒底纹、底部避让自定义 TabBar 与安全区；
- 字体：正文系统无衬线，标题用宋体系（`--font-serif`）带文人气；
- 复用原子类：`.app-page`、`.app-card`、`.app-btn-brand`（朱砂渐变胶囊）、`.app-btn-ghost`、`.app-chip`、`.app-field`、`.app-seal`（朱砂印章）、`.app-divider`、`.app-serif` 等；
- 动效：`cubic-bezier(0.16,1,0.3,1)` 缓入缓出，并尊重 `prefers-reduced-motion`。

---

## 5. backend 后端详解

### 5.1 分层架构与调用方向

```
Route（app/routes，轻量：声明路由/依赖/参数/响应）
  → Controller（app/controllers，仅跨 Service 复杂编排，@atomic 事务；本项目使用很少）
    → Service（app/services，业务校验/状态流转/多 CRUD 组合；模块末尾 service = Service() 单例）
      → CRUD（app/cruds，继承 CRUDBase[Model, Create, Update]；末尾 crud = Crud() 单例）
        → Model（app/models，Tortoise 实体）
  旁挂：Schema(Pydantic 校验) / Core(基础设施) / Plugin(可替换能力)
```

禁止反向依赖：Model/CRUD 不导入 Route；Service 不感知前端；业务逻辑不下沉到响应类。

### 5.2 入口与生命周期

- CLI 入口 [main.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/main.py)（Typer）：
  - `python main.py run --env=dev`：以 uvicorn 工厂方式启动（默认端口 **8801**）；
  - `migrate`：生成 Aerich 迁移（首次自动 `init_db(safe=True)` 建表）；
  - `upgrade`：应用迁移；
  - `generate <ModelName>`：调用 `generate/service/gen_code_service.py` 按 Jinja2 模板生成 route/schema/crud/service/controller/vue 代码。
- 应用工厂 [app/__init__.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/__init__.py) `create_app()`：注册异常处理器 → 中间件 → 路由 → 静态文件 → 文档（`/docs`、`/redoc`、`/ljdoc`，本地静态化 Swagger 资源）。
- 生命周期 [core/event.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/core/event.py)：
  - 启动：日志 → Redis → 数据库（含播种基础数据）→ APScheduler → **ARQ 连接池** → **卡死对账协程**；
  - 关闭：逆序释放。

### 5.3 配置体系

[app/settings.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/settings.py) 的 `Settings(BaseSettings)`：

- 按 `ENVIRONMENT`（dev/test/prod）加载 `env/.env.<env>`，`@lru_cache` 单例；
- 涵盖服务器、文档、CORS、ORM（`ORM_ENGINE` 切换 mysql/postgresql/sqlite）、Redis、ARQ 队列、任务超时阈值、微信支付、微信公众号/小程序、LLM 网关、短信（mock/tencent）、腾讯云 COS、LBS；
- `ORM_CONFIG` 属性动态产出 Tortoise 配置（连接池 maxsize=20，时区 Asia/Shanghai）；
- **安全门禁** `_check_unsafe_defaults`：prod 缺失 `SECRET_KEY`/`WORKER_CALLBACK_SECRET`/数据库密码/Redis 密码、短信真实渠道却回显验证码、CORS 用 `*` 时**直接拒绝启动**；dev/test 缺密钥自动生成临时值；
- 业务可变配置不放 env，而在数据库 `tb_system_config`（见 5.9）。

### 5.4 路由体系

统一 API 前缀 `/api`（[core/register.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/core/register.py)），三大路由树：

| 路由树 | 前缀 | 子模块（节选） |
| --- | --- | --- |
| 用户端 `routes/user` | `/api/user/v1` | account、task（含 task/template 工程模板）、base/common、template、digital、payment、feedback、storyboard、content |
| 管理端 `routes/admin` | `/api/admin/v1` | base/auth、base/myself、base/common、system/{menu,user,dept,role,log,task,monitor,cache,config}、video/{template,category}、credit、video/task、video/digital、payment |
| 回调 `routes/callback` | `/api/callback` | wxpay（微信支付/退款回调，SDK 验签免登录） |

内部接口（worker 专用，`X-Worker-Token` 校验）挂在用户端 task 路由下：`/task/callback`、`/task/checkpoint`（GET/POST）、`/task/cache`（GET/POST）。

路由约定：全部 POST 为主（即使查询）、中文 `summary`、需要操作日志的使用 `OperationLogRoute`、标量 body 用 `Body(..., embed=True)`。

### 5.5 鉴权与权限

[core/dependencies.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/core/dependencies.py)：

- Token 形态：`Authorization: Bearer <jwt>`；JWT 由 `plugin/encryption/jwts.py` 解析（含过期/非法区分）；
- **双命名空间**：解析后再与 Redis 键 `{REDIS_PREFIX}:admin:{account}` 或 `{REDIS_PREFIX}:user:{account}` 比对当前有效 token（支持服务端登出失效）；
- 导出三种依赖：
  - `DeepValidationAdminToken = Depends(validate_admin_api_key)`：管理端 Router 级鉴权；
  - `DeepValidationUserToken = validate_user_api_key`：裸函数，用户端 `Depends(...)` 使用；
  - `OptionalUserToken`：可选登录（免登录可用、登录后做归属/扣费用，如建单接口）；
- 管理端 RBAC：`AdminPermissionChecker("system:user:list")`，超管放行，否则聚合用户→角色→菜单的 `apiList` 权限点；
- 用户身份写入 `ctx`（ContextVar），供日志记录操作人。

### 5.6 统一响应与异常

[core/response.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/core/response.py)：

| 类 | code | HTTP | 语义 |
| --- | --- | --- | --- |
| `Success` | 1 | 200 | 成功 |
| `Fail` | 0 | 200 | 业务失败（项目大量业务异常仍返回 HTTP 200） |
| `AUTH` | 9 | 401 | 未授权 |
| `ERROR` | 0 | 500 | 服务异常 |

响应体形如 `{ "code": 1, "message": "操作成功", "data": ... }`。异常处理器注册于 `register.app_exceptions`（HTTPException / 请求校验 / 响应校验 / `BizException`）。中间件含 `HttpLogMiddleware`（访问与操作日志，可按路径忽略）与 CORS。

### 5.7 数据层

- 所有业务模型继承 `BaseModel`（[models/base.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/models/base.py)）：BigInt 主键、`deleted` 软删除、`to_dict()`（日期/Decimal 序列化、自动排除 deleted）、重写 `delete()` 为软删；需要时间戳加 `TimestampMixin`；
- 需要自动软删过滤的模型使用 `DefaultFilterManager`；
- 表名统一 `tb_` 前缀 + 小写下划线，字段必须有中文 `description`；外键 `db_constraint=False`（应用层维护关系）；
- `CRUDBase` 提供 get/count/query/list（pageNum/pageSize 分页）/create/update/delete；
- 迁移用 Aerich；`plugin/database/schema_sync.py` 在启动时**幂等只增不改**自动追平新增列/表。

### 5.8 核心 Service 说明

#### 5.8.1 生成任务 `services/generate_task.py`（约 1950 行，业务核心）

`class Service`（单例 `service`）的关键方法：

| 方法 | 职责 |
| --- | --- |
| `estimate(data, user)` | 下单前预估：调 `cost_rules.estimate_cost` 算价，返回 cost/明细/余额是否足够/预计秒数/可选规格（时长/画幅/清晰度）/视频编辑能力开关；与实扣同源 |
| `create(data: CreateSchema, user, order_no)` | 视频建单主流程：模板/规格校验 → 能力前置校验（有参考视频必须已接编辑模型）→ 图片角色轻量推断 → 预扣额度 → `_create_and_enqueue` 落库并下发 ARQ |
| `create_image / create_audio / create_text / create_digital / create_render` | 各任务类型建单（数字人/换口播有各自参数装配） |
| `deconstruct` | 对标视频拆解（逆推分镜） |
| `precheck` / `_detect_missing` | 建单前结构化预检，返回缺失项引导前端补素材 |
| `my_list / detail / _to_detail` | 用户作品列表/详情（组装模板、状态、结果等展示字段） |
| `regenerate / regenerate_segment / resume` | 重新生成 / 局部（单镜头台词）重跑 / 断点续跑（不重复扣费） |
| `get_checkpoint / update_checkpoint` | worker 断点读写 |
| `callback(payload: CallbackSchema)` | **worker 回写入口**：进度心跳/成功落库/分镜沉淀/结算返还/失败退款（见 3.2） |
| `reconcile_stuck / recover_orphan_tasks / list_silent_tasks` | 对账三件套 |
| `_settle_credit / _refund_credit` | 成功按实际用量结算、失败返还（异常不阻断回调） |

模块级辅助函数：`estimate_seconds`（视频 90s + 时长×25s 等估算）、`calc_stage`、`friendly_fail_reason`（失败原因用户侧脱敏）、`_build_raw_params`（下发 worker 的参数规范化）、`_abs_url`、`_normalize_pip` 等。

#### 5.8.2 额度 `services/credit.py`

`consume(user_id, cost, remark)` 免费额度优先、不足扣付费额度并写流水（`tb_credit_log`）；`_ensure_daily_reset` 跨天重置免费额度；`balance`（free_credits/credits/total/daily_free/today_used）；`grant`（充值/赠送）；`refund_consume_log`/`refund_by_task`（按 task_id 幂等返还）；`settle_by_task`（预扣→实际多退少不补）；管理端列表与流水查询。流水类型枚举：reset/consume/recharge/grant/refund/settle。

#### 5.8.3 定价规则 `services/cost_rules.py`

`estimate_cost(task_type, cfg, **ctx)` 是**预估与实扣唯一来源**：基础价（`gen.cost.*` DB 配置）+ 10 秒档/1080P/多图/逐镜多段附加项；`settle_refund`、`describe`（人类可读明细）。

#### 5.8.4 支付 `services/payment.py`

下单（`create_credit_order` 充值 / `create_video_order` 付费任务）、`mock_confirm`（开发态模拟支付）、微信 V3 `pay_callback`/`refund_callback`、`_deliver` 交付（充值到账走 `credit.grant`）、`apply_refund`/`auto_refund_by_task`、`reconcile_expired`、订单状态/列表。订单状态：1 待支付/2 已支付/3 已交付/4 已取消/5 退款中/6 已退款。支付网关与回调在 `core/wxpay.py` 与 `routes/callback/wxpay.py`。

#### 5.8.5 账号 `services/account.py`

`register`、`login`、`send_sms_code`（`core/sms.py`，mock 渠道开发态可回显验证码）、`login_by_code`（首次自动注册）、`set_password`、`info/update_info`、`change_password`、`logout`（删 Redis token）、`_generate_token`（JWT + 写 Redis）。密码用 passlib + argon2。

#### 5.8.6 其他 Service

| 模块 | 职责 |
| --- | --- |
| `system_config.py` | 业务配置表 CRUD；`DEFAULT_CONFIGS` 首次播种（模型名、画幅、定价、网关与路由 `gen.gw.*`/`gen.route.*`、缓存、真人策略、水印、ASR、质检阈值等约 60 项）；私密配置 `******` 打码；`is_public` 控制是否对用户端下发 |
| `digital.py` | 平台数字人形象与用户专属数字人 |
| `video_template.py` / `video_category.py` | 平台模板与分类（推荐位、排序、上下架） |
| `gen_template.py` | 用户「工程模板」（生成参数快照复用） |
| `storyboard.py` | `persist_from_usage` 把 worker 回写的分镜/镜头/质检沉淀为 `tb_episode`/`tb_shot`；镜头编辑回写 `usage.shot_prompts` |
| `asset_cache.py` | 中间产物缓存（跨任务复用降本，TTL 可配） |
| `sign.py` | 每日签到与连续 streak |
| `feedback.py` | 意见反馈 |
| `prompt_builder.py` / `skill_prompts.py` / `gen_rules.py` | prompt 组装、技能提示词资产加载、生成规则（时长/画幅/分辨率档位归一化等） |
| `system/*` | 菜单/用户/角色/部门/日志/任务/监控/缓存等后台域 |

### 5.9 异步基础设施（core）

| 文件 | 作用 |
| --- | --- |
| `task_queue.py` | ARQ 池初始化/关闭；`enqueue_generate_task`（固定 job_id 去重、残留结果键清理重试）；`job_alive`（exists 探活，异常时保守返回 True）；`enqueue_ai_task`/`read_ai_copy_result`、`enqueue_skill_task`/`read_skill_result`、`enqueue_skill_pipeline` 等轻量内容任务与结果轮询（Redis 键 `ai_copy:`/`skill:` 等） |
| `reconcile.py` | 后台协程：静默预警 → 孤儿回收 → 卡死判失败 → 支付单超时取消 |
| `scheduler.py` | APScheduler（Redis jobstore）+ 分布式锁，启动系统定时任务 |
| `cache.py` | Redis 客户端封装 |
| `database.py` | Tortoise 初始化/关闭与启动播种 |
| `oss.py` | 腾讯云 COS 客户端与上传（未启用回退本地） |
| `upload.py` | 素材上传校验：扩展名白名单（jpg/png/mp4/mov/webm 等）、50MB 上限、`save_upload_file` |
| `middlewares.py` / `handlers.py` / `exceptions.py` | 日志中间件、异常处理、`BizException` |
| `ratelimit.py` | 限流（短信发送等场景） |
| `routeclass.py` | `OperationLogRoute` 自定义路由类（自动操作日志） |
| `docs.py` | 自定义接口文档 UI |

### 5.10 plugin 可替换能力层

[core/plugin.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/core/plugin.py) 统一实例化，避免循环导入：

- `ctx`：ContextVar 请求上下文（g/stack/task/recorder）；
- `redis`（AIORedis）、`locker`（AsyncRedisLock）、`database`（OrmDB）、`scheduler`；
- `password`（argon2 等哈希）、`jwt`；
- 子目录：`database/`（aiomysql/aiopostgres/aioredis/aioorm/schema_sync）、`encryption/`（crypto/jwts/password）、`sms/`（aliyun/txyun/submail）、`wechat/`（公众号 mp、小程序 miniprogram）、`robot/`（钉钉/企微通知）、`scheduler/`、`logger`。

### 5.11 代码生成器

`generate/`：`GenCodeService` 依据 Tortoise 模型与 `generate/templates/*.j2`（controller/crud/route/schema/service/vue）+ `utils/`（字段拆分、Jinja2 工具）一键产出分层 CRUD 脚手架，生成后仍需按同层代码人工复核。

`scripts/` 运维脚本：`seed_video_templates.py`、`seed_digital.py`、`import_template_media.py`、`ensure_columns.py`、`check_system_config_keys.py`（配置键名校验）。

---

## 6. worker AI 生成组件详解

### 6.1 定位与原则

独立 Python 进程（[worker/](file:///f:/project/web3_pro/yiyuan-ai-video/worker)），通过 ARQ 消费 Redis 队列，调用 AI 网关完成真实生成，**不连接业务数据库**，结果一律 httpx 回调 backend。自底向上分层、禁止反向依赖：

```
plugin（logger/arq/notice/oss）
  → app/core（event/gateway/runtime_config/worker 等单例与基础设施）
    → app/tools（BaseGenTool 子类：真实网关调用 + 故障转移）
      → app/services（BaseGenService 子类：编排、进度、断点、用量、回调）
        → app/workers/generate_worker.py（最薄 ARQ 任务入口）
```

### 6.2 入口与配置

- [worker/main.py](file:///f:/project/web3_pro/yiyuan-ai-video/worker/main.py) Typer 命令：`run`（启动 ARQ Worker）、`check`（环境自检：Redis/队列/模型名/工具导入/OSS/热更新地址）、`enqueue`（联调下发测试任务）；
- `app/settings.py`（pydantic-settings，读 `env/.env.<env>`）：Redis/ARQ（队列名 `generate`、并发 5、单任务超时 5400s、重试 3 次、keep_result 600s）、回调（`NOTIFY_URL`、`NOTIFY_TOKEN` 与 backend `WORKER_CALLBACK_SECRET` 一致）、热更新间隔 60s、各能力模型名与网关、视频轮询/分辨率上限/真人模式/水印、BGM/转场/字幕/方言 TTS、抠像/头部检测并发、OSS 等；
- `app/core/worker.py` 的 `WorkerSettings` 注册 13 个任务函数（见 6.3）。

### 6.3 ARQ 任务注册表（generate_worker.py）

| 任务函数 | 对应业务 |
| --- | --- |
| `process_video` | 视频生成 / 视频复刻主链路 |
| `process_text` / `process_image` / `process_audio` | 文本 / 图片 / 语音与背景音乐 |
| `process_digital` | 数字人口播 |
| `process_render` | 视频换口播 |
| `process_deconstruct` | 对标视频拆解 |
| `ai_recognize` | 参考图角色识别（backend 可同步 await 结果） |
| `ai_detect_elements` | 对标视频元素槽位检测 |
| `ai_copy_generate` / `ai_image_prompt_generate` | 带货文案 / 图片提示词（结果写 Redis 供轮询） |
| `skills_run` / `skills_pipeline` | 单技能运行 / 技能流水线（含参考视频抽帧增强上下文） |

### 6.4 tools 工具层（`app/tools/`）

`base.py` 的 `BaseGenTool`：

- `generate(params) -> ToolResult` 抽象方法；
- `_switch_gateway` 切换命名网关；
- `_with_failover()`：按候选网关顺序故障转移（**视频仅在提交阶段切换，提交成功后轮询固定同一网关**，避免重复计费）；
- 子类：`text_tool`、`image_tool`、`video_tool`（文生/图生/参考生/编辑多模式）、`audio_tool`、`digital_tool`（支持 OpenAI 兼容与方舟 `ark` 原生协议）、`grid_tool`（九宫格）、`matting_tool`（AI 抠像，未配置时降级绿幕色键）、`head_track_tool`（人物头部检测）、`render_tool`、`video_understand_tool`、`script_anchor`、`prompt_template`。

### 6.5 services 编排层（`app/services/`）

- `base.py` 的 `BaseGenService.run(task_id, notify_url, params, ctx)` 模板方法：编排进度、断点、重试、BGM/音效/字幕锚点等后处理、用量汇总与回调；
- 业务 service：`video_service`（含多段出片 multiseg）、`deconstruct_service`、`digital_service`、`render_service`、`image_service`、`audio_service`、`text_service`、`ai_copy`、`ai_rewrite`、`ai_translate`、`ai_vision`、`image_prompt`、`broll_service`（B-roll 空镜）、`element_detect`/`element_binding`/`element_binding_qc`（元素检测/绑定/质检）、`watermark_service`、`prompt_builder`、`gen_rules`、`script_schema`。

### 6.6 媒体处理 core 能力

`app/core/` 包含大量视频/音频处理模块：`asr.py`（语音识别+词级时间戳）、`shots.py`（镜头切分）、`multiseg.py`（多段合成）、`compose.py`（成片合成）、`overlay.py`（字幕/贴纸叠加）、`subtitle.py`、`align.py`（音画对齐）、`frame_quality.py`（彩条/纯色退化画面质检）、`deidentify.py`（真人拟态化）、`media_prep.py`（参考媒体预处理）、`metrics.py`、`retry.py`、`asset_cache.py`、`skill_runtime.py`/`skill_orchestrator.py`/`skill_memory.py`（技能运行时与编排）。

### 6.7 网关与热更新

- 命名网关注册表 + 能力路由：`core/gateway.py` 的 `resolve(capability)` / `resolve_all(capability)`，能力含 chat/text/image/video/video_edit/audio/music/digital/asr/matting；
- 配置来源优先级：backend DB `gen.gw.<name>.*` + `gen.route.<capability>` → env 兜底槽位；
- `core/runtime_config.py` 周期（默认 60s）拉取 backend 全量配置热更新，无需重启；
- 提示词资产：`worker/skills/`（SKILL.md + assets）与 backend 单一来源 `backend/skills/prompts/`（容器只读挂载进 worker）。

### 6.8 回调插件（plugin/notice.py）

- `notify(url, payload, token)`：POST 进度/终态，头 `X-Worker-Token`，失败线性退避重试；
- `fetch_checkpoint` / `checkpoint_save`：断点拉取/回写（URL 由 callback 地址推导）。

---

## 7. admin 管理后台与 desktop 用户端（简述）

### 7.1 admin（SCUI，正常维护）

- 技术：Vue 3.5 Options API 为主、Vite、Element Plus 2.14、Pinia、ECharts、TinyMCE、xgplayer；dev 端口 2800，`/api` 代理 backend；
- 入口 `src/main.js` + `scui.js`（全局组件/指令统一注册）；
- 业务目录：
  - `src/views/system/`：菜单、用户、角色、部门、日志、任务、监控、缓存、**业务配置 config（热更新模型/定价/网关）**；
  - `src/views/video/`：模板、分类；`digital/` 数字人；`credit/user` 额度；`payment/` 订单与套餐；`home/` 首页看板；
  - `src/api/model/*.js` 由 `api/index.js` 自动收集；统一走 `utils/request.js`（axios）；
  - 动态菜单来自后端 + `config/route.js`，`import.meta.glob` 映射组件；权限用 `$AUTH`/`$ROLE` 与指令；
  - 通用组件 `scTable/scForm/scDialog/scUpload/scFilterBar/scWorkflow` 等。

### 7.2 desktop（已冻结）

Vue 3 `<script setup>` + Naive UI + Pinia 的响应式用户端，承接桌面与移动浏览器。结构（`src/api/model`、`composables`、`views/create|home|market|template|user`）与 mobile 同源，契约仍可作跨端回归参考（`backend/tests/test_desktop_api_contract.py`），但**不再为其补功能或联调**。

---

## 8. 数据库模型总览

全部表使用 `tb_` 前缀、软删除（`deleted`）、`create_time/update_time`。

### 8.1 业务表

| 模型 | 表名 | 说明 |
| --- | --- | --- |
| `UserModel` | `tb_user` | C 端用户：账号、昵称、密码(argon2)、`free_credits` 每日免费额度、`credits` 付费额度、`last_reset_date` |
| `UserSignModel` | `tb_user_sign` | 每日签到（user_id+sign_date 唯一、streak 连签） |
| `CreditLogModel` | `tb_credit_log` | 额度流水（change/balance/type/task_id） |
| `VideoCategoryModel` | `tb_video_category` | 模板分类 |
| `VideoTemplateModel` | `tb_video_template` | 平台视频模板（封面/示例/标签/默认文案三段式/prompt_parts/推荐位） |
| `GenerateTaskModel` | `tb_generate_task` | **生成任务主表**：task_no、type、status、progress、materials、params、checkpoint、result_video(Text)、result_text、fail_reason、usage(计费/失败码/分镜)、device、user_id、order_no |
| `GenTaskTemplateModel` | `tb_gen_task_template` | 用户工程模板（参数快照） |
| `EpisodeModel` | `tb_episode` | 分镜集（source: replicate/multi_segment） |
| `ShotModel` | `tb_shot` | 镜头：时间码、narration、prompt、status、result_url、qc_score/qc_low/qc_note |
| `DigitalHumanModel` | `tb_digital_human` | 平台/用户专属数字人形象 |
| `UserPaymentModel` | `tb_user_payment` | 支付订单（含渠道快照、source 业务快照） |
| `PaymentPackageModel` | `tb_payment_package` | 充值套餐 |
| `FeedbackModel` | `tb_feedback` | 意见反馈 |
| `GenAssetCacheModel` | `tb_gen_asset_cache` | 生成中间产物缓存 |

### 8.2 系统表（admin RBAC 与运维）

`tb_system_user`（管理员）、`tb_system_role`、`tb_system_menu`（含 `apiList` 权限点）、`tb_system_dept`、`tb_system_log`（操作日志）、`tb_system_task`/`tb_system_tasklog`（定时任务与日志）、`tb_system_config`（**业务配置键值表，热更新来源**）。另含 Aerich 迁移元数据表。

### 8.3 主要关系

```
UserModel 1─* GenerateTaskModel（user_id，应用层关联）
VideoTemplateModel 1─* GenerateTaskModel（template 外键, db_constraint=False）
GenerateTaskModel 1─1 EpisodeModel 1─* ShotModel
GenerateTaskModel 1─* CreditLogModel（task_id） / UserPaymentModel（order_no）
SystemUser *─* SystemRole *─* SystemMenu（RBAC）
```

---

## 9. 核心业务链路

### 9.1 注册与登录

1. **密码注册**：`/account/register`（账号 6-20 位、密码 6-32 位，前端 `utils/account.js` 校验与后端同源）→ argon2 哈希入库；
2. **验证码登录**：`/account/sms/send`（限流：60s 间隔、日 10 条、5 分钟有效；mock 渠道 dev 可回显）→ `/account/login/code`，不存在则自动注册；
3. 登录成功返回 `{ info, token }`：前端 `userStore.setToken/setUserInfo`；后端把 token 写入 Redis（用户命名空间）；
4. 后续请求 Bearer  token；失效由 request 层统一清登录态并带 `redirect` 跳登录，登录成功用 `goReplace` 安全回跳。

### 9.2 视频复刻（studio 页，最完整链路）

```
选对标视频 → uploadMedia(/base/common/upload/file) 得绝对 URL
→ detect-elements 检测原片元素槽位 → 用户绑定替换图
→ (可选) classify-images AI 识别图片角色
→ content/prepare 生成 title/subtitle/script 三段文案（轮询 content/result）
→ task/deconstruct 逆推分镜（轮询 task/detail.result_text）
→ task/estimate 实时显示消耗
→ task/create 建单（预扣额度、下发 ARQ）
→ 前端轮询 detail：progress + 四阶段文案
→ worker 生成完成回调 → success 落库 → 跳转作品/分镜编辑
```

### 9.3 额度计费（预算前置）

`预估（estimate_cost）→ 预扣（credit.consume，记流水）→ 生成 → 成功按 usage.cost 结算（settle 多退）/ 失败原路返还（refund，幂等）`。免费额度（默认 3 次/日，跨天重置）优先扣减。付费订单任务失败不走额度返还，触发支付单自动退款。

### 9.4 充值支付

`package/list 选套餐 → order/recharge 建单 → mock: order/mock/confirm；wechat: 拉起支付 → 微信回调 /api/callback/wxpay/video 验签 → pay_callback → _deliver 发额度 → 前端轮询 order/status 刷新`。超时未支付由对账协程取消。

### 9.5 轻量异步内容（文案类）

`content/rewrite|copy|translate|...` 立即返回 `{task_id}` → worker 执行并把结果写 Redis 键 → 前端 1.5s 轮询 `content/result`，响应 `status: done|pending|not_found`，done 时取 `result.content/metadata`。

---

## 10. 前后端接口契约映射

约定：基础路径 `/api/user/v1`（mobile 生产）；除上传外均为 POST JSON；响应包裹 `{code, message, data}`，`code=1/0/9`。

| mobile API 调用 | 后端路由 | 鉴权 | 关键入参 / 返回 |
| --- | --- | --- | --- |
| `account.register/login` | `/account/register` `/account/login` | 否 | account/password；返回 `{info, token}` |
| `account.smsSend/loginByCode` | `/account/sms/send` `/account/login/code` | 否 | phone[/code]；验证码登录首登返回 `is_new` |
| `account.info/credits` | `/account/info` `/account/credits` | 用户 | 资料 / `{free_credits, credits, total, daily_free, today_used}` |
| `account.changePassword/logout/...` | 同名 | 用户 | — |
| `common.genConfig` | `/base/common/gen-config` | 否 | 复刻档位/形态/意图/lead_acts/gen.* 配置 |
| `common.uploadFile` | `/base/common/upload/file` | 用户 | multipart `file`（≤50MB）→ `{url, filename, size}` |
| `template.recommend/list/detail/categoryList` | `/template/*` | 否/混合 | 分页 pageNum/pageSize |
| `task.estimate` | `/task/estimate` | 可选 | type/template_id/duration/shot_count/ratio/... → `{cost, detail, balance, enough, estimate_seconds, options}` |
| `task.create` | `/task/create` | 可选 | `CreateSchema`（materials/template_id/创意参数/image_roles 等） |
| `task.deconstruct/precheck` | 同名 | 可选/否 | 对标视频拆解 / 缺失项 |
| `task.classifyImages/detectElements` | 同名 | 否 | urls；reference_video |
| `task.imageCreate/audioCreate/textCreate/digitalCreate/renderCreate` | `/task/*/create` | 可选 | 各 Schema（grid/split、digital、VideoReNarrate） |
| `task.list/detail/delete` | 同名 | 用户 | 分页/状态筛选；id |
| `task.regenerate/regenerateSegment/resume` | 同名 | 用户 | id[+segment_index/new_text] |
| `storyboard.list/shotUpdate` | `/storyboard/list` `/storyboard/shot/update` | 用户 | task_id 分页；task_id/index/prompt/narration/时间码 |
| `digital.list/detail/personal*` | `/digital/*` | 混合 | 平台形象只读；专属数字人 CRUD |
| `payment.packageList/orderRecharge/orderStatus/orderList/orderMockConfirm` | `/payment/*` | 用户/否 | package_id/device；order_no |
| `content.copy/imagePrompt/voice/prepare/rewrite/translate` | `/content/*` | 用户 | 异步返回 `{task_id}` |
| `content.result` | `/content/result` | 用户 | `{status: done/pending/not_found, result?}` |
| `feedback.create` | `/feedback/create` | 用户 | content/contact |
| （内部）worker | `/task/callback` `/task/checkpoint` `/task/cache` | `X-Worker-Token` | 非前端调用 |

任务状态机：`processing → success | failed`（pending 前端按 processing 展示）；作品列表过滤内部类型 `deconstruct`。

---

## 11. 本地开发与运行

### 11.1 前置依赖

- Node.js（前端）、Python 3.11+（后端/worker）、MySQL（本地 dev 默认）或 PostgreSQL、Redis；
- 根目录基础设施（可选，prod 形态）：`docker compose up -d postgres redis`。

### 11.2 backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
pip install -r requirements.txt
cp env/.env.example env/.env.dev        # 填写 MySQL/Redis/网关等
python main.py migrate --env=dev        # 首次建表 + 播种基础数据/默认配置
python main.py run --env=dev            # http://127.0.0.1:8801
```

- 接口文档：`http://127.0.0.1:8801/docs`；
- dev 默认 `PAYMENT_MODE=mock`、`SMS_PROVIDER=mock`（可回显验证码），无需真实支付/短信即可联调；
- 密钥缺失时 dev 自动生成临时值（重启失效）。

### 11.3 worker

```bash
cd worker
pip install -r requirements.txt
cp env/.env.example env/.env.dev        # Redis、BACKEND_PUBLIC_URL、NOTIFY_TOKEN、网关密钥
python main.py check --env dev          # 环境自检
python main.py run --env dev            # 另开终端启动消费
```

> 仅做前端/建单联调时，任务会停留在 processing；必须启动 worker 才能跑通完整生成。容器部署时 `BACKEND_PUBLIC_URL` 须用服务名 `http://backend:8801`。

### 11.4 mobile

```bash
cd mobile
npm install
npm run dev:h5                          # http://localhost:5174 （/api 代理到 8801 的 /api/user）
```

微信小程序：`npm run dev:mp-weixin` 后用微信开发者工具打开 `dist/dev/mp-weixin`；需在 `manifest.json` 填入小程序 appid 并配置后端合法域名。

### 11.5 admin / desktop

```bash
cd admin   && npm install && npm run dev     # http://localhost:2800
cd desktop && npm install && npm run dev     # http://localhost:5173（冻结端）
```

---

## 12. 构建、部署与运维

### 12.1 Docker Compose

[docker-compose.yaml](file:///f:/project/web3_pro/yiyuan-ai-video/docker-compose.yaml) 编排 5 个服务（网络 `grapefruit`）：

| 服务 | 镜像/构建 | 端口 | 说明 |
| --- | --- | --- | --- |
| postgres | postgres:16 | 127.0.0.1:5432 | prod 数据库，密码取根目录 `.env` |
| redis | redis:latest | 127.0.0.1:6379 | `--requirepass` 注入密码 |
| backend | `devops/backend/Dockerfile` | 8801 | `python main.py run --env=prod`，挂载证书 |
| worker | `devops/worker/Dockerfile` | — | 只读挂载 `backend/skills/prompts` |
| caddy | caddy:2 | 80/443/443udp | 静态托管 admin/desktop + `/api` 反代，HTTP/3 |

`docker compose up -d --build` 全栈启动；`docker compose config` 校验编排。

### 12.2 前端构建与静态托管

- 构建脚本内置 `scripts/sync-build.mjs`：**先写新产物再删旧文件**，避免在线用户加载旧 chunk 404；
- admin/desktop 产物 → `devops/caddy/data/{admin,desktop}`，由 Caddy 托管（admin 在 `/admin` 子路径）；
- **mobile H5 产物 → `devops/nginx/data/h5`**（`npm run build`），由 Nginx 托管（部署形态以实际网关配置为准）。

### 12.3 部署脚本与检查清单

- [deploy.sh](file:///f:/project/web3_pro/yiyuan-ai-video/deploy.sh)：拉代码 → 构建 backend/worker 镜像 → 构建前端 → 重载 Caddy；数据库新增列由 `schema_sync.py` 启动自动追平；
- 发布检查：`docs/release-checklist.md`；AI 网关接入手册：`docs/ai-gateway-guide.md`；
- 修改业务配置项后运行：`python backend/scripts/check_system_config_keys.py`。

---

## 13. 测试体系

| 目录 | 框架 | 重点用例 |
| --- | --- | --- |
| `backend/tests/` | pytest（`pytest.ini`） | 成本规则、配置 upsert/键名、生成任务辅助、数字人 PIP、支付 Schema、孤儿回收、失败文案、技能端点、worker 配置端点、**跨端契约**（`test_mobile_replicate_alignment.py`、`test_desktop_api_contract.py`、`test_cross_worker_contract.py`）、路由接线 |
| `worker/tests/` | pytest | 网关路由/故障转移、运行时配置热更新、ASR/对齐/合成/字幕、镜头切分与质检、元素绑定、数字人、各 tool 参数护栏与恢复（resume）、重试、技能编排等 60+ 文件 |

运行：

```bash
cd backend && python -m pytest -q
cd worker  && python -m pytest tests/ -q
```

前端无统一测试/Lint 配置，以构建验证为准：mobile 用 `npm run build:h5`，涉及视觉在 375–768px 移动视口自测。

---

## 14. 关键约定与规范

来自 [AGENTS.md](file:///f:/project/web3_pro/yiyuan-ai-video/AGENTS.md) 的强制约束（摘要）：

1. **中文优先**：交流、注释、日志、用户可见文案全部中文；新增函数必须有中文文档字符串/注释，解释「为什么」；
2. **最小改动**：不批量格式化、不顺手重构、不升级依赖；公共逻辑进公共层，页面不得自建请求/存储实例；
3. **mobile 跨端**：只用 `<script setup>` + Composition API；平台能力必须走 `uni.*` 封装（chooseImage/chooseVideo/uploadFile/previewImage/saveImageToPhotosAlbum），禁止直接操作 DOM；生命周期从 `@dcloudio/uni-app` 导入；
4. **mobile 契约**：创作接口走 `/user/v1`（user token）；字段以后端 `backend/tests/` 跨端用例为准；设计原则「简单、引导式上手」，不堆砌高级控件；
5. **后端**：四空格缩进、类型提示、async 全异步；禁止可变默认参数与裸 `except`；CRUD/Service 末尾单例；表名 `tb_` 前缀；分页 `pageNum/pageSize`；时间格式 `YYYY-MM-DD HH:mm:ss`；
6. **响应语义**：`code=1/0/9`，部分业务异常保持 HTTP 200，未经授权不做全链路状态码迁移；
7. **安全**：禁止入库真实密钥；日志不记录密码/Token/Authorization；prod 配置门禁；软删过滤不得绕过；
8. **数据库**：模型变更走 Aerich 迁移（`migrate` → `upgrade`），禁止手改 SQLite；
9. **新增生成能力**四层落点：`worker/app/tools` 加工具 → `services` 加编排 → `workers/generate_worker.py` 注册任务函数并加入 `core/worker.py` 的 `functions` → `backend/app/services/generate_task.py` 下发对应任务类型。

---

## 15. 关键文件索引

### mobile

| 文件 | 作用 |
| --- | --- |
| [vite.config.js](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/vite.config.js) | 端口 5174、`/api→/api/user` 代理、SCSS 注入、`@` 别名 |
| [src/pages.json](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/pages.json) | 12 页面注册与全局样式 |
| [src/config/index.js](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/config/index.js) | API_URL / Token / 超时 |
| [src/utils/request.js](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/utils/request.js) | 请求封装、code 分发、401 防抖、SSE |
| [src/api/model/](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/api/model) | 9 个业务接口模块 |
| [src/store/modules/user.js](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/store/modules/user.js) | 认证/额度 Store |
| [src/pages/studio/index.vue](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/pages/studio/index.vue) | 创作工作台（复刻+九宫格） |
| [src/App.vue](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/App.vue) / [uni.scss](file:///f:/project/web3_pro/yiyuan-ai-video/mobile/src/uni.scss) | 设计令牌与全局原子类 |

### backend

| 文件 | 作用 |
| --- | --- |
| [main.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/main.py) | Typer 入口：run/migrate/upgrade/generate |
| [app/settings.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/settings.py) | 全部环境配置与 prod 安全门禁 |
| [app/__init__.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/__init__.py) / [core/register.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/core/register.py) | 应用工厂、路由/中间件/文档注册 |
| [app/routes/user/__init__.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/routes/user/__init__.py) | 用户端路由树 |
| [app/core/dependencies.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/core/dependencies.py) | 双角色 JWT 鉴权与 RBAC |
| [app/core/response.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/core/response.py) | Success/Fail/AUTH/ERROR |
| [app/core/task_queue.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/core/task_queue.py) | ARQ 下发/去重/结果读取 |
| [app/core/reconcile.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/core/reconcile.py) | 卡死/孤儿/订单对账协程 |
| [app/services/generate_task.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/services/generate_task.py) | 建单、回调、计费结算、续跑 |
| [app/services/cost_rules.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/services/cost_rules.py) | 预估/实扣同源定价 |
| [app/services/system_config.py](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/services/system_config.py) | DEFAULT_CONFIGS 业务配置清单 |
| [app/models/](file:///f:/project/web3_pro/yiyuan-ai-video/backend/app/models) | 全部 Tortoise 模型 |

### worker / 部署

| 文件 | 作用 |
| --- | --- |
| [worker/main.py](file:///f:/project/web3_pro/yiyuan-ai-video/worker/main.py) | run/check/enqueue CLI |
| [worker/app/core/worker.py](file:///f:/project/web3_pro/yiyuan-ai-video/worker/app/core/worker.py) | ARQ WorkerSettings 与任务注册 |
| [worker/app/workers/generate_worker.py](file:///f:/project/web3_pro/yiyuan-ai-video/worker/app/workers/generate_worker.py) | 13 个任务入口 |
| [worker/app/tools/base.py](file:///f:/project/web3_pro/yiyuan-ai-video/worker/app/tools/base.py) | 工具基类与网关故障转移 |
| [worker/plugin/notice.py](file:///f:/project/web3_pro/yiyuan-ai-video/worker/plugin/notice.py) | 回调/断点通知 |
| [docker-compose.yaml](file:///f:/project/web3_pro/yiyuan-ai-video/docker-compose.yaml) | 五服务容器编排 |
| [AGENTS.md](file:///f:/project/web3_pro/yiyuan-ai-video/AGENTS.md) | 全仓协作规则（权威约束） |
| [README.md](file:///f:/project/web3_pro/yiyuan-ai-video/README.md) | 项目总说明与快速开始 |
