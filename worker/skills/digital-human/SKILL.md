---
name: digital-human
description: 数字人口播能力（worker 的 DigitalHumanTool，能力路由 digital）。当需要在 worker 中新增/修改数字人、理解「形象图+口播音频→口型驱动视频」、数字人网关路由、为何不改写口播文案，或想把数字人做成 talking-head 口播/声纹复用/可表演多段脚本/字幕跟随头部/画中画讲解时使用。
---

# 数字人口播（digital-human）

> 本技能随 worker 提交到仓库、参与部署（`.codebuddy/skills` 为本地开发副本、不进仓库）。

## 能力简介
数字人形象图 + 口播音频 → 口型驱动视频。复用视频工具的「提交 + 轮询 + OSS 转存 + 断点续跑 + 网关故障转移」机制，差异仅在请求体与模型。

- 入口类：`worker/app/tools/digital_tool.py` → `DigitalHumanTool(name="digital", capability="digital")` 继承自 `VideoGenTool`
- 能力路由：`digital`（独立配置 `gen.route.digital`，未配置回退媒体/文本网关）
- 网关解析：`gateway.resolve("digital")`

## 主流程（`generate`）
1. **校验**：`model` 取 `config.DIGITAL_MODEL`（未配置明确失败）；`avatar` 形象图必填。
2. **准备口播音频**（阶段 1，可复用）：
   - 优先复用 `checkpoint.audio`；
   - 其次用调用方传入的 `audio`；
   - 最后用 `text`/`prompt` 经 `AudioGenTool().text_to_speech(...)` 现场合成（传 `_notify_url` 以命中 TTS 资产缓存）。
3. **提交数字人模型**：payload 携带 `image`(形象)、`audio`(口播)、`seconds`、`metadata.parameters`(resolution/ratio/duration)，`reference_image` 仅在派生姿势 != 主图时放入 `parameters`。
4. **轮询成片**：复用 `_submit_and_poll`，`mode="digital"`。

> ⚠️ **不改写口播文案**：口播需逐字念出，故 `prompt` 直接作为台词下发，不做 prompt 改写（与视频生成相反）。

## 关键参数（params）
| 参数 | 必填 | 说明 |
| --- | --- | --- |
| avatar | 是 | 数字人形象图地址 |
| text / prompt | 二选一(或传 audio) | 口播文案（逐字念出，不改写） |
| audio | 否 | 现成口播音频地址，优先于现场合成 |
| model | 否 | 取 `config.DIGITAL_MODEL`，未配置明确失败 |
| voice | 否 | 现场合成音色 |
| ratio / resolution / duration | 否 | 同视频工具 |
| reference_image / pose | 否 | 派生姿势参考图 |

## 返回（ToolResult）
- `content`：成片视频 URL
- `metadata`：`success`、`mode="digital"`、`digital_audio`(口播音频地址)

## 扩展方式
- 配置 `gen.digital_model`（模型名）与 `gen.route.digital`（OpenAI 兼容网关）。
- 不支持方舟原生协议时可把 `gen.route.digital` 指向 OpenAI 兼容网关。

## 导演方法论（按需加载）

数字人口播不只是「形象 + 音频 → 视频」的原子调用，更是一个**对镜头说话的表演（talking-head /
presenter-led A-roll）**。把它做成产品级能力时，遵循以下方法论（详细内容在 `references/`，仅一层深）：

- `references/talking-head.md`：**对镜头说话表演**——一张人物+场景图（正面、对镜头、留手势空间）+
  一个可复用声纹 + 口播脚本，由说话视频模型产出「真的在表演」的画面与口型同步；支持自然切镜。
- `references/voice-casting.md`：**选角与声纹**——Voice Design 生成可复用声纹样本（~5s），同一角色跨
  镜头/跨任务复用同一声音；明确「表演角色」与「画面呈现」解耦（画外音/被覆盖时声音仍属同一人）。
- `references/script-and-time.md`：**口播脚本语义时间**——用 Segment 组织可表演段落，发音用 Dual Text
  分离「显示字/读音」（如 `<API | A P I>`），用 Caption Cue（`||`）切分字幕，先用 `script_anchor`
  / `hypit measure` 思路测算每段时长再请求生成。
- `references/presenter-led-explainer.md`：**主讲人讲解**——数字人可全屏、可缩成小窗、可被 MG/演示
  覆盖，表演角色（声音与时间）保持不变；适合「边讲边演示」的产品/功能讲解形态。

> 当前实现：`DigitalHumanTool` 已是单段「avatar + text/audio → 视频」。声纹复用、多段脚本、字幕跟随头部、
> 画中画分别由上方 `references/` 中的 `voice-casting.md`、`script-and-time.md`、`talking-head.md`、
> `presenter-led-explainer.md` 给出具体落地方式（含涉及的 worker 模块与函数）。

## 关联
- 复用：`worker/app/tools/video_tool.py`（`_submit_and_poll`、断点续跑、故障转移）
- 复用：`worker/app/tools/audio_tool.py`（`text_to_speech` + TTS 资产缓存）
- 编排：`worker/app/services/digital_service.py`；任务入口 `process_digital`
