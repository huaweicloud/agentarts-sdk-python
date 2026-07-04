"""
Unit tests for gateway operations
"""


class TestGatewayOperations:
    """Test gateway operations"""

    def test_gateway_operations_import(self):
        """Test that gateway operations module can be imported"""
        import agentarts.toolkit.operations.gateway

        assert agentarts.toolkit.operations.gateway.__all__ == []
