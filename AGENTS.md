# Grapefruit 项目协作规则

本文件适用于整个仓库，供 Codex、代码助手和项目参与者在阅读、修改、审查与验证代码时使用。规则以当前仓库的真实结构和实现为依据；执行任务时，先确定改动所属子项目，再应用对应章节。

## 1. 适用范围与事实优先级

1. 用户在当前任务中的明确要求优先级最高。
2. 本文件规定全仓共同约束和各子项目的默认实现方式。
3. 当前源码、配置和相邻文件决定局部接口及写法；修改前必须先阅读同目录的代表性实现。
4. README、`docs/` 和 `.codebuddy/skills/` 仅作背景参考。它们存在乱码、旧版本号和过时目录描述时，以实际源码和清单文件为准。
5. 正确性、安全性和数据保护高于机械复制现有写法。不得复制硬编码密钥、可变默认参数、裸 `except`、吞异常或错误的旧配置。
6. 未经任务明确授权，不扩大改动范围，不顺手重构，不批量统一风格。

## 2. 项目结构与职责边界

| 路径                    | 职责                         | 主要技术与入口                                                   |
| --------------------- | -------------------------- | --------------------------------------------------------- |
| `backend/`            | HTTP API、管理端与用户端业务、代码生成器   | FastAPI、Pydantic、Tortoise ORM、Aerich；入口 `backend/main.py` |
| `worker/`             | AI 文本等后台任务消费与结果持久化         | Celery、Redis、PostgreSQL、Agno；入口 `worker/main.py`          |
| `frontend/`           | SCUI 中后台管理端                | Vue 3、Vite、Element Plus、Pinia；入口 `frontend/src/main.js`   |
| `desktop/`            | 桌面 Web 客户端和展示型页面           | Vue 3、Naive UI、Pinia、Vue I18n；入口 `desktop/src/main.js`    |
| `mobile/`             | H5、小程序等移动端应用               | UniApp、Uni UI、Pinia；入口 `mobile/src/main.js`               |
| `www/`                | 项目或公司文档站（当前尚未初始化）          | VitePress；配置 `www/.vitepress/config.mjs`                  |
| `devops/`             | Docker 镜像、Nginx 和 Redis 配置 | Dockerfile、Nginx、Redis                                    |
| `docker-compose.yaml` | 本地/服务器容器编排                 | MySQL、Redis、PostgreSQL、Backend、Nginx、Worker               |
| `deploy.sh`           | Linux 部署脚本                 | Git、pnpm、Docker Compose                                   |
| `docs/`、`http/`       | 开发说明、接口调用示例和请求样例           | Markdown、Python 示例、HTTP Client                            |

跨子项目改动必须说明调用链。例如接口字段变化通常需要同步检查后端 Schema/Route、对应 API 模块、页面表单和响应处理；不得只修改其中一端后声称完成。

## 3. 全仓通用协作规则

- 所有交流、状态说明、代码注释、运行日志、打印内容和命令行提示必须使用中文；第三方库原始异常文本可以保留，但必须补充中文上下文。

- 开始修改前先定位入口、相邻实现、调用方和数据来源。诊断问题时先证明根因，再实施修复。

- 优先最小且完整的改动。禁止无关重命名、目录搬迁、依赖升级、批量格式化和跨子项目框架迁移。

- 保留用户已有改动。没有 Git 元数据或无法读取差异时，必须明确说明限制，并通过路径、时间和内容检查控制改动范围。

- 新增依赖前说明必要性、版本和影响；仅在依赖实际变化时更新对应 `package-lock.json` 或 `requirements.txt`。

- 公共逻辑进入已有公共层；页面或路由不得重复实现已有的请求、权限、响应、存储、主题或日志基础设施。

- 代码生成器生成的文件必须按生成模板和同层代码复核，不能把生成结果视为天然正确。

- 修改与任务无关的历史缺陷时必须另行取得授权；可以在交付说明中记录风险，但不得借机扩大范围。

## 4. 代码注释与中文输出

- 所有新增或修改的函数、方法、异步函数、命令和任务入口都必须添加中文注释或文档字符串，说明职责；有参数或返回值时应说明关键语义。

- 变量、常量、正则、状态码、缓存 Key、动态 SQL、权限判断和不直观的实现步骤必须添加中文说明。

- 注释解释“为什么”和业务约束，不逐行翻译显而易见的代码。

- Python 业务文件若相邻文件使用 `# -*- coding: utf-8 -*-` 与文件信息头，则继续沿用；不得伪造作者、版本或时间。

- 用户可见提示、日志消息、Typer/Shell 输出、Celery 日志和前端通知必须使用中文。

- 禁止新增 `console.log('App Launch')`、`return {"error": "not found"}` 等英文业务输出；兼容外部协议所必需的固定英文值除外。

## 5. 安全、配置与数据保护

- 不得新增、输出、复制或提交真实密码、API Key、Token、JWT 密钥、数据库连接串和完整环境文件内容。

- 环境差异放入对应的 `backend/env/.env.*`、`worker/env/.env.*` 或各前端 `.env.*`；代码只读取配置项。

- 修改现有硬编码默认凭据时，应迁移到环境配置并提供安全的缺失配置错误，不能换成另一组明文值。

- 日志不得记录密码、验证码、Authorization 头、Cookie、完整请求头或模型服务密钥。必须记录时先脱敏。

- 数据库结构通过 Tortoise 模型和 Aerich 迁移维护；禁止直接编辑 `backend/db/db.sqlite3`。

- 默认不编辑以下第三方或生成内容：

  - `frontend/public/tinymce/`

  - `backend/static/swagger-ui/`

  - `backend/static/redoc/`

  - `www/cache/`

  - `*.map`、图片、字体、压缩资源和构建输出

- 删除、迁移或覆盖文件前必须精确确认目标；不得对项目根目录或宽泛路径执行递归破坏操作。

## 6. `backend/` FastAPI 后端规则

### 6.1 分层与调用方向

遵循以下主调用链：

```text
Route → Controller（仅复杂编排）→ Service → CRUD → Model
                         ↘ Schema / Core / Plugin
```

- `app/models/`：Tortoise ORM 实体和关联关系，不承载 HTTP 逻辑。

- `app/schemas/`：Pydantic 请求、查询和响应数据校验。

- `app/cruds/`：数据库查询与持久化，不承载业务规则。

- `app/services/`：业务校验、状态变更和多次 CRUD 组合。

- `app/controllers/`：跨 Service 流程、事务和复杂编排；简单接口可由 Route 直接调用 Service。

- `app/routes/`：声明路由、依赖、参数和响应包装，保持轻量。

- `app/core/`：数据库、缓存、依赖、异常、日志、中间件、响应和路由基础设施。

- `plugin/`：数据库、加密、OSS、短信、机器人和微信等可替换能力。

不得反向依赖：Model/CRUD 不导入 Route，Service 不依赖具体前端，业务逻辑不下沉到响应包装类。

### 6.2 Python 风格

- 使用四个空格缩进、UTF-8、`snake_case` 函数/变量、`PascalCase` 类名和明确类型提示。

- 异步数据库、Redis 和 HTTP 调用使用 `async`/`await`；不得在异步路由中加入阻塞 I/O。

- 导入按标准库、第三方库、项目模块分组；修改文件时清理本次造成的未使用导入。

- 函数必须有中文文档字符串。复杂业务方法应说明输入、返回值、异常和事务边界。

- 禁止使用 `list = []`、`dict = {}`、`Q()` 等可变或有状态对象作为新增函数默认值；使用 `None` 后在函数内部初始化。

- 禁止裸 `except:`。只捕获可处理的异常；无法恢复时记录中文上下文并继续抛出。

- 不为了风格统一重命名现有 `buildDataFunc.py`、`commonFunc.py` 等历史文件；新文件采用 `snake_case.py`。

### 6.3 Model 与 Schema

- 业务模型默认继承 `BaseModel`；需要创建和更新时间时同时使用 `TimestampMixin`。

- 需要软删除过滤的模型在 `Meta` 中使用 `DefaultFilterManager()`；删除通过现有软删除链路执行。

- 表名使用 `tb_` 前缀与小写下划线，例如 `tb_system_user`；字段必须提供中文 `description`。

- 外键按现有项目习惯设置清晰的 `related_name`，并根据项目策略使用 `db_constraint=False`。

- 枚举字段优先使用项目的 `StrCustomEnum`、`IntCustomEnum` 及 Tortoise 枚举字段。

- JSON、列表和字典默认值使用框架支持的工厂/可调用对象，禁止新增共享可变默认值。

- 查询 Schema 继承 `BaseQuerySchema`；创建、更新和领域操作分别建模，不用一个全可选 Schema 代替所有场景。

- Pydantic 字段提供中文说明；跨字段规则用 `field_validator` 或 `model_validator`，不要在 Route 中手写重复校验。

- API 字段命名必须与已有调用方一致。若需要从驼峰迁移到下划线，必须同时设计别名和兼容期。

### 6.4 CRUD、Service 与 Controller

- CRUD 类继承 `CRUDBase[Model, CreateSchema, UpdateSchema]`，模块末尾保持 `crud = Crud()` 单例模式。

- 动态查询使用 `tortoise.expressions.Q`，分页继续使用 `pageNum`/`pageSize` 对应的基础 Schema 约定。

- Service 模块末尾保持 `service = Service()`；Route 导入实例，不在请求期间反复创建 Service。

- Service 负责“数据不存在、状态不允许、账号重复”等业务校验，并返回模型或可序列化字典。

- 更新数据使用 `model_dump()` 并明确排除 `id`、关联字段和不可修改字段。

- 多服务、跨表原子操作放入 Controller，并使用 `@atomic()` 明确事务边界。

- 禁止在 Route 中拼装复杂查询或直接操作 ORM；简单的响应字段组装可以保留在现有同类 Route 中。

### 6.5 Route、鉴权与响应

- 路由使用 `APIRouter`，中文 `summary`，并沿用 `/api/admin/v1/...`、`/api/user/v1/...` 等当前注册前缀。

- 需要操作日志的路由使用 `OperationLogRoute`。

- 管理端路由默认在 Router 级声明 `DeepValidationAdminToken`；用户端按现有模式在需要鉴权的端点声明 `DeepValidationUserToken`。

- 单个 Body 标量参数继续使用 `Body(..., embed=True)`，避免前后端请求形状不一致。

- 成功、业务失败、鉴权失败和服务异常分别使用 `Success`、`Fail`、`AUTH`、`ERROR`。

- 当前业务协议以 JSON `code` 表示结果，部分业务异常仍返回 HTTP 200。除非任务明确要求全链路迁移，不得只修改一端的状态码语义。

- 返回模型前必须排除密码、软删除标记和其他敏感字段；关联数据按接口需要显式序列化。

### 6.6 数据库、缓存与迁移

- 数据库连接统一来自 `Settings.DB_URL` 和 `TORTOISE_CONFIG`，不得在业务模块重新拼接连接信息。

- Redis 使用 `app.core.plugin.redis` 和统一前缀；Key 必须包含业务命名空间及稳定标识。

- 修改模型后使用 `python main.py migrate --env=<环境>` 生成迁移，再用 `python main.py upgrade --env=<环境>` 应用。

- 迁移前确认目标环境和数据库；禁止在未确认的生产数据库上自动执行迁移。

- 不依赖固定演示密码、验证码或默认数据库凭据完成业务逻辑。

## 7. `worker/` Celery Worker 规则

- Worker 是独立同步任务进程，不照搬 FastAPI 的异步 Route/Service 写法。

- AI 业务模块沿用 `app/module/<module>/` 下的职责拆分：

  - `config.py`：模块配置和环境变量前缀。

  - `schemas.py`：任务参数校验。

  - `agent.py`：模型/Agent 组装和供应商调用。

  - `service.py`：任务记录、状态流转和生成业务。

  - `worker.py`：Celery 任务名、重试策略和对外参数。

- Celery 任务入口保持薄层，模块级导入 `service` 单例；任务名使用 `<module>.<action>`，例如 `ai_text.generate`。

- 任务状态使用 `pending → processing → success/failed`；所有异常路径必须写回失败状态或明确触发 Celery 重试。

- 原生 SQL 必须使用参数绑定。动态 SET 字段或排序字段必须来自服务内部白名单，不能直接接受外部 Key。

- 软删除查询默认排除 `deleted=true`；返回任务结果前移除内部删除字段和敏感数据。

- Redis Key 使用 `config.CELERY_APP_NAME` 等统一前缀，并包含 `task_id`。

- Worker 日志必须提供中文任务名、`task_id` 和失败上下文；不得只记录 `str(exc)` 后静默成功。

- 修改任务参数时同步检查业务端 `send_task` 调用、Schema、Service 和 README 示例。

- `worker/README.md` 中包含尚未落地或已变化的目录说明时，以 `worker/app/` 实际结构为准。

## 8. `frontend/` 管理端规则

### 8.1 Vue 与目录组织

- 新管理页面默认使用 Vue Options API，与现有绝大多数 `.vue` 文件保持一致；不得无关迁移到 `<script setup>`。

- Vue 单文件组件按 `<template>`、`<script>`、`<style>` 排列；相邻代码以 Tab 缩进为主，新代码跟随文件现状。

- JavaScript 优先使用单引号且不进行纯分号风格改写；修改已有文件时保持相邻写法。

- 页面按业务域放在 `src/views/<domain>/`；页面私有组件与页面同目录，通用组件放在 `src/components/scXxx/`。

- 组件必须声明语义化 `name`；`v-for` 必须有稳定 `:key`；复杂模板表达式抽到 `computed` 或 `methods`。

- 所有新增方法添加中文注释。通用事件优先使用 `handleXxx`；现有 CRUD 模块可继续使用 `add`、`table_edit` 等局部惯例。

### 8.2 组件、状态、路由与权限

- 优先复用 Element Plus 和已有 `scTable`、`scForm`、`scDialog`、`scUpload`、`scFilterBar` 等 SCUI 组件。

- 全局组件和指令在 `src/scui.js` 统一注册，不在页面重复注册同类全局能力。

- 状态进入 `src/store/modules/` 的 Pinia Store；Options API 页面继续通过现有 `$store` 兼容层访问。

- 动态菜单来自后端与 `src/config/route.js`，路由组件由 `import.meta.glob` 映射。新增页面必须同步检查菜单 `component` 值。

- 权限优先复用 `$AUTH`、`$ROLE` 和既有指令，不在按钮点击后才补做前端权限隐藏。

- 文案需要多语言时进入 `src/locales/`；禁止在已经国际化的页面新增仅中文硬编码。

### 8.3 API 与请求

- API 按业务域定义在 `src/api/model/*.js`，由 `src/api/index.js` 自动收集。

- 保持现有 API 描述对象形状：`url`、中文 `name`、调用方法。当前很多写操作也以 `.get()` 包装 POST；未经整体迁移不要单独重命名破坏调用方。

- 请求统一通过 `src/utils/request.js`，页面不得直接创建新的 Axios 实例。

- 页面依据统一 `code` 处理业务结果；401、网络错误和通用通知交给拦截器，页面只处理本业务状态。

- 表格列表优先使用远程分页、搜索参数和 `scTable.reload/upData`，不要在页面重复实现分页基础设施。

### 8.4 管理端 UI

- 保持紧凑、信息密集的后台风格：12px 基础字号、浅灰 `#f6f8f9` 工作区、白色内容面板和深色 `#222b45` 导航。

- 主色通过 `--el-color-primary` 及 Element Plus 派生变量控制；禁止在同一模块随意引入另一套主色。

- CRUD 页面优先采用 `el-container`、Header 工具栏、Main 表格、弹窗表单和统一消息反馈。

- 搜索区、按钮组、表格操作列、状态 Tag/Switch 保持同类页面一致；危险操作必须二次确认。

- 默认滚动条、菜单、标签页和布局尺寸由全局 SCSS 控制，页面不重复覆盖全局布局。

- 使用 `:deep()` 调整组件内部样式；组件私有样式优先 `scoped`，全局修正进入 `src/style/`。

- 在窄屏下遵循已有媒体查询；登录页在小屏隐藏侧图并让表单占满可用宽度。

## 9. `desktop/` 桌面端规则

- 默认使用 Composition API 和 `<script setup>`；组合式状态使用 `ref`、`computed` 和生命周期函数。

- UI 使用 Naive UI，图标优先使用 `@vicons/ionicons5`；不得混入 Element Plus 组件或变量。

- 应用状态进入 Pinia Store；主题、语言、侧栏折叠等全局状态统一由 `useGlobalStore` 管理。

- 用户可见文案进入 `src/locales/`，通过 `useI18n()` 的 `t()` 使用；Naive UI locale 与应用语言同步。

- 页面使用两空格或相邻文件缩进，新代码不触发整文件格式变化。

- 路由保持三类边界：独立首页、`/app` 布局内页面、登录/注册等独立页面。

- 新的布局内页面必须同时验证 `LAYOUT_MODE='top'` 和 `'side'`；不得只为一种布局写固定偏移。

- 明暗主题由 Store 与 `html.dark` 协同；所有自定义页面必须验证浅色和暗色。

- 普通容器优先使用明确的页面变量、主题类或 Naive UI 可用 Token。使用 `var(--n-*)` 前必须确认该变量在容器作用域真实存在。

- 稳定业务页面使用本地资源或受控 CDN；不得新增 `picsum.photos` 等随机外部图片作为生产依赖。

### 9.1 桌面端 UI

- 落地页内容宽度以 1120px 左右为基准，区块留白宽松，标题层级清晰；小屏断点沿用 768px 左右的现有设计。

- 品牌强调可使用绿色 `#18a058` 到蓝色 `#2080f0` 的渐变；业务页可使用现有紫色等语义色，但必须有明确用途。

- 卡片常用 10–16px 圆角、轻边框、低透明背景和克制阴影；Hover 位移通常不超过 4px。

- 导航滚动后可使用半透明背景、`backdrop-filter` 和细分隔线；暗色模式使用对应深色透明背景。

- 文本优先使用 Naive UI 文本颜色变量或透明度层级，避免大面积硬编码纯黑纯白。

- 响应式页面必须处理网格降列、导航折叠、表单双列改单列和触控按钮尺寸。

## 10. `mobile/` 移动端规则

- 使用 UniApp 跨端组件：`view`、`text`、`image`、`button` 等；不要把浏览器专用 DOM 当作默认实现。

- 页面路由、导航栏和 TabBar 在 `src/pages.json` 声明；新增页面必须同步注册。

- 尺寸优先使用 `rpx`，颜色、字号、圆角和间距优先复用 `src/uni.scss` 变量。

- 公共页面样式放入 `src/style/common.scss`；页面私有样式使用 `scoped`。

- 优先复用 Uni UI 和 `easycom`，避免为已有基础组件重复造轮子。

- 状态进入 Pinia；网络请求通过 `src/utils/request.js` 的 `uni.request` 封装；反馈和导航使用 `uni.*` API。

- 当前页面混用 Options API 与 `<script setup>`。修改时跟随相邻页面，新页面优先采用该业务目录的主流方式，不做无关统一。

- 相对导入按现有构建要求保留 `.js` 后缀；跨层复用前先确认小程序构建兼容性。

- 所有页面必须考虑底部安全区、弱网失败、加载状态、空状态和可触摸区域。

- 不假设所有后端接口都返回同一成功码：当前移动登录代码检查 `200`，管理端协议使用 `1`。接入接口时必须核对真实响应，并在集中请求/API 层统一，禁止页面各自猜测。

### 10.1 移动端 UI

- 保持轻量移动端风格：`#f8f8f8` 页面背景、白色卡片、`#007aff` 主色和清晰的触控反馈。

- 卡片、头像、列表和按钮尺寸使用 `rpx`；卡片圆角与阴影保持克制，避免桌面端大面积复杂特效。

- 表单错误、网络错误和操作结果使用移动端 Toast/Modal，文案简短中文化。

- 列表项、按钮和输入区需满足触控尺寸；不得仅靠 Hover 表达状态。

## 11. `www/` 文档站规则

- 文档内容放在 `www/src/`，站点标题、导航、侧栏、搜索和 Footer 在 `www/.vitepress/config.mjs` 配置。

- 主题覆盖放在 `www/.vitepress/theme/style.css`，优先使用 `--vp-*` CSS 变量。

- 保持当前紫色到青色 Hero 渐变和品牌按钮体系，除非任务明确要求重设计。

- 中英文导航或页面必须同步更新 locale 配置；链接文本和站点元数据使用中文或对应语言。

- 禁止直接修改 `www/cache/`；需要时由 VitePress 重新生成。

- Markdown 示例必须可执行且与当前真实命令、目录和版本一致，不保留模板默认链接冒充项目链接。

## 12. UI 与交互风格总则

- 先识别页面所属子项目，再使用其组件库、颜色、间距和布局；禁止跨端复制不兼容设计。

- 优先复用设计 Token、组件属性和全局样式，不在每个页面重复硬编码同一套颜色与间距。

- 新增页面必须有明确的视觉层级：页面标题/说明、主要操作、内容区域、空/错/加载状态。

- 表单必须包含中文标签、占位提示、校验、提交加载态和成功/失败反馈；不可重复提交。

- 表格或列表必须考虑加载、空数据、长文本、分页/刷新和危险操作确认。

- 动画用于状态反馈，时长和位移保持克制；必须尊重暗色主题、窄屏和低性能设备。

- 图标来自所在子项目既有图标体系；同一操作在同一子项目内保持名称、颜色和位置一致。

- 可访问性最低要求：图片有有效替代文本，表单有标签，纯图标按钮有标题/说明，文本与背景对比可读，键盘可操作的 Web 控件不移除焦点反馈。

## 13. API、状态与数据约定

- 后端当前统一响应主体使用 `code`、`message`，成功通常为 `code=1`，业务失败为 `code=0`，鉴权失败为 `code=9`。

- Token 通过 `Authorization: Bearer <token>` 发送；前端统一请求层负责附加 Token。

- 不在页面、Celery 任务或 Route 中重复解析环境变量；配置进入各自 Settings/Config 层。

- 管理端 API 以业务域对象组织；桌面端和移动端也必须通过集中 API/请求模块调用后端。

- 日期时间对外格式遵循当前 `YYYY-MM-DD HH:mm:ss` 约定；更改时必须同时检查序列化和前端展示。

- 软删除数据默认不进入普通查询；恢复、审计或物理删除必须由明确接口处理。

- 缓存和任务结果 Key 必须包含应用前缀、业务域和实体/任务标识，设置合理过期时间。

- 修改响应字段、成功码、分页字段或鉴权语义时，必须列出并同步所有调用方。

## 14. 修改后的验证要求

仓库没有统一的测试、Lint 或 Formatter 配置，不得虚构 `pytest`、ESLint、Prettier、Ruff 等已存在。按实际改动范围执行以下验证；运行前确认依赖已经安装。

### 14.1 Python

在项目根目录执行语法编译：

```powershell
python -m compileall backend/app backend/generate backend/plugin worker/app worker/plugin
```

涉及后端入口、数据库或 Redis 时，再使用目标环境执行最小启动/导入验证。若外部服务缺失，报告未验证项，不临时改成假数据掩盖问题。

### 14.2 管理端

```powershell
Set-Location frontend
npm run build
```

### 14.3 桌面端

```powershell
Set-Location desktop
npm run build
```

### 14.4 移动端

H5 改动至少执行：

```powershell
Set-Location mobile
npm run build:h5
```

涉及具体小程序平台时，追加相应的 `build:mp-*` 命令。

### 14.5 文档站

```powershell
Set-Location www
npm run build
```

### 14.6 Docker 与部署

```powershell
docker compose config
```

- 修改 Compose、Dockerfile、Nginx 或 Redis 配置时，检查服务依赖、端口、挂载路径、网络和健康状态。

- `deploy.sh` 中仍有历史项目名和 `fastapp`、`fastdocs` 等旧目录语义。修改部署流程时必须先与当前 `mobile/`、`www/` 等真实目录对齐，不能照抄旧名称。

- 所有部署脚本函数和日志必须使用中文说明；Shell 失败必须返回非零退出码。

### 14.7 验证结果报告

- 只声明实际运行且退出成功的命令。

- 明确列出未运行的命令、原因和剩余风险。

- 若验证失败，先保留完整错误信息并定位根因；不得删除验证、降低校验或伪造输出。

## 15. 明确禁止事项

- 禁止批量格式化、全仓换行符转换或只为个人偏好重写相邻代码。

- 禁止把 `frontend/`、`desktop/`、`mobile/` 强制迁移到同一种 Vue API、组件库或主题体系。

- 禁止直接编辑 SQLite、缓存、Source Map、第三方压缩资源、构建产物和无关锁文件。

- 禁止新增明文凭据、打印 Token、记录完整请求头或把环境文件内容写入文档。

- 禁止在 Route 中绕过鉴权，在 ORM 查询中绕过软删除，或在前端绕过统一请求拦截器。

- 禁止裸异常捕获、静默 `catch`、失败后仍返回成功状态或不记录任务失败原因。

- 禁止在没有命令输出或检查证据时声称“测试通过”“构建成功”或“问题已修复”。

- 禁止在未确认数据库、分支、目录和环境的情况下执行迁移、部署、删除或覆盖。

## 16. 任务交付清单

完成修改前逐项确认：

- [ ] 改动只覆盖用户授权范围，未覆盖用户已有修改。

- [ ] 已遵循所属子项目的架构、代码和 UI 风格。

- [ ] 所有新增/修改函数、复杂变量与关键步骤具有中文注释。

- [ ] 所有新增日志、打印和用户提示使用中文。

- [ ] 未引入真实凭据、敏感日志、共享可变默认值或吞异常逻辑。

- [ ] 已检查接口、Schema、数据库、缓存和所有调用方是否需要同步。

- [ ] 已运行与改动范围匹配的验证，并记录真实结果。

- [ ] 已说明无法验证的项目、环境限制和剩余风险。

- [ ] 未修改第三方资源、缓存、数据库、生成产物或无关锁文件。

