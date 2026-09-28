# 提示词资产层（prompt-assets）

## 职责

把运行时**真正喂给大模型**的提示词（散文 + 占位变量）从 `.py` 常量搬到 `worker/skills/prompts/*.md`，集中管理、可热更新、非工程师也能改。这是把"粗糙的硬编码提示词"改造为可维护资产层的核心机制，对应 Pixelle-Video 的 `prompts/` 集中管理模式。

- 加载器：`worker/skills/prompts/__init__.py`（`PromptRegistry`：扫描 / 解析 / 渲染 / 缓存 / 热更新）
- 散文资产：`worker/skills/prompts/*.md`
- 构建器（变量装配）：`worker/skills/prompt_library.py`

## 目录结构

```
worker/skills/prompts/
├── __init__.py                  # 加载器:render / reload / get
├── video_optimize.md            # 本地:视频 prompt 改写系统提示(原 prompt_template.PROMPT_OPTIMIZE_SYSTEM_TEMPLATE)
├── video_generation.md          # 改编自 Pixelle-Video:由口播/旁白生成英文视频 prompt
├── image_generation.md          # 改编自 Pixelle-Video:由口播/旁白生成英文图片 prompt
├── title_generation.md          # 改编自 Pixelle-Video:短视频标题生成
├── style_conversion.md          # 改编自 Pixelle-Video:风格描述 → 英文图片 prompt
└── asset_script_generation.md   # 改编自 Pixelle-Video:基于素材生成视频脚本(视频复刻)
```

## 提示词 MD 格式

```markdown
---
name: video_optimize
capability: video
version: 1
description: 视频生成 prompt 改写系统提示
variables: [ratio, resolution]
---
散文正文,用 {ratio} / {resolution} 占位;{{ }} 表示字面花括号(如 JSON 示例),渲染时还原为 { }。
```

## 加载器 API（`worker/skills/prompts/__init__.py`）

| 函数 | 说明 |
| --- | --- |
| `render(name, **vars) -> str` | 校验必填变量后用 `str.format` 注入（仅简单占位，**绝不 eval**） |
| `reload()` | 扫描目录按文件 mtime 增量重载；被 `runtime_config` 周期刷新调用 |
| `get(name)` | 取资产元信息（`PromptAsset`） |

## 设计原则

- 只在 MD 里放「散文 + 占位变量」；变量注入、条件分支、调用编排仍在各 tool / `prompt_library.py`。
- 新增 / 微调提示词：**直接改对应 `.md`**，无需改代码、无需发版，运营 / 产品也能参与。
- 新增一个提示词：在 `worker/skills/prompts/` 新建 `.md`（带 frontmatter），在 `prompt_library.py` 写薄构建器装配变量即可。

## 热更新

`worker/app/core/runtime_config.py` 的 `refresh_once()` 在每次配置刷新时调用 `prompts.reload()`，因此**改 `prompts/*.md` 即生效，无需重启 worker**。

## 改编自 Pixelle-Video 的能力（`worker/skills/prompt_library.py`）

| 构建器 | 资产文件 | 用途 |
| --- | --- | --- |
| `build_video_generation_prompt(narrations)` | `video_generation.md` | 口播/旁白 → 英文视频生成 prompt（输出 `{"video_prompts": [...]}`） |
| `parse_video_prompts(text)` | — | 解析 LLM 输出的英文分镜提示词列表（容错：围栏/多键/空 → None） |
| `build_image_generation_prompt(narrations, min_words, max_words)` | `image_generation.md` | 口播/旁白 → 英文图片生成 prompt（JSON） |
| `build_title_generation_prompt(content, max_length)` | `title_generation.md` | 内容 → 短视频标题（限长，语言与输入一致） |
| `build_style_conversion_prompt(description)` | `style_conversion.md` | 任意语言风格描述 → 英文图片 prompt |
| `build_asset_script_prompt(intent, duration, assets_text, title)` | `asset_script_generation.md` | 素材 + 意图 → 视频脚本（**视频复刻**场景） |
| `apply_image_prefix(prompt, prefix)` | — | 把风格前缀拼到图片 prompt 前 |
| `IMAGE_STYLE_PRESETS` / `DEFAULT_IMAGE_STYLE` | — | 图片风格预设（stick_figure / minimal / concept） |

> 这些能力面向「视频复刻」：由口播/旁白生成英文视频/图片 prompt、标题生成、风格转换、基于素材生成脚本。它们已通过 `worker/tests/test_prompts.py` 测试。
>
> 已接线（默认不影响既有链路）：
> - `image_tool`：传入 `style`（stick_figure / minimal / concept）时把风格预设拼到图片 prompt 前；不传则原样。
> - `video_tool`：多段生成在 `VIDEO_PROMPT_ENGINE="pixelle"` 时，用 `build_video_generation_prompt` + `parse_video_prompts` 重建逐段英文分镜提示词；默认 `native`（沿用中文改写），失败自动回退。

## 测试

`worker/tests/test_prompts.py`：覆盖画幅注入、i2v 首帧、缺变量报错、全部 7 个 Pixelle 构建器渲染、`parse_video_prompts` 解析、`VIDEO_PROMPT_ENGINE` 默认 native。

## 关联

- 调用方：`worker/app/tools/prompt_template.py`（`build_prompt_optimize_system` 委托 `render`）
- 热更新：`worker/app/core/runtime_config.py`
- 设计来源：[Pixelle-Video prompts/](https://github.com/ATH-MaaS/Pixelle-Video)（Apache-2.0）
