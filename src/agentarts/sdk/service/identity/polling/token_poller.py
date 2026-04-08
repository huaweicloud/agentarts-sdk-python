import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class PollingStatus(str, Enum):
    """Status of an OAuth2 token polling attempt.

    Variants:
        IN_PROGRESS: The user has not yet completed authorization; polling should continue.
        FAILED: The authorization session has failed; polling should stop immediately.
    """

    IN_PROGRESS = "IN_PROGRESS"
    FAILED = "FAILED"


@dataclass(frozen=True)
class PollingResult:
    """Result of a single token polling attempt.

    Attributes:
        status: The current polling status.
        access_token: The OAuth2 access token, present only when authorization succeeds.
    """

    status: PollingStatus = field(default=PollingStatus.IN_PROGRESS)
    access_token: Optional[str] = field(default=None)


class TokenPoller(ABC):
    """Abstract base class for token polling implementations."""

    @abstractmethod
    async def poll_for_token(self) -> str:
        """Poll for a token and return it when available.

        Returns:
            The retrieved access token as a string.

        Raises:
            asyncio.TimeoutError: If the polling exceeds the maximum timeout duration.
        """
        raise NotImplementedError


DEFAULT_POLLING_INTERVAL_SECONDS = 5
DEFAULT_POLLING_TIMEOUT_SECONDS = 300


class DefaultApiTokenPoller(TokenPoller):
    """Default implementation of token polling."""

    def __init__(self, auth_url: str, func: Callable[[], PollingResult]):
        """Initialize the token poller.

        Args:
            auth_url: The URL where the user performs authorization.
            func: A callable that returns a PollingResult indicating
                  the current status and, on success, the access token.
        """
        self.auth_url = auth_url
        self.polling_func = func
        self.logger = logging.getLogger("agent_identity.default_token_poller")
        self.logger.setLevel("INFO")
        if not self.logger.handlers:
            self.logger.addHandler(logging.StreamHandler())

    async def poll_for_token(self) -> str:
        """Poll for a token until it becomes available, fails, or times out.

        Returns:
            The retrieved access token as a string.

        Raises:
            asyncio.TimeoutError: If the polling exceeds the maximum timeout duration.
            RuntimeError: If the authorization session status is FAILED.
        """
        start_time = time.time()
        while time.time() - start_time < DEFAULT_POLLING_TIMEOUT_SECONDS:
            await asyncio.sleep(DEFAULT_POLLING_INTERVAL_SECONDS)

            self.logger.info(
                "Polling for token for authorization url: %s", self.auth_url
            )
            result = self.polling_func()

            if result.access_token is not None:
                self.logger.info("Token is ready")
                return result.access_token

            if result.status == PollingStatus.FAILED:
                self.logger.error(
                    "Authorization session failed for url: %s", self.auth_url
                )
                raise RuntimeError(
                    "Authorization session failed. "
                    "The user may have denied access or the session expired."
                )

        raise asyncio.TimeoutError(
            f"Polling timed out after {DEFAULT_POLLING_TIMEOUT_SECONDS} seconds. "
            + "User may not have completed authorization."
        )
