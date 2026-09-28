# -*- coding: utf-8 -*-
'''@文件    :skills/__init__.py
@说明    :backend 自有技能包。提示词资产集中在 backend/skills/prompts(单一来源),
          backend 运行时不依赖 worker,直接读这里的 MD,改 MD 即维护、不碰代码。
          目录约定(与 worker/skills 保持一致的标准结构):
            skills/prompts/   各功能模板的提示词 MD(frontmatter + 正文),按功能分门别类子目录
              ├─ copy/        文案生成(三段带货文案)
              ├─ generation/  视频生成参数(replace/context/material)
              └─ replicate/   视频复刻方法论(改编自 hypit,worker 通过引用复用,不复制)
            skills/docs/      backend 技能资产说明 + 视频复刻原始溯源(raw/)
          视频复刻相关的「标准资产」统一收归 prompts/replicate/,worker 的 loader 同时扫描本目录,
          实现引用复用、避免两份漂移(详见 skills/docs/prompt-assets.md)。
@时间    :2026/09/29
@作者    :一源AI
@版本    :1.0
'''
