# -*- coding: utf-8 -*-
'''生成工具基类:统一返回结构 + 网关故障转移'''
from typing import Any, Awaitable, Callable, Dict, List

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
    ) -> Any:
        """网关故障转移:按候选列表(gen.route.<cap> → 固定槽位回退链)依次尝试 call(gw)。

        call 为 async callable(gw) -> Any;抛异常视为该网关失败,自动切换下一个候选。
        与当前网关同址的候选会被跳过,避免重复打同一个网关。
        prefer_current=True 时先试当前网关(常规能力);
        prefer_current=False 时完全按候选列表顺序(如 music 与 audio 可能不是同一个网关)。
        全部失败时抛出最后一个异常,由调用方转成 failed 结果返回上游(不中断任务流程)。
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
                return await call(cand)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
        raise last_exc

    async def generate(self, params: dict) -> ToolResult:
        raise NotImplementedError
