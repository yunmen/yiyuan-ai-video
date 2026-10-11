"""素材归属校验不依赖数据库的安全回归。"""
import unittest
from types import SimpleNamespace

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


if __name__ == "__main__":
    unittest.main()
