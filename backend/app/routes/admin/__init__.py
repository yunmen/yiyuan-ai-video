from fastapi import APIRouter
from app.enums.base import ClientRoleEnum

from app.routes.admin.base import auth
from app.routes.admin.base import myself
from app.routes.admin.base import common as base_common
from app.routes.admin.system import log as system_log
from app.routes.admin.system import task as system_task
from app.routes.admin.system import monitor as system_monitor
from app.routes.admin.system import cache as system_cache
from app.routes.admin.system import menu as system_menu
from app.routes.admin.system import user as system_user
from app.routes.admin.system import dept as system_dept
from app.routes.admin.system import role as system_role
from app.routes.admin import video_template as admin_video_template
from app.routes.admin import video_category as admin_video_category
from app.routes.admin import credit as admin_credit
from app.routes.admin import generate_task as admin_generate_task
from app.routes.admin import digital as admin_digital
from app.routes.admin import payment as admin_payment
from app.routes.admin.system import config as system_config


router = APIRouter(prefix=f"/{ClientRoleEnum.ADMIN.value}/v1")

router.include_router(auth.router, prefix="/base/auth", tags=["授权管理"])
router.include_router(myself.router, prefix="/base/myself", tags=["个人中心"])
router.include_router(base_common.router, prefix="/base/common", tags=["公共接口"])
router.include_router(system_menu.router, prefix="/system/menu", tags=["系统管理-菜单管理"])
router.include_router(system_user.router, prefix="/system/user", tags=["系统管理-用户管理"])
router.include_router(system_dept.router, prefix="/system/dept", tags=["系统管理-部门管理"])
router.include_router(system_role.router, prefix="/system/role", tags=["系统管理-角色管理"])
router.include_router(system_log.router, prefix="/system/log", tags=["系统监控-日志管理"])
router.include_router(system_task.router, prefix="/system/task", tags=["系统监控-任务管理"])
router.include_router(system_monitor.router, prefix="/system/monitor", tags=["系统监控-系统信息"])
router.include_router(system_cache.router, prefix="/system/cache", tags=["系统监控-缓存数据"])
router.include_router(admin_video_template.router, prefix="/video/template", tags=["业务管理-视频模板"])
router.include_router(admin_video_category.router, prefix="/video/category", tags=["业务管理-模板分类"])
router.include_router(admin_credit.router, prefix="/credit", tags=["业务管理-用户额度"])
router.include_router(admin_generate_task.router, prefix="/video/task", tags=["业务管理-生成任务"])
router.include_router(admin_digital.router, prefix="/video/digital", tags=["业务管理-数字人"])
router.include_router(admin_payment.router, prefix="/payment", tags=["业务管理-支付订单"])
router.include_router(system_config.router, prefix="/system/config", tags=["系统管理-业务配置"])
