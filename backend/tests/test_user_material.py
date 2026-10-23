"""素材归属校验不依赖数据库的安全回归。"""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.exceptions import HTTPException
from app.services.user_material import material_key, validate_owner


class UserMaterialTest(unittest.TestCase):
    """公开地址、其他账号、删除记录都不能被认领。"""

    def test_exact_owner_and_active_record(self):
        """仅当前用户有效台账可用，地址和资源类型必须一致。"""
        record = SimpleNamespace(deleted=False, meta={"user_id": 1, "status": "ready"},
                                 content="/uploads/a.jpg", asset_type="uploaded_material")
        self.assertEqual(validate_owner(record, 1, record.content)["status"], "ready")
        for user_id, url in [(2, record.content), (1, "https://other/a.jpg")]:
            with self.assertRaises(HTTPException):
                validate_owner(record, user_id, url)
        record.deleted = True
        with self.assertRaises(HTTPException):
            validate_owner(record, 1, record.content)
        with self.assertRaises(HTTPException):
            validate_owner(None, 1, record.content)
        self.assertEqual(len(material_key(record.content)), 64)
        self.assertNotEqual(material_key(record.content), material_key("/uploads/b.jpg"))


class ClassificationTest(unittest.TestCase):
    def test_auto_unknown_conflict_and_user_resolution(self):
        from app.services.user_material import material_classification
        for url, filename, expected in [("/A.JPG?token=1", "图片.jpg", "image"), ("/a.MP4", "video.mov", "video")]:
            result = material_classification(url, {"filename": filename})
            self.assertEqual(result["kind"], expected)
            self.assertFalse(result["needs_confirmation"])
        for url, filename, reason in [("/a.bin", "a.bin", "unknown"), ("/a.jpg", "a.mp4", "conflict"), ("/a.mp4", "无后缀", "unknown")]:
            result = material_classification(url, {"filename": filename})
            self.assertIsNone(result["kind"])
            self.assertTrue(result["needs_confirmation"])
            self.assertEqual(result["classification_reason"], reason)
            result = material_classification(url, {"filename": filename, "user_kind": "video"})
            self.assertEqual(result["kind"], "video")
            self.assertFalse(result["needs_confirmation"])


class MaterialTypeTest(unittest.IsolatedAsyncioTestCase):
    async def test_mark_owner_ready_and_format(self):
        from app.services.user_material import mark_material_type
        record = SimpleNamespace(deleted=False, meta={"user_id": 1, "status": "ready"},
                                 content="/uploads/a.mp4", asset_type="uploaded_material", save=AsyncMock())
        with patch("app.models.asset_cache.GenAssetCacheModel.filter") as query:
            query.return_value.first = AsyncMock(return_value=record)
            for user_id, kind in [(2, "video"), (1, "image")]:
                with self.assertRaises(HTTPException):
                    await mark_material_type(user_id, record.content, kind)
            record.save.assert_not_awaited()
            result = await mark_material_type(1, record.content, "video")
            self.assertEqual(result["kind"], "video")
            self.assertEqual(record.meta["user_kind"], "video")
            record.save.assert_awaited_once()
            record.meta["filename"] = "冲突.jpg"
            result = await mark_material_type(1, record.content, "image")
            self.assertEqual(result["kind"], "image")
            self.assertFalse(result["needs_confirmation"])
            record.content = "/uploads/unknown"
            result = await mark_material_type(1, record.content, "video")
            self.assertEqual(result["classification_source"], "user")
            record.meta["status"] = "pending"
            with self.assertRaises(HTTPException):
                await mark_material_type(1, record.content, "video")


class MaterialRoleTest(unittest.IsolatedAsyncioTestCase):
    async def test_user_role_preserves_type_and_enforces_owner(self):
        from app.services.user_material import mark_material_role
        record = SimpleNamespace(deleted=False, meta={"user_id": 1, "status": "ready", "filename": "a.jpg"},
                                 content="/uploads/a.jpg", asset_type="uploaded_material", save=AsyncMock())
        with patch("app.models.asset_cache.GenAssetCacheModel.filter") as query:
            query.return_value.first = AsyncMock(return_value=record)
            for user_id, role in [(2, "person"), (1, "image")]:
                with self.assertRaises(HTTPException):
                    await mark_material_role(user_id, record.content, role)
            record.save.assert_not_awaited()
            for role in ["person", "scene", "product", None]:
                result = await mark_material_role(1, record.content, role)
                self.assertEqual(result["role"], role)
                self.assertEqual(record.meta["role"], role)
                self.assertEqual(result["kind"], "image")
                self.assertEqual(record.meta["filename"], "a.jpg")
            record.meta["status"] = "pending"
            with self.assertRaises(HTTPException):
                await mark_material_role(1, record.content, "person")
            record.deleted = True
            with self.assertRaises(HTTPException):
                await mark_material_role(1, record.content, "person")


if __name__ == "__main__":
    unittest.main()
