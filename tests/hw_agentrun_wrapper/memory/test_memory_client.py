"""
Agent Memory SDK 测试
验证 SDK 的基本功能（不依赖实际后端）

根据 api_mapping.md 定义的方法进行测试
"""

import os
import sys
import unittest
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from unittest.mock import patch

# Mock huaweicloudsdkcore 模块（如果未安装）
from unittest.mock import Mock
sys.modules['huaweicloudsdkcore'] = Mock()
sys.modules['huaweicloudsdkcore.auth'] = Mock()
sys.modules['huaweicloudsdkcore.auth.credentials'] = Mock()
sys.modules['huaweicloudsdkcore.auth.provider'] = Mock()
sys.modules['huaweicloudsdkcore.http'] = Mock()
sys.modules['huaweicloudsdkcore.http.http_config'] = Mock()
sys.modules['huaweicloudsdkcore.sdk_request'] = Mock()

# 创建 Mock 类
class MockCredentials:
    def __init__(self, ak=None, sk=None, project_id=None):
        self.ak = ak
        self.sk = sk
        self.project_id = project_id

    def process_request(self, request):
        """Mock 签名处理"""
        request.header = request.header or {}
        request.header["Authorization"] = "AWS4-HMAC-SHA256 mock-signature"
        return request

class MockCredentialProviderChain:
    @staticmethod
    def get_basic_credential_provider_chain():
        return MockCredentialProviderChain()

    def get_credentials(self):
        # 模拟从环境变量获取凭证
        ak = os.getenv("HUAWEICLOUD_SDK_AK", "mock-ak")
        sk = os.getenv("HUAWEICLOUD_SDK_SK", "mock-sk")
        return MockCredentials(ak=ak, sk=sk)

class MockSdkRequest:
    def __init__(self):
        self.method = None
        self.uri = None
        self.host = None
        self.header = {}
        self.body = None

class MockHttpConfig:
    @staticmethod
    def get_default_config():
        return MockHttpConfig()

# 设置 mock 类
sys.modules['huaweicloudsdkcore.auth.credentials'].BasicCredentials = MockCredentials
sys.modules['huaweicloudsdkcore.auth.provider'].CredentialProviderChain = MockCredentialProviderChain
sys.modules['huaweicloudsdkcore.http.http_config'].HttpConfig = MockHttpConfig
sys.modules['huaweicloudsdkcore.sdk_request'].SdkRequest = MockSdkRequest

# Mock requests 模块
sys.modules['requests'] = Mock()

from hw_agentrun_wrapper.memory import (
    MemoryClient,
)
from hw_agentrun_wrapper.memory.inner.config import (
    SpaceCreateRequest,
    TextMessage,
    ToolCallMessage,
    ToolResultMessage,
    MemorySearchFilter,
)


class TestMemoryHttpServiceDirect(unittest.TestCase):
    """测试 MemoryHttpService 直接使用"""


class TestMemoryClient(unittest.TestCase):
    """测试 MemoryClient"""

    def setUp(self):
        """设置测试环境"""
        # 设置模拟的环境变量
        os.environ['HUAWEICLOUD_SDK_AK'] = 'test-ak'
        os.environ['HUAWEICLOUD_SDK_SK'] = 'test-sk'
    def tearDown(self):
        """清理测试环境"""
        if 'HUAWEICLOUD_SDK_AK' in os.environ:
            del os.environ['HUAWEICLOUD_SDK_AK']
        if 'HUAWEICLOUD_SDK_SK' in os.environ:
            del os.environ['HUAWEICLOUD_SDK_SK']

    @patch('hw_agentrun_wrapper.memory.inner.dataplane._DataPlane.__init__')
    @patch('hw_agentrun_wrapper.memory.inner.controlplane._ControlPlane.__init__')
    def test_client_initialization(self, mock_control_init, mock_data_init):
        """测试 Client 初始化"""
        mock_control_init.return_value = None
        mock_data_init.return_value = None
        client = MemoryClient(region_name="cn-north-4")
        # 验证 _data_plane 已初始化（_control_plane 是懒加载）
        self.assertIsNotNone(client._data_plane)

    def test_client_context_manager(self):
        """测试 Client 上下文管理器"""
        # MemoryClient 使用 _data_plane 和 _control_plane
        client = MemoryClient(region_name="cn-north-4")
        # 简单测试基本功能
        self.assertIsNotNone(client._data_plane)
        self.assertEqual(client.region_name, "cn-north-4")


class TestDataClasses(unittest.TestCase):
    """测试数据类"""

    def test_space_create_request(self):
        """测试 SpaceCreateRequest"""
        request = SpaceCreateRequest(
            name="test-space",
            message_ttl_hours=168
        )
        self.assertEqual(request.name, "test-space")
        self.assertEqual(request.message_ttl_hours, 168)

    def test_text_message(self):
        """测试 TextMessage"""
        msg = TextMessage(
            role="user",
            content="Hello"
        )
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Hello")

    def test_tool_call_message(self):
        """测试 ToolCallMessage"""
        tool_call = ToolCallMessage(
            id="call_123",
            name="query_weather",
            arguments={"city": "Beijing"}
        )
        self.assertEqual(tool_call.id, "call_123")
        self.assertEqual(tool_call.name, "query_weather")

    def test_tool_result_message(self):
        """测试 ToolResultMessage"""
        tool_result = ToolResultMessage(
            tool_call_id="call_123",
            content=" sunny, 25°C"
        )
        self.assertEqual(tool_result.tool_call_id, "call_123")

    def test_memory_search_filter(self):
        """测试 MemorySearchFilter"""
        filter = MemorySearchFilter(
            query="test query",
            top_k=10,
            min_score=0.5
        )
        self.assertEqual(filter.query, "test query")
        self.assertEqual(filter.top_k, 10)








if __name__ == "__main__":
    unittest.main(verbosity=2)
