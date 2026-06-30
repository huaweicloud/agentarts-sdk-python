# Integration / e2e tests

Non-mock tests that hit **real Huawei Cloud APIs** (no HTTP mocking). They
verify the SDK wrapper layers end-to-end: `IdentityClient`, `RuntimeClient`,
`MemoryClient` / `AsyncMemoryClient`, `MCPGatewayClient`, `CodeInterpreter`,
`AgentArtsRuntimeApp`, and the `require_*` auth decorators.

## Three-tier safety model

The core tension: verifying write operations (create/update/delete) requires
creating real resources, which conflicts with "no residue / no overspend".
The suite resolves this with three tiers, each gated by environment variables.

| Tier | Switch | What runs | Cloud writes? | Cost |
|------|--------|-----------|---------------|------|
| **Default (read-only)** | — | `list`/`get` + ephemeral token issuance + local `AgentArtsRuntimeApp` (TestClient) | none | none |
| **Lifecycle** | `AGENTARTS_TEST_ALLOW_CREATE=1` | `create → get → update → delete` for every resource type | yes, teardown-guaranteed | low |
| **Billable** | `AGENTARTS_TEST_RUN_BILLABLE=1` | code-interpreter sandbox session, runtime `invoke`/`exec` | ephemeral sessions (paired start/stop) | real money |

Tests skip automatically (with a clear message listing the required vars) when
their gate is not satisfied, so `pytest tests/integration` is always safe to
run.

## Running

```bash
# Default tier — no credentials needed for the local RuntimeApp tests;
# cloud read-only tests skip without AK/SK.
uv run pytest tests/integration -m integration

# Read-only tier — real list/get calls, no writes.
export HUAWEICLOUD_SDK_AK=...
export HUAWEICLOUD_SDK_SK=...
export HUAWEICLOUD_SDK_REGION=cn-southwest-2
uv run pytest tests/integration -m integration

# Full lifecycle (create→delete).
export AGENTARTS_TEST_ALLOW_CREATE=1
uv run pytest tests/integration -m integration

# Billable sandbox/runtime sessions.
export AGENTARTS_TEST_RUN_BILLABLE=1
uv run pytest tests/integration -m "integration and slow"   # code-interpreter / runtime sessions
```

See `.env.example` for the full variable set. The default tier needs only
`HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` / `HUAWEICLOUD_SDK_REGION`.

## Resource hygiene

- Every created resource is registered with a session-scoped
  `resource_registry`; at session end it calls each deleter **in reverse
  order**, swallowing errors so a failing cleanup never masks a real failure.
- All resource names are prefixed `aa-it-<run_id>-…`, so any leaked resource is
  greppable for manual cleanup.
- The Memory suite is self-contained: `create_space` mints the space's own
  data-plane API key, so no pre-existing `HUAWEICLOUD_SDK_MEMORY_API_KEY` is
  needed; `delete_space` cascades to all sessions/messages/memories.
- Billable sessions use the `code_session` context manager (auto `stop_session`
  on exit) and register `stop_session` with the registry as a safety net.
- The auth decorators' local-auth bootstrap persists `.agent_identity.json`;
  `isolated_identity_config` chdir's into a temp dir so the repo is never
  polluted, and a pre-seeded `Config` makes the bootstrap reuse the session
  workload identity (no extra create).

### Cleaning up leaked resources

If a run is interrupted before teardown, find leftovers by the run prefix:

```bash
# Identity
# (list via the SDK) IdentityClient.list_workload_identities() / list_*_credential_providers()
#   filter for names starting with "aa-it-"

# Memory spaces
# MemoryClient.list_spaces() → delete spaces whose name starts with "aa-it-"

# MCP gateways
# MCPGatewayClient.list_mcp_gateways() → delete gateways whose name starts with "aa-it-"

# Runtime agents
# RuntimeClient.get_agents() → delete agents whose name starts with "aa-it-"

# Code interpreters
# CodeInterpreter.list_code_interpreters() → delete those whose name starts with "aa-it-"
```

> **Note:** `MCPGatewayClient.create_mcp_gateway` auto-creates a shared IAM
> agency `AgentArtsCoreGateway` (409-ignored if it already exists) which the
> SDK intentionally does **not** delete. This single shared agency is expected
> residue.

## What is deliberately NOT covered

- OAuth2 3-legged `require_access_token` — interactive browser round trip;
  covered by unit tests for wiring, e2e is a manual exercise (marked `slow`).
- `IAMClient.create_agency` — only a create wrapper, no read/delete in the SDK;
  exercised implicitly only via MCP gateway's shared-agency path.

## Method coverage

Status legend (from a real-cloud `ALLOW_CREATE=1` run, no `RUN_BILLABLE`):

- ✅ real-cloud pass · 🟦 local pass (no cloud) · ⏭ conditional skip ·
  ⚠️ xfail (SDK bug) · 🚫 skip (backend prereq) · 💰 requires `RUN_BILLABLE=1`

### AgentArtsRuntimeApp (local, 🟦)

| Method / endpoint | Test | Status |
|---|---|---|
| `@app.entrypoint` / `@app.ping` / `@app.websocket` decorators | various | 🟦 |
| `force_ping_status()` / `get_current_ping_status()` | test_ping_* | 🟦 |
| `GET /ping` (default/custom/forced) | test_ping_* (3) | 🟦 |
| `POST /invocations` (JSON 200 / bad-JSON 400 / no-entrypoint 404 / raise 500) | test_invocation_* (4) | 🟦 |
| `POST /invocations` (sync + async generator → SSE) | test_invocation_*_streams_sse (2) | 🟦 |
| `WS /ws` (no-handler 1011 / echo) | test_websocket_* (2) | 🟦 |

Not covered: `@app.async_task`, `has_running_tasks()`.

### IdentityClient

Read-only (default tier):

| Method | Test | HTTP | Status |
|---|---|---|---|
| `list_workload_identities` | test_list_workload_identities | GET /v1/workload-identities | ✅ |
| `list_api_key_credential_providers` | … | GET /v1/api-key-credential-providers | ✅ |
| `list_oauth2_credential_providers` | … | GET /v1/oauth2-credential-providers | ✅ |
| `list_sts_credential_providers` | … | GET /v1/sts-credential-providers | ✅ |
| `get_workload_identity` | test_get_and_token… | GET …/{name} | ⏭ |
| `create_workload_access_token` | same | POST /v1/workload-access-token-for-user-id | ⏭ |

Lifecycle (`ALLOW_CREATE`):

| Method | Test | HTTP | Status |
|---|---|---|---|
| `create_workload_identity` | fixture | POST /v1/workload-identities | ✅ |
| `get_workload_identity` | test_get_created_workload_identity | GET …/{name} | ✅ |
| `update_workload_identity` | test_update_workload_identity | PUT …/{name} | ✅ |
| `list_workload_identities` | test_list_workload_identities_contains_created | GET /v1/workload-identities | ✅ |
| `create_api_key_credential_provider` | fixture | POST /v1/api-key-credential-providers | ✅ |
| `get_api_key_credential_provider` | test_get_api_key_credential_provider | GET …/{name} | ✅ |
| `list_api_key_credential_providers` | test_list_api_key_credential_providers_contains_created | GET … | ✅ |
| `create_workload_access_token` | test_create_workload_access_token / test_get_resource_api_key | POST …/for-user-id | ✅ |
| `get_resource_api_key` | test_get_resource_api_key | POST /v1/api-key | ✅ |
| `create_oauth2_credential_provider` / `get_oauth2_credential_provider` | test_create_and_delete_oauth2… | POST/GET …/oauth2… | ⏭ (slow) |
| `create_sts_credential_provider` / `get_sts_credential_provider` | test_create_and_delete_sts… | POST/GET …/sts… | ⏭ |
| raw `delete_workload_identity` / `delete_*_credential_provider` | resource_registry teardown | DELETE … | ✅ (implicit) |

Not covered: `get_resource_oauth2_token` (3LO), `get_resource_sts_token`, `complete_resource_token_auth`, `update_*_credential_provider`.

### MemoryClient + AsyncMemoryClient

Sync (`ALLOW_CREATE`, all ✅):

| Method | Test | HTTP |
|---|---|---|
| `create_space` (with `memory_strategies_builtin`) | fixture | POST /v1/core/spaces (+space-keys) |
| `get_space` | test_get_space | GET /v1/core/spaces/{id} |
| `list_spaces` | test_list_spaces_contains_created | GET /v1/core/spaces |
| `update_space` | test_update_space | PUT /v1/core/spaces/{id} |
| `delete_space` | teardown | DELETE /v1/core/spaces/{id} |
| `create_memory_session` | fixture | POST …/sessions |
| `add_messages` (2× `TextMessage`) | fixture | POST …/messages |
| `list_messages` | test_list_messages | GET …/messages |
| `get_last_k_messages` | test_get_last_k_messages | GET …/messages ×2 |
| `get_message` | test_get_message | GET …/messages/{id} |
| `search_memories` | test_search_memories | POST …/memories/search |
| `list_memories` | test_list_memories | GET …/memories |
| `delete_memory` | test_delete_memory_if_any | DELETE …/memories/{id} — ⏭ (no extracted memories) |

Async (`ALLOW_CREATE`): `await get_last_k_messages` / `list_messages` / `get_message` / `search_memories` / `list_memories` / `delete_memory` — all ✅ (delete ⏭).

Coverage gaps: `AsyncMemoryClient.create_memory_session` / `add_messages` are not invoked in async mode (the async module's setup uses the sync client); `MemorySession` / `AsyncMemorySession` wrapper classes are not directly covered.

### MCPGatewayClient (`ALLOW_CREATE`, ⚠️ xfail — SDK `trust_policy` bug)

| Method | HTTP | Status |
|---|---|---|
| `create_mcp_gateway` (+ auto IAM agency) | POST /v1/core/gateways | ⚠️ xfail |
| `get_mcp_gateway` / `list_mcp_gateways` / `update_mcp_gateway` | GET/GET/PUT …/gateways | ⚠️ xfail |
| `create_mcp_gateway_target` / `get_/list_/update_/delete_mcp_gateway_target` | …/targets | ⚠️ xfail |
| `delete_mcp_gateway` | DELETE …/gateways/{id} | ⚠️ xfail |

Read-only `list_mcp_gateways(limit=1)` passes ✅ in `test_readonly_lists` (no resource created).

### RuntimeClient

Control plane (`ALLOW_CREATE`, 🚫 skip — backend requires `artifact_source_config` + `identity_configuration`; read-only `get_agents` ✅ in `test_readonly_lists`):

| Method | HTTP | Status |
|---|---|---|
| `create_agent` | POST /v1/core/runtimes | 🚫 skip |
| `find_agent_by_name` / `find_agent_by_id` / `get_agents` / `update_agent` | GET/GET/GET/PUT …/runtimes | 🚫 skip (get_agents ✅ read-only) |
| `create_agent_endpoint` / `find_/update_/delete_agent_endpoint` | …/endpoints | 🚫 skip |
| `delete_agent_by_name` | DELETE …/runtimes/{id} | 🚫 skip |

Data plane (`RUN_BILLABLE`, 💰):

| Method | Test | HTTP | Status |
|---|---|---|---|
| `start_session` | test_runtime_start_exec_stop | POST /runtimes/{name}/sessions-start | 💰 |
| `exec_command` | same | POST /runtimes/{name}/commands | 💰 |
| `stop_session` | same + teardown | POST /runtimes/{name}/sessions-stop | 💰 |

Not covered: `invoke_agent`, `upload_files`, `download_files`, `create_or_update_agent`.

### CodeInterpreter

Control plane (`ALLOW_CREATE`, ✅):

| Method | Test | HTTP | Status |
|---|---|---|---|
| `create_code_interpreter` | fixture | POST /v1/core/code-interpreters | ✅ |
| `get_code_interpreter` | test_get_code_interpreter | GET …/{id} | ✅ |
| `list_code_interpreters` | test_list_code_interpreters (+ read-only) | GET /v1/core/code-interpreters | ✅ |
| `update_code_interpreter` | test_update_code_interpreter | PUT …/{id} | ✅ |
| `delete_code_interpreter` | teardown | DELETE …/{id} | ✅ (implicit) |

Data plane (`RUN_BILLABLE`, 💰): `code_session` ctx manager, `start_session`, `execute_code`, `get_session`, `stop_session`.

Not covered: `execute_command`, `upload_file(s)`, `download_file(s)`, `install_packages`, `clear_context`, `invoke`.

### Auth decorators + Config (`ALLOW_CREATE`)

| Method | Test | Status |
|---|---|---|
| `require_api_key` | test_require_api_key_injects_key | ✅ |
| `require_sts_token` | test_require_sts_token_injects_credentials | ⏭ |
| `require_access_token` (3LO) | test_require_access_token_3lo_is_manual | ⏭ (slow) |
| `Config.load` / `Config.save` | seeded_identity_config fixture | ✅ (implicit) |

### Summary

Real-cloud run (`ALLOW_CREATE=1`, no `RUN_BILLABLE`): **45 passed / 13 skipped / 6 xfailed / 2 deselected**.

Known coverage gaps to follow up:

1. `AsyncMemoryClient.create_memory_session` / `add_messages` not invoked in async mode.
2. `MemorySession` / `AsyncMemorySession` wrapper classes not directly covered.
3. MCP gateway full lifecycle xfailed (pending `trust_policy` fix).
4. Runtime agent CRUD skipped (pending deployable artifact).
5. `get_resource_oauth2_token` / `get_resource_sts_token` / `complete_resource_token_auth`.
6. CodeInterpreter advanced methods (`execute_command` / `upload_*` / `download_*` / `install_packages` / `clear_context`).
7. Runtime data-plane `invoke_agent` / `upload_files` / `download_files`.
8. `IAMClient.create_agency` (only touched indirectly via MCP, and broken by the policy bug).
