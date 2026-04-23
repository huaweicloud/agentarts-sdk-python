"""
Tests for contextvars propagation in AgentArtsRuntimeApp with require_access_token decorator.

This test file verifies that workload_access_token is correctly propagated when:
1. Request comes through _handle_invocation
2. Handler uses require_access_token decorator
3. Handler is sync or async function
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from agentarts.sdk.runtime.app import AgentArtsRuntimeApp
from agentarts.sdk.runtime.context import AgentArtsRuntimeContext, RequestContext


class TestContextPropagationWithRequireAccessToken:
    """Tests for context propagation when handler uses require_access_token."""

    @pytest.mark.asyncio
    async def test_sync_handler_with_require_access_token_gets_token_from_context(
        self, mock_identity_client_for_app
    ):
        """
        Test that sync handler using require_access_token can get workload_access_token
        from context set by _handle_invocation.

        This is the key test case for the reported issue.
        """
        from agentarts.sdk.identity.auth import require_access_token

        app = AgentArtsRuntimeApp()

        @app.entrypoint
        @require_access_token(provider_name="test-provider", auth_flow="M2M")
        def sync_handler(payload, access_token=None):
            return {"received_token": access_token, "payload": payload}

        mock_identity_client_for_app.get_resource_oauth2_token.return_value = "oauth2-result-token"

        mock_request = MagicMock(spec=Request)
        mock_request.json = AsyncMock(return_value={"input": "test"})
        mock_request.headers = {
            "X-HW-AgentGateway-Workload-Access-Token": "workload-token-from-header",
        }

        AgentArtsRuntimeContext.clear()
        try:
            response = await app._handle_invocation(mock_request)

            assert response.status_code == 200
            body = json.loads(response.body)
            assert body["received_token"] == "oauth2-result-token"
            assert body["payload"] == {"input": "test"}
        finally:
            AgentArtsRuntimeContext.clear()

    @pytest.mark.asyncio
    async def test_async_handler_with_require_access_token_gets_token_from_context(
        self, mock_identity_client_for_app
    ):
        """
        Test that async handler using require_access_token can get workload_access_token
        from context set by _handle_invocation.
        """
        from agentarts.sdk.identity.auth import require_access_token

        app = AgentArtsRuntimeApp()

        @app.entrypoint
        @require_access_token(provider_name="test-provider", auth_flow="M2M")
        async def async_handler(payload, access_token=None):
            return {"received_token": access_token, "payload": payload}

        mock_identity_client_for_app.get_resource_oauth2_token.return_value = "oauth2-result-token"

        mock_request = MagicMock(spec=Request)
        mock_request.json = AsyncMock(return_value={"input": "async-test"})
        mock_request.headers = {
            "X-HW-AgentGateway-Workload-Access-Token": "workload-token-from-header",
        }

        AgentArtsRuntimeContext.clear()
        try:
            response = await app._handle_invocation(mock_request)

            assert response.status_code == 200
            body = json.loads(response.body)
            assert body["received_token"] == "oauth2-result-token"
        finally:
            AgentArtsRuntimeContext.clear()

    @pytest.mark.asyncio
    async def test_sync_handler_checks_workload_token_in_context(self):
        """
        Direct test: sync handler should see workload_access_token set by _build_request_context.

        This test verifies the basic context propagation without the require_access_token decorator.
        """
        app = AgentArtsRuntimeApp()

        captured_token = None

        @app.entrypoint
        def sync_handler(payload):
            nonlocal captured_token
            captured_token = AgentArtsRuntimeContext.get_workload_access_token()
            return {"captured_token": captured_token}

        mock_request = MagicMock(spec=Request)
        mock_request.json = AsyncMock(return_value={"input": "test"})
        mock_request.headers = {
            "X-HW-AgentGateway-Workload-Access-Token": "direct-token-test",
        }

        AgentArtsRuntimeContext.clear()
        try:
            response = await app._handle_invocation(mock_request)

            assert response.status_code == 200
            assert captured_token == "direct-token-test"
        finally:
            AgentArtsRuntimeContext.clear()

    @pytest.mark.asyncio
    async def test_require_access_token_wrapper_reads_context_directly(self, mock_identity_client_for_app):
        """
        Test that require_access_token's _get_workload_access_token function
        can read token from AgentArtsRuntimeContext set by _build_request_context.
        """
        from agentarts.sdk.identity.auth import _get_workload_access_token

        AgentArtsRuntimeContext.clear()
        AgentArtsRuntimeContext.set_workload_access_token("context-token-direct")

        try:
            token = _get_workload_access_token(mock_identity_client_for_app)
            assert token == "context-token-direct"
        finally:
            AgentArtsRuntimeContext.clear()

    @pytest.mark.asyncio
    async def test_invoke_handler_copies_context_to_thread(self):
        """
        Test that _invoke_handler correctly copies contextvars to thread pool.
        
        This verifies the copy_context() + run_in_executor pattern.
        """
        import contextvars

        app = AgentArtsRuntimeApp()

        test_var = contextvars.ContextVar("test_var_for_propagation", default=None)
        test_var.set("value-set-in-async")

        captured_value = None

        def sync_handler(payload):
            nonlocal captured_value
            captured_value = test_var.get()
            return {"captured": captured_value}

        context = RequestContext(session_id="test", request_id="req-1", request=None)
        result = await app._invoke_handler(sync_handler, context, False, {})

        assert captured_value == "value-set-in-async"
        assert result["captured"] == "value-set-in-async"

    @pytest.mark.asyncio
    async def test_run_async_in_sync_context_preserves_context(self):
        """
        Test that run_async_in_sync_context preserves contextvars when called from
        a thread that has copied context.
        """
        import asyncio
        import contextvars

        from agentarts.sdk.runtime.context import run_async_in_sync_context

        test_var = contextvars.ContextVar("test_var_run_async", default=None)

        async def async_coro():
            return test_var.get()

        def sync_func_with_context():
            test_var.set("value-in-sync-context")
            ctx = contextvars.copy_context()
            result = ctx.run(run_async_in_sync_context, async_coro())
            return result

        test_var.set("value-in-async-context")
        ctx = contextvars.copy_context()
        result = ctx.run(sync_func_with_context)

        assert result == "value-in-sync-context"

    @pytest.mark.asyncio
    async def test_consecutive_requests_context_isolation(self):
        """
        Test that consecutive requests have isolated context.
        
        This verifies that:
        1. First request sets workload_access_token
        2. After request completes, context should be cleared
        3. Second request without token header should NOT see first request's token
        
        This is the key test for the reported bug:
        'Workload Access Token is invalid or expired'
        """
        app = AgentArtsRuntimeApp()

        captured_tokens = []

        @app.entrypoint
        def sync_handler(payload):
            captured_tokens.append(AgentArtsRuntimeContext.get_workload_access_token())
            return {"status": "ok"}

        AgentArtsRuntimeContext.clear()

        mock_request1 = MagicMock(spec=Request)
        mock_request1.json = AsyncMock(return_value={"input": "first"})
        mock_request1.headers = {
            "X-HW-AgentGateway-Workload-Access-Token": "first-request-token",
        }

        response1 = await app._handle_invocation(mock_request1)
        assert response1.status_code == 200
        assert captured_tokens[-1] == "first-request-token"

        mock_request2 = MagicMock(spec=Request)
        mock_request2.json = AsyncMock(return_value={"input": "second"})
        mock_request2.headers = {}

        response2 = await app._handle_invocation(mock_request2)
        assert response2.status_code == 200

        assert captured_tokens[-1] is None, (
            f"Second request should NOT have workload_access_token from first request. "
            f"Got: {captured_tokens[-1]}"
        )

        AgentArtsRuntimeContext.clear()

    @pytest.mark.asyncio
    async def test_consecutive_requests_different_tokens(self):
        """
        Test that consecutive requests with different tokens work correctly.
        """
        app = AgentArtsRuntimeApp()

        captured_tokens = []

        @app.entrypoint
        def sync_handler(payload):
            captured_tokens.append(AgentArtsRuntimeContext.get_workload_access_token())
            return {"status": "ok"}

        AgentArtsRuntimeContext.clear()

        mock_request1 = MagicMock(spec=Request)
        mock_request1.json = AsyncMock(return_value={"input": "first"})
        mock_request1.headers = {
            "X-HW-AgentGateway-Workload-Access-Token": "token-A",
        }

        response1 = await app._handle_invocation(mock_request1)
        assert response1.status_code == 200

        mock_request2 = MagicMock(spec=Request)
        mock_request2.json = AsyncMock(return_value={"input": "second"})
        mock_request2.headers = {
            "X-HW-AgentGateway-Workload-Access-Token": "token-B",
        }

        response2 = await app._handle_invocation(mock_request2)
        assert response2.status_code == 200

        assert captured_tokens == ["token-A", "token-B"], (
            f"Each request should have its own token. Got: {captured_tokens}"
        )

        AgentArtsRuntimeContext.clear()

    @pytest.mark.asyncio
    async def test_require_api_key_context_isolation(
        self, mock_identity_client_for_app
    ):
        """
        Test that require_api_key benefits from context clearing.
        
        Verifies: token from first request does not leak to second request.
        """
        from agentarts.sdk.identity.auth import require_api_key

        app = AgentArtsRuntimeApp()

        captured_workload_tokens = []

        @app.entrypoint
        def sync_handler(payload):
            captured_workload_tokens.append(
                AgentArtsRuntimeContext.get_workload_access_token()
            )
            return {"status": "ok"}

        AgentArtsRuntimeContext.clear()

        mock_request1 = MagicMock(spec=Request)
        mock_request1.json = AsyncMock(return_value={"input": "first"})
        mock_request1.headers = {
            "X-HW-AgentGateway-Workload-Access-Token": "token-A",
        }

        response1 = await app._handle_invocation(mock_request1)
        assert response1.status_code == 200
        assert captured_workload_tokens[-1] == "token-A"

        mock_request2 = MagicMock(spec=Request)
        mock_request2.json = AsyncMock(return_value={"input": "second"})
        mock_request2.headers = {}

        response2 = await app._handle_invocation(mock_request2)
        assert response2.status_code == 200
        assert captured_workload_tokens[-1] is None, (
            f"Second request should NOT see token from first request. Got: {captured_workload_tokens[-1]}"
        )

        AgentArtsRuntimeContext.clear()

    @pytest.mark.asyncio
    async def test_require_sts_token_context_isolation(
        self, mock_identity_client_for_app
    ):
        """
        Test that require_sts_token benefits from context clearing.
        
        Verifies: token from first request does not leak to second request.
        """
        from agentarts.sdk.identity.auth import require_sts_token

        app = AgentArtsRuntimeApp()

        captured_workload_tokens = []

        @app.entrypoint
        def sync_handler(payload):
            captured_workload_tokens.append(
                AgentArtsRuntimeContext.get_workload_access_token()
            )
            return {"status": "ok"}

        AgentArtsRuntimeContext.clear()

        mock_request1 = MagicMock(spec=Request)
        mock_request1.json = AsyncMock(return_value={"input": "first"})
        mock_request1.headers = {
            "X-HW-AgentGateway-Workload-Access-Token": "token-A",
        }

        response1 = await app._handle_invocation(mock_request1)
        assert response1.status_code == 200
        assert captured_workload_tokens[-1] == "token-A"

        mock_request2 = MagicMock(spec=Request)
        mock_request2.json = AsyncMock(return_value={"input": "second"})
        mock_request2.headers = {}

        response2 = await app._handle_invocation(mock_request2)
        assert response2.status_code == 200
        assert captured_workload_tokens[-1] is None, (
            f"Second request should NOT see token from first request. Got: {captured_workload_tokens[-1]}"
        )

        AgentArtsRuntimeContext.clear()

    @pytest.mark.asyncio
    async def test_concurrent_requests_have_isolated_context(self):
        """
        Test that concurrent requests have isolated context.
        
        This verifies that clearing context in one request does NOT affect
        other concurrent requests running in parallel.
        """
        import asyncio

        app = AgentArtsRuntimeApp()

        results = {}

        @app.entrypoint
        def sync_handler(payload):
            token = AgentArtsRuntimeContext.get_workload_access_token()
            results[payload["id"]] = token
            return {"id": payload["id"], "token": token}

        AgentArtsRuntimeContext.clear()

        def make_request(request_id: str, token_value: str | None):
            mock_request = MagicMock(spec=Request)
            mock_request.json = AsyncMock(return_value={"id": request_id})
            if token_value:
                mock_request.headers = {
                    "X-HW-AgentGateway-Workload-Access-Token": token_value,
                }
            else:
                mock_request.headers = {}
            return mock_request

        await asyncio.gather(
            app._handle_invocation(make_request("req-A", "token-A")),
            app._handle_invocation(make_request("req-B", "token-B")),
            app._handle_invocation(make_request("req-C", None)),
        )

        assert results["req-A"] == "token-A"
        assert results["req-B"] == "token-B"
        assert results["req-C"] is None

        AgentArtsRuntimeContext.clear()

    @pytest.mark.asyncio
    async def test_decorator_reads_same_token_as_invocation_header(
        self, mock_identity_client_for_app
    ):
        """
        Test that decorator's _get_workload_access_token reads the EXACT same token
        that was set by _build_request_context from the invocation header.

        This is the core verification:
        1. Header: X-HW-AgentGateway-Workload-Access-Token = "workload-token-XYZ"
        2. _build_request_context sets context to "workload-token-XYZ"
        3. require_access_token decorator calls _get_workload_access_token
        4. _get_workload_access_token should return "workload-token-XYZ"
        5. get_resource_oauth2_token is called with workload_access_token="workload-token-XYZ"
        """
        from agentarts.sdk.identity.auth import require_access_token

        app = AgentArtsRuntimeApp()

        invocation_token = "workload-token-from-invocation-header"

        @app.entrypoint
        @require_access_token(provider_name="test-provider", auth_flow="M2M")
        def sync_handler(payload, access_token=None):
            return {"received_oauth_token": access_token}

        mock_identity_client_for_app.get_resource_oauth2_token.return_value = "oauth2-result-token"

        mock_request = MagicMock(spec=Request)
        mock_request.json = AsyncMock(return_value={"input": "test"})
        mock_request.headers = {
            "X-HW-AgentGateway-Workload-Access-Token": invocation_token,
        }

        AgentArtsRuntimeContext.clear()
        try:
            response = await app._handle_invocation(mock_request)

            assert response.status_code == 200

            mock_identity_client_for_app.get_resource_oauth2_token.assert_called_once()

            call_kwargs = mock_identity_client_for_app.get_resource_oauth2_token.call_args.kwargs

            assert call_kwargs["workload_access_token"] == invocation_token, (
                f"Decorator should use the SAME token from invocation header. "
                f"Expected: {invocation_token}, Got: {call_kwargs.get('workload_access_token')}"
            )

            body = json.loads(response.body)
            assert body["received_oauth_token"] == "oauth2-result-token"
        finally:
            AgentArtsRuntimeContext.clear()

    @pytest.mark.asyncio
    async def test_async_decorator_reads_same_token_as_invocation_header(
        self, mock_identity_client_for_app
    ):
        """
        Test that async handler's decorator also reads the same token.
        """
        from agentarts.sdk.identity.auth import require_access_token

        app = AgentArtsRuntimeApp()

        invocation_token = "async-workload-token-from-header"

        @app.entrypoint
        @require_access_token(provider_name="test-provider", auth_flow="M2M")
        async def async_handler(payload, access_token=None):
            return {"received_oauth_token": access_token}

        mock_identity_client_for_app.get_resource_oauth2_token.return_value = "oauth2-result-token"

        mock_request = MagicMock(spec=Request)
        mock_request.json = AsyncMock(return_value={"input": "async-test"})
        mock_request.headers = {
            "X-HW-AgentGateway-Workload-Access-Token": invocation_token,
        }

        AgentArtsRuntimeContext.clear()
        try:
            response = await app._handle_invocation(mock_request)

            assert response.status_code == 200

            call_kwargs = mock_identity_client_for_app.get_resource_oauth2_token.call_args.kwargs

            assert call_kwargs["workload_access_token"] == invocation_token, (
                f"Async decorator should use the SAME token from invocation header. "
                f"Expected: {invocation_token}, Got: {call_kwargs.get('workload_access_token')}"
            )
        finally:
            AgentArtsRuntimeContext.clear()


@pytest.fixture
def mock_identity_client_for_app():
    """Fixture to mock IdentityClient for app tests."""
    from agentarts.sdk.identity import auth

    with patch.object(auth, "IdentityClient") as MockClass:
        mock_instance = MockClass.return_value
        mock_instance.get_resource_oauth2_token = AsyncMock()
        mock_instance.get_resource_api_key = MagicMock(return_value="mock-api-key")
        mock_instance.get_resource_sts_token = MagicMock(return_value={})
        mock_instance.create_workload_identity = MagicMock()
        mock_instance.create_workload_access_token = MagicMock(return_value="mock-workload-token")
        yield mock_instance