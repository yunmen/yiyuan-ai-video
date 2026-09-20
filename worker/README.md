# worker — AI 异步生成任务组件

参考 `hwgg/worker` 重做的**自洽 ARQ 异步 AI 生成组件**。后端(`backend`)只负责建单并把任务下发到 ARQ 队列,真正的 AI 生成能力全部收拢在本组件,执行完成后通过 `notify_url` 回调后端落库,组件本身**不直连业务数据库**。

## 技术栈

| 组件 | 说明 |
| --- | --- |
| ARQ | 异步任务队列(Redis 作为 broker,原生 `async def` 任务,自带重试/并发) |
| httpx | 异步回调 backend 的 `notify_url` |
| loguru | 统一日志(plugin/logger) |
| pydantic-settings | 分环境配置(env/.env.{env}) |

## 目录分层(自底向上,禁止反向依赖)

```
worker/
├── env/.env.dev                  # 环境配置(Redis / ARQ / 回调 / 大模型)
├── plugin/                       # ① 可复用能力插件
│   ├── logger.py                 #    UniLogManager 日志门面
│   ├── arq.py                    #    ARQ RedisSettings 工厂
│   ├── notice.py                 #    回调通知(httpx 异步 POST backend)
│   └── factory.py                #    AI 工具工厂(预留真实大模型接入点)
├── app/
│   ├── core/
│   │   ├── plugin.py             # ② 全局单例门面(logger)
│   │   ├── event.py              # ③ ARQ 生命周期钩子(on_startup/on_shutdown)
│   │   └── worker.py             # ④ WorkerSettings 工厂(注册任务/队列/并发)
│   ├── enums/                    #    环境 / 生成类型枚举
│   ├── settings.py               #    环境配置(pydantic-settings)
│   ├── schemas/                  #    工具结果 ToolResult / Usage / 入参
│   ├── tools/                    # ⑤ 生成能力:Text/Image/Video/Audio 工具(当前模拟占位)
│   ├── services/                 # ⑥ 业务编排:分阶段进度 + 调 tool + 汇总用量 + 回调
│   └── workers/                  # ⑦ ARQ 任务入口(最薄层)
├── main.py                       # Typer CLI: run / check / enqueue
└── requirements.txt
```

调用链:`ARQ 任务方法 → service(编排+进度+回调) → tool(模拟/真实 AI)`。

## 核心设计

- **后端只下发,不处理**:`backend` 创建 `tb_generate_task` 记录(status=processing),调用 `app.core.task_queue.enqueue_generate_task("process_video", task_id, notify_url, params)` 下发到 ARQ。
- **worker 不碰 DB**:worker 消费任务,调用 `tool.generate`(当前模拟,预留 agno/OpenAI 接入点),通过 `notify_url` 把 `processing / success / failed` 状态与进度/结果/用量回传后端。
- **后端回写**:`backend/app/routes/user/task.py` 的 `/callback` 接口(带 `X-Worker-Token` 鉴权)接收回传并落库。
- **新增生成类型**:`tools/` 加工具 → `services/` 加 service → `workers/generate_worker.py` 加任务方法 → 注册进 `core/worker.py` 的 `functions`。

## 使用

```bash
cd worker
pip install -r requirements.txt

# 启动 worker(另开终端)
python main.py run --env dev

# 环境自检
python main.py check --env dev

# 联调:下发一个测试任务(需 backend 已启动且回调地址可达)
python main.py enqueue --env dev --task-id 1
```

## 待完善

- 真实大模型接入:`plugin/factory.py` 切换为 agno/OpenAI 兼容实现,`tools/*` 的 `generate` 改为真实调用。
- `notify_url` 鉴权令牌(`NOTIFY_TOKEN`)建议改为非对称/定期轮换,当前为共享密钥。
- 用量计费:`usage` 已由 worker 回传,后端 `callback` 暂只记录日志,后续落库参与结算。
- 任务取消:当前 worker 运行期间若用户删除任务,会在回调时因找不到记录而忽略;如需中途取消,需引入 cancel 信号。
