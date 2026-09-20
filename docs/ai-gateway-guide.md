# AI 网关（中转站）接入与配置手册

> 适用范围：文本 / 图片 / 视频 / 语音 / 音乐全部能力走 OpenAI 兼容中转站的部署方式。
>
> 相关代码：`worker/app/core/gateway.py`、`worker/app/tools/*`、`worker/app/core/runtime_config.py`、`backend/app/services/system_config.py`
>
> 相关工具：`worker/scripts/probe_gateway.py`（网关能力探测）

---

## 1. 方案概述

### 1.1 能力划分

系统把 AI 能力抽象成 6 类，每类可以独立指定「走哪个网关、用哪个模型」：

| 能力 (`capability`) | 用途 | 执行方 |
|---|---|---|
| `chat` | 视频 prompt 改写、文案润色 | worker + backend |
| `text` | 文本生成 | worker |
| `image` | 文生图 / 图生图 | worker |
| `video` | 文生 / 图生 / 参考生视频 | worker |
| `audio` | 语音合成（TTS） | worker |
| `music` | 背景音乐 | worker |

### 1.2 网关抽象

一个「网关」= `base_url` + `api_key` + `proto`（协议）。

- `proto = openai`：走 OpenAI 兼容接口（中转站、阿里百炼等），视频提交 `/videos`、图片 `/images/generations`、音频 `/audio/*`
- `proto = ark`：走火山方舟原生接口，视频提交 `/contents/generations/tasks`

未显式配置 `proto` 时按地址自动嗅探：URL 含 `volces.com` → `ark`，否则 `openai`。

### 1.3 为什么可以全压一个中转站

各类能力最终都收敛到「一个地址 + 一组模型名」，不需要为每家官方单独对接：

- 所有能力共用同一套 OpenAI 兼容调用路径
- 模型名是配置项，换模型不需要改代码
- 网关地址是配置项，换中转站不需要改代码
- 能力路由（`gen.route.*`）在「全压单网关」场景下完全不需要使用

### 1.4 默认链路（未做任何配置时）

| 配置层 | 默认值 |
|---|---|
| 数据库 `gen.llm_base_url` / `gen.worker_llm_base_url` | 空 |
| worker 环境变量 `CHAT_LLM_BASE_URL` / `LLM_BASE_API_URL` | `https://ydtoken.capitalai.cn/v1` |

即：**数据库为空时回退到 worker 的环境变量默认值**。配置优先级始终是「数据库 → 环境变量」。

---

## 2. 快速开始

### 步骤一：探测网关能力（零成本，务必先做）

```bash
python worker/scripts/probe_gateway.py \
  --base-url https://aitoken.capitalai.cn/v1 \
  --api-key sk-xxx \
  --models
```

输出三部分：

1. **端点探测结果** —— 各能力端点是否被该中转站实现（重点看 `video_submit` / `music`）
2. **模型清单** —— `GET /models` 返回的全部模型名
3. **可回填配置** —— 按能力分组推荐模型名，并直接给出 `KEY = VALUE` 清单

### 步骤二：在管理端填配置

路径：管理端左侧菜单 **业务配置**（页面按「配置键」搜索，逐条编辑 VALUE）
（组件：`admin/src/views/system/config/index.vue`；菜单由后端 `tb_system_menu` 驱动）

对应接口：`POST /admin/v1/system/config/list` / `/upsert`
所需权限点：`system:config:list` / `system:config:update`

> 注意区分同名页面：若打开的「业务配置」显示 `SCUI` / `@SCUI`，说明菜单指向了 SCUI 框架演示页，见 5.3。

最少只需填 2 个网关项 + 若干模型项，详见第 3 节。

### 步骤三：生效与验证

- **worker 侧**（所有生成能力）：默认 **60 秒**轮询热更新（`CONFIG_REFRESH_INTERVAL`，最小 15 秒），改完等一分钟，或重启 worker 立即生效
- **backend 侧**（文案润色）：每次调用读库，**立即生效**

验证顺序建议：文生视频（最关键、最贵）→ 文生图 → 图生图 → 语音 → 背景音乐。

---

## 3. 配置项清单

### 3.1 网关配置

| KEY | 是否必填 | 说明 |
|---|---|---|
| `gen.llm_base_url` | **是** | 主网关地址，如 `https://aitoken.capitalai.cn/v1` |
| `gen.llm_api_key` | **是** | 主网关密钥 |
| `gen.worker_llm_base_url` | 否 | 视频专用网关。**留空则回退主网关** |
| `gen.worker_llm_api_key` | 否 | 视频专用网关密钥 |
| `gen.audio_llm_base_url` | 否 | 音频专用网关。留空则回退媒体网关 |
| `gen.audio_llm_api_key` | 否 | 音频专用网关密钥 |

密钥为敏感配置（`is_public = false`），不会下发给普通用户端。

### 3.2 模型配置

| KEY | 能力 | 代码默认值 |
|---|---|---|
| `gen.chat_model` | prompt 改写 / 文案润色 | `qwen3.7-max` |
| `gen.text_model` | 文本生成 | `qwen3.7-max` |
| `gen.image_model` | 文生图 | `qwen-image-2.0` |
| `gen.image_model_edit` | 图生图 / 图片编辑 | 空（**留空则复用 `gen.image_model`**） |
| `gen.video_model_t2v` | 文生视频 | `happyhorse-1.1-t2v` |
| `gen.video_model_i2v` | 图生视频 | `happyhorse-1.1-i2v` |
| `gen.video_model_r2v` | 参考生视频 | `happyhorse-1.1-r2v` |
| `gen.audio_model` | 语音合成 TTS | `qwen-audio-3.0-tts-plus` |
| `gen.music_model` | 背景音乐 | `fun-music-v1` |

> 以上默认值来自 `backend/app/services/system_config.py` 的 `DEFAULT_CONFIGS`（首次启动播种值）。
> 它们是项目当前线上在用的模型，换网关时需要按新网关 `/models` 的实际返回逐个核对。

**生成模式与模型的对应关系**（`worker/app/tools/video_tool.py`）：

| 输入 | 走哪种模式 | 使用的模型配置 |
|---|---|---|
| 无素材 | `text_to_video` | `gen.video_model_t2v` |
| 1 张图 | `image_to_video` | `gen.video_model_i2v` |
| 多张图 | `reference_to_video` | `gen.video_model_r2v` |

### 3.3 非模型参数（保持默认即可）

| KEY | 默认值 | 说明 |
|---|---|---|
| `gen.image_ratio` | `1:1` | 图片默认画幅 |
| `gen.video_ratio` | `9:16` | 视频画幅 |
| `gen.video_resolution` | `1080P` | 视频清晰度 |

### 3.4 全压单网关场景下建议留空的配置

| KEY 前缀 | 项数 | 留空原因 |
|---|---|---|
| `gen.gw.*` | 12 | 命名网关注册表，仅在多供应商混用时需要 |
| `gen.route.*` | 6 | 能力路由，未配置时自动回退固定槽位 |

---

## 4. 故障转移

### 4.1 候选列表如何生成

`gateway.resolve_all(capability)` 返回有序候选列表：

1. 先取 `gen.route.<capability>` 指向的命名网关（若命中且 url/key 齐全）
2. 再按固定槽位回退链补齐（`worker/app/core/gateway.py` 的 `_FALLBACK`）

各能力的回退链（按优先级）：

| 能力 | 回退链 |
|---|---|
| `chat` / `text` | `CHAT_LLM_*`(`gen.llm_*`) → `LLM_BASE_*`(`gen.worker_llm_*`) |
| `image` / `video` | `LLM_BASE_*`(`gen.worker_llm_*`) → `CHAT_LLM_*`(`gen.llm_*`) |
| `audio` / `music` | `AUDIO_LLM_*`(`gen.audio_llm_*`) → `LLM_BASE_*` → `CHAT_LLM_*` |

**去重规则：按地址（url）去重，只保留第一个命中的槽位。**
故障转移的意义是换一个地址重试，同一地址重复出现没有意义。

### 4.2 双向回退（一处配置全局生效）

`worker/app/core/runtime_config.py` 中有双向兜底：

- `gen.worker_llm_base_url` 留空 → `LLM_BASE_API_URL` 回退为 `CHAT_LLM_BASE_URL`
- `gen.llm_base_url` 留空 → `CHAT_LLM_BASE_URL` 回退为 `LLM_BASE_API_URL`

因此：

- **只配一个地址** → 两槽位被拉平为同值 → 去重后只有 1 个候选（无故障转移，行为与旧版一致）
- **配两个不同地址** → 保留 2 个候选（自动获得故障转移，无需额外开关）

### 4.3 切换时机

故障转移**只在「发起请求」阶段生效**：

| 能力 | 切换行为 |
|---|---|
| `chat` / `text` / `image` / `audio` / `music` | 请求抛异常即切下一个候选重试 |
| `video` | **仅提交阶段**切换；提交成功后不再切换，轮询复用「提交成功的那个网关」 |

视频不在轮询阶段切换的原因：任务 ID 只存在于提交它的那个网关上，换网关查不到任务。

此外，`video_tool` 的 prompt 改写走 `chat` 能力网关，其失败**不会改动视频网关状态**，避免把后续轮询带偏。

### 4.4 构造函数显式指定 `base_url` 的场景

`__init__` 时显式传入 `base_url` 的工具实例会被标记为 `_pinned`，**不参与故障转移**。用于测试和直连排查，避免意外打到别的网关。

### 4.5 如何开启

1. 配置两个**地址不同**的网关，例如：
   - `gen.llm_base_url` = `https://aitoken.capitalai.cn/v1`
   - `gen.worker_llm_base_url` = `https://ydtoken.capitalai.cn/v1`（备用）
2. 无需其他开关，候选列表自动包含两者

### 4.6 日志关键字

| 日志片段 | 含义 |
|---|---|
| `[网关故障转移]` / `经网关 [...] 失败,切换备选 [...]` | 触发切换 |
| `[...] 经 [fallback:LLM_BASE_API_URL] 失败` | 具体失败的是哪个槽位 |
| `任务已提交: external_task_id=..., 网关=...` | 视频最终提交成功的网关 |

---

## 5. 配置生效与排查

### 5.1 生效机制

| 侧 | 机制 | 延迟 |
|---|---|---|
| worker | `runtime_config` 周期拉取 `POST /api/user/v1/base/common/worker-config`（需 `X-Worker-Token`） | `CONFIG_REFRESH_INTERVAL`，默认 60s |
| backend | `copy_writer` 每次调用读库 | 立即 |

worker 拉取失败时保持现状，不影响生成主流程。

### 5.2 常见问题排查

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 改了配置但模型没变 | KEY 名写成了下划线风格（`gen_llm_base_url`），worker 匹配不上，**静默回退 env 默认值** | 执行 `python backend/scripts/check_system_config_keys.py` 校验键名 |
| 模型名报 404 / not found | 模型不存在于该网关 | 用探测脚本 `--models` 核对清单 |
| 视频一直失败，其他正常 | 网关未实现 `/videos` 端点 | 探测脚本看 `video_submit` 判定；未支持则把视频单独指向别的网关 |
| 密钥保存后被覆盖成 `******` | 管理端列表对敏感项打码，回填占位符有保护逻辑 | 只要提交值仍是 `******` 就会保留库中原值；首次配置必须填真实值 |
| 改完没生效 | 未等热更新周期 | 等 60s 或重启 worker |
| 全部能力同时失败 | 单网关单点故障 | 配置第二个网关地址以启用故障转移 |
| 「业务配置」页显示 `SCUI` / `@SCUI`，且只有「系统设置 / 短信配置 / 扩展配置」三个标签 | 菜单的组件路径指向了 SCUI 框架演示页，数据是前端硬编码的 | 见 5.3 |

### 5.3 业务配置页显示的是演示数据（找不到 `gen.*` 配置项）

管理端存在两个容易混淆的页面，先确认菜单指向的是哪一个：

| 组件路径 | 性质 |
|---|---|
| `setting/system/index` | SCUI 框架自带演示页。「系统设置」「扩展配置」都是**前端硬编码假数据**（`file_serve` / `crm_url` 等），保存按钮无后端交互，**改了不生效** |
| `system/config/index` | **真实配置页**：读取 `tb_system_config`，列出全部 `gen.*` 配置项，支持搜索、新增、编辑 |

菜单由后端 `tb_system_menu` 表驱动，处理方式：

1. **推荐**：管理端「菜单管理」中找到「业务配置」，把**组件**改为 `system/config/index`，保存后刷新页面
   （非超管角色还需在该菜单的「接口权限」中包含 `system:config:list` 与 `system:config:update`）
2. 种子数据 `backend/app/mock/data.py` 已同步修正，但 `init_menu_data()` **仅在菜单表为空时播种**，
   已部署环境不会自动更新，需按第 1 条手工修改

---

## 6. 探测脚本参考

路径：`worker/scripts/probe_gateway.py`

### 6.1 用法

```bash
# 只打印配置模板(不发任何请求)
python worker/scripts/probe_gateway.py --print-config

# 探测端点 + 拉模型清单并按能力推荐模型名(零成本,推荐先跑)
python worker/scripts/probe_gateway.py --base-url <URL> --api-key <KEY> --models

# 真实验证 chat / 图片链路(少量消耗)
python worker/scripts/probe_gateway.py --base-url <URL> --api-key <KEY> --real

# 含视频 / 音乐 / 语音的真实调用(会产生真实费用)
python worker/scripts/probe_gateway.py --base-url <URL> --api-key <KEY> --real --allow-costly
```

### 6.2 探测模式判读规则

`probe` 模式发送**缺少参数的请求**，按返回码判断端点是否存在：

| 判定 | 返回码 | 含义 |
|---|---|---|
| `SUPPORTED` | 200 / 201 / 400 / 422 | 端点存在（参数校验失败属预期） |
| `AUTH` | 401 / 403 | 端点存在，但 key 无效或权限不足 |
| `MISSING` | 404 / 405 | 端点不存在，该能力不被支持 |
| `RATE` | 429 | 端点存在但被限流 |
| `ERROR` | 5xx | 网关异常 |

> `video_query` 使用一个不存在的任务 ID 探测；若返回 404 且提示"任务不存在"，同样说明端点存在。

### 6.3 探测端点清单

| 能力 | 方法 | 路径 |
|---|---|---|
| models | GET | `/models` |
| chat/text | POST | `/chat/completions` |
| image | POST | `/images/generations` |
| image_edit | POST | `/images/edits` |
| video_submit | POST | `/videos` |
| video_query | GET | `/videos/{id}` |
| speech | POST | `/audio/speech` |
| music | POST | `/audio/music/generations` |

### 6.4 模型推荐关键词

| 配置项 | 匹配关键词 | 排除关键词 |
|---|---|---|
| `gen.chat_model` | qwen, deepseek, gpt, claude, glm, kimi, chat | image, video, tts, music, embed |
| `gen.text_model` | qwen, deepseek, gpt, glm, kimi | image, video, tts, music, embed |
| `gen.image_model` | image, seedream, flux, dall, kolors, draw | video, edit, chat |
| `gen.image_model_edit` | edit, seededit | video |
| `gen.video_model_t2v` | t2v, text2video, seedance, wan, video | i2v, r2v, image2video, ref2video |
| `gen.video_model_i2v` | i2v, image2video, img2video | — |
| `gen.video_model_r2v` | r2v, ref2video, reference | — |
| `gen.audio_model` | tts, speech, voice | music |
| `gen.music_model` | music, song, bgm | — |

推荐结果仅作参考，**必须人工确认**。

---

## 7. 代码结构（维护者）

### 7.1 关键文件

| 文件 | 职责 |
|---|---|
| `worker/app/core/gateway.py` | 命名网关注册表、能力路由、候选列表解析（`load` / `resolve` / `resolve_all` / `auto_proto`） |
| `worker/app/core/runtime_config.py` | 配置热更新（`KEY_MAP`、双向回退） |
| `worker/app/tools/base.py` | 工具基类：`_switch_gateway` / `_with_failover` / `_pinned` |
| `worker/app/tools/*_tool.py` | 各能力实现（text / image / video / audio） |
| `backend/app/services/system_config.py` | 配置项定义（`DEFAULT_CONFIGS`）、播种、打码 |
| `backend/app/routes/admin/system/config.py` | 管理端配置接口 |

### 7.2 关键函数

| 函数 | 说明 |
|---|---|
| `gateway.resolve_all(cap)` | 返回按能力去重后的候选网关列表 |
| `gateway.resolve(cap)` | 返回主用网关（候选列表首个），向后兼容 |
| `BaseGenTool._with_failover(cap, call, label, prefer_current)` | 候选网关间依次重试 |
| `BaseGenTool._switch_gateway(gw)` | 切换网关并重建 client |

### 7.3 相关测试

```bash
cd worker
python -m pytest tests/ -q
```

| 测试文件 | 覆盖内容 |
|---|---|
| `tests/test_gateway_route.py` | 能力路由、候选列表顺序、同址去重、故障转移切换、视频提交切换 + 轮询复用 |
| `tests/test_video_tool_ark.py` | 方舟原生视频协议 |
| `tests/test_image_tool_ark.py` | 方舟原生图片协议 |
| `tests/test_runtime_config.py` | 配置热更新与双网关回退 |

---

## 附录 A：能力 → 配置 → 代码 速查

| 能力 | 模型配置项 | 网关槽位（首选→备选） | 代码入口 |
|---|---|---|---|
| chat | `gen.chat_model` | `gen.llm_*` → `gen.worker_llm_*` | `video_tool._optimize_prompt`、`backend/services/copy_writer.py` |
| text | `gen.text_model` | `gen.llm_*` → `gen.worker_llm_*` | `tools/text_tool.py` |
| image | `gen.image_model` / `gen.image_model_edit` | `gen.worker_llm_*` → `gen.llm_*` | `tools/image_tool.py` |
| video | `gen.video_model_t2v` / `_i2v` / `_r2v` | `gen.worker_llm_*` → `gen.llm_*` | `tools/video_tool.py` |
| audio | `gen.audio_model` | `gen.audio_llm_*` → `gen.worker_llm_*` → `gen.llm_*` | `tools/audio_tool.py` |
| music | `gen.music_model` | `gen.audio_llm_*` → `gen.worker_llm_*` → `gen.llm_*` | `tools/audio_tool.py` |

---

## 附录 B：本次变更记录

| 变更 | 文件 |
|---|---|
| 新增 `resolve_all()`，候选列表按地址去重 | `worker/app/core/gateway.py` |
| 新增网关故障转移能力（`_switch_gateway` / `_with_failover` / `_pinned`） | `worker/app/tools/base.py` |
| 四个生成工具接入故障转移 | `worker/app/tools/{text,image,audio,video}_tool.py` |
| 修复视频用量模型名固定为默认值的问题（改为取实际使用模型） | `worker/app/tools/video_tool.py` |
| 新增故障转移相关单测 | `worker/tests/test_gateway_route.py` |
| 新增网关能力探测脚本 | `worker/scripts/probe_gateway.py` |
