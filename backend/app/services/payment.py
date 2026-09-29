# -*- coding: utf-8 -*-
'''
@文件    :payment.py
@说明    :支付/退款Service(参考 ai-creator 项目设计)
          支付:下单(微信Native/mock)→ 回调验签 → 事务A确认收款(PENDING→PAID)
               → 事务B交付(创建生成任务并入队)→ DELIVERED
          退款:admin发起/任务失败自动退 → 渠道退款 → 退款回调幂等终结(REFUNDED)
          幂等:行锁串行化回调;DELIVERED/REFUNDED 重复进入直接返回。
@时间    :2026/09/19 14:30:00
@作者    :一源AI
@版本    :1.0
'''
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional

from fastapi.exceptions import HTTPException
from tortoise.transactions import in_transaction

from app.cruds.payment import crud
from app.cruds.system_config import crud as config_crud
from app.cruds.video_template import crud as template_crud
from app.services.payment_package import service as package_service
from app.enums.base import EnvironmentEnum
from app.enums.payment import OrderStatusEnum, PaymentGatewayEnum, PaymentBizTypeEnum
from app.core.wxpay import get_wxpay
from app.core.logger import logger
from app.settings import config


def _gen_order_no(prefix: str = "WX") -> str:
    """订单号:{前缀}-{yymmdd}-{HHMMSS}-{毫秒3位}{随机4位},长度<32 满足微信限制"""
    now = datetime.now()
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-{now.strftime('%y%m%d')}-{now.strftime('%H%M%S')}-{now.microsecond // 1000:03d}{suffix}"


def _yuan_to_fen(amount: Decimal) -> int:
    """元转分(Decimal 精确量化,拒绝超过 2 位小数)"""
    quantized = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(quantized * 100)


async def _get_video_price() -> Decimal:
    """从系统配置读取单次生成定价(元),缺失兜底 9.90"""
    obj = await config_crud.get_by_key("gen.video_price")
    try:
        return Decimal(str(obj.value)).quantize(Decimal("0.01")) if obj and obj.value else Decimal("9.90")
    except Exception:  # noqa: BLE001
        return Decimal("9.90")


class Service:
    # ------------------------------------------------------------------ 下单
    async def create_video_order(self, user, payload) -> Dict:
        """创建视频生成订单并发起支付(微信 Native 扫码 / mock)

        模板可选:普通生成(选平台模板视频)必传并校验;视频复刻链路用户自带对标视频,
        无需模板。视频价格为统一价,与模板无关,故无模板时仅按"视频复刻生成"命名,不影响计费与交付。
        """
        # 仅当「传了 template_id」时才校验模板;未传则 template=None(复刻链路)。
        template = await template_crud.get_by_id(payload.template_id) if payload.template_id else None
        if payload.template_id and (not template or not template.active):
            raise HTTPException(status_code=200, detail="模板不存在或已下架")
        amount = await _get_video_price()
        gateway = PaymentGatewayEnum.MOCK.value if config.PAYMENT_MODE == "mock" else PaymentGatewayEnum.WECHAT.value
        order_no = _gen_order_no("MOCK" if gateway == "mock" else "WX")
        notify_url = f"{config.BACKEND_PUBLIC_URL}/api/callback/wxpay/video"

        code_url = None
        request_snapshot = None
        if gateway == PaymentGatewayEnum.WECHAT.value:
            wxpay = get_wxpay()
            code, message = await wxpay.pay(
                description=f"一源AI视频-{template.title if template else '视频复刻生成'}"[:127],
                out_trade_no=order_no,
                amount={"total": _yuan_to_fen(amount)},
                notify_url=notify_url,
                attach=config.PAYMENT_SOURCE_TAG,
            )
            if code != 200:
                raise HTTPException(status_code=200, detail=f"支付下单失败:{message}")
            request_snapshot = {"code_url": (message or {}) if isinstance(message, dict) else message}
            code_url = (message or {}).get("code_url") if isinstance(message, dict) else None
        else:
            code_url = f"MOCKPAY://{order_no}"

        obj = await crud.create({
            "user_id": user.id,
            "order_no": order_no,
            "biz_type": PaymentBizTypeEnum.VIDEO_GEN.value,
            "package_name": f"爆款视频生成 · {template.title}" if template else "爆款视频生成 · 视频复刻",
            "amount": amount,
            "status": OrderStatusEnum.PENDING.value,
            "gateway": gateway,
            "source": {
                "template_id": template.id if template else None,
                "template_title": template.title if template else "视频复刻生成",
                "materials": payload.materials,
                "remark": payload.remark,
                "device": payload.device,
                "intent": payload.intent,
                "image_roles": payload.image_roles,
                # 复刻形态(口播/短剧/街采…)与真人策略也随订单快照保存:
                # 它们和时长/画幅一样是用户在页面做的选择,交付阶段重建 CreateSchema 时若不带,
                # 付费链路就会静默丢掉(与额度链路行为不一致)。
                "format": payload.format,
                "real_person_strategy": payload.real_person_strategy,
                # 规格随订单快照保存:支付成功后的交付阶段按同一份参数建单,
                # 否则用户在付费链路选的时长/画幅/清晰度会被丢掉(与额度链路不一致)。
                "duration": payload.duration,
                "ratio": payload.ratio,
                "resolution": payload.resolution,
            },
            "request": request_snapshot,
        })
        return {
            "order_no": obj.order_no,
            "amount": str(amount),
            "gateway": gateway,
            "code_url": code_url,
            "mock": gateway == PaymentGatewayEnum.MOCK.value,
        }

    async def create_credit_order(self, user, payload) -> Dict:
        """创建额度充值订单并发起支付(微信 Native 扫码 / mock)

        支付成功回调 → _deliver 按 biz_type 走充值交付,调用 credit_service.grant 到账。
        """
        package = await package_service.get_by_id(payload.package_id)
        amount = Decimal(str(package.price)).quantize(Decimal("0.01"))
        gateway = PaymentGatewayEnum.MOCK.value if config.PAYMENT_MODE == "mock" else PaymentGatewayEnum.WECHAT.value
        order_no = _gen_order_no("MOCK" if gateway == "mock" else "WX")
        notify_url = f"{config.BACKEND_PUBLIC_URL}/api/callback/wxpay/video"

        code_url = None
        request_snapshot = None
        if gateway == PaymentGatewayEnum.WECHAT.value:
            wxpay = get_wxpay()
            code, message = await wxpay.pay(
                description=f"一源AI-额度充值{package.credits}次"[:127],
                out_trade_no=order_no,
                amount={"total": _yuan_to_fen(amount)},
                notify_url=notify_url,
                attach=config.PAYMENT_SOURCE_TAG,
            )
            if code != 200:
                raise HTTPException(status_code=200, detail=f"支付下单失败:{message}")
            request_snapshot = {"code_url": (message or {}) if isinstance(message, dict) else message}
            code_url = (message or {}).get("code_url") if isinstance(message, dict) else None
        else:
            code_url = f"MOCKPAY://{order_no}"

        obj = await crud.create({
            "user_id": user.id,
            "order_no": order_no,
            "biz_type": PaymentBizTypeEnum.CREDIT_RECHARGE.value,
            "package_name": f"{package.name} · {package.credits} 次额度",
            "amount": amount,
            "status": OrderStatusEnum.PENDING.value,
            "gateway": gateway,
            "source": {
                "package_id": package.id,
                "package_name": package.name,
                "credits": package.credits,
                "device": payload.device,
            },
            "request": request_snapshot,
        })
        return {
            "order_no": obj.order_no,
            "amount": str(amount),
            "gateway": gateway,
            "code_url": code_url,
            "mock": gateway == PaymentGatewayEnum.MOCK.value,
        }

    # -------------------------------------------------------------- 状态查询
    async def order_status(self, user, order_no: str) -> Dict:
        obj = await crud.get_by_order_no(order_no)
        if not obj or obj.user_id != user.id:
            raise HTTPException(status_code=200, detail="订单不存在")
        # 待支付订单轮询时主动向微信查单:回调依赖公网 HTTPS,未配置域名前
        # 微信通知无法到达,查单可让支付结果秒级到账(pay_callback 内部幂等)
        if obj.status == OrderStatusEnum.PENDING.value and obj.gateway == PaymentGatewayEnum.WECHAT.value:
            try:
                wxpay = get_wxpay()
                code, message = await wxpay.query(out_trade_no=obj.order_no)
                if code == 200 and isinstance(message, dict) and message.get("trade_state") == "SUCCESS":
                    await self.pay_callback({
                        "out_trade_no": obj.order_no,
                        "trade_state": "SUCCESS",
                        "transaction_id": message.get("transaction_id"),
                        "attach": config.PAYMENT_SOURCE_TAG,
                        "amount": {"total": _yuan_to_fen(obj.amount), "currency": "CNY"},
                    })
                    obj = await crud.get_by_order_no(order_no)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"订单轮询查单失败 order={order_no}: {exc}")
        data = obj.to_dict()
        # 交付后附带任务Id,前端可直接跳转生成页
        if obj.status == OrderStatusEnum.DELIVERED.value and obj.response:
            data["task_id"] = (obj.response or {}).get("task_id")
        return data

    async def list_by_user(self, user, payload) -> Dict:
        from tortoise.expressions import Q
        q = Q(user_id=user.id)
        if payload.status:
            q &= Q(status=payload.status)
        total = await crud.model.filter(q).count()
        rows = await crud.model.filter(q).order_by("-id").offset(
            (payload.pageNum - 1) * payload.pageSize
        ).limit(payload.pageSize).all()
        return {"total": total, "data": [r.to_dict() for r in rows]}

    async def list_all(self, payload) -> Dict:
        from tortoise.expressions import Q
        q = Q()
        if payload.status:
            q &= Q(status=payload.status)
        if payload.keyword:
            q &= Q(order_no__contains=payload.keyword) | Q(package_name__contains=payload.keyword)
        total = await crud.model.filter(q).count()
        rows = await crud.model.filter(q).order_by("-id").offset(
            (payload.pageNum - 1) * payload.pageSize
        ).limit(payload.pageSize).all()
        return {"total": total, "data": [r.to_dict() for r in rows]}

    # --------------------------------------------------------- mock 支付确认
    async def mock_confirm(self, order_no: str, user=None) -> Dict:
        """开发环境模拟支付成功:构造成功报文走与微信回调完全一致的幂等交付链路"""
        if config.ENVIRONMENT != EnvironmentEnum.DEV or config.PAYMENT_MODE != "mock":
            raise HTTPException(status_code=200, detail="仅开发环境 mock 模式可用")
        obj = await crud.get_by_order_no(order_no)
        if not obj:
            raise HTTPException(status_code=200, detail="订单不存在")
        # 归属校验:仅订单本人可模拟确认,防止越权确认他人订单
        if user is not None and getattr(obj, "user_id", None) and obj.user_id != user.id:
            raise HTTPException(status_code=200, detail="无权操作该订单")
        resource = {
            "out_trade_no": obj.order_no,
            "trade_state": "SUCCESS",
            "transaction_id": f"MOCK-TX-{obj.order_no}",
            "attach": config.PAYMENT_SOURCE_TAG,
            "amount": {"total": _yuan_to_fen(obj.amount), "currency": "CNY"},
        }
        await self.pay_callback(resource)
        return {"order_no": order_no}

    # ---------------------------------------------------------------- 支付回调
    def _validate_resource(self, obj, resource: Dict) -> None:
        """回调业务契约校验(防串单/防伪造金额)"""
        if resource.get("trade_state") != "SUCCESS":
            raise HTTPException(status_code=400, detail="非成功支付通知")
        if resource.get("attach") != config.PAYMENT_SOURCE_TAG:
            raise HTTPException(status_code=400, detail="来源标识不匹配")
        amount = resource.get("amount") or {}
        total = amount.get("total")
        if not isinstance(total, int) or isinstance(total, bool):
            raise HTTPException(status_code=400, detail="金额格式非法")
        if total != _yuan_to_fen(obj.amount):
            raise HTTPException(status_code=400, detail="支付金额与订单不符")
        if amount.get("currency", "CNY") != "CNY":
            raise HTTPException(status_code=400, detail="币种不符")

    async def pay_callback(self, resource: Dict) -> None:
        """支付成功回调:事务A确认收款 → 事务B交付(创建生成任务)"""
        order_no = resource.get("out_trade_no")
        if not order_no:
            raise HTTPException(status_code=400, detail="缺少订单号")

        # 事务A:行锁确认收款(重复回调直接返回,保证幂等)
        need_deliver = False
        order_id = None
        async with in_transaction():
            obj = await crud.get_by_order_no_for_update(order_no)
            if not obj:
                raise HTTPException(status_code=400, detail="订单不存在")
            if obj.status != OrderStatusEnum.PENDING.value:
                # 已收款但未交付(上次交付异常)时,借这次回调补偿交付,避免订单永久卡在「已支付」
                if obj.status == OrderStatusEnum.PAID.value:
                    need_deliver = True
                    order_id = obj.id
                else:
                    logger.info(f"支付回调幂等忽略 order={order_no} status={obj.status}")
                return
            self._validate_resource(obj, resource)
            obj.status = OrderStatusEnum.PAID.value
            obj.transaction_id = resource.get("transaction_id")
            obj.pay_time = datetime.now()
            obj.response = {**(obj.response or {}), "pay_notify": resource}
            await obj.save()
            need_deliver = True
            order_id = obj.id

        # 事务B:交付权益(失败可重试,微信侧会重复通知)
        if need_deliver:
            await self._deliver(order_id)

    async def _deliver(self, order_id: int) -> None:
        """交付:按下单快照创建生成任务并入队(独立事务,可安全重试)"""
        async with in_transaction():
            obj = await crud.model.select_for_update().get_or_none(id=order_id)
            if not obj:
                return
            if obj.status == OrderStatusEnum.DELIVERED.value:
                return  # 已交付,幂等返回
            if obj.status != OrderStatusEnum.PAID.value:
                return
            source = obj.source or {}
            from app.services.generate_task import service as task_service
            from app.schemas.generate_task import CreateSchema
            from app.cruds.account import crud as user_crud

            user = await user_crud.get(obj.user_id)
            if obj.biz_type == PaymentBizTypeEnum.CREDIT_RECHARGE.value:
                # 额度充值:直接到账,不创建生成任务
                from app.services.credit import service as credit_service
                credits = int(source.get("credits") or 0)
                await credit_service.grant(
                    obj.user_id, credits,
                    remark=f"充值到账 · {source.get('package_name') or obj.package_name}",
                )
                obj.status = OrderStatusEnum.DELIVERED.value
                obj.response = {**(obj.response or {}), "credits": credits}
                await obj.save()
                logger.info(f"充值订单交付完成 order={obj.order_no} credits={credits}")
                return

            task = await task_service.create(
                CreateSchema(
                    template_id=source.get("template_id"),
                    materials=source.get("materials") or [],
                    remark=source.get("remark"),
                    device=source.get("device") or "desktop",
                    intent=source.get("intent"),
                    image_roles=source.get("image_roles"),
                    # 与下单时的快照保持一致:复刻形态/真人策略不能只在额度链路生效
                    format=source.get("format"),
                    real_person_strategy=source.get("real_person_strategy"),
                    # 与下单时的快照保持一致:付费链路同样尊重用户选的规格
                    duration=source.get("duration"),
                    ratio=source.get("ratio"),
                    resolution=source.get("resolution"),
                ),
                user=user,
                order_no=obj.order_no,
            )
            obj.status = OrderStatusEnum.DELIVERED.value
            obj.response = {**(obj.response or {}), "task_id": task["id"], "task_no": task["task_no"]}
            await obj.save()
            logger.info(f"订单交付完成 order={obj.order_no} task={task['task_no']}")

    # ---------------------------------------------------------------- 退款
    async def apply_refund(self, order_no: str, reason: Optional[str] = None, auto: bool = False) -> Dict:
        """发起退款(admin 手动 / 任务失败自动)。全额退款,退款单号复用原订单号"""
        obj = await crud.get_by_order_no(order_no)
        if not obj:
            raise HTTPException(status_code=200, detail="订单不存在")
        if obj.status in (OrderStatusEnum.REFUNDING.value, OrderStatusEnum.REFUNDED.value):
            return {"order_no": order_no, "status": obj.status}  # 幂等
        if obj.status not in (OrderStatusEnum.PAID.value, OrderStatusEnum.DELIVERED.value):
            raise HTTPException(status_code=200, detail="当前状态不允许退款")
        if obj.pay_time and datetime.now() - obj.pay_time.replace(tzinfo=None) > timedelta(days=config.PAYMENT_REFUND_WINDOW_DAYS):
            raise HTTPException(status_code=200, detail=f"超过 {config.PAYMENT_REFUND_WINDOW_DAYS} 天退款窗口")

        reason = reason or ("生成失败自动退款" if auto else "管理员退款")
        notify_url = f"{config.BACKEND_PUBLIC_URL}/api/callback/wxpay/refund"
        if obj.gateway == PaymentGatewayEnum.WECHAT.value:
            wxpay = get_wxpay()
            fen = _yuan_to_fen(obj.amount)
            code, message = await wxpay.refund(
                out_refund_no=obj.order_no,
                amount={"refund": fen, "total": fen, "currency": "CNY"},
                transaction_id=obj.transaction_id,
                out_trade_no=obj.order_no,
                reason=reason,
                notify_url=notify_url,
            )
            if code != 200:
                raise HTTPException(status_code=200, detail=f"退款申请失败:{message}")
            await crud.model.filter(id=obj.id).update(
                status=OrderStatusEnum.REFUNDING.value, remark=reason, update_time=datetime.now()
            )
            return {"order_no": order_no, "status": OrderStatusEnum.REFUNDING.value}
        # mock:直接终结(与微信退款回调同链路)
        await crud.model.filter(id=obj.id).update(
            status=OrderStatusEnum.REFUNDING.value, remark=reason, update_time=datetime.now()
        )
        await self.finalize_refund(order_no)
        return {"order_no": order_no, "status": OrderStatusEnum.REFUNDED.value}

    async def refund_callback(self, resource: Dict) -> None:
        """微信退款结果回调"""
        refund_no = resource.get("out_refund_no")
        if not refund_no:
            raise HTTPException(status_code=400, detail="缺少退款单号")
        if resource.get("refund_status") != "SUCCESS":
            logger.warning(f"退款未成功 order={refund_no} status={resource.get('refund_status')}")
            return
        await self.finalize_refund(refund_no)

    async def finalize_refund(self, order_no: str) -> bool:
        """退款终结(幂等):置 REFUNDED 并红冲权益(未完成的生成任务标记失败)"""
        async with in_transaction():
            obj = await crud.get_by_order_no_for_update(order_no)
            if not obj:
                return False
            if obj.status == OrderStatusEnum.REFUNDED.value:
                return False  # 已退款,幂等返回
            obj.status = OrderStatusEnum.REFUNDED.value
            obj.update_time = datetime.now()
            await obj.save()
            # 红冲:关联任务仍在生成中则终止
            from app.models.video import GenerateTaskModel
            from app.enums.business import TaskStatusEnum
            await GenerateTaskModel.filter(
                order_no=order_no, status=TaskStatusEnum.PROCESSING.value
            ).update(status=TaskStatusEnum.FAILED.value, fail_reason="订单已退款,任务终止", update_time=datetime.now())
            logger.info(f"退款终结完成 order={order_no}")
            return True

    async def refund_query(self, order_no: str) -> Dict:
        """退款查询兜底(防回调丢失):网关已成功则本地终结"""
        obj = await crud.get_by_order_no(order_no)
        if not obj:
            raise HTTPException(status_code=200, detail="订单不存在")
        if obj.status == OrderStatusEnum.REFUNDED.value:
            return {"order_no": order_no, "status": obj.status}
        if obj.gateway == PaymentGatewayEnum.WECHAT.value:
            wxpay = get_wxpay()
            code, message = await wxpay.query_refund(out_refund_no=order_no)
            if code == 200 and isinstance(message, dict) and message.get("refund_status") == "SUCCESS":
                await self.finalize_refund(order_no)
            else:
                return {"order_no": order_no, "status": obj.status, "gateway_msg": message}
        else:
            await self.finalize_refund(order_no)
        fresh = await crud.get_by_order_no(order_no)
        return {"order_no": order_no, "status": fresh.status}

    # ---------------------------------------------------- 任务失败自动退款
    async def auto_refund_by_task(self, task) -> None:
        """生成任务失败 → 关联付费订单自动退款"""
        if not getattr(task, "order_no", None):
            return
        obj = await crud.get_by_order_no(task.order_no)
        if not obj or obj.status != OrderStatusEnum.DELIVERED.value:
            return
        try:
            await self.apply_refund(obj.order_no, reason=f"生成失败自动退款(任务{task.task_no})", auto=True)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"任务失败自动退款失败 order={obj.order_no}: {exc}")

    # ---------------------------------------------------------- 超时订单对账
    async def reconcile_expired(self) -> int:
        """取消超时未支付订单(由对账后台协程周期调用)"""
        deadline = datetime.now() - timedelta(minutes=config.PAYMENT_ORDER_EXPIRE_MINUTES)
        rows = await crud.list_expired_pending(deadline)
        count = 0
        for obj in rows:
            # 真实模式先向微信查单,确认未付款才取消(防回调丢失误取消)
            if obj.gateway == PaymentGatewayEnum.WECHAT.value:
                try:
                    wxpay = get_wxpay()
                    code, message = await wxpay.query(out_trade_no=obj.order_no)
                    if code == 200 and isinstance(message, dict) and message.get("trade_state") == "SUCCESS":
                        await self.pay_callback({
                            "out_trade_no": obj.order_no,
                            "trade_state": "SUCCESS",
                            "transaction_id": message.get("transaction_id"),
                            "attach": config.PAYMENT_SOURCE_TAG,
                            "amount": {"total": _yuan_to_fen(obj.amount), "currency": "CNY"},
                        })
                        continue
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"超时订单查单失败 order={obj.order_no}: {exc}")
                    continue
            await crud.model.filter(id=obj.id).update(
                status=OrderStatusEnum.CANCELLED.value, remark="超时未支付自动取消", update_time=datetime.now()
            )
            count += 1
        return count


service = Service()
