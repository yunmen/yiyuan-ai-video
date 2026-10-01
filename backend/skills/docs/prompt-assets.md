# 提示词资产层（backend/skills/prompt-assets）

## 职责

把 backend 运行时**真正喂给大模型**的提示词（散文 + 占位变量）从 `.py` 常量搬到
`backend/skills/prompts/*.md`，集中管理、可热更新、非工程师也能改。这是把"粗糙的硬编码提示词"
改造为可维护资产层的核心机制，对应 Pixelle-Video 的 `prompts/` 集中管理模式。

- 加载器：`backend/skills/prompts/__init__.py`（`PromptAsset`：扫描 / 解析 / 渲染 / 缓存 / 热更新）
- 散文资产：`backend/skills/prompts/`（按功能模板分门别类子目录）
- 调用方：`backend/app/services/skill_prompts.py` 统一加载 → `prompt_builder.py`(backend 组装)；
  `copy_writer` 已迁至 `worker/app/services/ai_copy.py`;其文案资产 `merchant_copy`/`merchant_copy_demand` 也已迁入 `worker/skills/text-generation/assets/`(worker 自有,单一来源,backend 不再持有)

> 与 `worker/skills/prompts` 解耦：backend 运行时不依赖 worker，提示词自有、自维护。

## 标准目录结构

```
backend/skills/
├── __init__.py                  # 技能包入口
├── prompts/                    # 提示词资产层(单一来源)
│   ├── __init__.py             # 加载器:render / reload / get(递归扫描子目录)
│   ├── copy/                   # 已废弃:merchant_copy/merchant_copy_demand 已迁入 worker/skills/text-generation/assets/,backend 不再持有
│   └── generation/             # 视频生成参数(prompt_builder 用)
│       ├── replace/            # 替换原视频元素的指令与护栏
│       │   ├── gen_replace_blanket.md
│       │   ├── gen_replace_product.md
│       │   ├── gen_replace_person.md
│       │   ├── gen_replace_scene.md
│       │   ├── gen_replace_keep_guard.md
│       │   └── gen_replace_category_guard.md
│       ├── context/            # 上下文(模板/商家信息/复刻要求)
│       │   ├── gen_context_template_rule.md
│       │   ├── gen_context_v2v_note.md
│       │   ├── gen_context_merchant_intro.md
│       │   └── gen_reference_requirement.md
│       └── material/           # 各生成模式的素材语义说明
│           ├── gen_material_hint_t2v.md
│           ├── gen_material_hint_i2v.md
│           ├── gen_material_hint_v2v_base.md
│           ├── gen_material_hint_v2v_extra.md
│           └── gen_material_hint_r2v.md
│       └── replicate/           # 视频复刻方法论(改编自 Hypit,单一来源;worker 引用复用,不复制)
│           ├── reference_understanding.md   # name: replicate_reference_understanding
│           ├── transformation_lenses.md     # name: replicate_transformation_lenses
│           ├── generated_dependencies.md    # name: replicate_generated_dependencies
│           ├── video_direction.md           # name: replicate_video_direction
│           ├── image_direction.md           # name: replicate_image_direction
│           ├── voice_direction.md           # name: replicate_voice_direction
│           ├── broll.md                     # name: replicate_broll
│           ├── captions.md                  # name: replicate_captions
│           ├── shot_reverse.md              # 原 worker 专属,已收归权威资产(name: shot_reverse)
│           ├── shot_qc.md                   # 同上(name: shot_qc)
│           ├── creative_faithful.md         # 创意档位·忠实复刻(name: replicate_creative_faithful)
│           ├── creative_rewrite.md          # 创意档位·轻度改写(name: replicate_creative_rewrite)
│           ├── creative_viral.md            # 创意档位·爆款改造(name: replicate_creative_viral)
│           ├── hook_boost.md                # 开头钩子强化(name: replicate_hook_boost)
│           └── formats/                    # 各类复刻目标形态(7 种, name: replicate_format_*)
└── docs/
    ├── prompt-assets.md        # 本文件
    └── replicate/              # 视频复刻技能归档(参考知识 + 原始溯源)
        └── raw/               # 改编来源:hypit skills 的 creation/production/playbooks/agents 原始 MD
```

分类说明：

- `copy/`：~~（已废弃）`merchant_copy`/`merchant_copy_demand` 已迁入 `worker/skills/text-generation/assets/`，不再位于本目录；文案生成由 `worker/app/services/ai_copy.py` 承担。
- `generation/replace/`：视频编辑(v2v)场景下"替换原视频元素"的指令与护栏。
- `generation/context/`：生成上下文里的固定规则（模板只给结构/画幅、视频编辑不写死画幅时长、商家信息逐字照念、纯复刻默认要求）。
- `generation/material/`：各生成模式（t2v/i2v/v2v/r2v）的素材语义说明（部分带 `{count}`/`{ref}`/`{obj}` 占位）。
- `replicate/`：视频复刻方法论资产（改编自 [hypit-ai/hypit](https://github.com/hypit-ai/hypit) 的 skills，原始 MD 见 `docs/replicate/raw/`）。含参考理解、改造透镜、生成依赖、视频/图像/声音方向、B-roll、字幕，原 worker 专属的 `shot_reverse`/`shot_qc`，以及**创意档位**资产（`creative_faithful`/`creative_rewrite`/`creative_viral` + `hook_boost`）。**这是复刻相关提示词的单一来源**，worker 通过引用复用（其 loader 同时扫描本目录），不复制、避免两份漂移。
- **创意档位的定位**：`replicate/` 下的方法论散文（改造透镜等）属于「模型该怎么想」，创意档位资产属于「这次要改到什么程度」——它们按 `/gen-config` 下发的档位 key 组装，前端只拿到 `label`/`desc`，正文永不暴露给用户（用户调的是业务旋钮，不是直接编辑提示词）。

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

- `name`：加载键（`skill_prompts.load_skill_prompt(name)` / `render_skill_prompt(name, ...)` 用此名，不依赖子目录路径）。
- `variables`：必填占位符白名单；`render` 时缺失会抛错（由调用方 `default` 兜底）。
- `capability` / `version` / `description`：仅作文档与元信息，不参与渲染。

## 加载器 API（`backend/skills/prompts/__init__.py`）

| 函数 | 说明 |
| --- | --- |
| `render(name, **vars) -> str` | 校验必填变量后用 `str.format` 注入（仅简单占位，**绝不 eval**） |
| `reload()` | 递归扫描 `prompts/` 目录按文件 mtime 增量重载（支持子目录分类） |
| `get(name)` | 取资产元信息（`PromptAsset`） |

`backend/app/services/skill_prompts.py` 在此之上封装 `load_skill_prompt` / `render_skill_prompt`，
加载失败时回退调用方传入的内联兜底常量（`prompt_builder.py` 的 `DEFAULT_*`），保证生成链路不中断。

## 资产清单与调用点

| 资产文件 | 用途 | 调用点 |
| --- | --- | --- |
| `worker/skills/text-generation/assets/merchant_copy.md` | 三段带货文案系统提示 | `worker/app/services/ai_copy.py:_merchant_copy_system` |
| `worker/skills/text-generation/assets/merchant_copy_demand.md` | 追加 subject/demand 字段要求 | `worker/app/services/ai_copy.py:_merchant_copy_system`(with_demand) |
| `generation/replace/gen_replace_blanket.md` | v2v 无显式意图时的兜底替换要求 | `prompt_builder.build_replace_requirement` 空意图分支 |
| `generation/context/gen_reference_requirement.md` | 纯复刻(未选替换意图)的系统默认要求 | `prompt_builder.build_gen_params` 无 intent 分支 |
| `generation/replace/gen_replace_product.md` / `gen_replace_person.md` / `gen_replace_scene.md` | 替换维度=商品/人物/场景 的指令正文 | `prompt_builder.build_replace_requirement` |
| `generation/replace/gen_replace_keep_guard.md` | 通用护栏：上传图只是替换素材而非首帧 | `prompt_builder.build_replace_requirement` |
| `generation/replace/gen_replace_category_guard.md` | 品类串扰护栏：以用户素材文案为准 | `prompt_builder.build_replace_requirement` |
| `generation/context/gen_context_template_rule.md` | 模板上下文首段规则(模板只给结构/画幅) | `prompt_builder.build_prompt_context` |
| `generation/context/gen_context_v2v_note.md` | 视频编辑不写死画幅/时长的说明 | `prompt_builder.build_prompt_context`(v2v) |
| `generation/context/gen_context_merchant_intro.md` | 商家信息段首「逐字照念」声明 | `prompt_builder.build_prompt_context` |
| `generation/material/gen_material_hint_t2v.md` / `i2v.md` / `v2v_base.md` / `v2v_extra.md` / `r2v.md` | 各生成模式的素材语义说明(i2v/v2v_extra/r2v 带 `{count}`/`{ref}`/`{obj}` 占位) | `prompt_builder.build_material_hint` |
| `replicate/reference_understanding.md` | 参考视频时间码级语义解读方法论(改编自 hypit reference-video) | `prompt_library._append_replicate_methodology`(注入 shot_reverse) |
| `replicate/transformation_lenses.md` | 改造透镜:保留角色/重塑形态、换脸/用我的商品范式(改编自 hypit transformations) | 同上(注入 shot_reverse) |
| `replicate/generated_dependencies.md` | 哪些生成资产依赖哪些参考、浅依赖原则(改编自 hypit generated-dependencies) | 同上(注入 shot_reverse) |
| `replicate/video_direction.md` / `image_direction.md` / `voice_direction.md` | 参考素材驱动表演/动作/镜头、替换外观的选角锚点、角色声音(改编自 hypit craft) | 复刻方法论参考资产(可复用) |
| `replicate/broll.md` / `captions.md` | B-roll 角色与交接、字幕阅读节奏与样式(改编自 hypit craft) | 复刻方法论参考资产(可复用) |
| `replicate/shot_reverse.md` | 逐镜头逆推提示词(原 worker 专属,已收归权威资产) | `prompt_library.build_shot_reverse_prompt` |
| `replicate/shot_qc.md` | 逐镜头质检提示词(原 worker 专属,已收归权威资产) | `prompt_library.build_shot_qc_prompt` |
| `replicate/formats/*.md` | 7 种复刻目标形态:短剧/口播/主讲人讲解/街采/双人播客/榜单/旁白演示(资产名 `replicate_format_<形态key>`) | `prompt_builder._render_replicate_format`(建单注入 `[复刻目标形态]` 到 prompt_context);`prompt_library._append_replicate_format`(worker 拆解逆推注入) |
| `replicate/creative_faithful.md` / `creative_rewrite.md` / `creative_viral.md` | 创意档位:忠实复刻(只描述原片事实)/轻度改写(保结构换措辞)/爆款改造(重排节奏、强化情绪起伏)(资产名 `replicate_creative_<档位key>`) | `prompt_builder.build_creative_requirement`(建单注入 `[创作要求]` 到 prompt_context);`prompt_library.resolve_reverse_assets`(worker 按档位选择逆推方法论子集) |
| `replicate/hook_boost.md` | 开头钩子强化:只重写前 3 秒的画面与首句口播(资产名 `replicate_hook_boost`) | 同上(仅当 `hook_boost=strong` 时注入) |
| `generation/replace/gen_lead_act_dance.md` / `gen_lead_act_pitch.md` | 主角表现=跳舞律动/推广种草 时注入的创意增强指令(仅「换人物」时生效) | `prompt_builder.build_lead_act_requirement` |

## 设计原则

- 只在 MD 里放「散文 + 占位变量」；变量注入、条件分支、调用编排仍在各 service（`prompt_builder.py` / `copy_writer.py`）。
- 新增 / 微调提示词：**直接改对应 `.md`**，无需改代码、无需发版，运营 / 产品也能参与。
- 新增一个提示词：在 `backend/skills/prompts/<分类>/` 新建 `.md`（带 frontmatter），在 `prompt_builder.py` / `copy_writer.py` 通过 `skill_prompts` 读取即可。
- backend 侧为每条提示词保留了「内联兜底常量」（`prompt_builder.py` 中的 `DEFAULT_*`），
  仅在 md 加载失败时回退；**日常维护只改 md，不要改兜底常量**，否则会出现双源漂移。

## 关联

- 调用方：`backend/app/services/skill_prompts.py` 统一加载 → `backend/app/services/prompt_builder.py`（生成参数提示词）、`backend/app/services/copy_writer.py`（文案提示词）
- 复刻流水线(worker)引用复用：`worker/skills/prompts/__init__.py` 的 `reload()` 同时扫描本目录，`prompt_library.resolve_reverse_assets(creative_level)` 决定注入哪一组方法论 ——
  不指定档位时沿用改造前的全量集合（`reference_understanding` + `video_direction` + `transformation_lenses` + `generated_dependencies`），保证老任务重跑结果不变；
  选「忠实复刻」只注入 `reference_understanding` + `video_direction`（不塞改造透镜，避免模型主动重写原片结构、白耗 token）；
  「轻度改写/爆款改造」再追加改造透镜与对应档位资产；`hook_boost=strong` 另加 `hook_boost`（只作用于第一镜，用独立标题与通篇档位区分）。
  **backend 是复刻提示词的单一来源，worker 不另存副本**，避免两份漂移。
- 提示词资产的两处加载器（`backend/skills/prompts/__init__.py` 与 `worker/skills/prompts/__init__.py`）**刻意保留两份同源实现**：backend 与 worker 可独立部署，共享同一文件需要额外的打包/挂载方案；改动 `_parse`/`render`/`reload` 等公共部分时必须同步两侧，各自特有的能力（worker 的 `safe_render`、backend 目录扫描）只留在本侧。
- 设计来源：[Pixelle-Video prompts/](https://github.com/ATH-MaaS/Pixelle-Video)（Apache-2.0）；视频复刻方法论改编自 [hypit-ai/hypit](https://github.com/hypit-ai/hypit) 的 skills（原始 MD 见 `docs/replicate/raw/`）。
