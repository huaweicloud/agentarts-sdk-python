"""
Test memory space operations
"""

import unittest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

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

from hw_agentrun_toolkit.operations.memory.space import (
    create_space,
    get_space,
    list_spaces,
    update_space,
    delete_space,
    _get_client,
)
from hw_agentrun_toolkit.operations.memory.models import SpaceResult, SpaceListResult


class TestGetClient(unittest.TestCase):
    """测试_get_client函数"""

    @patch('hw_agentrun_toolkit.operations.memory.space.MemoryClient')
    def test_get_client_without_region(self, mock_client_class):
        """测试没有提供region的情况"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        result = _get_client()
        
        # 验证MemoryClient被正确调用
        mock_client_class.assert_called_once_with()
        self.assertEqual(result, mock_client)

    @patch('hw_agentrun_toolkit.operations.memory.space.MemoryClient')
    def test_get_client_with_region(self, mock_client_class):
        """测试提供了region的情况"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        result = _get_client(region="cn-north-4")
        
        # 验证MemoryClient被正确调用，包含region参数
        mock_client_class.assert_called_once_with(region_name="cn-north-4")
        self.assertEqual(result, mock_client)


class TestCreateSpace(unittest.TestCase):
    """测试create_space函数"""

    def setUp(self):
        """设置测试环境"""
        self.mock_client = Mock()
        
    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_create_space_success(self, mock_get_client):
        """测试成功创建Space"""
        # 设置模拟的客户端和响应
        mock_get_client.return_value = self.mock_client
        self.mock_client.create_space.return_value = {
            "id": "space-123",
            "project_id": "proj-123",
            "name": "test-space"
        }
        
        # 调用函数
        result = create_space(
            project_id="proj-123",
            message_ttl_hours=168,
            tenant_vpc_id="vpc-123",
            tenant_subnet_id="subnet-123",
            api_key_id="key-123"
        )
        
        # 验证结果
        self.assertIsInstance(result, SpaceResult)
        self.assertTrue(result.success)
        self.assertEqual(result.space_id, "space-123")
        self.assertIsNotNone(result.space)
        self.assertIsNone(result.error)
        
        # 验证客户端调用
        self.mock_client.create_space.assert_called_once()

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_create_space_with_custom_parameters(self, mock_get_client):
        """测试创建Space时使用自定义参数"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.create_space.return_value = {"id": "space-456"}
        
        # 使用额外的参数
        result = create_space(
            project_id="proj-123",
            message_ttl_hours=336,
            enable_memory_extract=False,
            meta={"custom": "value"}
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.space_id, "space-456")
        
        # 验证传递的参数
        call_args = self.mock_client.create_space.call_args[0][0]  # 第一个参数是request
        self.assertEqual(call_args.project_id, "proj-123")
        self.assertEqual(call_args.message_ttl_hours, 336)
        self.assertFalse(call_args.enable_memory_extract)
        self.assertEqual(call_args.meta, {"custom": "value"})

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_create_space_failure(self, mock_get_client):
        """测试创建Space失败"""
        mock_get_client.return_value = self.mock_client
        # 模拟异常
        self.mock_client.create_space.side_effect = Exception("Invalid credentials")
        
        result = create_space(project_id="proj-123")
        
        # 验证结果
        self.assertIsInstance(result, SpaceResult)
        self.assertFalse(result.success)
        self.assertIsNone(result.space_id)
        self.assertIsNone(result.space)
        self.assertIsNotNone(result.error)
        self.assertIn("Invalid credentials", result.error)

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_create_space_with_region(self, mock_get_client):
        """测试创建Space时指定region"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.create_space.return_value = {"id": "space-789"}
        
        result = create_space(
            project_id="proj-123",
            region="cn-north-4"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.space_id, "space-789")
        
        # 验证_get_client被正确调用
        mock_get_client.assert_called_once_with(region="cn-north-4")

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_create_space_with_minimum_parameters(self, mock_get_client):
        """测试使用最少参数创建Space"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.create_space.return_value = {"id": "space-minimal"}
        
        result = create_space(project_id="proj-123")
        
        self.assertTrue(result.success)
        self.assertEqual(result.space_id, "space-minimal")
        
        # 验证使用默认值
        call_args = self.mock_client.create_space.call_args[0][0]
        self.assertEqual(call_args.project_id, "proj-123")
        self.assertEqual(call_args.message_ttl_hours, 168)  # 默认值


class TestGetSpace(unittest.TestCase):
    """测试get_space函数"""

    def setUp(self):
        """设置测试环境"""
        self.mock_client = Mock()
        
    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_get_space_success(self, mock_get_client):
        """测试成功获取Space"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.get_space.return_value = {
            "id": "space-123",
            "project_id": "proj-123",
            "name": "test-space",
            "status": "active"
        }
        
        result = get_space(space_id="space-123")
        
        self.assertTrue(result.success)
        self.assertEqual(result.space_id, "space-123")
        self.assertIsNotNone(result.space)
        self.assertEqual(result.space["name"], "test-space")

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_get_space_not_found(self, mock_get_client):
        """测试获取不存在的Space"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.get_space.side_effect = Exception("Space not found")
        
        result = get_space(space_id="nonexistent")
        
        self.assertFalse(result.success)
        self.assertEqual(result.space_id, "nonexistent")
        self.assertIsNone(result.space)
        self.assertIn("Space not found", result.error)

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_get_space_region(self, mock_get_client):
        """测试获取Space时指定region"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.get_space.return_value = {"id": "space-456"}
        
        result = get_space(
            space_id="space-456",
            region="cn-north-4"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.space_id, "space-456")
        
        # 验证_get_client被正确调用
        mock_get_client.assert_called_once_with(region="cn-north-4")


class TestListSpaces(unittest.TestCase):
    """测试list_spaces函数"""

    def setUp(self):
        """设置测试环境"""
        self.mock_client = Mock()
        
    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_list_spaces_success(self, mock_get_client):
        """测试成功列出Spaces"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.list_spaces.return_value = {
            "items": [
                {"id": "space-1", "name": "Space 1"},
                {"id": "space-2", "name": "Space 2"}
            ],
            "total": 2
        }
        
        result = list_spaces(project_id="proj-123")
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.spaces), 2)
        self.assertEqual(result.total, 2)
        self.assertEqual(result.spaces[0]["id"], "space-1")
        self.assertEqual(result.spaces[1]["id"], "space-2")

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_list_spaces_with_pagination(self, mock_get_client):
        """测试列出Spaces时使用分页"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.list_spaces.return_value = {
            "items": [
                {"id": "space-1", "name": "Space 1"},
                {"id": "space-2", "name": "Space 2"},
                {"id": "space-3", "name": "Space 3"}
            ],
            "total": 5
        }
        
        result = list_spaces(
            project_id="proj-123",
            limit=3,
            offset=1
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.spaces), 3)
        self.assertEqual(result.total, 5)
        
        # 验证客户端调用时的分页参数
        call_args = self.mock_client.list_spaces.call_args
        self.assertEqual(call_args[1]["limit"], 3)
        self.assertEqual(call_args[1]["offset"], 1)

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_list_spaces_empty_result(self, mock_get_client):
        """测试列出Spaces时返回空结果"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.list_spaces.return_value = {
            "items": [],
            "total": 0
        }
        
        result = list_spaces(project_id="proj-empty")
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.spaces), 0)
        self.assertEqual(result.total, 0)

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_list_spaces_failure(self, mock_get_client):
        """测试列出Spaces失败"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.list_spaces.side_effect = Exception("API Error")
        
        result = list_spaces(project_id="proj-123")
        
        self.assertFalse(result.success)
        self.assertEqual(len(result.spaces), 0)
        self.assertEqual(result.total, 0)
        self.assertIn("API Error", result.error)

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_list_spaces_region(self, mock_get_client):
        """测试列出Spaces时指定region"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.list_spaces.return_value = {"items": [], "total": 0}
        
        result = list_spaces(
            project_id="proj-123",
            region="cn-north-4"
        )
        
        self.assertTrue(result.success)
        mock_get_client.assert_called_once_with(region="cn-north-4")


class TestUpdateSpace(unittest.TestCase):
    """测试update_space函数"""

    def setUp(self):
        """设置测试环境"""
        self.mock_client = Mock()
        
    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_update_space_success(self, mock_get_client):
        """测试成功更新Space"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.update_space.return_value = {
            "id": "space-123",
            "message_ttl_hours": 336,
            "enable_memory_extract": False
        }
        
        result = update_space(
            space_id="space-123",
            message_ttl_hours=336,
            enable_memory_extract=False
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.space_id, "space-123")
        self.assertIsNotNone(result.space)
        self.assertEqual(result.space["message_ttl_hours"], 336)

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_update_space_partial_update(self, mock_get_client):
        """测试部分更新Space"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.update_space.return_value = {"id": "space-456"}
        
        result = update_space(
            space_id="space-456",
            enable_memory_extract=True
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.space_id, "space-456")
        
        # 验证只更新的字段
        call_args = self.mock_client.update_space.call_args[0][1]  # 第二个参数是request
        self.assertIsNone(call_args.message_ttl_hours)  # 未提供的字段为None
        self.assertTrue(call_args.enable_memory_extract)

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_update_space_failure(self, mock_get_client):
        """测试更新Space失败"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.update_space.side_effect = Exception("Update failed")
        
        result = update_space(space_id="space-error")
        
        self.assertFalse(result.success)
        self.assertEqual(result.space_id, "space-error")
        self.assertIsNone(result.space)
        self.assertIn("Update failed", result.error)

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_update_space_region(self, mock_get_client):
        """测试更新Space时指定region"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.update_space.return_value = {"id": "space-789"}
        
        result = update_space(
            space_id="space-789",
            region="cn-north-4"
        )
        
        self.assertTrue(result.success)
        mock_get_client.assert_called_once_with(region="cn-north-4")


class TestDeleteSpace(unittest.TestCase):
    """测试delete_space函数"""

    def setUp(self):
        """设置测试环境"""
        self.mock_client = Mock()
        
    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_delete_space_success(self, mock_get_client):
        """测试成功删除Space"""
        mock_get_client.return_value = self.mock_client
        
        result = delete_space(space_id="space-123")
        
        self.assertTrue(result.success)
        self.assertEqual(result.space_id, "space-123")
        self.assertIsNone(result.space)
        self.assertIsNone(result.error)
        
        # 验证删除被调用
        self.mock_client.delete_space.assert_called_once_with("space-123")

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_delete_space_failure(self, mock_get_client):
        """测试删除Space失败"""
        mock_get_client.return_value = self.mock_client
        self.mock_client.delete_space.side_effect = Exception("Delete failed")
        
        result = delete_space(space_id="space-error")
        
        self.assertFalse(result.success)
        self.assertEqual(result.space_id, "space-error")
        self.assertIsNone(result.space)
        self.assertIn("Delete failed", result.error)

    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_delete_space_region(self, mock_get_client):
        """测试删除Space时指定region"""
        mock_get_client.return_value = self.mock_client
        
        result = delete_space(
            space_id="space-456",
            region="cn-north-4"
        )
        
        self.assertTrue(result.success)
        mock_get_client.assert_called_once_with(region="cn-north-4")


class TestIntegration(unittest.TestCase):
    """测试整个的操作流程"""

    def setUp(self):
        """设置测试环境"""
        self.mock_client = Mock()
        
    @patch('hw_agentrun_toolkit.operations.memory.space._get_client')
    def test_full_space_lifecycle(self, mock_get_client):
        """测试完整的Space生命周期"""
        mock_get_client.return_value = self.mock_client
        
        # 模拟不同操作的响应
        self.mock_client.create_space.return_value = {"id": "new-space-123"}
        self.mock_client.get_space.return_value = {"id": "existing-space-123", "name": "Test Space"}
        self.mock_client.list_spaces.return_value = {
            "items": [{"id": "space-1"}, {"id": "space-2"}],
            "total": 2
        }
        self.mock_client.update_space.return_value = {"id": "existing-space-123", "status": "updated"}
        
        # 创建Space
        create_result = create_space(project_id="proj-123")
        self.assertTrue(create_result.success)
        self.assertEqual(create_result.space_id, "new-space-123")
        
        # 获取Space
        get_result = get_space(space_id="existing-space-123")
        self.assertTrue(get_result.success)
        self.assertEqual(get_result.space["name"], "Test Space")
        
        # 列出Spaces
        list_result = list_spaces(project_id="proj-123")
        self.assertTrue(list_result.success)
        self.assertEqual(len(list_result.spaces), 2)
        
        # 更新Space
        update_result = update_space(
            space_id="existing-space-123",
            enable_memory_extract=True
        )
        self.assertTrue(update_result.success)
        
        # 删除Space
        delete_result = delete_space(space_id="existing-space-123")
        self.assertTrue(delete_result.success)


if __name__ == "__main__":
    unittest.main(verbosity=2)
