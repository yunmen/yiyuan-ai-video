---
name: audio-synthesis
description: 音频生成能力（worker 的 AudioGenTool，能力路由 audio / music）。当需要在 worker 中新增/修改语音合成(TTS)、背景音乐(bgm)、理解 audio 与 music 双网关路由、TTS 资产缓存或音频格式时使用。
---

# 音频合成（audio-synthesis）

> 本技能随 worker 提交到仓库、参与部署。

## 能力简介
语音合成（TTS）与背景音乐（bgm），结果统一转存自有 OSS。是数字人口播的下游依赖。

- 入口类：`worker/app/tools/audio_tool.py` → `AudioGenTool(name="audio", description="音频生成(语音合成/背景音乐)")`
- 能力路由：`audio`（语音）、`music`（背景音乐，可指向不同网关）
- 网关解析：`gateway.resolve("audio")` / `gateway.resolve("music")`

## 模式路由（按 `audio_type`）
| audio_type | 方法 | 接口 | 能力路由 |
| --- | --- | --- | --- |
| `bgm`/`music`/`song` | `generate_music` | `POST /audio/music/generations` | `music`（`prefer_current=False`，允许不同网关） |
| 其它（默认 `tts`） | `text_to_speech` | Speech API | `audio` |

## 语音合成（text_to_speech）
| 参数 | 必填 | 说明 |
| --- | --- | --- |
| text | 是 | 合成文本；为空返回 `invalid_request` |
| model | 否 | 取 `config.AUDIO_MODEL` |
| voice | 否 | 取 `config.AUDIO_VOICE` |
| response_format | 否 | `mp3`/`wav`/`opus`/`aac`/`flac`/`pcm`，取 `config.AUDIO_FORMAT` |

- **资产缓存**：`文案 + 音色 + 模型 + 格式` 完全相同 → 复用已合成 OSS 直链，零付费调用（`app/core/asset_cache`）。
- 响应兼容两种形态：URL 结果（转存）或二进制音频（直接上传 OSS，`_to_url`）。

## 背景音乐（generate_music）
| 参数 | 必填 | 说明 |
| --- | --- | --- |
| prompt / lyrics | 至少一 | 描述或歌词 |
| is_instrumental | 否 | 是否纯音乐；纯音乐时 `gender` 置空 |
| gender | 否 | `female`/`male` |
| model | 否 | 取 `config.MUSIC_MODEL` |

## 返回（ToolResult）
- `content`：音频 URL
- `metadata`：`success`、`mode`(`tts`/`bgm`)、`model`、`voice`、`chars`、`cache`(`hit`/`miss`)

## 扩展方式
- 新增 TTS/音乐模型：配置 `AUDIO_MODEL`/`AUDIO_VOICE`/`MUSIC_MODEL` 与路由 `gen.route.audio`/`gen.route.music`，**无需改代码**。
- 新增输出格式：扩展 `_EXT_MAP`。

## 关联
- 资产缓存：`worker/app/core/asset_cache.py`（`ASSET_TTS_AUDIO`）
- OSS：`worker/app/utils/oss.py`（`persist_url_list`/`upload_bytes`）
- 编排：`worker/app/services/audio_service.py`；任务入口 `process_audio`
- 被数字人依赖：`worker/app/tools/digital_tool.py`
