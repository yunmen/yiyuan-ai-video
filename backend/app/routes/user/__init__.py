from fastapi import APIRouter
from app.enums.base import ClientRoleEnum

from app.routes.user import template as user_template
from app.routes.user import task as user_task
from app.routes.user import common as user_common
from app.routes.user import account as user_account
from app.routes.user import digital as user_digital
from app.routes.user import payment as user_payment
from app.routes.user import feedback as user_feedback
from app.routes.user import storyboard as user_storyboard


router = APIRouter(prefix=f"/{ClientRoleEnum.USER.value}/v1")

router.include_router(user_template.router, prefix="/template", tags=["用户端-视频模板"])
router.include_router(user_task.router, prefix="/task", tags=["用户端-生成任务"])
router.include_router(user_common.router, prefix="/base/common", tags=["用户端-公共接口"])
router.include_router(user_account.router, prefix="/account", tags=["用户端-账号"])
router.include_router(user_digital.router, prefix="/digital", tags=["用户端-数字人"])
router.include_router(user_payment.router, prefix="/payment", tags=["用户端-支付"])
router.include_router(user_feedback.router, prefix="/feedback", tags=["用户端-意见反馈"])
router.include_router(user_storyboard.router, prefix="/storyboard", tags=["用户端-分镜"])
