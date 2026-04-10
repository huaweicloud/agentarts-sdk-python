import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from agentarts.sdk.service.identity.polling import token_poller
from agentarts.sdk.service.identity.polling.token_poller import (
    DEFAULT_POLLING_TIMEOUT_SECONDS,
    DefaultApiTokenPoller,
    PollingResult,
    PollingStatus,
)


@pytest.mark.asyncio
async def test_poll_for_token_returns_token_on_success():
    """Token is returned immediately when poll_fn yields a successful result."""

    def poll_fn() -> PollingResult:
        return PollingResult(access_token="test-token-123")

    poller = DefaultApiTokenPoller(auth_url="https://example.com/auth", func=poll_fn)

    with patch.object(asyncio, "sleep", new_callable=AsyncMock):
        token = await poller.poll_for_token()

    assert token == "test-token-123"


@pytest.mark.asyncio
async def test_poll_for_token_raises_on_failed_status():
    """RuntimeError is raised immediately when poll_fn returns FAILED status."""

    def poll_fn() -> PollingResult:
        return PollingResult(status=PollingStatus.FAILED)

    poller = DefaultApiTokenPoller(auth_url="https://example.com/auth", func=poll_fn)

    with patch.object(asyncio, "sleep", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="Authorization session failed"):
            await poller.poll_for_token()


@pytest.mark.asyncio
async def test_poll_for_token_polls_until_token_available():
    """Poller retries while status is IN_PROGRESS, then returns when token appears."""
    call_count = 0

    def poll_fn() -> PollingResult:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return PollingResult(status=PollingStatus.IN_PROGRESS)
        return PollingResult(access_token="delayed-token")

    poller = DefaultApiTokenPoller(auth_url="https://example.com/auth", func=poll_fn)

    with patch.object(asyncio, "sleep", new_callable=AsyncMock):
        token = await poller.poll_for_token()

    assert token == "delayed-token"
    assert call_count == 3


@pytest.mark.asyncio
async def test_poll_for_token_fails_fast_after_in_progress_then_failed():
    """Poller stops immediately when status transitions from IN_PROGRESS to FAILED."""
    call_count = 0

    def poll_fn() -> PollingResult:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return PollingResult(status=PollingStatus.IN_PROGRESS)
        return PollingResult(status=PollingStatus.FAILED)

    poller = DefaultApiTokenPoller(auth_url="https://example.com/auth", func=poll_fn)

    with patch.object(asyncio, "sleep", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="Authorization session failed"):
            await poller.poll_for_token()

    assert call_count == 3


@pytest.mark.asyncio
async def test_poll_for_token_times_out():
    """TimeoutError is raised when polling exceeds the timeout without a token or failure."""

    def poll_fn() -> PollingResult:
        return PollingResult(status=PollingStatus.IN_PROGRESS)

    poller = DefaultApiTokenPoller(auth_url="https://example.com/auth", func=poll_fn)

    call_count = 0

    def fake_time():
        nonlocal call_count
        call_count += 1
        # First call (loop condition check) returns 0, second returns past timeout
        if call_count <= 1:
            return 0
        return DEFAULT_POLLING_TIMEOUT_SECONDS + 1

    with (
        patch.object(token_poller, "time") as mock_time,
        patch.object(asyncio, "sleep", new_callable=AsyncMock),
    ):
        mock_time.time = fake_time

        with pytest.raises(asyncio.TimeoutError, match="Polling timed out"):
            await poller.poll_for_token()


def test_polling_result_defaults():
    """PollingResult defaults to IN_PROGRESS status with no token."""
    result = PollingResult()
    assert result.status == PollingStatus.IN_PROGRESS
    assert result.access_token is None


def test_polling_result_with_token():
    """PollingResult with access_token keeps default IN_PROGRESS status."""
    result = PollingResult(access_token="token-abc")
    assert result.status == PollingStatus.IN_PROGRESS
    assert result.access_token == "token-abc"


def test_polling_result_failed():
    """PollingResult can represent a FAILED status."""
    result = PollingResult(status=PollingStatus.FAILED)
    assert result.status == PollingStatus.FAILED
    assert result.access_token is None


def test_polling_result_is_frozen():
    """PollingResult is immutable."""
    result = PollingResult(access_token="token")
    with pytest.raises(AttributeError):
        result.access_token = "new-token"  # type: ignore[misc]


def test_polling_status_values():
    """PollingStatus enum has the expected string values."""
    assert PollingStatus.IN_PROGRESS == "IN_PROGRESS"
    assert PollingStatus.FAILED == "FAILED"
    assert PollingStatus.IN_PROGRESS.value == "IN_PROGRESS"
    assert PollingStatus.FAILED.value == "FAILED"
