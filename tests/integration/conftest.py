"""Shared fixtures for the non-mock integration / e2e suite.

Safety model (three tiers, see README.md):
  * default ............ read-only list/get + local RuntimeApp (no cloud writes)
  * ALLOW_CREATE=1 ..... create→get→update→delete lifecycle, teardown-guaranteed
  * RUN_BILLABLE=1 ..... code-interpreter sandbox + runtime invoke (real money)

Every resource created by a test is registered with the session-scoped
``resource_registry``; at session end the registry calls each deleter in reverse
order, swallowing errors so a failing cleanup never masks a real failure.
"""

from __future__ import annotations

import os
import uuid
from types import SimpleNamespace

import pytest

from tests.integration._helpers import (
    ENV_ALLOW_CREATE,
    ENV_AK,
    ENV_CODE_INTERPRETER_API_KEY,
    ENV_PRE_WORKLOAD_IDENTITY,
    ENV_REGION,
    ENV_RUN_BILLABLE,
    ENV_RUNTIME_AGENT_NAME,
    ENV_SK,
    env_truthy,
    safe_delete,
)


# --------------------------------------------------------------------------- #
# Auto-mark every test under tests/integration with `integration`.
# --------------------------------------------------------------------------- #
def pytest_collection_modifyitems(config, items) -> None:  # noqa: ANN001
    marker = pytest.mark.integration
    for item in items:
        path = str(item.fspath).replace("\\", "/")
        if "tests/integration" in path:
            item.add_marker(marker)


# --------------------------------------------------------------------------- #
# Run identity + cleanup registry
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def run_id() -> str:
    """A short, run-scoped id baked into every resource name (grep target)."""
    return os.getenv("AGENTARTS_TEST_RUN_ID") or uuid.uuid4().hex[:8]


class _ResourceRegistry:
    """LIFO registry of cleanup callables, drained at session end."""

    def __init__(self) -> None:
        self._items: list[tuple[object, str]] = []

    def register(self, deleter, desc: str) -> None:
        self._items.append((deleter, desc))

    def cleanup_all(self) -> None:
        for deleter, desc in reversed(self._items):
            safe_delete(deleter, desc)
        self._items.clear()


@pytest.fixture(scope="session")
def resource_registry() -> _ResourceRegistry:
    reg = _ResourceRegistry()
    yield reg
    reg.cleanup_all()


# --------------------------------------------------------------------------- #
# Credential / tier gates
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def cloud_credentials():
    """Gate: skip unless AK/SK are present. Region has a sane default."""
    ak = os.getenv(ENV_AK)
    sk = os.getenv(ENV_SK)
    if not ak or not sk:
        pytest.skip(
            f"Set {ENV_AK} and {ENV_SK} (and optionally {ENV_REGION}) to run "
            "cloud integration tests"
        )
    from agentarts.sdk.utils.constant import get_region

    return {"ak": ak, "sk": sk, "region": get_region()}


@pytest.fixture(scope="session")
def allow_create():
    if not env_truthy(ENV_ALLOW_CREATE):
        pytest.skip(
            f"Set {ENV_ALLOW_CREATE}=1 to run create/delete lifecycle tests "
            "(they create real cloud resources, cleaned up via resource_registry)"
        )
    return True


@pytest.fixture(scope="session")
def allow_billable():
    if not env_truthy(ENV_RUN_BILLABLE):
        pytest.skip(
            f"Set {ENV_RUN_BILLABLE}=1 to run billable tests "
            "(code-interpreter sandbox / runtime invoke cost real money)"
        )
    return True


@pytest.fixture(scope="session")
def pre_workload_identity():
    name = os.getenv(ENV_PRE_WORKLOAD_IDENTITY)
    if not name:
        pytest.skip(
            f"Set {ENV_PRE_WORKLOAD_IDENTITY} to exercise get/token against a "
            "pre-provisioned workload identity (read-only tier)"
        )
    return name


@pytest.fixture(scope="session")
def code_interpreter_api_key():
    key = os.getenv(ENV_CODE_INTERPRETER_API_KEY)
    if not key:
        pytest.skip(
            f"Set {ENV_CODE_INTERPRETER_API_KEY} to run code-interpreter data-plane tests"
        )
    return key


@pytest.fixture(scope="session")
def runtime_agent_name():
    name = os.getenv(ENV_RUNTIME_AGENT_NAME)
    if not name:
        pytest.skip(
            f"Set {ENV_RUNTIME_AGENT_NAME} to a pre-deployed agent for "
            "runtime data-plane (session/invoke) tests"
        )
    return name


@pytest.fixture(scope="session")
def code_interpreter_name():
    name = os.getenv("AGENTARTS_TEST_CODE_INTERPRETER_NAME")
    if not name:
        pytest.skip(
            "Set AGENTARTS_TEST_CODE_INTERPRETER_NAME to a pre-provisioned "
            "code interpreter for the billable sandbox-session test"
        )
    return name


@pytest.fixture
def sts_agency_urn():
    urn = os.getenv("AGENTARTS_TEST_STS_AGENCY_URN")
    if not urn:
        pytest.skip(
            "Set AGENTARTS_TEST_STS_AGENCY_URN (iam::<agency_name>) to exercise "
            "STS credential-provider lifecycle"
        )
    return urn


# --------------------------------------------------------------------------- #
# Shared clients (session-scoped → one connection pool, minimal handshakes)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def identity_client(cloud_credentials):
    from agentarts.sdk import IdentityClient

    return IdentityClient(region=cloud_credentials["region"])


@pytest.fixture(scope="session")
def runtime_client(cloud_credentials):
    from agentarts.sdk.service.runtime_client import RuntimeClient

    return RuntimeClient()  # control-plane endpoint + AK/SK from env


@pytest.fixture(scope="session")
def mcp_gateway_client(cloud_credentials):
    from agentarts.sdk import MCPGatewayClient

    return MCPGatewayClient()


@pytest.fixture(scope="session")
def memory_control_client(cloud_credentials):
    """MemoryClient for control-plane ops (create/delete space). AK/SK from env."""
    from agentarts.sdk import MemoryClient

    return MemoryClient()


@pytest.fixture(scope="session")
def memory_space(memory_control_client, allow_create, run_id, resource_registry):
    """A shared Memory Space for the whole session (sync + async modules reuse it).

    create_space mints the Space's own data-plane API key, so downstream data
    clients need no pre-existing memory API key. delete_space (registered for
    session-end cleanup) cascades to all sessions/messages/memories.
    """
    from tests.integration._helpers import unique_name

    name = unique_name("space", run_id)
    space = memory_control_client.create_space(
        name=name,
        message_ttl_hours=168,
        # backend rejects a space with no strategy ("at least one built-in or
        # custom memory strategy is required"); pick the cheapest one. We keep
        # is_force_extract=False on add_messages so no extra LLM extraction cost
        # is forced during the test.
        memory_strategies_builtin=["semantic"],
    )
    resource_registry.register(
        lambda: memory_control_client.delete_space(space.id), f"space:{name}"
    )
    return space


# --------------------------------------------------------------------------- #
# Identity cleanup helpers (the SDK has no delete wrappers → drop to raw client)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def identity_cleanup(identity_client):
    """Bound deleters for workload identities & credential providers.

    The high-level ``IdentityClient`` exposes no ``delete_*`` methods, so we
    call the generated ``AgentIdentityClient`` (``identity_client.client``)
    directly. Request-model class names mirror the Get/Create convention.
    """

    def delete_workload_identity(name: str) -> None:
        from huaweicloudsdkagentidentity.v1 import DeleteWorkloadIdentityRequest

        identity_client.client.delete_workload_identity(
            request=DeleteWorkloadIdentityRequest(workload_identity_name=name)
        )

    def delete_credential_provider(kind: str, name: str) -> None:
        from huaweicloudsdkagentidentity.v1 import (
            DeleteApiKeyCredentialProviderRequest,
            DeleteOauth2CredentialProviderRequest,
            DeleteStsCredentialProviderRequest,
        )

        mapping = {
            "api_key": (
                "delete_api_key_credential_provider",
                DeleteApiKeyCredentialProviderRequest,
            ),
            "oauth2": (
                "delete_oauth2_credential_provider",
                DeleteOauth2CredentialProviderRequest,
            ),
            "sts": (
                "delete_sts_credential_provider",
                DeleteStsCredentialProviderRequest,
            ),
        }
        method_name, req_cls = mapping[kind]
        getattr(identity_client.client, method_name)(
            request=req_cls(credential_provider_name=name)
        )

    return SimpleNamespace(
        workload_identity=delete_workload_identity,
        credential_provider=delete_credential_provider,
    )


# --------------------------------------------------------------------------- #
# Shared identity resources (workload identity + api-key credential provider).
# Session-scoped so the identity lifecycle module and the auth-decorator module
# reuse the same resources (one create each, cleaned up once at session end).
# --------------------------------------------------------------------------- #
_DUMMY_API_KEY = "aa-it-dummy-api-key-0123456789abcdef"


@pytest.fixture(scope="session")
def created_workload_identity(
    identity_client, allow_create, run_id, identity_cleanup, resource_registry
):
    from tests.integration._helpers import unique_name

    name = unique_name("wi", run_id)
    wi = identity_client.create_workload_identity(name=name)
    resource_registry.register(
        lambda: identity_cleanup.workload_identity(name), f"workload_identity:{name}"
    )
    return {"name": name, "obj": wi}


@pytest.fixture(scope="session")
def created_api_key_provider(
    identity_client, created_workload_identity, run_id, identity_cleanup, resource_registry
):
    from tests.integration._helpers import unique_name

    name = unique_name("cp-ak", run_id)
    identity_client.create_api_key_credential_provider(name=name, api_key=_DUMMY_API_KEY)
    resource_registry.register(
        lambda: identity_cleanup.credential_provider("api_key", name),
        f"credential_provider:api_key:{name}",
    )
    return name


# --------------------------------------------------------------------------- #
# Filesystem isolation for the auth decorators (which persist .agent_identity.json)
# --------------------------------------------------------------------------- #
@pytest.fixture
def isolated_identity_config(tmp_path, monkeypatch):
    """chdir into a temp dir so `.agent_identity.json` never pollutes the repo."""
    monkeypatch.chdir(tmp_path)
    return tmp_path
