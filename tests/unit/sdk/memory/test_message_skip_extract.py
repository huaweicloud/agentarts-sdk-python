"""Per-message extraction flags survive request and response conversion."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from agentarts.sdk.memory import (
    AddMessagesRequest,
    AsyncMemoryClient,
    AsyncMemorySession,
    MemoryClient,
    MemorySession,
    MessageInfo,
    MessageRequest,
    TextMessage,
    ToolCallMessage,
    ToolResultMessage,
)


@pytest.mark.parametrize(
    "fields", [{}, {"skip_extract": None}, {"skip_extract": True}, {"skip_extract": False}]
)
@pytest.mark.parametrize(
    "message_type", [TextMessage, ToolCallMessage, ToolResultMessage, MessageRequest]
)
def test_optional_flag_serialization(message_type, fields):
    if message_type is MessageRequest:
        part = Mock()
        part.to_dict.return_value = {"type": "text", "text": "hello"}
        message = MessageRequest(role="user", parts=[part], **fields)
        payload = AddMessagesRequest(messages=[message]).to_dict()["messages"][0]
    else:
        kwargs = {"content": "hello"} if message_type is TextMessage else {}
        payload = message_type(**kwargs, **fields).to_dict()

    if fields.get("skip_extract") is None:
        assert "skip_extract" not in payload
    else:
        assert payload["skip_extract"] is fields["skip_extract"]
    assert all("skip_extract" not in part for part in payload["parts"])


@pytest.mark.parametrize(
    "fields", [{}, {"skip_extract": None}, {"skip_extract": True}, {"skip_extract": False}]
)
def test_optional_flag_deserialization(fields):
    message = MessageInfo.from_dict({"id": "msg-1", "session_id": "session-1", **fields})
    assert message.skip_extract is fields.get("skip_extract", False)


def test_message_info_defaults_to_database_value():
    assert MessageInfo(id="msg-1", session_id="session-1", seq=1).skip_extract is False


def make_messages():
    return [
        TextMessage(content="skip this", skip_extract=True),
        ToolCallMessage(id="call-1", name="lookup", skip_extract=False),
        ToolResultMessage(tool_call_id="call-1", content="result"),
    ]


def response_messages():
    return [
        {"id": "msg-1", "session_id": "session-1", "seq": 1, "skip_extract": True},
        {"id": "msg-2", "session_id": "session-1", "seq": 2, "skip_extract": False},
        {"id": "msg-3", "session_id": "session-1", "seq": 3},
    ]


def assert_add_payload(request):
    payload = request.call_args.kwargs["data"]
    assert "skip_extract" not in payload
    assert payload["messages"][0]["skip_extract"] is True
    assert payload["messages"][1]["skip_extract"] is False
    assert "skip_extract" not in payload["messages"][2]


def assert_flags(messages):
    assert [message.skip_extract for message in messages] == [True, False, False]


@pytest.mark.parametrize("session_mode", [False, True], ids=["client", "session"])
def test_sync_message_api_round_trip(session_mode):
    target = (
        MemorySession(
            space_id="space-1", actor_id="actor-1", session_id="session-1", api_key="test-key"
        )
        if session_mode
        else MemoryClient(api_key="test-key")
    )
    scope = {} if session_mode else {"space_id": "space-1", "session_id": "session-1"}
    try:
        with patch.object(target._data_plane.client, "_make_request") as request:
            request.return_value = {"messages": response_messages()}
            result = target.add_messages(messages=make_messages(), **scope)
            assert_add_payload(request)
            assert_flags(result.items)

            for item in response_messages():
                request.return_value = item
                result = target.get_message(message_id=item["id"], **scope)
                assert result.skip_extract is item.get("skip_extract", False)

            request.return_value = {"items": response_messages(), "total": 3}
            assert_flags(target.list_messages(**scope).items)
            assert_flags(target.get_last_k_messages(k=3, **scope))
    finally:
        target.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("session_mode", [False, True], ids=["client", "session"])
async def test_async_message_api_round_trip(session_mode):
    target = (
        AsyncMemorySession(
            space_id="space-1", actor_id="actor-1", session_id="session-1", api_key="test-key"
        )
        if session_mode
        else AsyncMemoryClient(api_key="test-key")
    )
    scope = {} if session_mode else {"space_id": "space-1", "session_id": "session-1"}
    try:
        with patch.object(
            target._async_data_plane.client, "_make_request", new_callable=AsyncMock
        ) as request:
            request.return_value = {"messages": response_messages()}
            result = await target.add_messages(messages=make_messages(), **scope)
            assert_add_payload(request)
            assert_flags(result.items)

            for item in response_messages():
                request.return_value = item
                result = await target.get_message(message_id=item["id"], **scope)
                assert result.skip_extract is item.get("skip_extract", False)

            request.return_value = {"items": response_messages(), "total": 3}
            assert_flags((await target.list_messages(**scope)).items)
            assert_flags(await target.get_last_k_messages(k=3, **scope))
    finally:
        await target.close()
