# FastAPI Boot 基础框架

这是从 `fast_api_boot` 项目提取出来的**通用基础框架副本**，移除了 RWA 学院代理系统的业务代码，保留可复用的中后台脚手架。

你可以直接基于这个副本开始新的业务开发，无需再从原项目中剥离业务代码。

---

## 包含内容

| 目录 | 说明 |
|------|------|
| `backend/` | FastAPI 后端框架：分层架构、RBAC 权限、代码生成器、插件体系、任务调度 |
| `frontend/` | Vue 3 管理后台（SCUI）：动态路由、布局系统、通用组件库 |
| `desktop/` | Vue 3 桌面端（Naive UI）：登录 + 首页 + 个人中心骨架 |
| `devops/` | Docker / Nginx / Redis 配置 |

> **已移除**：RWA 价格、礼包、课程、用户订单、支付、余额、释放排期、邀请关系等业务代码。

---

## 技术栈

- **后端**：FastAPI + Tortoise ORM + Aerich + Redis + APScheduler + Typer
- **管理后台**：Vue 3 + Vite + Element Plus + Pinia + Vue Router + Axios
- **桌面端**：Vue 3 + Vite + Naive UI + Pinia + Vue Router

---

## 快速开始

### 1. 启动基础设施

```bash
docker-compose up -d mysql redis
```

### 2. 启动后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python main.py migrate --env=dev
python main.py upgrade --env=dev
python main.py run --env=dev
```

后端默认运行在 `http://127.0.0.1:8801`

### 3. 启动管理后台

```bash
cd frontend
npm install
npm run dev
```

默认运行在 `http://localhost:2800`

### 4. 启动桌面端

```bash
cd desktop
npm install
npm run dev
```

默认运行在 `http://localhost:5173`

---

## 后端核心命令

```bash
# 启动服务
python main.py run --env=dev

# 生成数据库迁移
python main.py migrate --env=dev

# 应用数据库迁移
python main.py upgrade --env=dev

# 根据模型生成 CRUD 代码
python main.py generate <ModelName>
```

---

## 框架特性

- **系统管理**：用户、角色、菜单、部门、字典、参数配置
- **权限控制**：JWT + RBAC，支持按钮级权限
- **代码生成**：根据 Tortoise ORM 模型自动生成后端 CRUD + 路由
- **任务调度**：APScheduler + Redis 持久化
- **操作日志**：路由级自动记录请求与响应
- **多布局**：header / menu / dock / default 四种布局
- **动态路由**：后端菜单驱动前端路由
- **组件库**：scTable、scForm、scDialog、scUpload、scSelect 等

---

## 开发新模块建议

### 后端

1. 在 `app/models/` 下定义 Tortoise 模型
2. 运行 `python main.py generate <ModelName>` 生成 schema/crud/service/route
3. 在 `app/routes/admin/__init__.py` 中注册路由
4. 在 `app/core/database.py` 中添加初始化数据方法（可选）

### 前端

1. 在 `src/views/` 下创建业务页面
2. 在 `src/api/model/` 下定义 API
3. 在 `src/config/route.js` 中配置菜单路由
4. 使用 `scTable` / `scForm` / `scDialog` 等组件构建 CRUD 页面

---

## 与原版项目的关系

- **原版项目**：`f:/project/web3_pro/fast_api_boot`（保留完整 RWA 业务代码）
- **框架副本**：当前目录（`f:/project/web3_pro/fast_api_boot_framework`）

后续业务开发请在当前框架副本上进行，原项目作为历史备份保留。

---

## License

[LICENSE](LICENSE)
