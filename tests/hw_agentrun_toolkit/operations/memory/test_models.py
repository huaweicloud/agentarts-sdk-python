"""
Test memory operation models
"""

import unittest
import sys
import os
from pathlib import Path
from unittest.mock import Mock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

# Mock huaweicloudsdkcore 模块
sys.modules['huaweicloudsdkcore'] = Mock()
sys.modules['huaweicloudsdkcore.auth'] = Mock()
sys.modules['huaweicloudsdkcore.auth.credentials'] = Mock()
sys.modules['huaweicloudsdkcore.auth.provider'] = Mock()
sys.modules['huaweicloudsdkcore.http'] = Mock()
sys.modules['huaweicloudsdkcore.http.http_config'] = Mock()
sys.modules['huaweicloudsdkcore.sdk_request'] = Mock()

# Mock requests 模块
sys.modules['requests'] = Mock()

from hw_agentrun_toolkit.operations.memory.models import SpaceResult, SpaceListResult


class TestSpaceResult(unittest.TestCase):
    """测试SpaceResult模型"""

    def test_successful_result(self):
        """测试成功的结果"""
        result = SpaceResult(
            success=True,
            space_id="space-123",
            space={"id": "space-123", "name": "test-space"}
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.space_id, "space-123")
        self.assertEqual(result.space["id"], "space-123")
        self.assertIsNone(result.error)

    def test_failed_result(self):
        """测试失败的结果"""
        error_msg = "Failed to create space"
        result = SpaceResult(
            success=False,
            error=error_msg
        )
        
        self.assertFalse(result.success)
        self.assertIsNone(result.space_id)
        self.assertIsNone(result.space)
        self.assertEqual(result.error, error_msg)

    def test_result_with_all_fields(self):
        """测试包含所有字段的结果"""
        space_data = {
            "id": "space-123",
            "name": "test-space",
            "project_id": "proj-123",
            "status": "active"
        }
        result = SpaceResult(
            success=True,
            space_id="space-123",
            space=space_data,
            error=None
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.space_id, "space-123")
        self.assertEqual(result.space, space_data)

    def test_result_minimal(self):
        """测试最小化的结果"""
        # 只提供必填字段
        result = SpaceResult(success=True)
        
        self.assertTrue(result.success)
        self.assertIsNone(result.space_id)
        self.assertIsNone(result.space)
        self.assertIsNone(result.error)


class TestSpaceListResult(unittest.TestCase):
    """测试SpaceListResult模型"""

    def test_successful_list_result(self):
        """测试成功的列表结果"""
        spaces = [
            {"id": "space-1", "name": "Space 1"},
            {"id": "space-2", "name": "Space 2"}
        ]
        
        result = SpaceListResult(
            success=True,
            spaces=spaces,
            total=2
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.spaces), 2)
        self.assertEqual(result.total, 2)
        self.assertIsNone(result.error)

    def test_failed_list_result(self):
        """测试失败的列表结果"""
        error_msg = "Failed to list spaces"
        result = SpaceListResult(
            success=False,
            error=error_msg
        )
        
        self.assertFalse(result.success)
        self.assertEqual(len(result.spaces), 0)
        self.assertEqual(result.total, 0)
        self.assertEqual(result.error, error_msg)

    def test_list_result_with_defaults(self):
        """测试使用默认值的列表结果"""
        # 不提供spaces和total，使用默认值
        result = SpaceListResult(success=True)
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.spaces), 0)
        self.assertEqual(result.total, 0)

    def test_list_result_with_partial_data(self):
        """测试部分数据的列表结果"""
        spaces = [{"id": "space-1", "name": "Space 1"}]
        
        # 只提供spaces，不提供total（使用默认值）
        result = SpaceListResult(
            success=True,
            spaces=spaces
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.spaces), 1)
        self.assertEqual(result.total, 0)  # 默认值为0

    def test_list_result_custom_total(self):
        """测试自定义总数的列表结果"""
        spaces = [
            {"id": "space-1", "name": "Space 1"},
            {"id": "space-2", "name": "Space 2"},
            {"id": "space-3", "name": "Space 3"}
        ]
        
        # 提供的spaces数量3，但total为5（表示还有更多结果）
        result = SpaceListResult(
            success=True,
            spaces=spaces,
            total=5
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.spaces), 3)
        self.assertEqual(result.total, 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
