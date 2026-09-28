# 视频复刻（产品级能力契约）

> 本文档定义「视频复刻」这一**产品级能力**的对外契约：它调用 `VideoGenTool`（`video-generation` 原子能力）并叠加「参考视频解析 → 镜头拆解 → 逐镜头逆推 → 多段生成 → 逐镜头质检」等增强链路。
> 这是 OpenMontage「能力靠代码注册表 + 目录约定被发现」与 MoneyPrinterTurbo「Skill 明确 scope 与退出码语义」思路在本项目的落地：**scope、不做什么、输入、输出契约、失败语义、付费行为**都在这里一次性写清，避免消费方凭猜。
> 所有陈述均对照 `worker/app/tools/video_tool.py` 与 `worker/app/core/` 的实际代码，非外部推测。

## 1. 能力定位

把一条已有的参考视频，按用户的替换意图（商品 / 人物 / 场景）复刻成一条新视频，**尽量保留原片的镜头结构与运镜**，只把用户指定的元素换成新的。

- 强项：**直传原片做视频编辑**（`edit_video` 走 Seedance 2.x 视频编辑，保留原片运镜 / 节奏），而不是「拆帧 → 重绘 → 再拼」（后者会丢运镜）。
- 边界：参考视频 ≤ 30s 走单段视频编辑；> 30s 自动拆成多段逐段编辑 + 流复制拼接。
- 不产出「分镜脚本的纯文本创意」——那是 `script` / `copy_writer` 的职责。

## 2. 触发与入口

- 入口：`VideoGenTool.generate(params, notify_url, task_id)`（`video_tool.py` L295）。
- 路由：按 `gen.route.video` 选网关，提交阶段故障转移（见 `BaseGenTool._with_failover`）。
- 何时走多段：参考视频真长 > 15s（`MAX_SEGMENT_SECONDS`）→ `_generate_multi_segment`。

## 3. 输入参数（来自下发 `params`，缺键静默回退，不阻断）

| 参数 | 类型 | 作用 | 缺失时 |
|---|---|---|---|
| `reference_video` | URL | 原片（复刻来源）；多段时逐段裁对应切片编辑 | 单段进入纯文生/图生路径 |
| `original_video` | URL | 局部重跑时对原片重新抽帧（保证重跑窗口与原片对齐） | — |
| `materials` | URL[] | 替换素材（商品图 / 人物图 / 场景图）；视频素材自动剔除，由 `reference_video` 承载 | 纯复刻（不替换） |
| `intent` | str[] | 替换意图维度：`product` / `person` / `scene`（与 backend `prompt_builder.VALENT_INTENTS` 一致） | 纯复刻 |
| `ratio` / `resolution` | str | 目标画幅 / 清晰度 | 取默认 9:16 / 1080P |
| `duration` | int | 目标成片时长（秒） | 取参考视频时长 |
| `prompt` / `prompt_context` | str | 用户备注 + 后端视觉识别出的主体/商品/场景描述 | — |
| `script` | dict | 成片脚本时间轴（含 `segments[].timing`、`text`） | 无词级时间轴，退化为整段 |
| `script_anchors` | dict | 词锚点（词序号 → 时间） | — |

## 4. 输出契约

返回 `ToolResult`：

- `content`：成片 URL（多段为单条已拼接 URL）。
- `metadata`（**透明回写 backend，随详情接口完整透出**）：

| 字段 | 含义 | 说明 |
|---|---|---|
| `success` | 是否成功 | 失败时不抛异常，由上游转 `failed` 回调 |
| `usage` | 用量（模型 / 秒数 / 画幅等） | 同时承载下方自定义字段，整包即回调 `usage` |
| `shots` | 原片分镜表（仅多段任务） | `[{index,start,end,duration,narration}]` |
| `shot_prompts` | 逐镜头逆推描述（仅多段任务） | `[{index,prompt}]`，落库用列表（JSON 整数键不稳定） |
| `shot_qc` | 逐镜头质检结果（仅多段任务） | `[{index,score,low,issue}]`，只标记不重跑 |
| `decision_log` | 决策日志（P2-9） | 每次生成的「链路/模型/分辨率/时长/网关」 |
| `cost_snapshot` | 成本快照（P2-9） | `{total_seconds,actions,by_model}` |
| `degraded` / `degrade_reason` / `degrade_note` | 降级标记 | 编辑失败退化为参考帧重生成时置位 |
| `output_mismatch` / `output_note` / `output_detail` | 技术自检偏差（画幅/时长/分辨率） | 只标记不阻断，转成用户可见提示 |

## 5. 失败分类语义（消费方据此给用户看不同的提示）

| `error_type` | 含义 | 用户可见文案基调 |
|---|---|---|
| `invalid_request` | 入参非法（缺首帧 / 缺参考视频 / 分段越界 / 时间窗无效） | 「请检查素材/分段」 |
| `request_error` | 外部请求异常（下载失败 / 候选网关全部失败 / 素材预处理异常） | 「网络/素材问题，可重试」 |
| `config_error` | 环境/配置缺失（无 ffmpeg / 无 chat 模型） | 「服务暂不可用」 |
| `compose_error` | 多段组装失败（拼接待原片续接首帧抽不出） | 「生成中出错，可重试」 |
| `timeout` | 轮询结束仍无结果 | 「生成超时，可重试」 |

**原则**：任何增强链路（镜头解析、逆推、质检）失败都**只回退、不阻断**——已付费的成片不会因为一次额外的多模态调用失败而变成失败任务。

## 6. 不做什么（明确边界，避免消费方误用）

- **不洗图 / 不重绘**：不把原片拆帧后用图像模型重绘（会丢运镜）；只用视频编辑直传原片。
- **不做「语义检索补空镜」**：当前没有公开素材库检索能力（属 P2-10 待办，未实现）。
- **不做跨任务资产复用**：分镜表/逆推描述随单次任务落库，不跨原片复用（属 P1-6 未做部分）。
- **默认不自动重跑**：逐镜头质检低分**只标记**，不自动重跑（见 §7）。

## 7. 付费行为（硬性约束）

- **绝不静默触发额外费用**：所有增强链路（逆推、质检）只在「已付费成片已经产出的前提下」做增强，且失败不重跑。
- **质检 = 只标记**：`shot_qc` 只把低分镜头与「差在哪」写进 `metadata`，由前端展示；是否重新生成由**用户决定**。
- **自动重跑默认关闭**：`config.VIDEO_QC_AUTO_RETRY = False`。开启后仅对「从第一个低分镜头起的后缀片段」重跑一次（有界），仍低分则放弃。因重跑会产生额外模型费用，属须显式开启的行为变更，**不得默认开启**。
- **断点续跑**：`checkpoint` 机制保证重跑不重复付费（已生成段不重算）。

## 8. 增强链路（内部，对消费方透明）

| 阶段 | 模块 | 失败策略 |
|---|---|---|
| 参考视频解析 | `core/shots.py`（ffmpeg `scene` 滤镜 + ASR 台词归集） | 失败 → 空分镜表，多段仍按秒切分 |
| 逐镜头逆推 | `_build_shot_prompts`（多模态 + 网关故障转移 + 资产缓存） | 失败 → 沿用原有逐段提示词 |
| 多段生成 | `_generate_multi_segment`（按镜头切分 + 尾帧续接） | 单段失败 → 整任务失败 |
| 逐镜头质检 | `_review_shots_with_vision`（原片 vs 成片同位置比对） | 失败 → 无质检结果 |
| 决策日志 | `_attach_decision_log` / `_with_failover` | 仅记录成功提交 |

## 9. 关联文档

- 原子能力：`video-generation.md`、`prompt-assets.md`、`script-anchor.md`
- 竞品对标与能力融路线图：`docs/视频复刻-外部项目对标与能力融入方案.md`
- 网关配置：`docs/ai-gateway-guide.md`

## 10. 复刻资产消费地图(backend/skills/prompts/replicate/,worker 引用复用)

单一来源在 backend,worker 经 `skills/prompts` 加载器引用(不复制、避免两份漂移)。
下表说明每个资产**由谁消费、何时生效** —— 避免"文件在、却没人用"的假象。

| 资产 | 消费方 | 触发条件 |
|---|---|---|
| reference_understanding / transformation_lenses / generated_dependencies / video_direction | 逐镜头逆推 `build_shot_reverse_prompt` | 复刻逆推(拆解 + 出片两条链路) |
| transformation_lenses | 逐镜头质检 `build_shot_qc_prompt` | 成片质检 |
| voice_direction / captions | 复刻脚本兜底 `build_asset_script_prompt` | 有参考视频**且**完全没有任何文案 |
| image_direction | 图片提示词改写 `_apply_image_direction` | 图片任务带 `intent`(复刻换商品/人物/场景) |
| formats/* | 逆推按形态重塑 + backend `[复刻目标形态]` | 指定形态时 |
| broll | **未接入** | 项目无 B-roll/空镜能力,资产仅备查 |

两条容易踩错的边界(踩了就是事故,不是效果差):

- voice_direction / captions 属于**脚本生成**环节 —— 不能塞给 TTS(会被念出来),
  也不能接到烧字幕(那是纯文本烧录,没有 LLM 环节);
- image_direction 是给"写提示词的模型"的元指引 —— 不能直接拼进图片模型 prompt,
  否则干扰出图、甚至产生文字伪影,故走一次 chat 改写而非拼接。
