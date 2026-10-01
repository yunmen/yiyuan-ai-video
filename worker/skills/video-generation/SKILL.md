---
name: video-generation
description: 视频生成能力（worker 的 VideoGenTool，能力路由 video）。当需要在 worker 中新增/修改视频生成、理解 t2v/i2v/r2v/edit 链路、时长档位、分辨率降档、prompt 改写、脚本锚点、字幕合成或断点续跑逻辑时使用。
---

# 视频生成（video-generation）

> 本技能随 worker 提交到仓库、参与部署。

## 能力简介
文生视频 / 图生视频 / 参考生视频 / 视频编辑，提交外部网关并轮询到终态，结果转存 OSS，支持断点续跑与网关故障转移。是当前最复杂的原子能力，串联 `prompt_template`、`script_anchor`、`subtitle`、`compose`、`multiseg`、`media_prep`。

- 入口类：`worker/app/tools/video_tool.py` → `VideoGenTool(name="video", capability="video")`
- 能力路由：`video`
- 网关解析：`gateway.resolve("video")`

## 生成模式（按素材数量自动选择，可被 `gen_mode` 覆盖）
| 条件 | 模式 | 说明 |
| --- | --- | --- |
| 无素材 | `t2v` | 文生视频 |
| 1 张素材 | `i2v` | 首帧图生视频，画幅由首帧决定 |
| 多张素材 | `r2v` | 参考图生视频 |
| 传入 `reference_video`/`original_video` | `edit` | 视频编辑；失败时降级抽参考帧走 `r2v` 保留场景 |

## 关键参数（params）
| 参数 | 必填 | 说明 |
| --- | --- | --- |
| prompt / prompt_context | 是(二选一) | 提示词；`prompt_context` 优先 |
| materials | 否 | 素材地址列表，决定 t2v/i2v/r2v |
| duration | 否 | 档位 `5`/`10`（`SUPPORTED_DURATIONS`），自动 clamp；连续区间由 `gen.video_durations` 放开 |
| ratio | 否 | 取 `config.VIDEO_RATIO`；i2v 由首帧决定、提示词不指定 |
| resolution | 否 | `1080p`/`720p`/`480p` 降档阶梯；按模型上限压档（`seedance-2` 仅 720p） |
| gen_mode | 否 | 强制 `t2v`/`i2v`/`r2v`/`edit` |
| script | 否 | 词锚点结构（`script_anchor.build_segments` 消费） |
| reference_video / original_video / intent | 否 | 视频编辑相关 |

## 生成流水线
1. **prompt 改写**：`build_prompt_optimize_system(ratio, resolution)` 注入画幅/清晰度 → Chat 改写（超时 90s，失败静默回退原始 prompt）。
2. **提交**：`_submit_and_poll(...)` 按模式组装 payload → `/videos` 提交，写 `checkpoint`（含 `external_task_id`、模式）。
3. **轮询**：轮询到终态；提交阶段才切换网关，提交成功后复用同一网关。
4. **转存**：结果 `persist_url_list` 转存 OSS。
5. **断点续跑**：`checkpoint.stage` 标记进度，重启/重试从断点继续。

## 返回（ToolResult）
- `content`：视频 URL 或逗号拼接的多段 URL
- `metadata`：`success`、`mode`、`model`、`resolution`、`ratio`、`duration`、`degrade_note`（若有降级）

## 故障转移与降级
- `_with_failover("video", call)`；分辨率不支持时报错会被识别并降档重试（`_is_resolution_error`）。
- 视频编辑失败自动降级 `r2v`（抽参考帧保留场景），不会退化为纯文生。

## 扩展方式
- 新增模型：`VIDEO_MODEL_T2V` / `VIDEO_MODEL_I2V` / `VIDEO_MODEL_R2V`。
- 放开时长：`gen.video_durations`（离散 `5,10` 或连续 `4-15`）。
- 分辨率上限：后台 `gen.video_resolution_cap`（如 `seedance-2:720p`）。
- 新增画幅/清晰度文案：改 `prompt_template.RATIO_LABELS` / `RESOLUTION_LABELS`。

## 运行时提示词资产（assets/）
本能力的提示词散文集中在 `assets/` 子目录，由 `worker/skills/prompts/__init__.py` 的加载器扫描渲染：
- `video_generation.md`：口播/旁白 → 英文视频生成 prompt（`build_video_generation_prompt`，`video_tool.py:1919`）
- `video_optimize.md`：prompt 改写系统提示（注入画幅/清晰度，`prompt_template.build_prompt_optimize_system`）
- `video_optimize_edit.md`：视频编辑/v2v 改写基调（`build_prompt_optimize_system(edit=True)`）
- `asset_script_generation.md`：基于素材生成视频脚本（`build_asset_script_prompt`，`video_tool.py:1440`）

## 关联
- 提示词模板：`worker/app/tools/prompt_template.py`
- 词锚点：`worker/app/tools/script_anchor.py`
- 基类/故障转移：`worker/app/tools/base.py`
- 编排：`worker/app/services/video_service.py`；任务入口 `process_video`
