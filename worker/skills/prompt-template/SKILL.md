---
name: prompt-template
description: 提示词模板能力（worker 的 prompt_template.py，纯函数无网关）。当需要理解视频 prompt 改写系统提示如何注入画幅/清晰度、为何不硬编码「竖版 9:16」、或新增画幅/清晰度文案档位时使用。
---

# 提示词模板（prompt-template）

> 本技能随 worker 提交到仓库、参与部署。

## 能力简介
纯函数模块，把**画幅 / 清晰度**等生成参数注入提示词模板，杜绝硬编码（此前系统提示写死「竖版 9:16」，与可配置的 `gen.video_ratio` 互相矛盾）。由视频工具在 prompt 改写阶段调用。

- 入口：`worker/app/tools/prompt_template.py`
- 特点：**无网关、无 ToolResult**，仅渲染字符串，可独立单测。

## 关键导出
| 符号 | 说明 |
| --- | --- |
| `PROMPT_OPTIMIZE_SYSTEM_TEMPLATE` | prompt 改写系统提示模板，含 `{ratio}`/`{resolution}` 占位 |
| `build_prompt_optimize_system(ratio, resolution)` | 渲染系统提示；`ratio=None` 表示画幅由首帧决定（i2v），提示词不指定画幅 |
| `ratio_label(ratio)` | 画幅文案；未知画幅原样描述不谎报 |
| `resolution_label(resolution)` | 清晰度文案；未知档位原样输出 |
| `RATIO_LABELS` / `RESOLUTION_LABELS` | 文案映射表，键需与 backend `gen_rules.SUPPORTED_RATIOS` 对齐 |

## 设计约束
- 改写系统提示明确：**台词必须逐字照用**、**补充要求(替换/保持原样)整条保留**、素材图只说明「替换成什么样」不得编造场景。
- i2v 由首帧决定画幅，模板传 `None` 避免与模型行为矛盾。

## 扩展方式
- 新增画幅/清晰度档位：同步扩展 `RATIO_LABELS`/`RESOLUTION_LABELS` 与 backend `gen_rules.SUPPORTED_RATIOS`，并校验两端一致。

## 关联
- 提示词散文（各能力 MD 资产）收归对应 skill 的 `assets/` 子目录（如 `video-generation/assets/video_optimize.md`），由 `worker/skills/prompts/__init__.py` 的 `reload()` 一并扫描加载；新增/微调提示词改对应 `assets/` 下 MD 即可，免发版
- 调用方：`worker/app/tools/video_tool.py`（prompt 改写阶段）
- 契约对齐：backend `app/services/gen_rules.py`
