# 基于FastAPI的异步后端框架

在 FastAPI 大型项目中，各层协作遵循"API 接收请求 → Controllers 协调流程 → Service 执行业务 → CRUD 操作数据"的链路。通过严格分层，可显著提升代码的可维护性、复用性和可测试性，是应对复杂业务场景的关键架构设计。

## API 层（路由层/Routing Layer）

**定位**：最上层，直接与客户端（前端、第三方服务等）交互。

**职责**：
- 处理 HTTP 请求（解析 URL、Method、Query 参数、Body 等）
- 验证请求数据的合法性（如通过 Pydantic Model 校验入参）
- 调用下游逻辑（如 Service 或 Controllers）处理业务
- 将业务结果转换为 HTTP 响应（如 JSON、状态码、错误信息）

**FastAPI 特性**：
通过 @router.get()/@router.post()等装饰器定义路由，天然绑定 HTTP 语义，是项目的"入口网关"。

## Controllers 层（控制器层/Coordinator Layer）

**定位**：中间层，协调请求流程（可选，小型项目可能省略）。

**职责**：
- 接收 API 层的请求委托，调度多个 Service 完成复杂逻辑
- 处理跨 Service 的流程控制（如顺序调用、条件分支、异常捕获）
- 统一处理请求上下文（如用户认证信息提取、日志记录）

**注意**：
在 FastAPI 中，Controllers 并非强制要求（路由函数可直接调用 Service），但在大型项目中，为了避免路由函数臃肿，常将其作为"流程协调者"存在。

## Service 层（服务层/Business Logic Layer）

**定位**：核心业务逻辑层，项目价值的集中体现。

**职责**：
- 实现具体业务规则（如订单支付、用户权限校验、促销活动计算）
- 整合多个 CRUD 操作完成原子业务（如"创建订单"需要调用 get_user、check_stock、deduct_stock、create_order_record等）
- 处理事务边界（如通过数据库事务保证多个 CRUD 操作的原子性）
- 封装领域模型（Domain Model），实现面向对象的业务逻辑表达

**特点**：
不直接操作数据库（依赖 CRUD 层），不与 HTTP 上下文耦合（可独立测试）。

## CRUD 层（数据访问层/Data Access Layer）

**定位**：最底层，直接与数据库（或其他存储）交互。

**职责**：
- 封装数据库的增删改查（Create/Read/Update/Delete）操作
- 操作 ORM 模型（如 SQLAlchemy、Tortoise-ORM 的 Model）
- 处理与数据库相关的细节（如事务、索引、分页、联表查询）

**特点**：
仅关注"数据如何存储/读取"，不包含任何业务逻辑（例如：get_user_by_id()只负责从数据库查询用户，不处理用户状态校验）。



## 应用分离

