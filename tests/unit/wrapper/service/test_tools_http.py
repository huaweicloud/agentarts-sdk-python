import unittest
from unittest.mock import patch

from agentarts.wrapper.service import ControlToolsHttpClient, DataToolsHttpClient

class TestDataToolsHttpClient(unittest.TestCase):
    def setUp(self, mock_invoke):
        self.control_client = ControlToolsHttpClient()
        self.data_client = DataToolsHttpClient()
    

    def test_create_code_interpreter(self):
        """测试create_code_interpreter方法"""
        # TODO
        pass
    
    def test_list_code_interpreters(self):
        """测试list_code_interpreters方法"""
        # TODO
        pass

    def test_update_code_interpreter(self):
        """测试update_code_interpreter方法"""
        # TODO
        pass

    def test_get_code_interpreter(self):
        """测试get_code_interpreter方法"""
        # TODO
        pass

    def test_delete_code_interpreter(self):
        """测试delete_code_interpreter方法"""
        # TODO
        pass
    
    def test_start_session(self):
        """测试start_session方法"""
        # TODO
        pass

    def test_get_session(self):
        """测试get_session方法"""
        # TODO
        pass
    
    
    def test_stop_session(self):
        """测试stop_session方法"""
        # TODO
        pass

    def test_invoke(self):
        """测试invoke方法"""
        # TODO
        pass
