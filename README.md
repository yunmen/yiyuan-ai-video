# 一源 AI 视频（yiyuan-ai-video）

面向本地商家与电商的 **AI 短视频营销内容生成平台**。

核心链路：选择爆款模板 / 上传素材 → 提交生成任务 → 异步调用 AI 模型 → 结果落库并回显。
支持文生视频 / 图生视频 / 参考生视频、数字人口播、文生图 / 图生图、文本生成、语音合成、背景音乐，并配套用户额度、每日签到、余额与支付订单。

---

## 目录结构

| 目录 | 说明 |
|------|------|
| `backend/` | FastAPI 后端：用户 / 管理端接口、RBAC 权限、支付、生成任务建单与回调落库、系统业务配置 |
| `worker/` | AI 异步生成组件（ARQ + Redis）：消费生成任务、调用真实模型、回调 backend |
| `admin/` | 管理后台（Vue 3 + Element Plus / SCUI）：用户、任务、数字人、支付订单、系统配置 |
| `desktop/` | 用户端（Vue 3 + Naive UI，响应式）：同一套代码同时适配桌面端与移动端浏览器 |
| `devops/` | Docker、Caddy、Redis、PostgreSQL 配置 |
| `docs/` | 项目文档 |

---

## 架构总览

```
用户端 (desktop 响应式,兼容移动端)
        │  HTTP
        ▼
   backend (FastAPI)  ── 创建生成任务(tb_generate_task) ──► ARQ 队列 (Redis)
        ▲                                                        │
        │  回调 /callback (X-Worker-Token 鉴权)                  ▼
        └──────────── worker ──► AI 网关(OpenAI 兼容中转站)
                        调用 Text/Image/Video/Audio 工具
```

两个关键设计：

- **backend 只建单，不生成**：创建任务记录后把任务下发到 ARQ 队列，真实生成全部在 worker 中完成。
- **worker 不直连业务数据库**：生成完成后通过 `notify_url` 回调 backend 落库，保持组件可独立部署。

模型调用统一走 **OpenAI 兼容网关（中转站）**，网关地址与各能力模型名均为后台可配、热更新生效，并支持多网关故障转移。详见 [`docs/ai-gateway-guide.md`](docs/ai-gateway-guide.md)。

---

## 技术栈

| 部分 | 技术 |
|------|------|
| 后端 | FastAPI + Tortoise ORM + Aerich + Redis + APScheduler + Typer + loguru |
| 生成组件 | ARQ + httpx + pydantic-settings + OpenAI 兼容 SDK |
| 管理后台 | Vue 3 + Vite + Element Plus + Pinia + ECharts + xgplayer |
| 用户端 | Vue 3 + Vite + Naive UI + Pinia（响应式，兼容桌面与移动端） |
| 基础设施 | PostgreSQL 16 / Redis / Caddy / Docker Compose |

---

## 快速开始

### 1. 启动基础设施

```bash
docker-compose up -d postgres redis   # PostgreSQL(prod 形态) + Redis
```

> **本地 dev 开发用 MySQL**：在 `backend/env/.env.dev` 配置 `MYSQL_*`（`ORM_ENGINE` 默认即 `mysql`），
> 自行启动一个 MySQL 实例即可，无需使用上面的 postgres 容器。

### 2. 后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows；Linux/macOS 用 source venv/bin/activate
pip install -r requirements.txt

# 复制并填写环境配置
cp env/.env.example env/.env.dev

python main.py migrate --env=dev   # 首次运行自动建表并初始化基础数据
python main.py run --env=dev       # 启动服务
```

后端默认运行在 `http://127.0.0.1:8801`。

### 3. 生成组件（worker）

```bash
cd worker
pip install -r requirements.txt

cp env/.env.example env/.env.dev   # 填写 Redis / 回调地址 / 网关密钥

python main.py check --env dev     # 环境自检
python main.py run --env dev       # 启动 worker
```

worker 需要能访问后端（`BACKEND_PUBLIC_URL`）与 AI 网关。

### 4. 管理后台

```bash
cd admin
npm install
npm run dev
```

默认运行在 `http://localhost:2800`，`/api` 已代理到 `http://127.0.0.1:8801`。

### 5. 用户端（desktop，响应式）

```bash
cd desktop && npm install && npm run dev       # 用户端，http://localhost:5173
```

---

## 核心配置

系统业务配置（模型名、画幅、定价、网关地址与密钥）存放在数据库，**管理端可直接修改，worker 周期热更新**，无需重启或改代码：

- 管理端路径：左侧菜单**业务配置**（列表可按「配置键」搜索，逐条编辑 VALUE）
- 接口：`POST /admin/v1/system/config/upsert`（权限点 `system:config:update`）
- 配置项定义：`backend/app/services/system_config.py` 的 `DEFAULT_CONFIGS`（首次启动播种）
- worker 侧热更新：`worker/app/core/runtime_config.py`，默认 60 秒轮询

> **接入新 AI 网关（中转站）请先阅读 [`docs/ai-gateway-guide.md`](docs/ai-gateway-guide.md)**，其中包含配置项完整清单、各能力模型对照、故障转移机制与排查方法。
>
> 新增或修改配置项后，建议执行键名校验：
> ```bash
> python backend/scripts/check_system_config_keys.py
> ```

---

## 后端核心命令

```bash
python main.py run --env=dev         # 启动服务
python main.py migrate --env=dev     # 初始化 / 生成数据库迁移(首次运行自动建表)
python main.py upgrade --env=dev     # 应用迁移(仓库已清空历史迁移,按需使用)
python main.py generate <ModelName>  # 根据 ORM 模型生成 CRUD 代码
```

---

## 构建与部署

前端构建产物由 Caddy 静态托管（`devops/caddy/data`），构建命令已内置同步：

```bash
cd admin    && npm run build    # 构建并同步到 devops/caddy/data/admin
cd desktop  && npm run build    # 构建并同步到 devops/caddy/data/desktop
```

同步由 `scripts/sync-build.mjs` 完成，采用「先写新产物、再删旧文件」的顺序，
避免在线用户加载旧 chunk 时出现 404。

整栈启动：

```bash
docker-compose up -d --build
```

- 网关：Caddy（`devops/caddy/Caddyfile`），admin 部署在 `/admin` 子路径，接口走同源 `/api` 反代
- 数据库：**prod 用 PostgreSQL 16**（编排已内置），**dev 用 MySQL**；首次启动由 `python main.py migrate` 自动建表
- 对象存储：腾讯云 COS（`backend/app/core/oss.py`、`worker/plugin/oss.py`）

---

## 测试

```bash
# worker（网关路由、故障转移、配置热更新、工具协议适配）
cd worker && python -m pytest tests/ -q

# backend
cd backend && python -m pytest -q
```

开发/测试依赖见根目录 `requirements-dev.txt`。

---

## 新增生成能力

沿用「工具 → 编排 → 任务」三层，逐层新增：

1. `worker/app/tools/` 新增工具（继承 `BaseGenTool`，实现 `generate`）
2. `worker/app/services/` 新增编排 service（负责进度、断点、用量汇总、回调）
3. `worker/app/workers/generate_worker.py` 新增 ARQ 任务方法，并注册进 `worker/app/core/worker.py` 的 `functions`
4. `backend/app/services/generate_task.py` 下发对应任务类型

---

## 文档

| 文档 | 说明 |
|------|------|
| [`docs/ai-gateway-guide.md`](docs/ai-gateway-guide.md) | AI 网关（中转站）接入与配置手册 |
| [`worker/README.md`](worker/README.md) | 生成组件的目录分层与设计说明 |

---

## License

[LICENSE](LICENSE)
