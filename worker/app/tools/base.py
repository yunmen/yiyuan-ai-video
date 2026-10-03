# -*- coding: utf-8 -*-
'''生成工具基类:统一返回结构 + 网关故障转移'''
from typing import Any, Awaitable, Callable, Dict, List, Optional

from openai import AsyncOpenAI

from app.core import gateway
from app.core.plugin import logger
from app.schemas.base import ToolResult


class BaseGenTool:
    name: str = "base"
    description: str = ""

    # 网关状态由各子类 __init__ 填充;基类给默认值,让故障转移逻辑自洽。
    api_key: str = ""
    base_url: str = ""
    proto: str = "openai"
    client: Any = None
    # 构造时显式传入 base_url(测试/直连场景)置 True:不参与故障转移,避免意外打到别的网关。
    _pinned: bool = False
    # 判定「这个错误换网关也没用」的回调,返回 True 则立即抛出、不再往下转移。
    # 供子类按自身语义覆写(如 VideoGenTool 用它挡掉参数类错误)。None = 一律转移。
    # 走类属性而非方法参数,是为了不改动 _with_failover 的签名(测试以固定签名桩替换它)。
    failover_stop_on: Optional[Callable[[Exception], bool]] = None

    def _switch_gateway(self, gw: Dict[str, str]) -> None:
        """故障转移:切到备选网关,更新本地网关状态并按新网关重建 client。

        异步任务(如视频)只在提交阶段切换;提交成功后不再切换,
        后续轮询自然复用"提交成功的那个网关",不会出现跨网关查任务的问题。
        """
        url = (gw.get("url") or "").rstrip("/")
        if not url or url == self.base_url.rstrip("/"):
            return
        self.api_key = gw.get("key") or self.api_key
        self.base_url = url
        self.proto = gw.get("proto") or gateway.auto_proto(url)
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def _with_failover(
        self,
        capability: str,
        call: Callable[[Dict[str, str]], Awaitable[Any]],
        label: str = "",
        prefer_current: bool = True,
        decision: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """网关故障转移:按候选列表(gen.route.<cap> → 固定槽位回退链)依次尝试 call(gw)。

        call 为 async callable(gw) -> Any;抛异常视为该网关失败,自动切换下一个候选。
        与当前网关同址的候选会被跳过,避免重复打同一个网关。
        prefer_current=True 时先试当前网关(常规能力);
        prefer_current=False 时完全按候选列表顺序(如 music 与 audio 可能不是同一个网关)。
        全部失败时抛出最后一个异常,由调用方转成 failed 结果返回上游(不中断任务流程)。

        decision(可选):调用方预先填好「模型/分辨率/时长/成本估算」的字典;**提交成功后**
        由这里把「最终实际选用的网关」回填进去(name + url)。这样决策日志能记录
        "这个任务用了哪个网关、为什么(候选列表顺序/故障转移)",且只在成功时记
        (失败的任务没有"选用"可言)。

        「什么错误不值得再转移」由**类属性** failover_stop_on 决定(子类覆写),
        刻意不走参数:方法签名保持不变,测试里用固定签名桩替换本方法的写法不受影响。
        """
        current = {"name": f"current:{self.base_url}", "url": self.base_url, "key": self.api_key, "proto": self.proto}
        candidates: List[Dict[str, str]] = [current] if prefer_current else []
        if not self._pinned:
            for cand in gateway.resolve_all(capability):
                if cand["url"].rstrip("/") == self.base_url.rstrip("/"):
                    continue
                candidates.append(cand)
        if not candidates:
            candidates = [current]

        last_exc: Exception = RuntimeError(f"能力[{capability}]无可用网关")
        for idx, cand in enumerate(candidates):
            if idx > 0:
                logger.warning(
                    f"[{self.name}] {label or capability} 经网关 [{candidates[idx - 1]['name']}] 失败,"
                    f"切换备选 [{cand['name']}] {cand['url']}: {last_exc}"
                )
                self._switch_gateway(cand)
            try:
                result = await call(cand)
                if decision is not None:
                    decision["gateway_name"] = cand["name"]
                    decision["gateway_url"] = cand["url"]
                return result
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                # 命中「换网关也没用」的错误(如参数类):立即抛出、不再往下转移,
                # 保留当前网关的原始报错(它才是这次提交真正的问题)。
                if self.failover_stop_on is not None and self.failover_stop_on(exc):
                    logger.info(
                        f"[{self.name}] {label or capability} 命中不可转移错误,直接失败不再切换网关: {exc}"
                    )
                    raise
        raise last_exc

    async def generate(self, params: dict) -> ToolResult:
        raise NotImplementedError
