"""用户上传素材的分页与直传确认参数。"""
from typing import Literal
from pydantic import BaseModel, Field
from app.schemas.base import BaseQuerySchema


class MaterialQuerySchema(BaseQuerySchema):
    """限制分页大小，筛选图片或视频。"""
    pageNum: int = Field(1, ge=1, description="页码")
    pageSize: int = Field(20, ge=1, le=50, description="每页条数")
    kind: Literal["all", "image", "video", "pending"] = Field("all", description="素材类型")


class ConfirmMaterialSchema(BaseModel):
    """地址必须已由服务器为当前用户签发，不能认领任意远程文件。"""
    url: str = Field(..., min_length=1, max_length=2048, description="本次上传的服务端素材地址")


class MaterialRoleSchema(ConfirmMaterialSchema):
    role: Literal["person", "scene", "product"] | None = Field(..., description="用户标记的素材用途，null 清除标记")


class MaterialTypeSchema(ConfirmMaterialSchema):
    kind: Literal["image", "video"] = Field(..., description="用户确认的素材类型")


class MaterialSyncSchema(BaseModel):
    """按游标分批核验早期已签发、尚未确认的本人上传。"""
    cursor: int = Field(0, ge=0, description="上一批最后检查的记录Id")
