# 生成能力（Skills）总索引

本文档索引 `worker` 组件中所有「原子生成能力」（skill）。每个能力对应 `worker/app/tools/` 下的一个工具类，由 `services/` 编排、`workers/generate_worker.py` 作为 ARQ 任务入口消费。

> 设计理念参照 [Pixelle-Video](https://github.com/ATH-MaaS/Pixelle-Video) 的「原子能力 + 文档」模式：每个 AI 能力是一个独立、可组合、有文档的模块；能力靠代码注册表与目录约定被发现和运用，MD 文档逐篇说明「是什么、怎么调用、怎么扩展」。

## 调用链

```
ARQ 任务方法(process_*) → service(编排+进度+回调) → tool(真实 AI 网关)
```

- `backend` 只建单并下发任务到 ARQ 队列（`enqueue_generate_task`）。
- `worker` 不直连业务数据库，执行完成后通过 `notify_url` 回调 backend 落库。
- 任务状态：`processing → success / failed`。

## 能力路由表

各能力走 OpenAI 兼容网关，网关地址与模型名由 backend 下发并热更新。

| 能力 | 工具类 | capability（路由键） | 入口任务 | 说明 |
| --- | --- | --- | --- | --- |
| 文本生成 | `TextGenTool` | `text` | `process_text` | Chat Completions，文案/标题/改写基座 |
| 图像生成 | `ImageGenTool` | `image` | `process_image` | 文生图 / 图生图（编辑） |
| 视频生成 | `VideoGenTool` | `video` | `process_video` | t2v / i2v / r2v / edit |
| 数字人口播 | `DigitalHumanTool` | `digital` | `process_digital` | 形象图 + 口播音频 → 口型驱动视频 |
| 音频合成 | `AudioGenTool` | `audio` / `music` | `process_audio` | TTS / 背景音乐 |
| 提示词模板 | `prompt_template`（纯函数） | — | — | 画幅/清晰度标签装配（散文见资产层） |
| 提示词资产层 | `prompts/`（MD 资产 + 加载器） | — | — | 运行时提示词的集中管理/热更新（含 Pixelle-Video 引入能力） |
| 词锚点编排 | `script_anchor`（纯函数） | — | — | 脚本/字幕词序号锚点与时间估算 |

## 统一接口

所有网关工具继承 `worker/app/tools/base.py` 的 `BaseGenTool`：

```python
class BaseGenTool:
    name: str            # 能力名，如 "image"
    description: str     # 能力描述
    capability: str      # 网关路由键（默认等于 name）

    async def generate(
        self,
        params: dict,
        checkpoint: dict | None = None,   # 断点续跑进度
        on_stage = None,                   # 阶段回调（上报进度）
    ) -> "ToolResult": ...
```

统一返回结构（`worker/app/schemas/base.py`）：

```python
@dataclass
class ToolResult:
    content: Any                     # 结果（URL 字符串 / 文本 / 逗号拼接的多段 URL）
    metadata: Dict[str, Any]         # success / error_type / mode / model / 用量等

@dataclass
class Usage:                         # 计费用，预留
    model: str = ""
    tokens: int = 0
    images: int = 0
    seconds: int = 0
    chars: int = 0
```

**失败不抛异常**：工具内部捕获异常后返回 `ToolResult(metadata={"success": False, "error_type": ...})`，由上层 service 转成 `failed` 回调，不会中断任务流程。

### 网关故障转移

`BaseGenTool._with_failover(capability, call)` 按候选列表（`gen.route.<cap>` → 固定槽位回退链）依次尝试；当前网关失败自动切换下一个候选。`video` 仅在**提交阶段**切换，提交成功后轮询复用同一网关。

## 如何新增一个生成能力

1. `tools/` 新增工具类继承 `BaseGenTool`，实现 `generate`，声明 `name` / `description` / `capability`。
2. `services/` 新增对应 service，编排「分阶段进度 + 调 tool + 汇总用量 + 回调」。
3. `workers/generate_worker.py` 新增 `process_xxx` 任务方法，转调 service。
4. 在 `core/worker.py` 的 `functions` 注册任务。
5. 在本文档与 `.codebuddy/skills/` 新增对应能力文档。

## 文档导航

| 能力 | Agent 技能（`.codebuddy/skills/`） | 开发者文档 |
| --- | --- | --- |
| 文本生成 | `text-generation/SKILL.md` | [text-generation.md](./text-generation.md) |
| 图像生成 | `image-generation/SKILL.md` | [image-generation.md](./image-generation.md) |
| 视频生成 | `video-generation/SKILL.md` | [video-generation.md](./video-generation.md) |
| 数字人口播 | `digital-human/SKILL.md` | [digital-human.md](./digital-human.md) |
| 音频合成 | `audio-synthesis/SKILL.md` | [audio-synthesis.md](./audio-synthesis.md) |
| 提示词模板 | `prompt-template/SKILL.md` | [prompt-template.md](./prompt-template.md) |
| 提示词资产层 | — | [prompt-assets.md](./prompt-assets.md) |
| 词锚点编排 | `script-anchor/SKILL.md` | [script-anchor.md](./script-anchor.md) |

## 关联文档

- `worker/README.md`：组件架构与运行方式
- `docs/ai-gateway-guide.md`：网关配置项、各能力模型对照与排查
- `docs/release-checklist.md`：发布核对清单
