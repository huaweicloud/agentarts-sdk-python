"""Tests for memory module"""

from unittest.mock import MagicMock, patch


def test_memory_client_import():
    """Test that MemoryClient can be imported"""
    from agentarts.sdk import MemoryClient

    assert MemoryClient is not None


def test_memory_client_creation():
    """Test MemoryClient creation"""
    from agentarts.sdk import MemoryClient

    client = MemoryClient(region_name="cn-north-4", api_key="test-api-key")

    assert client is not None


def test_memory_types_import():
    """Test that memory types can be imported"""
    from agentarts.sdk.memory import (
        MessageRequest,
        SessionCreateRequest,
        SpaceCreateRequest,
        SpaceUpdateRequest,
    )

    assert SpaceCreateRequest is not None
    assert SpaceUpdateRequest is not None
    assert SessionCreateRequest is not None
    assert MessageRequest is not None


class TestMemoryClientClose:
    """Tests for MemoryClient close functionality."""

    def test_memory_client_close_without_control_plane(self):
        """Test MemoryClient close when control plane is not initialized."""
        from agentarts.sdk import MemoryClient

        client = MemoryClient(region_name="cn-north-4", api_key="test-api-key")

        assert client._control_plane is None
        assert client._data_plane is not None

        client.close()

        assert client._control_plane is None

    def test_memory_client_close_with_control_plane(self):
        """Test MemoryClient close when control plane is initialized."""
        from agentarts.sdk import MemoryClient
        from agentarts.sdk.memory.inner.controlplane import _ControlPlane

        client = MemoryClient(region_name="cn-north-4", api_key="test-api-key")

        mock_control_plane = MagicMock(spec=_ControlPlane)
        client._control_plane = mock_control_plane

        client.close()

        mock_control_plane.close.assert_called_once()

    def test_memory_client_context_manager(self):
        """Test MemoryClient works as context manager."""
        from agentarts.sdk import MemoryClient

        with MemoryClient(region_name="cn-north-4", api_key="test-api-key") as client:
            assert client is not None

    def test_memory_client_context_manager_calls_close(self):
        """Test context manager calls close on exit."""
        from agentarts.sdk import MemoryClient

        client = MemoryClient(region_name="cn-north-4", api_key="test-api-key")

        with patch.object(client, "close") as mock_close:
            with client:
                pass
            mock_close.assert_called_once()


class TestDataPlaneClose:
    """Tests for _DataPlane close functionality."""

    def test_dataplane_close(self):
        """Test _DataPlane close method."""
        from agentarts.sdk.memory.inner.dataplane import _DataPlane

        dataplane = _DataPlane(region_name="cn-north-4", api_key="test-api-key")

        assert dataplane.client is not None

        dataplane.close()

    def test_dataplane_close_calls_client_close(self):
        """Test _DataPlane close calls underlying client close."""
        from agentarts.sdk.memory.inner.dataplane import _DataPlane

        dataplane = _DataPlane(region_name="cn-north-4", api_key="test-api-key")

        with patch.object(dataplane.client, "close") as mock_close:
            dataplane.close()
            mock_close.assert_called_once()


class TestControlPlaneClose:
    """Tests for _ControlPlane close functionality."""

    def test_controlplane_close(self):
        """Test _ControlPlane close method."""
        from agentarts.sdk.memory.inner.controlplane import _ControlPlane

        with patch("agentarts.sdk.service.memory_service.ControlPlaneAuthenticationStrategy.setup_credentials"):
            controlplane = _ControlPlane(region_name="cn-north-4")

            assert controlplane.client is not None

            controlplane.close()

    def test_controlplane_close_calls_client_close(self):
        """Test _ControlPlane close calls underlying client close."""
        from agentarts.sdk.memory.inner.controlplane import _ControlPlane

        with patch("agentarts.sdk.service.memory_service.ControlPlaneAuthenticationStrategy.setup_credentials"):
            controlplane = _ControlPlane(region_name="cn-north-4")

            with patch.object(controlplane.client, "close") as mock_close:
                controlplane.close()
                mock_close.assert_called_once()


class TestMemoryHttpServiceClose:
    """Tests for MemoryHttpService close functionality."""

    def test_memory_http_service_close(self):
        """Test MemoryHttpService close method."""
        from agentarts.sdk.service.memory_service import MemoryHttpService

        service = MemoryHttpService(
            region_name="cn-north-4",
            endpoint_type="data",
            api_key="test-api-key"
        )

        assert service.session is not None

        service.close()

    def test_memory_http_service_close_calls_session_close(self):
        """Test MemoryHttpService close calls session close."""
        from agentarts.sdk.service.memory_service import MemoryHttpService

        service = MemoryHttpService(
            region_name="cn-north-4",
            endpoint_type="data",
            api_key="test-api-key"
        )

        with patch.object(service.session, "close") as mock_close:
            service.close()
            mock_close.assert_called_once()

    def test_memory_http_service_close_control_plane(self):
        """Test MemoryHttpService close for control plane."""
        from agentarts.sdk.service.memory_service import MemoryHttpService

        with patch("agentarts.sdk.service.memory_service.ControlPlaneAuthenticationStrategy.setup_credentials"):
            service = MemoryHttpService(
                region_name="cn-north-4",
                endpoint_type="control"
            )

            assert service.session is not None

            service.close()

    def test_memory_http_service_close_safe_when_no_session(self):
        """Test MemoryHttpService close is safe when session is None."""
        from agentarts.sdk.service.memory_service import MemoryHttpService

        service = MemoryHttpService(
            region_name="cn-north-4",
            endpoint_type="data",
            api_key="test-api-key"
        )

        service.session = None

        service.close()


class TestCloseMethodChaining:
    """Tests for close method chaining from MemoryClient to session."""

    def test_close_method_chain(self):
        """Test that close calls propagate from client to session."""
        from agentarts.sdk import MemoryClient
        from agentarts.sdk.memory.inner.controlplane import _ControlPlane

        client = MemoryClient(region_name="cn-north-4", api_key="test-api-key")

        mock_control_plane = MagicMock(spec=_ControlPlane)
        client._control_plane = mock_control_plane

        with patch.object(client._data_plane.client.session, "close") as mock_session_close:
            client.close()

            mock_control_plane.close.assert_called_once()

            mock_session_close.assert_called_once()


class TestMemorySession:
    """Tests for MemorySession (sync)."""

    def test_session_auto_create_passes_request_object(self):
        """Regression: __init__ must pass a SessionCreateRequest object to the data
        plane, not a pre-converted dict (the data plane calls .to_dict() internally)."""
        from agentarts.sdk.memory import MemorySession, SessionCreateRequest, SessionInfo

        with patch(
            "agentarts.sdk.memory.session._DataPlane.create_memory_session",
            return_value=SessionInfo(id="new-session-123", space_id="space-123", actor_id="user-1"),
        ) as mock_create:
            session = MemorySession(
                space_id="space-123",
                actor_id="user-1",
                api_key="test-key",
            )

        assert session.session_id == "new-session-123"
        mock_create.assert_called_once()
        call_args = mock_create.call_args.args
        assert call_args[0] == "space-123"
        assert isinstance(call_args[1], SessionCreateRequest)
        assert call_args[1].actor_id == "user-1"

    def test_session_get_message_arg_order(self):
        """Regression: get_message must forward args as (message_id, space_id,
        session_id) to match the data plane signature."""
        from agentarts.sdk.memory import MemorySession, MessageInfo

        session = MemorySession(
            space_id="space-123",
            actor_id="user-1",
            session_id="session-456",
            api_key="test-key",
        )

        mock_data_plane = MagicMock()
        mock_data_plane.get_message.return_value = MessageInfo(id="msg-1", session_id="session-456", seq=1)
        session._data_plane = mock_data_plane

        session.get_message("msg-1")

        mock_data_plane.get_message.assert_called_once_with("msg-1", "space-123", "session-456")
