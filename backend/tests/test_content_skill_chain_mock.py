# -*- coding: utf-8 -*-
"""前端→后端→worker 技能链整条链路 mock 联调 + 副本漂移守护。

目标:不依赖真实 Redis broker / 大模型网关,验证整条功能链路是通的,**重点验证
「backend 下发的任务 worker 能不能正确消费」**(这是副本漂移最高危处:backend 下发一个
函数名,worker 注册表里没有 → 任务永远不被执行,前端轮询永久 pending,且没有任何报错)。

真实链路(本测试逐段保留,只 mock 两个外部依赖):
  1. 前端 /content/*  →  backend 路由函数(真实)  →  enqueue_skill_* (真实 ARQ 下发)
        backend 用 arq_pool.enqueue_job("skills_pipeline"/"skills_run", *args, _job_id=jid)
        返回 {"task_id": jid}
  2. worker 消费(本测试用 FakeARQPool 记录下发 + 按 worker functions 注册名查真实 handler 模拟):
        ARQ 以 fn(ctx, *args) 调用,ctx={job_id, redis};本测试在 FakeARQPool 上复刻这一调用,
        证明「下发函数名 == worker functions 注册名」且真实 handler 能跑通
  3. worker handler 写 skill:{job_id}  →  backend /content/result 读同一个 FakeARQPool  →  done

mock 掉的两处:
  - arq_pool:用内存 FakeARQPool 同时充当「broker(enqueue_job)」与「结果存储(get/set)」,
    让 enqueue 写下的 job 与 worker 写回的 skill:{task_id} 落在同一对象上(模拟真实 ARQ 同一连接)
  - skill handler 的 LLM 网关调用:确定性桩。**本次只覆盖文本任务(text-generation)与音频
    (audio-synthesis)两类单技能下发链路;视频生成 / 图片生成(image-generation / script-anchor
    / video-replicate-prep 流水线)不在本测试范围,其桩与对应 case 已移除**,避免误触发视频/图片逻辑。
    文本桩既验证「技能确实被编排器调度」,又钉死 params 透传。

副本漂移守护(改一端另一端没跟上即红):
  - backend 下发的任务名("skills_run"/"skills_pipeline")必须在 worker functions 注册表里真实存在
  - content.py 硬编码技能名(_SKILL_*)必须在 worker 注册表里存在
  - video-replicate-prep 计划步骤必须都是已注册技能且必须产出 'copy'(Replicate.vue 只读 bb.copy)
  - Replicate.vue 不得再展示图提示词/词锚点等中间技能产物

运行:在 backend 目录执行 `python -m pytest tests/test_content_skill_chain_mock.py -q`
"""
import asyncio
import json
import uuid
from pathlib import Path

import pytest

from app.routes.user import content as content_route
from app.core import task_queue as backend_task_queue
from app.core import ratelimit as backend_ratelimit

from _cross_worker_loader import worker_app_context


REPO_ROOT = Path(__file__).resolve().parents[2]          # backend/tests → backend → repo
DESKTOP_REPLICATE = REPO_ROOT / "desktop" / "src" / "views" / "create" / "Replicate.vue"


class FakeJob:
    """模拟 arq Job:enqueue 后仅用 .job_id。"""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id


class FakeARQPool:
    """内存版 ARQ 连接池替身:同时充当 broker 与结果存储。

    - enqueue_job:记录下发的 (函数名, 参数, job_id),返回 FakeJob(模拟真实 arq 下发)
    - set/get/delete/exists:结果存储接口(worker 经 ctx["redis"] 写、backend 经 arq_pool 读,
      真实 ARQ 中本就是同一个连接,这里复用同一对象以保证 skill:{task_id} 键两端一致)
    """

    def __init__(self) -> None:
        self._store: dict = {}
        self._jobs: list = []          # 记录所有下发任务,供「worker 消费」逐个取出

    async def enqueue_job(self, name, *args, **kwargs):
        jid = kwargs.get("_job_id") or f"skill-{uuid.uuid4().hex}"
        self._jobs.append({"name": name, "args": args, "kwargs": kwargs, "job_id": jid})
        return FakeJob(jid)

    async def set(self, key, value, ex=None):
        self._store[key] = value

    async def get(self, key):
        return self._store.get(key)

    async def delete(self, key):
        self._store.pop(key, None)

    async def exists(self, key):
        return 1 if key in self._store else 0

    def drain_jobs(self) -> list:
        jobs, self._jobs = self._jobs, []
        return jobs


def _install_mock_skills(captured: dict) -> None:
    """在 worker 上下文内把 LLM 网关相关技能替换为确定性桩。

    本次只覆盖**文本任务(text-generation)**与音频(audio-synthesis)两类单技能下发链路;
    视频生成 / 图片生成(image-generation / script-anchor / video-replicate-prep)不在本次测试范围,
    其桩一并移除,避免误触发视频/图片相关逻辑。

    每次进入 worker_app_context 都会重建 app 包、registry 也是新实例,因此必须在每个块内重新安装。
    """
    from app.core.skill_runtime import registry
    from app.schemas.base import ToolResult

    async def mock_text(instruction, params):
        # 文本任务真实链路:params 直接携带 title/script,worker 返回文案结构化体
        title = params.get("title") or (params.get("template_title") or "文案")[:20]
        script = params.get("script") or "MOCK_SCRIPT_口播"
        return ToolResult(content={
            "title": f"MOCK_{title}",
            "subtitle": "MOCK_SUBTITLE",
            "script": script,
            "subject": "MOCK_SUBJECT",
            "demand": "MOCK_DEMAND",
        }, metadata={"skill": "text-generation"})

    async def mock_audio(instruction, params):
        text = params.get("text") or instruction
        assert text, "audio-synthesis 缺少合成文本"
        return ToolResult(content={
            "audio_url": f"https://mock/tts/{uuid.uuid4().hex}.mp3",
            "text": text,
        }, metadata={"skill": "audio-synthesis"})

    registry._specs["text-generation"].handler = mock_text
    registry._specs["audio-synthesis"].handler = mock_audio


def _consume_worker(pool: FakeARQPool, captured: dict) -> None:
    """模拟 worker 进程:取出 backend 下发的每个任务,按 worker functions 注册名查真实 handler,
    用 ARQ 风格 ctx(job_id + redis)调用。证明「下发函数名 == worker 注册名且 handler 能跑通」。

    若下发名不在 worker functions → 直接断言失败(这正是后端改名但 worker 没跟上的副本漂移)。
    """
    jobs = pool.drain_jobs()
    for job in jobs:
        # 在 worker 上下文内解析函数,保证拿到 worker 真实的 functions 注册表
        with worker_app_context():
            from app.core.worker import get_worker_settings
            from app.core.skill_runtime import register_builtin_skills
            fns = {f.__name__: f for f in get_worker_settings().functions}
            assert job["name"] in fns, (
                f"backend 下发的任务名 '{job['name']}' 在 worker functions 注册表里不存在"
                f"(worker 无法消费,前端会永久 pending): {sorted(fns)}"
            )
            register_builtin_skills()
            _install_mock_skills(captured)
            ctx = {"job_id": job["job_id"], "redis": pool}
            print(f"[联调] worker 开始消费任务 name={job['name']} job_id={job['job_id']}")
            asyncio.run(fns[job["name"]](ctx, *job["args"]))
            print(f"[联调] worker 消费完成 name={job['name']}, 已写回 skill:{job['job_id']}")


def _stub_request():
    """路由函数仅把 request 交给 ratelimit.client_ip 取 IP;限流已 stub,这里给最小可用对象。"""

    class _R:
        client = None
        headers = {}

    return _R()


def _body(resp) -> dict:
    return json.loads(resp.body)


class Chain:
    """联调夹具载体:共享 FakeARQPool + 桩捕获(黑板贯穿证据) + worker 消费入口。"""

    def __init__(self) -> None:
        self.pool = FakeARQPool()
        self.captured: dict = {}

    def consume(self) -> None:
        """让 worker 消费掉 backend 已下发的全部任务(模拟 worker 异步消费)。"""
        _consume_worker(self.pool, self.captured)


@pytest.fixture
def chain(monkeypatch) -> Chain:
    """装配 mock 联调链路:限流放行 + arq_pool 指向 FakeARQPool(保留真实 enqueue 下发)。"""
    ch = Chain()

    async def _noop_check(*args, **kwargs):
        return None

    monkeypatch.setattr(backend_ratelimit, "check", _noop_check)
    # 关键:保留真实 enqueue_skill_* ,只把底层 arq_pool 换成内存替身;
    # enqueue 写下的 job 与 worker 写回的 skill:{task_id} 落同一对象,复刻真实 ARQ 同一连接。
    monkeypatch.setattr(backend_task_queue, "arq_pool", ch.pool)
    return ch


def test_copy_single_chain(chain: Chain):
    """单技能 /content/copy → 后端真实 enqueue(skills_run) → worker 消费 → text-generation 产物。"""
    print("[联调] ① 前端调用后端 /content/copy (文本任务)")
    task = asyncio.run(content_route.content_copy(
        request=_stub_request(), instruction="",
        params={"title": "保温杯", "script": "来咯上链接"},
    ))
    task_id = _body(task)["data"]["task_id"]
    print(f"[联调] ② 后端真实 enqueue_skill_task 下发,返回 task_id={task_id}")
    chain.consume()
    rb = _body(asyncio.run(content_route.content_result(request=_stub_request(), task_id=task_id)))
    assert rb["data"]["status"] == "done", rb
    print(f"[联调] ③ /content/result 轮询 status={rb['data']['status']}, 文案 script={rb['data']['result']['content']['script']}")
    # 单技能产物在 result.content 下
    assert rb["data"]["result"]["content"]["script"] == "来咯上链接", rb


def test_voice_single_chain(chain: Chain):
    """单技能 /content/voice → 后端真实 enqueue(skills_run) → worker 消费 → audio-synthesis 音频直链。"""
    print("[联调] ① 前端调用后端 /content/voice (音频任务)")
    task = asyncio.run(content_route.content_voice(
        request=_stub_request(), instruction="", params={"text": "你好世界"},
    ))
    task_id = _body(task)["data"]["task_id"]
    print(f"[联调] ② 后端真实 enqueue_skill_task 下发,返回 task_id={task_id}")
    chain.consume()
    rb = _body(asyncio.run(content_route.content_result(request=_stub_request(), task_id=task_id)))
    assert rb["data"]["status"] == "done", rb
    print(f"[联调] ③ /content/result 轮询 status={rb['data']['status']}, 音频={rb['data']['result']['content']['audio_url']}")
    assert rb["data"]["result"]["content"]["audio_url"].startswith("https://mock/tts/"), rb


# —— 副本漂移守护 ——


def test_backend_enqueue_names_registered_in_worker():
    """最高危副本漂移:backend 下发的任务名必须在 worker functions 注册表里真实存在,
    否则 worker 永远消费不到,前端轮询永久 pending 且无任何报错。"""
    with worker_app_context():
        from app.core.worker import get_worker_settings
        fns = {f.__name__ for f in get_worker_settings().functions}
    expected = {"skills_run", "skills_pipeline"}
    missing = expected - fns
    assert not missing, f"backend 下发的任务名在 worker 未注册(worker 无法消费): {sorted(missing)}"


def test_backend_content_mapping_matches_worker_skills():
    """content.py 内部硬编码的技能名必须在 worker 真实注册表里存在,否则 /content/* 下发的技能
    worker 不认识(改了不生效,且前端轮询永远 pending)。"""
    with worker_app_context():
        from app.core.skill_runtime import register_builtin_skills, registry
        register_builtin_skills()
        registered = set(registry._specs.keys())
    names = {content_route._SKILL_COPY, content_route._SKILL_IMAGE, content_route._SKILL_VOICE}
    missing = names - registered
    assert not missing, f"content.py 映射的技能在 worker 未注册(改了不生效): {sorted(missing)}"


def test_plan_store_keys_match_frontend_contract():
    """video-replicate-prep 计划的步骤必须都是已注册技能,且必须产出 'copy'(Replicate.vue 只读
    bb.copy);改名技能名/store_key 会让前端拿不到文案且不报错。"""
    with worker_app_context():
        from app.core.skill_orchestrator import PLAN_REGISTRY
        from app.core.skill_runtime import register_builtin_skills, registry
        register_builtin_skills()
        registered = set(registry._specs.keys())
        plan = PLAN_REGISTRY["video-replicate-prep"]
        step_names = {s.name for s in plan.steps}
        assert step_names <= registered, f"计划引用了未注册技能: {sorted(step_names - registered)}"
        store_keys = {s.store_key for s in plan.steps}
        assert "copy" in store_keys, "video-replicate-prep 未产出 copy,Replicate.vue 无文案可读"


def test_frontend_replicate_hides_intermediate_skill_products():
    """Replicate.vue 不得再展示图提示词/词锚点等中间技能产物(避免把内部编排暴露给终端用户)。"""
    if not DESKTOP_REPLICATE.exists():
        pytest.skip(f"未找到前端文件({DESKTOP_REPLICATE}),跳过")
    text = DESKTOP_REPLICATE.read_text(encoding="utf-8")
    assert "prepImg" not in text, "Replicate.vue 仍残留图提示词展示变量(中间产物暴露)"
    assert "prepAnchor" not in text, "Replicate.vue 仍残留词锚点展示变量(中间产物暴露)"
