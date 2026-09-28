# 数字人口播能力（digital-human）

## 职责

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

## 调用约定

```python
tool = DigitalHumanTool()
result = await tool.generate({
    "avatar": "https://.../avatar.png",     # 必填
    "text": "欢迎光临本店，今天推荐招牌拿铁",  # 口播文案（逐字念出，不改写）
    # "audio": "https://.../tts.mp3",        # 可选，优先于现场合成
    "duration": 10,
    "ratio": "9:16",
    "resolution": "1080p",
    # "voice": "male",                       # 现场合成音色
})
```

## 参数

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

## 关联文件

- 复用：`worker/app/tools/video_tool.py`（`_submit_and_poll`、断点续跑、故障转移）
- 复用：`worker/app/tools/audio_tool.py`（`text_to_speech` + TTS 资产缓存）
- 编排：`worker/app/services/digital_service.py`；任务入口 `process_digital`
