# -*- coding: utf-8 -*-
'''
@文件    :seed_video_templates.py
@说明    :视频模板与分类种子数据脚本(幂等,重复执行不会重复写入)
@时间    :2026/09/29 10:00:00

视频模板种子数据。

背景:
  模板库为空时,用户端「选模板」没有可选项,后台运营要从零逐条录入
  (标题/分类/标签/默认文案/画面构成三段式)。本脚本一次性铺一批可直接上架的模板,
  封面与示例视频由运营后续在后台上传替换(脚本默认不写死任何外部地址)。

用法(需在 backend 容器内执行,容器才能解析数据库主机 postgres):
  docker exec -e ENVIRONMENT=prod backend python scripts/seed_video_templates.py --dry-run
  docker exec -e ENVIRONMENT=prod backend python scripts/seed_video_templates.py
  docker exec -e ENVIRONMENT=prod backend python scripts/seed_video_templates.py --update
  docker exec -e ENVIRONMENT=prod backend python scripts/seed_video_templates.py --placeholder-url https://<占位地址>

参数说明:
  --env             目标环境,决定读取 backend/env/.env.<env>(默认取环境变量 ENVIRONMENT,再回退 prod)
  --dry-run         只打印将要写入的数据,不写库
  --update          已存在同名模板时更新文案与画面构成(不覆盖封面/示例视频/示例图/使用次数)
  --placeholder-url 封面与示例视频的占位地址;留空则不写地址,由运营在后台上传
'''
import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# 让脚本能从 backend 根目录直接运行
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    """解析命令行参数(ENVIRONMENT 必须在导入 app.settings 之前确定)"""
    parser = argparse.ArgumentParser(description="初始化视频模板分类与模板种子数据(幂等)")
    parser.add_argument(
        "--env", default=os.getenv("ENVIRONMENT") or "prod",
        help="目标环境:决定读取 backend/env/.env.<env>(dev/test/prod)",
    )
    parser.add_argument("--dry-run", action="store_true", help="只打印计划写入的数据,不写库")
    parser.add_argument(
        "--update", action="store_true",
        help="已存在同名模板时更新文案与画面构成(不覆盖封面/示例视频/示例图/使用次数)",
    )
    parser.add_argument(
        "--placeholder-url", default="",
        help="封面与示例视频的占位地址;留空则不写地址,由运营在后台上传",
    )
    return parser.parse_args()


# 模块级解析:app.settings 在导入时即按 ENVIRONMENT 读取对应环境文件
ARGS = parse_args()
os.environ["ENVIRONMENT"] = ARGS.env

from tortoise import Tortoise  # noqa: E402
from tortoise.transactions import in_transaction  # noqa: E402
from app.settings import config  # noqa: E402
from app.models.video import VideoCategoryModel, VideoTemplateModel  # noqa: E402


# 分类种子(sort 倒序,越大越靠前)。已存在的同名分类跳过,不覆盖运营已维护的排序。
CATEGORIES: List[Dict[str, Any]] = [
    {"name": "文旅景区", "sort": 90, "remark": "景区宣传、民宿营地、城市打卡"},
    {"name": "房产置业", "sort": 80, "remark": "房源展示、样板间、小区配套"},
    {"name": "美食探店", "sort": 70, "remark": "餐饮门店、招牌菜、夜宵烟火气"},
    {"name": "零售带货", "sort": 60, "remark": "产品展示、开箱种草、直播促销"},
    {"name": "美妆个护", "sort": 50, "remark": "护肤彩妆、质地特写、洗护用品"},
    {"name": "健身运动", "sort": 40, "remark": "健身房、运动装备、课程训练"},
    {"name": "教育培训", "sort": 30, "remark": "知识口播、课程预告、数字人播报"},
    {"name": "家居生活", "sort": 20, "remark": "家居好物、收纳改造、生活场景"},
    {"name": "门店宣传", "sort": 10, "remark": "开业活动、门店形象、到店引流"},
]

# 模板种子。prompt_parts 为画面构成三段式(person 主体 / shot 镜头 / setting 场景),
# 是真正参与生成提示词的内容;desc 仅用于后台展示与运营理解,不再喂给模型(见 prompt_builder)。
# duration 只能取模型支持的档位(当前 5/10 秒,见 gen_rules.SUPPORTED_DURATIONS)。
TEMPLATES: List[Dict[str, Any]] = [
    {
        "title": "深夜烟火大排档",
        "category": "美食探店",
        "duration": 10, "hot": 96, "sort": 92,
        "tags": ["探店", "夜宵", "小龙虾", "烟火气"],
        "desc": "适合夜宵/大排档类门店:炭火与蒸汽特写配合摊主出镜,突出人气与现做现炒",
        "prompt_parts": {
            "person": "一位穿围裙、正在翻烤小龙虾的摊主",
            "shot": "中景缓慢推进,浅景深,炭火光斑虚化,手持轻微晃动",
            "setting": "深夜烟火气十足的露天大排档,霓虹灯招牌、腾起的蒸汽与排队人群",
        },
        "default_text": {
            "title": "深夜这口小龙虾藏不住了",
            "subtitle": "现捞现炒 · 凌晨还在排队",
            "script": "晚上十点还在排队的这家小龙虾,现捞现炒,蒜蓉和麻辣两个味,一份就能吃到爽。位置我放在视频下方,来晚了可就没了。",
        },
        "recommend": True, "recommend_sort": 90, "active": True,
    },
    {
        "title": "招牌菜出锅特写",
        "category": "美食探店",
        "duration": 10, "hot": 88, "sort": 88,
        "tags": ["探店", "招牌菜", "美食特写"],
        "desc": "适合餐饮门店的招牌单品:俯拍出锅瞬间与蒸汽,突出色泽与分量",
        "prompt_parts": {
            "person": "一盘刚出锅、还在冒热气的招牌菜",
            "shot": "俯拍 45 度缓慢环绕推进,蒸汽升腾,暖色顶光",
            "setting": "木质餐桌上的精致摆盘,背景是虚化的餐厅暖光",
        },
        "default_text": {
            "title": "这一锅端上来就赢了",
            "subtitle": "每日现做 · 卖完就收",
            "script": "来这家只点这一道就够了,每天现做,出锅那一刻香味能飘半条街。想吃的趁早,晚了真的没了。",
        },
        "recommend": True, "recommend_sort": 80, "active": True,
    },
    {
        "title": "咖啡馆午后慢时光",
        "category": "美食探店",
        "duration": 10, "hot": 72, "sort": 76,
        "tags": ["咖啡", "探店", "氛围感"],
        "desc": "适合咖啡馆/甜品店:窗边自然光与手部细节,突出环境与松弛感",
        "prompt_parts": {
            "person": "一位穿米色针织衫、正在拉花的女店主",
            "shot": "近景缓慢推近到特写,手持微晃,浅景深",
            "setting": "午后阳光洒入的社区咖啡馆窗边,绿植与原木吧台",
        },
        "default_text": {
            "title": "藏在巷子里的下午三点",
            "subtitle": "手冲现磨 · 窗边有座",
            "script": "下午三点最舒服的位置我替你找到了,一杯手冲,阳光刚好落在桌角。周末别赶时间,来这儿坐一会儿。",
        },
        "recommend": False, "recommend_sort": 0, "active": True,
    },
    {
        "title": "烘焙甜品上新",
        "category": "美食探店",
        "duration": 5, "hot": 60, "sort": 70,
        "tags": ["烘焙", "甜品", "上新"],
        "desc": "适合烘焙/甜品上新:微距展示切面与质地,短平快突出食欲",
        "prompt_parts": {
            "person": "一双戴烘焙手套、正在装盘的手",
            "shot": "微距特写,缓慢横移,柔和侧光",
            "setting": "明亮的烘焙工作室,白色大理石台面与撒落的糖粉",
        },
        "default_text": {
            "title": "今天的甜品刚出炉",
            "subtitle": "每日限量 · 卖完等明天",
            "script": "今天这批刚出炉,外皮酥、内里还流心,一天只做这么多。想吃的早点来,晚了只能等明天。",
        },
        "recommend": False, "recommend_sort": 0, "active": True,
    },
    {
        "title": "产品质感大片",
        "category": "零售带货",
        "duration": 10, "hot": 94, "sort": 90,
        "tags": ["产品展示", "质感", "电商"],
        "desc": "通用电商产品主图视频:纯色影棚 + 微距环绕,突出材质与做工",
        "prompt_parts": {
            "person": "一件置于展台上的产品",
            "shot": "微距环绕缓慢推进,高光沿表面扫过,结尾轻微上摇",
            "setting": "纯色渐变影棚背景,柔和顶光与地面倒影",
        },
        "default_text": {
            "title": "细节到位才敢拿出来卖",
            "subtitle": "实拍细节 · 现货发出",
            "script": "拿到手第一感觉就是做工扎实,边角和用料都对得起这个价。现在下单现货发出,不满意包退。",
        },
        "recommend": True, "recommend_sort": 85, "active": True,
    },
    {
        "title": "开箱种草第一视角",
        "category": "零售带货",
        "duration": 10, "hot": 86, "sort": 84,
        "tags": ["开箱", "种草", "第一视角"],
        "desc": "适合开箱测评与好物推荐:第一视角拆箱,真实感强",
        "prompt_parts": {
            "person": "一双正在拆快递的手",
            "shot": "第一视角俯拍,跟随手部动作缓慢下移并推近",
            "setting": "居家桌面,自然窗光与简约桌布",
        },
        "default_text": {
            "title": "拆开那一刻有点惊喜",
            "subtitle": "真实开箱 · 不好用不推荐",
            "script": "快递到手就拆了,配件齐全,第一眼做工比我预期好。用了两天才来拍,确实值得推荐一次。",
        },
        "recommend": True, "recommend_sort": 70, "active": True,
    },
    {
        "title": "服饰上身展示",
        "category": "零售带货",
        "duration": 10, "hot": 74, "sort": 78,
        "tags": ["服饰", "穿搭", "展示"],
        "desc": "适合服装/配饰:全身中景展示版型与上身效果",
        "prompt_parts": {
            "person": "一位穿当季新款的年轻模特",
            "shot": "全身中景,正面缓慢推进后轻微侧转",
            "setting": "简洁街拍背景,浅灰墙面与自然侧光",
        },
        "default_text": {
            "title": "上身比挂着好看太多",
            "subtitle": "显瘦版型 · 多色可选",
            "script": "这件上身是真的显瘦,肩膀和腰线都收得刚好,日常通勤也能穿。喜欢的抓紧,热门色经常断码。",
        },
        "recommend": False, "recommend_sort": 0, "active": True,
    },
    {
        "title": "直播间促销口播",
        "category": "零售带货",
        "duration": 10, "hot": 58, "sort": 66,
        "tags": ["直播", "促销", "口播"],
        "desc": "适合直播切片与限时促销:主播手持产品,强调价格与时效",
        "prompt_parts": {
            "person": "一位手持产品的带货主播",
            "shot": "中景固定机位,轻微推近,结尾定格在产品特写",
            "setting": "明亮的直播间,背景是整齐的货架与补光灯",
        },
        "default_text": {
            "title": "这个价只限今天",
            "subtitle": "限时福利 · 手慢无",
            "script": "这个价格只限今天,库存清完就恢复原价。现在下单还顺丰发出,想要的别犹豫,一会儿就没了。",
        },
        "recommend": False, "recommend_sort": 0, "active": True,
    },
    {
        "title": "精华质地微距",
        "category": "美妆个护",
        "duration": 10, "hot": 82, "sort": 86,
        "tags": ["护肤", "精华", "微距"],
        "desc": "适合护肤品类:液滴与质地微距,突出吸收感与高级质感",
        "prompt_parts": {
            "person": "一瓶精华与正在滴取的滴管",
            "shot": "微距特写,液滴缓慢下落,浅景深虚化背景",
            "setting": "大理石台面,柔光与水纹投影,旁有绿植点缀",
        },
        "default_text": {
            "title": "一抹就化开的质地",
            "subtitle": "清爽不黏 · 四季可用",
            "script": "这瓶我用了小半个月,质地一抹就化开,不黏也不闷。换季容易干的可以试试,早上晚上都能用。",
        },
        "recommend": True, "recommend_sort": 75, "active": True,
    },
    {
        "title": "口红试色特写",
        "category": "美妆个护",
        "duration": 5, "hot": 70, "sort": 74,
        "tags": ["彩妆", "口红", "试色"],
        "desc": "适合彩妆试色:唇部大特写,突出显色与质地",
        "prompt_parts": {
            "person": "一位妆容精致的模特唇部特写",
            "shot": "大特写缓慢推近,环形补光形成眼神光般的高光",
            "setting": "化妆镜前,整齐摆放的彩妆与柔和暖光",
        },
        "default_text": {
            "title": "这支色号显白一整个度",
            "subtitle": "素颜可涂 · 持久不沾杯",
            "script": "这支薄涂日常、厚涂有气场,黄皮也能驾驭。出门一整天颜色还在,喝水基本不沾杯。",
        },
        "recommend": False, "recommend_sort": 0, "active": True,
    },
    {
        "title": "洗护泡沫特写",
        "category": "美妆个护",
        "duration": 5, "hot": 52, "sort": 64,
        "tags": ["洗护", "泡沫", "个护"],
        "desc": "适合洗护用品:泡沫与水花微距,突出清爽与温和",
        "prompt_parts": {
            "person": "一簇绵密泡沫与产品瓶身",
            "shot": "微距俯拍,缓慢横移,水珠反光清晰",
            "setting": "浴室暖光环境,木质托盘与白色毛巾",
        },
        "default_text": {
            "title": "泡沫细到能揉进发丝",
            "subtitle": "温和清洁 · 洗完不干",
            "script": "一点点就能打出很多泡沫,洗完清爽但不紧绷,味道也很干净。家里一直回购的就是这一瓶。",
        },
        "recommend": False, "recommend_sort": 0, "active": True,
    },
    {
        "title": "知识点白板讲解",
        "category": "教育培训",
        "duration": 10, "hot": 78, "sort": 82,
        "tags": ["知识科普", "口播", "讲解"],
        "desc": "适合知识科普与干货口播:讲师出镜 + 白板板书,信息密度高",
        "prompt_parts": {
            "person": "一位穿衬衫、正在板书的讲师",
            "shot": "中景固定机位,轻微推近,构图留出板书空间",
            "setting": "简洁教室,白板与柔和顶光,背景无杂物",
        },
        "default_text": {
            "title": "三分钟讲清一个知识点",
            "subtitle": "干货分享 · 建议收藏",
            "script": "这个问题其实一句话就能说清:先判断前提,再套结论,最后验证一次。照这三步走,基本不会再错。",
        },
        "recommend": False, "recommend_sort": 0, "active": True,
    },
    {
        "title": "数字人新闻播报",
        "category": "教育培训",
        "duration": 10, "hot": 80, "sort": 80,
        "tags": ["数字人", "播报", "资讯"],
        "desc": "适合资讯播报与固定口播:数字人半身出镜,画面稳定、适合批量产出",
        "prompt_parts": {
            "person": "一位职业形象的数字人主播",
            "shot": "半身中景,正面固定机位,几乎无运镜",
            "setting": "简洁虚拟演播室,渐变蓝背景与柔和面部补光",
        },
        "default_text": {
            "title": "今日要闻一分钟",
            "subtitle": "重点摘要 · 持续更新",
            "script": "今天这条消息值得关注:政策已经落地,影响范围覆盖多数从业者。具体怎么变,一分钟给你讲明白。",
        },
        "recommend": True, "recommend_sort": 65, "active": True,
    },
    {
        "title": "课程预告片",
        "category": "教育培训",
        "duration": 10, "hot": 56, "sort": 68,
        "tags": ["课程", "预告", "招生"],
        "desc": "适合课程招生与活动预告:讲师 + 书房场景,突出专业感",
        "prompt_parts": {
            "person": "一位手持书本的年轻讲师",
            "shot": "中景缓慢后拉,逐步展示环境与书架",
            "setting": "明亮书房,背景是有序的书架与暖色台灯",
        },
        "default_text": {
            "title": "这门课下周开讲",
            "subtitle": "名额有限 · 早鸟优惠",
            "script": "这门课我们打磨了三个月,从入门到能上手一共八节。下周开讲,早鸟名额不多,想学的抓紧报名。",
        },
        "recommend": False, "recommend_sort": 0, "active": True,
    },
    {
        "title": "景区宣传片头",
        "category": "文旅景区",
        "duration": 10, "hot": 90, "sort": 94,
        "tags": ["文旅", "景区", "航拍"],
        "desc": "适合景区/城市宣传:大远景航拍开场,气势强、适合做片头",
        "prompt_parts": {
            "person": "一位背对镜头、望向远方的旅人",
            "shot": "大远景缓慢横摇并向前推进,无人机视角",
            "setting": "清晨的山谷景区,薄雾缭绕的山脊线与初升阳光",
        },
        "default_text": {
            "title": "来这里赴一场山水之约",
            "subtitle": "全年可游 · 自驾直达",
            "script": "这里的清晨值得早起来看一次:雾从谷底升起来,光落在山脊上。周末两天的行程刚刚好,导航就能直达。",
        },
        "recommend": True, "recommend_sort": 95, "active": True,
    },
    {
        "title": "民宿营地慢生活",
        "category": "文旅景区",
        "duration": 10, "hot": 62, "sort": 72,
        "tags": ["民宿", "露营", "慢生活"],
        "desc": "适合民宿/营地推广:露台黄昏与生活方式展示,突出松弛感",
        "prompt_parts": {
            "person": "一位坐在露台藤椅上的旅客",
            "shot": "中景缓慢推进,自然光,结尾定格在远景",
            "setting": "山野民宿露台,帐篷、串灯与黄昏暖光",
        },
        "default_text": {
            "title": "把周末交给这片山野",
            "subtitle": "整院独享 · 含早餐",
            "script": "不用赶行程的一个周末:白天去山里走走,晚上在露台看星星。院子整院独享,第二天还有热腾腾的早餐。",
        },
        "recommend": False, "recommend_sort": 0, "active": True,
    },
    {
        "title": "房源一镜到底",
        "category": "房产置业",
        "duration": 10, "hot": 50, "sort": 62,
        "tags": ["房产", "样板间", "一镜到底"],
        "desc": "适合房源展示:广角一镜到底,空间感与采光一目了然",
        "prompt_parts": {
            "person": "无人物出镜的室内空间",
            "shot": "广角一镜到底,沿客厅中轴缓慢平移前进",
            "setting": "采光充足的样板客厅,落地窗、布艺沙发与木质地板",
        },
        "default_text": {
            "title": "这套房采光是真的好",
            "subtitle": "南北通透 · 随时看房",
            "script": "这套三面采光,上午客厅有太阳,下午卧室也亮。户型方正没浪费,想看的随时约,钥匙就在我们这儿。",
        },
        "recommend": False, "recommend_sort": 0, "active": True,
    },
    {
        "title": "小区配套讲解",
        "category": "房产置业",
        "duration": 10, "hot": 44, "sort": 58,
        "tags": ["房产", "配套", "讲解"],
        "desc": "适合新房/小区介绍:顾问边走边讲,展示园林与配套",
        "prompt_parts": {
            "person": "一位穿职业装的置业顾问",
            "shot": "中景跟拍,缓慢前推,保持人物在画面右侧",
            "setting": "小区园林中庭,绿化步道与远处楼体",
        },
        "default_text": {
            "title": "住进来才知道配套有多省心",
            "subtitle": "地铁近 · 学区在侧",
            "script": "出门就是地铁口,孩子上学走路十分钟,楼下商超已经开业。住进来以后,日常基本不用开车。",
        },
        "recommend": False, "recommend_sort": 0, "active": True,
    },
    {
        "title": "家居好物改造",
        "category": "家居生活",
        "duration": 10, "hot": 48, "sort": 60,
        "tags": ["家居", "好物", "改造"],
        "desc": "适合家居好物与收纳改造:前后对比式俯拍,突出变化",
        "prompt_parts": {
            "person": "一双正在整理桌面与收纳的手",
            "shot": "俯拍 45 度缓慢下移,推近到整理后的细节",
            "setting": "温馨客厅一角,木质家具、布艺与暖色灯光",
        },
        "default_text": {
            "title": "几十块把桌面收拾干净",
            "subtitle": "收纳好物 · 一秒归位",
            "script": "这张桌子之前乱得没法用,加了收纳盒之后十分钟就归位。花不了多少钱,看着顺眼多了。",
        },
        "recommend": False, "recommend_sort": 0, "active": True,
    },
    {
        "title": "门店开业活动",
        "category": "门店宣传",
        "duration": 10, "hot": 68, "sort": 74,
        "tags": ["开业", "活动", "到店"],
        "desc": "适合门店开业与节日活动:门头 + 店长出镜,突出优惠与位置",
        "prompt_parts": {
            "person": "一位微笑站立的门店店长",
            "shot": "中景缓慢推进,轻微上摇展示门头招牌",
            "setting": "布置一新的门店门口,气球拱门与红色开业横幅",
        },
        "default_text": {
            "title": "新店开业全场五折",
            "subtitle": "活动三天 · 到店即享",
            "script": "新店开业前三天全场五折,进店还有小礼品。就在路口第一家,看到红色拱门就是,等你来逛。",
        },
        "recommend": False, "recommend_sort": 0, "active": True,
    },
]

# --update 时允许覆盖的字段:不含 cover / video_url / example_images / use_count,
# 避免把运营已上传的封面、示例视频和真实使用数据冲掉
UPDATABLE_FIELDS = (
    "duration", "hot", "sort", "desc", "tags",
    "default_text", "prompt_parts", "recommend", "recommend_sort", "active",
)


def build_payload(item: Dict[str, Any], placeholder_url: str) -> Dict[str, Any]:
    """把种子条目补齐为完整建库字段(占位地址为空时不写封面/示例视频)"""
    data: Dict[str, Any] = dict(item)
    data.setdefault("tags", [])
    data.setdefault("example_images", [])
    data.setdefault("active", True)
    data.setdefault("recommend", False)
    data.setdefault("recommend_sort", 0)
    if placeholder_url:
        data.setdefault("cover", placeholder_url)
        data.setdefault("video_url", placeholder_url)
    return data


async def ensure_categories(dry_run: bool) -> Dict[str, int]:
    """补种缺失的分类;已存在的同名分类跳过(不覆盖运营已维护的排序)"""
    stat = {"created": 0, "skipped": 0}
    for item in CATEGORIES:
        exist = await VideoCategoryModel.get_or_none(name=item["name"])
        if exist:
            stat["skipped"] += 1
            continue
        if dry_run:
            stat["created"] += 1
            print(f"[分类·待新增] {item['name']}(排序 {item['sort']})")
            continue
        await VideoCategoryModel.create(**item)
        stat["created"] += 1
        print(f"[分类·新增] {item['name']}(排序 {item['sort']})")
    return stat


async def ensure_templates(dry_run: bool, update: bool, placeholder_url: str) -> Dict[str, int]:
    """写入模板种子:同名(标题 + 分类)视为同一条,默认跳过,--update 时更新文案与画面构成"""
    stat = {"created": 0, "updated": 0, "skipped": 0}
    for item in TEMPLATES:
        data = build_payload(item, placeholder_url)
        exist = await VideoTemplateModel.get_or_none(title=data["title"], category=data["category"])
        if not exist:
            if dry_run:
                stat["created"] += 1
                print(f"[模板·待新增] {data['category']} / {data['title']}({data['duration']} 秒)")
                continue
            await VideoTemplateModel.create(**data)
            stat["created"] += 1
            print(f"[模板·新增] {data['category']} / {data['title']}({data['duration']} 秒)")
            continue
        if not update:
            stat["skipped"] += 1
            continue
        if dry_run:
            stat["updated"] += 1
            print(f"[模板·待更新] {data['category']} / {data['title']}")
            continue
        for field in UPDATABLE_FIELDS:
            setattr(exist, field, data[field])
        await exist.save(update_fields=list(UPDATABLE_FIELDS))
        stat["updated"] += 1
        print(f"[模板·更新] {data['category']} / {data['title']}")
    return stat


async def run(dry_run: bool, update: bool, placeholder_url: str) -> int:
    """连接数据库并执行种子写入(整体放在一个事务里,失败则全部回滚)"""
    await Tortoise.init(config=config.ORM_CONFIG)
    try:
        print(f"目标环境: {ARGS.env} | 模式: {'预演(不写库)' if dry_run else '写入'}"
              f" | 模板总数: {len(TEMPLATES)} | 分类总数: {len(CATEGORIES)}")
        if dry_run:
            cat_stat = await ensure_categories(dry_run=True)
            tpl_stat = await ensure_templates(dry_run=True, update=update, placeholder_url=placeholder_url)
        else:
            async with in_transaction():
                cat_stat = await ensure_categories(dry_run=False)
                tpl_stat = await ensure_templates(dry_run=False, update=update, placeholder_url=placeholder_url)
        print("-" * 56)
        print(f"分类:新增 {cat_stat['created']} 个,已存在跳过 {cat_stat['skipped']} 个")
        print(f"模板:新增 {tpl_stat['created']} 条,更新 {tpl_stat['updated']} 条,已存在跳过 {tpl_stat['skipped']} 条")
        if not dry_run and not placeholder_url:
            print("提示:封面与示例视频未写入地址,请在管理端「视频模板」中上传后上架。")
        return 0
    finally:
        await Tortoise.close_connections()


def main() -> int:
    """脚本入口"""
    try:
        return asyncio.run(run(ARGS.dry_run, ARGS.update, ARGS.placeholder_url.strip()))
    except Exception as exc:  # noqa: BLE001
        # 保留完整错误信息用于定位(多为环境文件或数据库不可达)
        print(f"[错误] 种子数据初始化失败: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
