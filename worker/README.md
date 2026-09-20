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
│   └── notice.py                 #    回调通知(httpx 异步 POST backend)
├── app/
│   ├── core/
│   │   ├── plugin.py             # ② 全局单例门面(logger)
│   │   ├── event.py              # ③ ARQ 生命周期钩子(on_startup/on_shutdown)
│   │   ├── gateway.py            #    命名网关注册表 + 能力路由 + 候选网关解析
│   │   ├── runtime_config.py     #    业务配置热更新(周期拉取 backend 配置)
│   │   └── worker.py             # ④ WorkerSettings 工厂(注册任务/队列/并发)
│   ├── enums/                    #    环境 / 生成类型枚举
│   ├── settings.py               #    环境配置(pydantic-settings)
│   ├── schemas/                  #    工具结果 ToolResult / Usage / 入参
│   ├── tools/                    # ⑤ 生成能力(真实调用 OpenAI 兼容网关)
│   │   ├── base.py               #    BaseGenTool:网关故障转移(_with_failover)
│   │   ├── text_tool.py          #    文本生成
│   │   ├── image_tool.py         #    文生图 / 图生图
│   │   ├── video_tool.py         #    文生 / 图生 / 参考生视频
│   │   └── audio_tool.py         #    语音合成 / 背景音乐
│   ├── utils/                    #    OSS 转存等通用工具
│   ├── services/                 # ⑥ 业务编排:分阶段进度 + 调 tool + 汇总用量 + 回调
│   └── workers/                  # ⑦ ARQ 任务入口(最薄层):generate_worker.py
├── scripts/                      # 运维脚本:probe_gateway.py(网关能力探测)
├── tests/                        # 单测
├── main.py                       # Typer CLI: run / check / enqueue
└── requirements.txt
```

调用链:`ARQ 任务方法 → service(编排+进度+回调) → tool(真实 AI 网关)`。

## 核心设计

- **后端只下发,不处理**:`backend` 创建 `tb_generate_task` 记录(status=processing),调用 `app.core.task_queue.enqueue_generate_task("process_video", task_id, notify_url, params)` 下发到 ARQ。
- **worker 不碰 DB**:worker 消费任务,调用 `tool.generate`(真实调用 AI 网关),通过 `notify_url` 把 `processing / success / failed` 状态与进度/结果/用量回传后端。
- **后端回写**:`backend/app/routes/user/task.py` 的 `/callback` 接口(带 `X-Worker-Token` 鉴权)接收回传并落库。
- **新增生成类型**:`tools/` 加工具 → `services/` 加 service → `workers/generate_worker.py` 加任务方法 → 注册进 `core/worker.py` 的 `functions`。

## AI 网关与模型配置

各能力(chat / text / image / video / audio / music)统一走 OpenAI 兼容网关，网关地址与模型名由 backend 下发并热更新：

- 解析入口：`app/core/gateway.py` 的 `resolve_all(capability)`(候选列表)与 `resolve(capability)`(主用网关)
- 热更新：`app/core/runtime_config.py` 周期拉取 backend 全量配置（默认 60 秒）
- 故障转移：`app/tools/base.py` 的 `_with_failover()`，当前网关失败自动切换候选网关；
  视频仅在提交阶段切换，提交成功后轮询复用同一网关

完整配置项清单、各能力模型对照与排查方法见 [`../docs/ai-gateway-guide.md`](../docs/ai-gateway-guide.md)。

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

- `notify_url` 鉴权令牌(`NOTIFY_TOKEN`)建议改为非对称/定期轮换,当前为共享密钥。
- 用量计费:`usage` 已由 worker 回传,后端 `callback` 暂只记录日志,后续落库参与结算。
- 任务取消:当前 worker 运行期间若用户删除任务,会在回调时因找不到记录而忽略;如需中途取消,需引入 cancel 信号。
