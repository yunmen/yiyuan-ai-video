# 图像生成能力（image-generation）

## 职责

文生图 / 图生图（图片编辑），结果统一转存自有 OSS。

- 入口类：`worker/app/tools/image_tool.py` → `ImageGenTool(name="image", description="图像生成(文生图/图生图)")`
- 能力路由：`image`（未配置时回退媒体/文本网关）
- 网关解析：`gateway.resolve("image")`

## 生成模式（按入参自动分流）

| 条件 | 方法 | 接口 |
| --- | --- | --- |
| 有 `input_image` 或 `materials` | `image_to_image` | OpenAI 兼容 `/images/edits` |
| 无参考图 | `text_to_image` | `/images/generations`（方舟原生同端点） |

- 方舟原生（`proto=ark`）：走 httpx 直连 `/images/generations`，图生图用 `image` 字段传参考图。
- 中转站：文生图走 SDK `images.generate`；图生图走 `client.post("/images/edits")`。

## 调用约定

```python
tool = ImageGenTool()
result = await tool.generate({
    "prompt": "清新风格的咖啡杯产品图",
    "ratio": "1:1",            # 可选
    "num_images": 2,           # 可选 1-4
    # "input_image": "https://...",   # 图生图时提供
    # "negative_prompt": "模糊",       # 图生图反向提示词
})
if result.metadata.get("success"):
    urls = result.content.split(",")   # 逗号拼接的 OSS URL
```

## 参数

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| prompt | 是 | 提示词；为空返回 `invalid_request` |
| input_image / materials | 图生图必填其一 | 参考图地址（取 `materials[0]`） |
| ratio | 否 | `1:1`/`16:9`/`9:16`/`4:3`/`3:4`，映射尺寸见 `RATIO_SIZE` |
| num_images | 否 | 1–4，缺省 1 |
| negative_prompt | 否 | 反向提示词（图生图） |
| model | 否 | 文生图取 `IMAGE_MODEL`；图生图取 `IMAGE_MODEL_EDIT` 或 `IMAGE_MODEL` |

## 返回（ToolResult）

- `content`：逗号拼接的图片 URL 字符串（已转存 OSS；失败保留原始直链）
- `metadata`：`success`、`mode`(`text2img`/`img2img`)、`model`、`num_images`、`ratio`

## 故障转移

`_with_failover("image", call)`；图生图失败返回 `invalid_request` 或 `request_error`。

## 扩展方式

- 新增/切换模型：配置 `IMAGE_MODEL` / `IMAGE_MODEL_EDIT` 与 `gen.route.image`，**无需改代码**。
- 新增画幅：同步扩展 `RATIO_SIZE` 与 backend `gen_rules.SUPPORTED_RATIOS`。

## 关联文件

- 基类：`worker/app/tools/base.py`
- OSS 转存：`worker/app/utils/oss.py`（`persist_url_list`）
- 编排：`worker/app/services/image_service.py`；任务入口 `process_image`
