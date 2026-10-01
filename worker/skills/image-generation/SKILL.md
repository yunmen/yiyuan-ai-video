---
name: image-generation
description: 图像生成能力（worker 的 ImageGenTool，能力路由 image）。当需要在 worker 中新增/修改图片生成、理解文生图/图生图分支、image 网关路由、方舟原生协议或 OSS 转存逻辑时使用。
---

# 图像生成（image-generation）

> 本技能随 worker 提交到仓库、参与部署。

## 能力简介
文生图 / 图生图（图片编辑），结果统一转存自有 OSS。

- 入口类：`worker/app/tools/image_tool.py` → `ImageGenTool(name="image", description="图像生成(文生图/图生图)")`
- 能力路由：`image`（未配置时回退媒体/文本网关）
- 网关解析：`gateway.resolve("image")`

## 生成模式（按入参自动分流）
| 条件 | 方法 | 接口 |
| --- | --- | --- |
| 有 `input_image` 或 `materials` | `image_to_image` | OpenAI 兼容 `/images/edits` |
| 无参考图 | `text_to_image` | `/images/generations`（或方舟原生同端点） |

- 方舟原生（`proto=ark`）：走 httpx 直连 `/images/generations`，图生图用 `image` 字段传参考图。
- 中转站：文生图走 SDK `images.generate`；图生图走 `client.post("/images/edits")`。

## 关键参数（params）
| 参数 | 必填 | 说明 |
| --- | --- | --- |
| prompt | 是 | 提示词；为空返回 `invalid_request` |
| input_image / materials | 图生图必填其一 | 参考图地址（取 `materials[0]`） |
| ratio | 否 | `1:1`/`16:9`/`9:16`/`4:3`/`3:4`，映射尺寸见 `RATIO_SIZE` |
| num_images | 否 | 1–4，缺省 1 |
| negative_prompt | 否 | 反向提示词（图生图） |
| model | 否 | 文生图取 `IMAGE_MODEL`；图生图取 `IMAGE_MODEL_EDIT` 或 `IMAGE_MODEL` |

## 返回（ToolResult）
- `content`：逗号拼接的图片 URL 字符串（已转存 OSS；失败则保留原始直链）
- `metadata`：`success`、`mode`(`text2img`/`img2img`)、`model`、`num_images`、`ratio`

## 故障转移
`_with_failover("image", call)`；图生图失败返回 `invalid_request` 或 `request_error`。

## 扩展方式
- 新增/切换模型：配置 `IMAGE_MODEL` / `IMAGE_MODEL_EDIT` 与 `gen.route.image`，**无需改代码**。
- 新增画幅：同步扩展 `RATIO_SIZE` 与 backend `gen_rules.SUPPORTED_RATIOS`。

## 运行时提示词资产（assets/）
本能力的提示词散文集中在 `assets/` 子目录，由 `worker/skills/prompts/__init__.py` 的加载器扫描渲染：
- `image_generation.md`：由口播/旁白生成英文图片生成 prompt（`prompt_library.build_image_generation_prompt`）
- `style_conversion.md`：风格描述转英文图片 prompt（`build_style_conversion_prompt`）

> 注：这两项当前为预留原子能力，生产链路暂由 backend `prompt_builder` 承担，资产保留在此以备复用。

## 关联
- 基类：`worker/app/tools/base.py`
- OSS 转存：`worker/app/utils/oss.py`（`persist_url_list`）
- 编排：`worker/app/services/image_service.py`；任务入口 `process_image`
