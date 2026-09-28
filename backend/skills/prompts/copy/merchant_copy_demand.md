---
name: merchant_copy_demand
capability: text
version: 1
description: merchant_copy 在 with_demand=True 时追加的 subject/demand 字段要求(单一来源)
variables: []
---
另外请在 JSON 中追加两个字段:"subject": "素材里的主体是什么,≤40字;若同时有人物与产品,写成『人物:xx;产品:yy』", "demand": "画面要求,≤90字,必须写成可直接执行的画面指令,形如『把参考视频里的原人物换成上传图第1张的人物(外观/服饰保持一致),把原商品换成上传图第2张的商品(包装与文字一并替换),其余场景、运镜与节奏严格保持原样』。要求:同时有**人物与产品**时,两者都要分别写清替换对象与保持要求;只描述画面怎么改,不要写成口播台词或营销话术"
