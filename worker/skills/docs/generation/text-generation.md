# 文本生成能力（text-generation）

## 职责

通过 OpenAI 兼容的 Chat Completions API 生成文本，是文案、标题、改写等上层能力的底层基座。

- 入口类：`worker/app/tools/text_tool.py` → `TextGenTool(name="text", description="文本生成")`
- 能力路由：`text`（未配置时回退主网关 `config.CHAT_LLM_*` / 媒体网关）
- 网关解析：`gateway.resolve("text")`

## 调用约定

```python
tool = TextGenTool()                       # 构造时按 gen.route.text 解析网关；无 API_KEY 抛 RuntimeError
result: ToolResult = await tool.generate({
    "prompt": "为一款咖啡写一句探店文案",
    # "model": "xxx"                      # 可选，缺省 config.TEXT_MODEL
})
if result.metadata.get("success"):
    text = result.content                  # 生成文本
```

## 参数

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

## 关联文件

- 基类：`worker/app/tools/base.py`（`BaseGenTool._with_failover`）
- 编排：`worker/app/services/text_service.py`
- 任务入口：`worker/app/workers/generate_worker.py` → `process_text`
- 统一返回结构：`worker/app/schemas/base.py`（`ToolResult` / `Usage`）
