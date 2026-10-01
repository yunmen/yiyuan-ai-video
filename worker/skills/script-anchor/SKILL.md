---
name: script-anchor
description: 词锚点编排能力（worker 的 script_anchor.py，纯函数无网关）。当需要理解脚本/字幕如何按词序号打锚点、时间如何估算、或为何 worker 与 backend 必须同步修改并使用跨端契约测试时使用。
---

# 词锚点编排（script-anchor）

> 本技能随 worker 提交到仓库、参与部署。

## 能力简介
词锚点编排纯函数，把结构化文案切成词序列并派生叙事分段与锚点，供视频生成做脚本/字幕时间对齐。是视频工具的子能力。

- 入口：`worker/app/tools/script_anchor.py`
- 特点：**无网关、无 ToolResult**，纯函数；是 backend `app/services/script_schema.py` 的**镜像实现**。

## 关键约定
- **锚点一律用「词序号」**（`from_word`/`to_word`/`at_word`），绝不用秒；时间由 `estimate_timing` 按词数估算兜底，接真实对齐后替换。
- worker 与 backend 独立部署、不能共享模块，故镜像一份；**两端漂移由 `backend/tests/test_cross_worker_contract.py` 用同一批样例断言输出完全一致兜底**。
- ⚠️ 改任何一端必须同步改另一端，否则一致性测试会失败。

## 关键导出
| 符号 | 说明 |
| --- | --- |
| `split_words(text)` | 分词：中文按单字、连续字母数字按词，标点/空白丢弃 |
| `build_segments(structured)` | 结构化文案 → 叙事分段（title→hook / subtitle→selling / script→script） |
| `_default_anchors(segments)` | 默认锚点：每段一个选区 + 段首瞬时点 |
| `estimate_timing(...)` | 按词数估算时间 |
| `render_anchor_hint(...)` | 渲染锚点提示 |
| `resolve_tracks(...)` | 解析多音轨 |
| `SCRIPT_VERSION` | 脚本结构版本 |

## 扩展方式
- 新增分段字段：同步改 `STRUCTURED_TO_SEGMENT` 与 backend 的 `prompt_builder.structured`。
- 任何改动两端一起改，并跑 `test_cross_worker_contract`。

## 关联
- 调用方：`worker/app/tools/video_tool.py`
- 镜像源：backend `app/services/script_schema.py`
- 契约测试：`backend/tests/test_cross_worker_contract.py`
