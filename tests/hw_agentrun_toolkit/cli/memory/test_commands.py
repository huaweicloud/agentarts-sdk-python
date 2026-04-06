"""
Test memory CLI commands
"""

import unittest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
import json

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

from hw_agentrun_toolkit.cli.memory import commands
from hw_agentrun_toolkit.operations.memory import (
    create_space,
    delete_space,
    get_space,
    list_spaces,
    update_space,
    SpaceResult,
    SpaceListResult,
)


class TestCreateSpaceCommand(unittest.TestCase):
    """测试create_space_cmd命令"""

    def setUp(self):
        """设置测试环境"""
        self.cli_app = commands.memory_app
        self.output = StringIO()

    def tearDown(self):
        """清理测试环境"""
        self.output.close()

    @patch('hw_agentrun_toolkit.cli.memory.commands.create_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print')
    def test_create_space_success_table(self, mock_print, mock_create_space):
        """测试成功创建Space (table输出)"""
        # 模拟创建Space成功
        mock_result = SpaceResult(
            success=True,
            space_id="space-123",
            space={"id": "space-123", "status": "active"}
        )
        mock_create_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["create", "--project-id", "proj-123"])

        # 验证
        mock_create_space.assert_called_once()
        mock_print.assert_called()
        calls = mock_print.call_args_list
        # 检查是否有成功的消息输出
        print_calls = [call for call in calls if call[0] and 'created successfully' in str(call[0])]

    @patch('hw_agentrun_toolkit.cli.memory.commands.create_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print_json')
    def test_create_space_success_json(self, mock_print_json, mock_create_space):
        """测试成功创建Space (JSON输出)"""
        # 模拟创建Space成功
        mock_result = SpaceResult(
            success=True,
            space_id="space-123",
            space={"id": "space-123", "project_id": "proj-123"}
        )
        mock_create_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["create", "--project-id", "proj-123", "--output", "json"])

        # 验证JSON输出
        mock_print_json.assert_called_once()
        called_data = mock_print_json.call_args[0][0]
        called_dict = json.loads(called_data)
        self.assertEqual(called_dict["id"], "space-123")

    @patch('hw_agentrun_toolkit.cli.memory.commands.create_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands._handle_error')
    def test_create_space_failure(self, mock_handle_error, mock_create_space):
        """测试创建Space失败"""
        # 模拟创建Space失败
        mock_result = SpaceResult(success=False, error="Invalid project ID")
        mock_create_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["create", "--project-id", "proj-error"])

        # 验证错误处理
        mock_handle_error.assert_called_once_with("Failed to create space: Invalid project ID")

    @patch('hw_agentrun_toolkit.cli.memory.commands.create_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print')
    def test_create_space_with_all_params(self, mock_print, mock_create_space):
        """测试创建Space时使用所有参数"""
        mock_result = SpaceResult(
            success=True,
            space_id="space-full",
            space={"id": "space-full"}
        )
        mock_create_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app([
            "create",
            "--project-id", "proj-123",
            "--ttl", "336",
            "--vpc-id", "vpc-456",
            "--subnet-id", "subnet-789",
            "--api-key-id", "key-123",
            "--region", "cn-north-4",
            "--output", "table"
        ])

        # 验证所有参数都被传递
        call_args = mock_create_space.call_args[1]
        self.assertEqual(call_args["project_id"], "proj-123")
        self.assertEqual(call_args["message_ttl_hours"], 336)
        self.assertEqual(call_args["tenant_vpc_id"], "vpc-456")
        self.assertEqual(call_args["tenant_subnet_id"], "subnet-789")
        self.assertEqual(call_args["api_key_id"], "key-123")
        self.assertEqual(call_args["region"], "cn-north-4")

    def test_create_space_invalid_ttl(self):
        """测试创建Space时提供无效的TTL值"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["create", "--project-id", "proj-123", "--ttl", "0"])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Message TTL must be greater than 0 hours")

    def test_create_space_empty_project_id(self):
        """测试创建Space时提供空的project ID"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["create", "--project-id", ""])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Project ID cannot be empty")

    def test_create_space_whitespace_project_id(self):
        """测试创建Space时提供只有空格的project ID"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["create", "--project-id", "   "])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Project ID cannot be empty")


class TestGetSpaceCommand(unittest.TestCase):
    """测试get_space_cmd命令"""

    def setUp(self):
        """设置测试环境"""
        self.cli_app = commands.memory_app
        self.output = StringIO()

    @patch('hw_agentrun_toolkit.cli.memory.commands.get_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print')
    def test_get_space_success_table(self, mock_print, mock_get_space):
        """测试成功获取Space (table输出)"""
        # 模拟获取Space成功
        mock_result = SpaceResult(
            success=True,
            space={"id": "space-123", "project_id": "proj-123", "status": "active"}
        )
        mock_get_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["get", "space-123"])

        # 验证Print被调用
        mock_print.assert_called()

    @patch('hw_agentrun_toolkit.cli.memory.commands.get_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print_json')
    def test_get_space_success_json(self, mock_print_json, mock_get_space):
        """测试成功获取Space (JSON输出)"""
        # 模拟获取Space成功
        mock_result = SpaceResult(
            success=True,
            space={"id": "space-123", "project_id": "proj-123"}
        )
        mock_get_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["get", "space-123", "--output", "json"])

        # 验证JSON输出
        mock_print_json.assert_called_once()

    @patch('hw_agentrun_toolkit.cli.memory.commands.get_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands._handle_error')
    def test_get_space_failure(self, mock_handle_error, mock_get_space):
        """测试获取Space失败"""
        # 模拟获取Space失败
        mock_result = SpaceResult(success=False, error="Space not found")
        mock_get_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["get", "nonexistent"])

        # 验证错误处理
        mock_handle_error.assert_called_once_with("Failed to get space: Space not found")

    @patch('hw_agentrun_toolkit.cli.memory.commands.get_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print')
    def test_get_space_with_region(self, mock_print, mock_get_space):
        """测试获取Space时指定region"""
        mock_result = SpaceResult(
            success=True,
            space={"id": "space-123"}
        )
        mock_get_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["get", "space-123", "--region", "cn-north-4"])

        # 验证region参数被传递
        call_args = mock_get_space.call_args[1]
        self.assertEqual(call_args["region"], "cn-north-4")

    def test_get_space_empty_space_id(self):
        """测试获取Space时提供空的space ID"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["get", ""])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Space ID cannot be empty")

    def test_get_space_whitespace_space_id(self):
        """测试获取Space时提供只有空格的space ID"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["get", "   "])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Space ID cannot be empty")


class TestListSpacesCommand(unittest.TestCase):
    """测试list_spaces_cmd命令"""

    def setUp(self):
        """设置测试环境"""
        self.cli_app = commands.memory_app

    @patch('hw_agentrun_toolkit.cli.memory.commands.list_spaces')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print')
    def test_list_spaces_success_table(self, mock_print, mock_list_spaces):
        """测试成功列出Spaces (table输出)"""
        # 模拟列出Spaces成功
        mock_result = SpaceListResult(
            success=True,
            spaces=[
                {"id": "space-1", "project_id": "proj-1", "status": "active"},
                {"id": "space-2", "project_id": "proj-2", "status": "inactive"}
            ],
            total=2
        )
        mock_list_spaces.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["list", "--project-id", "proj-123"])

        # 验证Print被调用
        mock_print.assert_called()

    @patch('hw_agentrun_toolkit.cli.memory.commands.list_spaces')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print_json')
    def test_list_spaces_success_json(self, mock_print_json, mock_list_spaces):
        """测试成功列出Spaces (JSON输出)"""
        # 模拟列出Spaces成功
        mock_result = SpaceListResult(
            success=True,
            spaces=[
                {"id": "space-1", "project_id": "proj-1"}
            ],
            total=1
        )
        mock_list_spaces.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["list", "--project-id", "proj-123", "--output", "json"])

        # 验证JSON输出
        mock_print_json.assert_called_once()
        called_data = mock_print_json.call_args[0][0]
        called_dict = json.loads(called_data)
        self.assertEqual(called_dict["total"], 1)

    @patch('hw_agentrun_toolkit.cli.memory.commands.list_spaces')
    @patch('hw_agentrun_toolkit.cli.memory.commands._handle_error')
    def test_list_spaces_failure(self, mock_handle_error, mock_list_spaces):
        """测试列出Spaces失败"""
        # 模拟列出Spaces失败
        mock_result = SpaceListResult(success=False, error="API Error")
        mock_list_spaces.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["list", "--project-id", "proj-error"])

        # 验证错误处理
        mock_handle_error.assert_called_once_with("Failed to list spaces: API Error")

    @patch('hw_agentrun_toolkit.cli.memory.commands.list_spaces')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print')
    def test_list_spaces_with_pagination(self, mock_print, mock_list_spaces):
        """测试列出Spaces时使用分页"""
        mock_result = SpaceListResult(
            success=True,
            spaces=[{"id": "space-1"}],
            total=5
        )
        mock_list_spaces.return_value = mock_result

        # 调用CLI命令
        self.cli_app([
            "list",
            "--project-id", "proj-123",
            "--limit", "10",
            "--offset", "5"
        ])

        # 验证分页参数被传递
        call_args = mock_list_spaces.call_args[1]
        self.assertEqual(call_args["limit"], 10)
        self.assertEqual(call_args["offset"], 5)

    def test_list_spaces_invalid_limit(self):
        """测试列出Spaces时提供无效的limit值"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["list", "--project-id", "proj-123", "--limit", "0"])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Limit must be greater than 0")

    def test_list_spaces_invalid_offset(self):
        """测试列出Spaces时提供无效的offset值"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["list", "--project-id", "proj-123", "--offset", "-1"])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Offset must be greater than or equal to 0")

    def test_list_spaces_limit_too_high(self):
        """测试列出Spaces时limit超过最大值"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["list", "--project-id", "proj-123", "--limit", "101"])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Limit cannot exceed 100")

    def test_list_spaces_empty_project_id(self):
        """测试列出Spaces时提供空的project ID"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["list", "--project-id", ""])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Project ID cannot be empty")


class TestUpdateSpaceCommand(unittest.TestCase):
    """测试update_space_cmd命令"""

    def setUp(self):
        """设置测试环境"""
        self.cli_app = commands.memory_app

    @patch('hw_agentrun_toolkit.cli.memory.commands.update_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print')
    def test_update_space_success_ttl(self, mock_print, mock_update_space):
        """测试成功更新Space的TTL"""
        # 模拟更新Space成功
        mock_result = SpaceResult(
            success=True,
            space={"id": "space-123", "message_ttl_hours": 336}
        )
        mock_update_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["update", "space-123", "--ttl", "336"])

        # 验证更新被调用
        mock_update_space.assert_called_once()
        call_args = mock_update_space.call_args[1]
        self.assertEqual(call_args["space_id"], "space-123")
        self.assertEqual(call_args["message_ttl_hours"], 336)

    @patch('hw_agentrun_toolkit.cli.memory.commands.update_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print')
    def test_update_space_success_memory_extract(self, mock_print, mock_update_space):
        """测试成功更新Space的memory extract设置"""
        # 模拟更新Space成功
        mock_result = SpaceResult(
            success=True,
            space={"id": "space-123", "enable_memory_extract": True}
        )
        mock_update_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["update", "space-123", "--enable-extract"])

        # 验证更新被调用
        mock_update_space.assert_called_once()
        call_args = mock_update_space.call_args[1]
        self.assertEqual(call_args["space_id"], "space-123")
        self.assertTrue(call_args["enable_memory_extract"])

    @patch('hw_agentrun_toolkit.cli.memory.commands.update_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print_json')
    def test_update_space_success_json(self, mock_print_json, mock_update_space):
        """测试成功更新Space (JSON输出)"""
        # 模拟更新Space成功
        mock_result = SpaceResult(
            success=True,
            space={"id": "space-123", "message_ttl_hours": 720}
        )
        mock_update_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["update", "space-123", "--ttl", "720", "--output", "json"])

        # 验证JSON输出
        mock_print_json.assert_called_once()

    @patch('hw_agentrun_toolkit.cli.memory.commands.update_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands._handle_error')
    def test_update_space_failure(self, mock_handle_error, mock_update_space):
        """测试更新Space失败"""
        # 模拟更新Space失败
        mock_result = SpaceResult(success=False, error="Invalid space ID")
        mock_update_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["update", "nonexistent", "--ttl", "336"])

        # 验证错误处理
        mock_handle_error.assert_called_once_with("Failed to update space: Invalid space ID")

    def test_update_space_no_params(self):
        """测试更新Space时不提供任何参数"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["update", "space-123"])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with(
                "At least one update parameter must be provided (--ttl or --enable-extract)"
            )

    def test_update_space_invalid_ttl(self):
        """测试更新Space时提供无效的TTL值"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["update", "space-123", "--ttl", "0"])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Message TTL must be greater than 0 hours")

    def test_update_space_empty_space_id(self):
        """测试更新Space时提供空的space ID"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["update", "", "--ttl", "336"])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Space ID cannot be empty")

    def test_update_space_whitespace_space_id(self):
        """测试更新Space时提供只有空格的space ID"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["update", "   ", "--ttl", "336"])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Space ID cannot be empty")


class TestDeleteSpaceCommand(unittest.TestCase):
    """测试delete_space_cmd命令"""

    def setUp(self):
        """设置测试环境"""
        self.cli_app = commands.memory_app

    @patch('hw_agentrun_toolkit.cli.memory.commands.delete_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print')
    @patch('typer.confirm')
    def test_delete_space_success_force(self, mock_confirm, mock_print, mock_delete_space):
        """测试成功删除Space (强制删除)"""
        # 模拟删除Space成功
        mock_result = SpaceResult(success=True, space_id="space-123")
        mock_delete_space.return_value = mock_result

        # 调用CLI命令 (force)
        self.cli_app(["delete", "space-123", "--force"])

        # 验证删除被调用
        mock_delete_space.assert_called_once_with(space_id="space-123")
        # 验证确认未被调用 (因为使用了force)
        mock_confirm.assert_not_called()
        # 验证成功消息被打印
        mock_print.assert_called()

    @patch('hw_agentrun_toolkit.cli.memory.commands.delete_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print')
    @patch('typer.confirm', return_value=False)
    def test_delete_space_cancelled(self, mock_confirm, mock_print, mock_delete_space):
        """测试取消删除Space"""
        # 调用CLI命令 (用户取消)
        self.cli_app(["delete", "space-123"])

        # 验证删除未被调用
        mock_delete_space.assert_not_called()
        # 验证确认被调用
        mock_confirm.assert_called_once()
        # 验证取消消息被打印
        mock_print.assert_called_with("[yellow]Deletion cancelled.[/yellow]")

    @patch('hw_agentrun_toolkit.cli.memory.commands.delete_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands._handle_error')
    def test_delete_space_failure(self, mock_handle_error, mock_delete_space):
        """测试删除Space失败"""
        # 模拟删除Space失败
        mock_result = SpaceResult(success=False, error="Delete failed")
        mock_delete_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["delete", "space-error"])

        # 验证错误处理
        mock_handle_error.assert_called_once_with("Failed to delete space: Delete failed")

    def test_delete_space_empty_space_id(self):
        """测试删除Space时提供空的space ID"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["delete", ""])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Space ID cannot be empty")

    def test_delete_space_whitespace_space_id(self):
        """测试删除Space时提供只有空格的space ID"""
        with patch('hw_agentrun_toolkit.cli.memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["delete", "   "])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Space ID cannot be empty")


class TestSpaceStatusCommand(unittest.TestCase):
    """测试space_status_cmd命令"""

    def setUp(self):
        """设置测试环境"""
        self.cli_app = commands.memory_app

    @patch('hw_agentrun_toolkit.cli.memory.commands.get_space')
    @patch('hw_agentrun_toolkit.cli.memory.commands.console.print')
    def test_space_status_success_table(self, mock_print, mock_get_space):
        """测试成功获取Space状态 (table输出)"""
        # 模拟获取Space成功
        mock_result = SpaceResult(
            success=True,
            space={
                "id": "space-123",
                "status": "active",
                "message_ttl_hours": 168,
                "enable_memory_extract": True,
                "project_id": "proj-123",
                "created_at": "2023-01-01"
            }
        )
        mock_get_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["status", "space-123"])

        # 验证Print被调用
        mock_print.assert_called()

    @patch('hw_agentrun_toolkit.cli_memory.commands.get_space')
    @patch('hw_agentrun_toolkit.cli_memory.commands.console.print_json')
    def test_space_status_success_json(self, mock_print_json, mock_get_space):
        """测试成功获取Space状态 (JSON输出)"""
        # 模拟获取Space成功
        mock_result = SpaceResult(
            success=True,
            space={
                "id": "space-123",
                "status": "active",
                "message_ttl_hours": 168,
                "enable_memory_extract": True,
                "project_id": "proj-123",
                "created_at": "2023-01-01"
            }
        )
        mock_get_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["status", "space-123", "--output", "json"])

        # 验证JSON输出
        mock_print_json.assert_called_once()

    @patch('hw_agentrun_toolkit.cli_memory.commands.get_space')
    @patch('hw_agentrun_toolkit.cli_memory.commands/console.print')
    def test_space_status_warning(self, mock_print, mock_get_space):
        """测试获取Space状态显示警告信息"""
        # 模拟获取Space成功，但TTL较低应该显示警告
        mock_result = SpaceResult(
            success=True,
            space={
                "id": "space-123",
                "status": "active",
                "message_ttl_hours": 12,  # 低TTL
                "enable_memory_extract": False,
                "project_id": "proj-123",
                "created_at": "2023-01-01"
            }
        )
        mock_get_space.return_value = mock_result

        # 调用CLI命令
        self.cli_app(["status", "space-123"])

        # 验证Print被调用
        mock_print.assert_called()
        # 检查警告信息是否被打印 (通过检查输出内容)
        warning_printed = any(
            call and 'Warning: Message TTL is low' in str(call)
            for call in mock_print.call_args_list
        )
        self.assertTrue(warning_printed)

    def test_space_status_empty_space_id(self):
        """测试获取Space状态时提供空的space ID"""
        with patch('hw_agentrun_toolkit.cli_memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["status", ""])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Space ID cannot be empty")

    def test_space_status_whitespace_space_id(self):
        """测试获取Space状态时提供只有空格的space ID"""
        with patch('hw_agentrun_toolkit.cli_memory.commands._handle_error') as mock_handle_error:
            self.cli_app(["status", "   "])
            
            # 验证错误处理被调用
            mock_handle_error.assert_called_once_with("Space ID cannot be empty")


class TestIntegration(unittest.TestCase):
    """测试整个CLI工具的集成"""

    def setUp(self):
        """设置测试环境"""
        self.cli_app = commands.memory_app

    def test_cli_complete_lifecycle(self):
        """测试完整的Space生命周期CLI操作"""
        # 切换Mock到不同的函数
        create_result = SpaceResult(
            success=True,
            space_id="test-space-cli",
            space={"id": "test-space-cli", "status": "active"}
        )
        get_result = SpaceResult(
            success=True,
            space={"id": "test-space-cli", "project_id": "proj-test", "status": "active"}
        )
        list_result = SpaceListResult(
            success=True,
            spaces=[{"id": "test-space-cli", "project_id": "proj-test", "status": "active"}],
            total=1
        )
        update_result = SpaceResult(
            success=True,
            space={"id": "test-space-cli", "message_ttl_hours": 720}
        )
        delete_result = SpaceResult(success=True, space_id="test-space-cli")

        with patch('hw_agentrun_toolkit.cli.memory.commands.create_space', return_value=create_result), \
             patch('hw_agentrun_toolkit.cli.memory.commands.get_space', return_value=get_result), \
             patch('hw_agentrun_toolkit.cli.memory.commands.list_spaces', return_value=list_result), \
             patch('hw_agentrun_toolkit.cli.memory.commands.update_space', return_value=update_result), \
             patch('hw_agentrun_toolkit.cli.memory.commands.delete_space', return_value=delete_result):
            
            # 创建Space
            self.cli_app(["create", "--project-id", "proj-test", "--output", "json"])
            
            # 获取Space
            self.cli_app(["get", "test-space-cli", "--output", "json"])
            
            # 列出Spaces
            self.cli_app(["list", "--project-id", "proj-test", "--output", "json"])
            
            # 更新Space
            self.cli_app(["update", "test-space-cli", "--ttl", "720", "--output", "json"])
            
            # 检查Space状态
            self.cli_app(["status", "test-space-cli", "--output", "json"])
            
            # 删除Space
            self.cli_app(["delete", "test-space-cli", "--force"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
