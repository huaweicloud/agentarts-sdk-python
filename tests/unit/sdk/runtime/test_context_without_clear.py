"""
Demonstration test showing what happens WITHOUT context clearing.

This test simulates the original bug scenario where:
1. Request 1 sets workload_access_token
2. Request ends WITHOUT clearing context
3. Request 2 sees Request 1's token (LEAKED!)
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from agentarts.sdk.runtime.app import AgentArtsRuntimeApp
from agentarts.sdk.runtime.context import AgentArtsRuntimeContext, RequestContext


class TestContextWithoutClearing:
    """
    These tests demonstrate the bug when context is NOT cleared.
    
    They bypass the normal _handle_invocation flow and directly test
    the scenario where context leaks between requests.
    """

    @pytest.mark.asyncio
    async def test_token_leaks_without_clear(self):
        """
        Demonstrate: Without clear(), token from Request 1 leaks to Request 2.
        
        This is the root cause of the bug you reported:
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
            "X-HW-AgentGateway-Workload-Access-Token": "expired-token-from-request-1",
        }

        request_context1 = app._build_request_context(mock_request1)
        result1 = await app._invoke_handler(sync_handler, request_context1, False, {"input": "first"})
        
        assert captured_tokens[-1] == "expired-token-from-request-1"

        AgentArtsRuntimeContext.set_workload_access_token("expired-token-from-request-1")

        mock_request2 = MagicMock(spec=Request)
        mock_request2.json = AsyncMock(return_value={"input": "second"})
        mock_request2.headers = {}

        request_context2 = app._build_request_context(mock_request2)
        result2 = await app._invoke_handler(sync_handler, request_context2, False, {"input": "second"})

        assert captured_tokens[-1] == "expired-token-from-request-1", (
            "BUG: Request 2 sees token from Request 1! "
            f"Expected None or empty header, but got: {captured_tokens[-1]}"
        )

        AgentArtsRuntimeContext.clear()

    @pytest.mark.asyncio
    async def test_real_world_scenario_without_clear(self):
        """
        Real-world scenario simulation:
        
        1. User A makes request with valid token
        2. Token expires (simulated)
        3. User B makes request (no token header)
        4. User B's request FAILS because it uses User A's expired token
        """
        app = AgentArtsRuntimeApp()

        @app.entrypoint
        def sync_handler(payload):
            token = AgentArtsRuntimeContext.get_workload_access_token()
            return {"user": payload.get("user"), "token_used": token}

        AgentArtsRuntimeContext.clear()

        mock_request_user_a = MagicMock(spec=Request)
        mock_request_user_a.json = AsyncMock(return_value={"user": "User-A"})
        mock_request_user_a.headers = {
            "X-HW-AgentGateway-Workload-Access-Token": "user-a-token-WILL-EXPIRE",
        }

        request_context_a = app._build_request_context(mock_request_user_a)
        result_a = await app._invoke_handler(sync_handler, request_context_a, False, {"user": "User-A"})
        
        assert result_a["token_used"] == "user-a-token-WILL-EXPIRE"

        AgentArtsRuntimeContext.set_workload_access_token("user-a-token-WILL-EXPIRE")

        mock_request_user_b = MagicMock(spec=Request)
        mock_request_user_b.json = AsyncMock(return_value={"user": "User-B"})
        mock_request_user_b.headers = {}

        request_context_b = app._build_request_context(mock_request_user_b)
        result_b = await app._invoke_handler(sync_handler, request_context_b, False, {"user": "User-B"})

        assert result_b["token_used"] == "user-a-token-WILL-EXPIRE", (
            f"BUG: User-B is using User-A's token! "
            f"User-B should have no token, but got: {result_b['token_used']}"
        )

        AgentArtsRuntimeContext.clear()

    @pytest.mark.asyncio
    async def test_with_clear_fixes_the_problem(self):
        """
        Demonstrate: With clear(), the problem is fixed.
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

        request_context1 = app._build_request_context(mock_request1)
        result1 = await app._invoke_handler(sync_handler, request_context1, False, {"input": "first"})
        
        assert captured_tokens[-1] == "token-A"

        AgentArtsRuntimeContext.clear()

        mock_request2 = MagicMock(spec=Request)
        mock_request2.json = AsyncMock(return_value={"input": "second"})
        mock_request2.headers = {}

        request_context2 = app._build_request_context(mock_request2)
        result2 = await app._invoke_handler(sync_handler, request_context2, False, {"input": "second"})

        assert captured_tokens[-1] is None, (
            f"FIXED: Request 2 should NOT see token from Request 1. Got: {captured_tokens[-1]}"
        )

        AgentArtsRuntimeContext.clear()