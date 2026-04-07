"""
AgentArts Runtime Models

Defines constants, enumerations, and data models used by the runtime application.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


SESSION_HEADER = "x-hw-agentarts-session-id"
ACCESS_TOKEN_HEADER = "X-HW-AgentGateway-Workload-Access-Token"
USER_ID_HEADER = "X-Hw-AgentArts-Runtime-User-Id"

CUSTOM_HEADER_PREFIX = "X-Hw-AgentArts-Runtime-Custom-"


class PingStatus(Enum):
    """
    Health status of the AgentArts runtime.

    Used by the ``/ping`` endpoint to report the current health
    of the runtime to the control plane for liveness/readiness probes.

    Attributes:
        HEALTHY: Runtime is healthy and accepting requests.
        HEALTHY_BUSY: Runtime is healthy but processing requests.
        UNHEALTHY: Runtime is unhealthy and not accepting requests.
    """

    HEALTHY = "Healthy"
    HEALTHY_BUSY = "HealthyBusy"
    UNHEALTHY = "Unhealthy"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PingStatus):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False