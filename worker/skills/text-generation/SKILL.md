---
name: text-generation
description: 文本生成能力（worker 的 TextGenTool，能力路由 text）。当需要在 worker 中新增/修改文本生成、理解 text 网关路由或 Chat Completions 调用约定时使用；是文案/标题/改写等上层能力的底层基座。
---

# 文本生成（text-generation）

> 本技能随 worker 提交到仓库、参与部署。

## 能力简介
通过 OpenAI 兼容的 Chat Completions API 生成文本。所有「写文案、起标题、改写提示词」等上层能力最终都落在这一个工具上。

- 入口类：`worker/app/tools/text_tool.py` → `TextGenTool(name="text", description="文本生成")`
- 能力路由：`text`（未配置时回退主网关 `config.CHAT_LLM_*` / 媒体网关）
- 网关解析：`gateway.resolve("text")`

## 统一接口
所有生成工具继承 `BaseGenTool`，对外只暴露：

```python
async def generate(params: dict, checkpoint: dict | None = None, on_stage = None) -> ToolResult
```

失败时**不抛异常**，统一返回 `ToolResult(content=..., metadata={"success": False, "error_type": ...})`，由上层 service 转成 `failed` 回调（与其他工具一致）。

## 关键参数（params）
| 参数 | 必填 | 说明 |
| --- | --- | --- |
| prompt | 是 | 用户提示词；为空返回 `invalid_request` |
| model | 否 | 缺省取 `config.TEXT_MODEL` |

## 返回（ToolResult）
- `content`：生成文本字符串
- `metadata`：`success`、`model`、`input_tokens`、`output_tokens`、`total_tokens`

## 故障转移
`_with_failover("text", call)`：当前网关失败自动切换候选网关（`gen.route.text` → 固定槽位回退链），全部失败返回最后一个异常对应的 `request_error`。

## 扩展方式
- 新增/切换模型：在后端业务配置填写 `gen.route.text` 与 `TEXT_MODEL`，**无需改代码**。
- 若需新的文本形态（如结构化 JSON 输出），在该文件新增方法并在 `text_service` 中编排。

## 运行时提示词资产（assets/）
本能力的提示词散文集中在 `assets/` 子目录，由 `worker/skills/prompts/__init__.py` 的加载器扫描渲染：
- `content_narration.md`：从用户内容提炼短视频口播文案（`prompt_library.build_content_narration_prompt`）
- `topic_narration.md`：从主题发散口播文案（`build_topic_narration_prompt`）
- `title_generation.md`：生成短视频标题（`build_title_generation_prompt`）

> 注：这三项当前为预留原子能力，worker 生产链路暂未接线（文案/标题由 backend `copy_writer` 承担），资产保留在此以备复用。

## 关联
- 基类：`worker/app/tools/base.py`（`BaseGenTool._with_failover`）
- 编排：`worker/app/services/text_service.py`
- 任务入口：`worker/app/workers/generate_worker.py` → `process_text`
- 统一返回结构：`worker/app/schemas/base.py`（`ToolResult` / `Usage`）
