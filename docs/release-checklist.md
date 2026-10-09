# 上线检查清单 · 数字人口播

> **交付端**：`backend`（含 `worker`）、`admin`、`desktop`
> **适用版本**：数字人口播功能（数字人形象 + 口播文案/音频 → 口型驱动视频）
> **接续开发**：本轮已修项、遗留待办与已知测试噪声见 [`digital-human-followups.md`](./digital-human-followups.md)

---

## 0. 结论速览

代码链路已完整并可自动化验证（backend 133 项、worker 543 项单测全绿），
但**上线前有 8 项阻断事项必须人工处理**，其中 2.2 / 2.3 / 2.7 / 2.8 不处理则数字人功能必然不可用。

> ⚠️ 2026-10-04 复核：本地两份 env **不可作为线上配置依据**（`backend/env/.env.prod` 仍是
> MySQL 形态、`SECRET_KEY` 为空），服务器为独立副本；`docker-compose` 已是 `--env=prod`，
> 启动安全校验在生效。

> ✅ 已知测试噪声已消除：`tests/test_skill_orchestrator_plans.py` 原先在 worker 全量 pytest 下有 9 个用例
> 因 `asyncio.get_event_loop()` 依赖已被关闭的默认事件循环而假失败，现已改走 `asyncio.run`，
> worker 全量 543 项全绿（详见接续开发文档 P2 项）。

| 编号 | 阻断项 | 不处理的后果 |
|---|---|---|
| 2.1 | 数据库补列 | 数字人接口直接报错（列不存在）——现已由 backend 启动自动追平 |
| 2.2 | worker `BACKEND_PUBLIC_URL` | 管理端配置的 `gen.digital_model` 传不到 worker，任务全部失败 |
| 2.3 | 数字人模型未配置 | 数字人任务以「未配置模型」失败 |
| 2.4 | 回调令牌不一致 | 任务全部卡 `processing`，4 小时后判失败 |
| 2.5 | 短信仍是 mock 渠道 | 验证码明文返回前端，任何手机号可无校验注册 |
| 2.6 | worker OSS 字段名 | 生成结果用模型临时直链，过期后作品打不开 |
| 2.7 | 代码未提交、未推送 | 服务器拉不到新字段,功能静默不生效 |
| 2.8 | ORM_ENGINE 未设为 postgresql | backend 用 MySQL 驱动连 PG,启动即失败 |

---

## 1. 变更范围

### 1.1 新增文件

| 文件 | 作用 |
|---|---|
| `worker/app/tools/digital_tool.py` | 数字人口播生成工具（形象图 + 音频 → 口型视频） |
| `worker/app/services/digital_service.py` | 数字人任务编排（进度/断点/回调） |
| `worker/tests/test_digital_tool.py` | 数字人工具单测（10 项，含画中画混音 / motion 透传 / 多段断点续跑） |
| `backend/plugin/database/schema_sync.py` | 数据库结构追平（backend 启动时自动执行，幂等） |
| `backend/scripts/ensure_columns.py` | 结构缺口的核查 / 手工补执行脚本（本文档 2.1 备用） |

### 1.2 主要改动

| 端 | 改动 |
|---|---|
| backend | 数据模型新增 4 列；新增 `digital` 任务类型；新增 `POST /api/user/v1/task/digital/create`；用户端数字人列表/详情强制只返回**已上架**；管理端数字人权限点由 `save` 校正为 `create/update/active/delete`；菜单权限点启动自愈 |
| worker | 新增 `digital` 能力路由（`gen.route.digital`）；新增数字人工具与编排；ARQ 注册任务数 4 → 5；新增 `DIGITAL_MODEL` 配置与热更新映射 |
| admin | 数字人表单新增形象图 / 音色 / 生成模型 / 默认口播文案；生成任务页新增「数字人」类型筛选与视频预览 |
| desktop | 数字人页完整流程（列表 → 选形象 → 填台词 → 提交 → 跳生成页）；生成页阶段按任务类型展示；作品页标题兼容数字人名称 |

### 1.3 启动时自动完成（无需人工）

`backend` 启动链路 `lifespan → init_database_data()` 会自动：

- **补种配置项**：`gen.digital_model`、`gen.route.digital` 缺失即写入；
- **补齐菜单权限点**：按菜单 `name` 增量补齐缺失权限点（只增不减，不覆盖自定义项）。

验证：重启后日志中应出现

```
菜单权限点同步 [digital] 补齐: ['video:digital:create', ...]
```

---

## 2. 阻断项

### 2.1 数据库补列（现已由 backend 启动自动追平）

**背景**：本仓库未托管 aerich 迁移历史（`backend/migrations/models/` 为空），
且 `generate_schemas(safe=True)` **只建缺失的表、不给已存在的表加列**，
所以模型新增的字段以前需要在已部署库上手工补。

**现状（无需人工）**：`backend/plugin/database/aioorm.py` 的 `OrmDB.startup()` 会在
`Tortoise.init` 之后调用 `backend/plugin/database/schema_sync.py` 的 `sync_schema()`，
对已部署库**自动补新增列 / 补建后加的表**（先查 information_schema 判断缺口，
只 ADD COLUMN、只建缺失表，可重复执行）。因此**任何启动方式（`docker compose up`、
重启 backend、手工重启）都会追平结构**，不需要再按顺序「先补列再重启」。

**兜底（人工核查 / 不方便重启服务时）**：

```bash
# 1) 复核将要执行的 SQL（不连库）
python backend/scripts/ensure_columns.py --print-sql

# 2) 连库检查缺口（只读，不修改）
python backend/scripts/ensure_columns.py

# 3) 连库直接补列 / 补表（幂等）
python backend/scripts/ensure_columns.py --apply
```

本次数字人功能涉及的 SQL（PostgreSQL 会自动用双引号方言）：

```sql
-- MySQL
ALTER TABLE `tb_digital_human` ADD COLUMN `image` VARCHAR(255) NULL;
ALTER TABLE `tb_digital_human` ADD COLUMN `voice` VARCHAR(100) NULL;
ALTER TABLE `tb_digital_human` ADD COLUMN `model` VARCHAR(100) NULL;
ALTER TABLE `tb_digital_human` ADD COLUMN `default_text` TEXT NULL;
```

**验收**：

```bash
# 列应存在且均为可空
docker compose exec postgres psql -U postgres -d grapefruit -c "\d tb_digital_human"
# 启动时若确实补过列/表,日志中会出现;无缺口时不会打印,属正常
docker compose logs backend | grep 数据库结构追平
```

> 新增模型字段/新表时，请把条目登记到 `backend/plugin/database/schema_sync.py`
> 的 `TABLE_COLUMNS` / `CREATE_TABLES`，启动时即会自动追平。

---

### 2.2 worker 的 `BACKEND_PUBLIC_URL`

**原因**：`worker/app/core/runtime_config.py` 通过该地址周期拉取 `gen.*` 配置。
`worker/app/settings.py` 的默认值是 `http://127.0.0.1:8801`，而**仓库内所有 worker env 文件都没有配置该项**。
在容器内 `127.0.0.1` 指向自身 → 热更新必然失败 → **管理端填写的 `gen.digital_model` 永远传不到 worker**。

**处理**：在**服务器**的 `worker/env/.env.prod` 中补齐（仓库内副本已改，但该文件在 `.gitignore` 中，服务器有独立副本）：

```ini
# 拉取 backend 业务配置(热更新)
BACKEND_PUBLIC_URL=http://backend:8801
CONFIG_REFRESH_INTERVAL=60

# 数字人口播(留空则完全依赖管理端 gen.digital_model 下发)
DIGITAL_MODEL=
```

**验收**：

```bash
docker compose exec worker python main.py check --env prod
```

输出中应包含：

```
配置热更新: http://backend:8801 (间隔 60s)
```

🚫 若出现 `WARNING ... BACKEND_PUBLIC_URL 指向本机`，说明配置未生效，**必须修复后再上线**。

---

### 2.3 配置数字人模型

**原因**：代码链路完整 ≠ 能出片。是否可用取决于 AI 网关是否提供数字人（口型驱动）模型。

```bash
# 1) 探测网关有哪些模型（零成本）
python worker/scripts/probe_gateway.py --base-url <网关地址> --api-key <密钥> --models
```

在**管理后台「系统管理 → 业务配置」**中填写（页面按「配置键」搜索后逐条编辑）：

| 配置键 | 值 |
|---|---|
| `gen.digital_model` | 数字人（口型驱动）模型名 |

若数字人模型不在视频网关，再填 `gen.route.digital` = `gen.gw.<名字>` 中定义的网关名。

**约束**：数字人能力复用视频的「提交 + 轮询」机制，**OpenAI 兼容网关与方舟原生网关（proto=ark）都支持**。
方舟原生协议下形象图以 `reference_image`、口播音频以 `audio_url` 下发（形象图不能标 `first_frame`，
否则会被当图生视频处理、丢掉音频驱动）。

**生效延迟**：worker 热更新周期默认 60s（或重启 worker 立即生效）。

**验收**：`gen.digital_model` 留空时提交数字人任务，应得到明确失败提示（而非静默产出无口型视频）：

```
数字人口播未配置模型:请在管理端「业务配置」填写 gen.digital_model(数字人模型名)
```

---

### 2.4 回调令牌必须两边一致

`backend.WORKER_CALLBACK_SECRET` ↔ `worker.NOTIFY_TOKEN`，不一致时回调接口直接
返回 `非法回调请求`，任务永远卡在 `processing`，直到 `TASK_STUCK_TIMEOUT`（默认 14400s）后被
对账协程判失败。

```bash
docker compose exec backend env | findstr WORKER_CALLBACK_SECRET
docker compose exec worker  env | findstr NOTIFY_TOKEN
```

两者必须**完全相同**。

---

### 2.5 ⚠️ 短信通道仍是 mock：验证码会明文返回给前端

**旧描述已过期**（2026-10-04 核对）：原文说编排以 `--env=test` 启动、跳过安全校验 —— 现 `docker-compose.yaml` 的 backend 已是 `command: ["python", "main.py", "run", "--env=prod"]`，`_check_unsafe_defaults()` **已在生效**，会在 `SECRET_KEY` / `WORKER_CALLBACK_SECRET` / 数据库密码 / `REDIS_PASSWORD` 缺失、或 `CORS_ALLOW_ORIGINS` 含 `*` 时**直接拒绝启动**。`PAYMENT_MODE` 本地副本已为 `wechat`（真实微信支付）。

**仍然存在的真实风险 —— 短信通道**：

| 配置项 | 代码默认值 | 后果 |
|---|---|---|
| `SMS_PROVIDER` | `mock` | 不发真实短信，验证码只写日志 |
| `SMS_DEV_RETURN_CODE` | `True` | **注册/登录验证码直接返回给前端响应里** |

启动校验**不会拦住这一项**（源码明确放行 mock 渠道回显，理由是"mock 本就不真实发码"）。结果是：**任何手机号都能无验证码校验注册**，且验证码在接口响应中明文可见。

```yaml
# docker-compose.yaml
backend:
    command: ["python", "main.py", "run", "--env=test"]
```

`_check_unsafe_defaults()` 只在 `env == "prod"` 时生效（`backend/app/settings.py`），
而以下默认值均为「开发态」：

| 配置项 | 代码默认值 | 线上风险 |
|---|---|---|
| `SECRET_KEY` | 内置固定值 | JWT 可被伪造（**已由启动校验兜住，不配就起不来**） |
| `PAYMENT_MODE` | `mock` | 可模拟支付成功（本地副本已配 `wechat`） |
| `CORS_ALLOW_ORIGINS` | 含 `*` | 跨域全开（**已由启动校验兜住**） |

**处理**（二选一或同时）：

1. 在服务器 `backend/env/.env.prod` 中显式覆盖上述项为生产值；
2. 或把 `docker-compose.yaml` 的启动参数改为 `--env=prod`，让安全校验在启动时强制拦截。

**验收**：

```bash
docker compose exec backend env | findstr "SMS_PROVIDER SMS_DEV_RETURN_CODE PAYMENT_MODE"
# 已接短信:SMS_PROVIDER=tencent  SMS_DEV_RETURN_CODE=false  PAYMENT_MODE=wechat
# 暂用 mock(风险自担):SMS_PROVIDER=mock  需自行加注册风控
```

---

### 2.6 worker 的 OSS 字段名

**原因**：`worker/plugin/oss.py` 是腾讯云 COS，`worker/app/settings.py` 读取的是 `OSS_SERVICE_*`；
但仓库内 `worker/env/.env.*` 写成了 `OSS_SECRET_ID` / `OSS_BUCKET` / `OSS_PROVIDER=aliyun` 等
（后端命名），因 `Settings` 设置了 `extra="ignore"` 被**静默忽略** → `OSS_ENABLED` 为假
→ 生成结果只保留模型临时直链，**过期后用户作品打不开**。

**处理**：服务器 `worker/env/.env.prod` 改为

```ini
OSS_ENABLE=true
OSS_SERVICE_SecretId=
OSS_SERVICE_SecretKey=
OSS_SERVICE_Bucket=
OSS_SERVICE_Region=ap-chengdu
OSS_SERVICE_Accelerate=false
```

**验收**：

```bash
docker compose exec worker python main.py check --env prod
# 应输出：OSS 转存: 已启用
# 若输出「未启用(生成结果保留模型原始直链,可能过期)」→ 字段名仍然不对
```

---

### 2.7 ⚠️ 代码必须先提交并推送，否则服务器拿不到本轮改动

服务器按 `git pull` 部署，而 `backend/env/.env.*`、`worker/env/.env.*` 都在 `.gitignore` 中
（配置要人工同步，见 2.2 / 2.4 / 2.6），**代码则必须入库**。

**上线前第一件事**：

```bash
git status                     # 确认没有遗留的未提交改动
git push                       # 本地领先远端的提交全部推上去
docker compose up -d --build backend worker
```

> 若工作区有未提交改动就上线，服务器上跑的是**旧代码**：新字段（`motion` / `pip.bg_volume`）不存在，
> 前端传了会被后端丢弃，且不会报错 —— 表现为"功能没生效"，极难排查。

### 2.8 ⚠️ `ORM_ENGINE` 必须为 `postgresql`

`docker-compose.yaml` 的数据库是 `postgres:16`，但 `Settings.ORM_ENGINE` **代码默认值是 `mysql`**。
若服务器 `backend/env/.env.prod` 未显式写 `ORM_ENGINE = "postgresql"`，backend 会用 MySQL 驱动
去连 PostgreSQL 容器 —— 表现为启动即连接失败或"表不存在"，且启动安全校验**不会拦**（它只看
`ORM_ENGINE` 对应的那个密码项是否为空）。

> 注意：`backend/env/.env.prod` 在 `.gitignore` 中，**仓库内这份副本仍是 MySQL 形态**
> （`MYSQL_HOST = "mysql"` 指向早已不存在的 compose 服务），文件头注释也写明了这一点。
> **不要拿仓库内副本推断线上配置**，必须登录服务器核对。

**验收**（服务器上执行）：

```bash
docker compose exec backend env | findstr ORM_ENGINE
# ORM_ENGINE=postgresql     ← 必须
docker compose exec postgres psql -U postgres -d grapefruit -c "\d tb_digital_human"
# 列应存在且均为可空
```

---

## 3. 部署步骤

> 根目录的 `deploy.sh` 已与现状对齐（项目名 `yiyuan-ai-video`、工作目录 `/home/ubuntu/pro`、
> 前端目录 `admin/` `desktop/`），可等价执行「拉代码 → compose 构建启动 → 构建前端 → 重载 caddy」；
> 手工部署时按下面步骤执行即可。

```bash
# ---------- 1. 拉取代码（本地先提交并推送,见 2.7） ----------
#   本地: git status   # 必须干净
#        git push      # 本地领先的提交全部推上远端
git pull

# ---------- 2. 数据库结构:backend 启动时自动追平(见 2.1),无需手工补列 ----------
#   如需人工核查 / 不方便重启服务时:
#   python backend/scripts/ensure_columns.py            # 只读检查
#   python backend/scripts/ensure_columns.py --apply    # 补列 / 补表

# ---------- 3. 同步服务器 env（2.2 / 2.6） ----------
#   编辑 worker/env/.env.prod：BACKEND_PUBLIC_URL / CONFIG_REFRESH_INTERVAL / DIGITAL_MODEL / OSS_SERVICE_*

# ---------- 4. 重建后端与 worker ----------
docker compose up -d --build backend worker

# ---------- 5. 确认启动自愈生效 ----------
docker compose logs backend | findstr "菜单权限点同步"
docker compose logs backend | findstr "数据库结构追平"
docker compose logs worker  | findstr "配置热更新"

# ---------- 6. 配置数字人模型（2.3）：管理后台 → 系统管理 → 业务配置 ----------

# ---------- 7. 构建三个前端（各一次） ----------
cd admin   && npm install && npm run build
#   内部执行：vite build && node ../scripts/sync-build.mjs dist ../devops/caddy/data/admin
cd ../desktop && npm install && npm run build
#   内部执行：vite build && node ../scripts/sync-build.mjs dist ../devops/caddy/data/desktop

# ---------- 8. 重载网关 ----------
docker compose restart caddy
```

**关于构建产物**：`devops/caddy/data` 在 `.gitignore` 中，是**服务器本地运行时目录**，
因此前端构建必须在服务器上执行（或本地构建后把 `dist` 内容手工同步到对应目录）。

**前端生产基址必须与 Caddy 一致**（Caddy 未对 `/api/*` 做路径重写，前端负责带上正确前缀）：

| 端 | 文件 | 值 | 访问路径 |
|---|---|---|---|
| admin | `admin/.env.production` | `VITE_APP_API_BASEURL=/api/admin` | `/admin/`（vite `base: '/admin/'`） |
| desktop | `desktop/.env.production` | `VITE_APP_API_BASEURL=/api/user` | `/` |

**改动这两个基址会导致全站接口 404。**

---

## 4. 数字人形象录入

### 4.1 主路径：管理后台页面

**业务管理 → 数字人**（浏览器地址 `/admin/digital`，admin 用 history 路由 + `base: '/admin/'`），
支持列表 / 新增 / 编辑 / 查看 / 上下架 / 删除 / 预览视频。

表单字段说明：

| 字段 | 说明 | 是否必填 |
|---|---|---|
| 名称 | 数字人展示名 | ✅ |
| 头像 | 列表展示用 | — |
| 性别 / 风格 / 标签 / 简介 | 展示与筛选 | — |
| 预览视频 | 列表页可预览的示例成片 | — |
| **形象图** | 口型驱动底图（建议正方形半身照）；留空回退头像 | 建议填 |
| **音色** | TTS 音色标识；留空用网关默认音色（`AUDIO_VOICE`） | — |
| **生成模型** | 覆盖全局 `gen.digital_model`；一般留空 | — |
| **默认口播** | 用户未填文案时使用的默认台词 | 建议填 |

> ⚠️ **非超管账号需先授权**：数字人菜单的接口权限点为
> `video:digital:list / create / update / active / delete`。
> 本次已修正菜单 seed 并加了启动自愈（只增不减），重启 backend 后自动补齐；
> 若仍 403，请到「系统管理 → 角色管理」给对应角色勾选「数字人」菜单。
>
> 注意：**超级管理员账号（`superuser=True`）绕过权限校验**，用它验证会掩盖权限问题，
> 请务必用运营角色复验第 5 节第 2 条。

### 4.2 备用路径：直连接口

管理页面不可用时（例如前端产物未及时同步）：

```bash
# 1) 获取管理端令牌（默认超管 admin / admin123456，上线前务必修改）
curl -s -X POST http://<host>/api/admin/v1/base/auth/password \
  -H "Content-Type: application/json" \
  -d '{"account":"admin","password":"admin123456"}'

# 2) 新增数字人（Authorization 必须带 "Bearer " 前缀）
curl -s -X POST http://<host>/api/admin/v1/video/digital/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <上一步返回的 token>" \
  -d '{
        "name": "知性小姐姐",
        "avatar": "https://<cos>/digital/avatar.jpg",
        "image": "https://<cos>/digital/portrait.jpg",
        "gender": "女",
        "style": "知性主播",
        "desc": "适合本地商家口播",
        "tags": ["口播", "餐饮"],
        "voice": "alloy",
        "model": null,
        "default_text": "欢迎来本店，开业期间全场5折！",
        "preview_video": null,
        "sort": 0,
        "active": true
      }'
```

---

## 5. 回归验证清单

| # | 端 | 验证点 | 预期 | 覆盖方式 |
|---|---|---|---|---|
| 1 | admin | 管理后台「数字人」页正常打开 | 列表加载成功（无 404 / 无白屏） | 手工 |
| 2 | admin | 用**非超管**账号新增/编辑/上下架数字人 | 全部保存成功（不再 403） | 自动化（权限点比对）+ 手工 |
| 3 | admin | 新增数字人填写形象图 + 音色 + 默认口播 | 保存成功，重新打开表单数据回显 | 手工 |
| 4 | admin | 「生成任务」页类型筛选选「数字人」 | 能筛出数字人任务，结果可预览播放 | 手工 |
| 5 | desktop | `/digital` 列表 | 只显示已上架数字人；后台下架后刷新消失 | 手工 |
| 6 | desktop | 选数字人 → 填台词 → 开始生成 | 跳转 `/generate/{id}`，进度按「解析口播文案 → 合成口播音频 → 提交数字人任务 → 口型驱动合成 → 回传成片」推进 | 手工 |
| 7 | desktop | 生成成功 | 作品标题为数字人名称，可下载播放，**口型与音频同步** | 手工 |
| 8 | desktop | 未登录点「选择」 | 弹登录框，不建单 | 手工 |
| 9 | backend | 用户端列表 / 详情接口 | 下架数字人不返回；详情传下架 id 返回「数字人不存在」 | 自动化 |
| 10 | backend | 未配置 `gen.digital_model` 时提交 | 任务失败，原因明确指向「业务配置」 | 自动化 |
| 11 | backend | 失败任务「断点续跑」 | 不重复扣额度；已合成音频被复用（日志 `断点续跑:复用已合成口播音频`） | 自动化 |
| 12 | backend | 生成失败 | 额度原路返还（消耗文案「数字人口播消耗」） | 手工 |
| 13 | 全端 | 既有能力回归 | 文生视频 / 图生图 / 语音 / 背景音乐不受影响 | 手工 |

---

## 6. 观测点与日志关键字

| 日志 | 位置 | 含义 |
|---|---|---|
| `[process_digital] task_id=... start` | worker | 数字人任务开始消费 |
| `[DigitalHumanTool] 口播音频就绪 tts=... voice=...` | worker | TTS 合成完成 |
| `[DigitalHumanTool] 提交数字人口播 model=... duration=...` | worker | 已提交数字人模型 |
| `[配置热更新] ...` | worker | 配置拉取成功（含变更项） |
| `[配置热更新] 拉取失败(保持现状)` | worker | **热更新失败，查 2.2** |
| `菜单权限点同步 [xxx] 补齐: [...]` | backend | 权限点自愈动作 |
| `非法回调请求` | backend | 回调令牌不一致，查 2.4 |

**卡单排查**：任务长时间 `processing` → 依次检查 2.2（模型未下发）、2.4（回调被拒）、
worker 是否存活（`docker compose ps worker`）。

---

## 7. 回滚方案

本次**无破坏性 schema 变更**（仅新增可空列），回滚粒度可控：

1. **只止血数字人**（推荐，无需回滚代码）：管理后台把 `gen.digital_model` 置空，
   60s 内生效，数字人任务立即以明确原因失败，其余能力不受影响。

2. **回滚代码**：`git revert` 后重新构建 `backend` / `worker` / `admin` / `desktop`。
   旧代码不认识新列，Tortoise 按模型选取字段，多出的可空列不影响运行。

3. **worker 异常**：`docker compose stop worker`。
   残留任务由 backend 对账协程在 `TASK_STUCK_TIMEOUT` 后自动判失败并退额度。

---

## 8. 已知缺口（不阻断本次上线，需知悉）

| 项 | 现状 | 影响 |
|---|---|---|
| 权限点既有缺口 | `system:dept:*`(7)、`system:task:*`(6)、`system:monitor:detail`、`system:cache:admin:all/delete` 共 16 个权限点后端在用但菜单 seed 未提供（对应菜单在种子里不存在） | 非超管访问这些系统模块会 403，与数字人无关 |
| 数字人模型可用性 | 代码就绪，但依赖网关提供口型驱动模型 | 未配置前数字人任务会明确失败（见 2.3） |
