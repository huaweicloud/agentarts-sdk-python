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

**Overview**: 69 tests across 12 files. Real-cloud run (`ALLOW_CREATE=1`, no
`RUN_BILLABLE`): **48 passed / 13 skipped / 6 xfailed / 2 deselected**.

Status legend: ✅ real-cloud pass · 🟦 local pass · ⏭ conditional skip ·
⚠️ xfail (SDK bug) · 🚫 skip (backend prereq) · 💰 requires `RUN_BILLABLE=1`

### AgentArtsRuntimeApp (local, 🟦)

| Method / endpoint | Test | Status |
|---|---|---|
| `@app.entrypoint` / `@app.ping` / `@app.websocket` decorators | various | 🟦 |
| `force_ping_status()` / `get_current_ping_status()` | test_ping_* | 🟦 |
| `GET /ping` (default / custom / forced) | test_ping_* (3) | 🟦 |
| `POST /invocations` (JSON 200 / bad-JSON 400 / no-entrypoint 404 / raise 500) | test_invocation_* (4) | 🟦 |
| `POST /invocations` (sync + async generator → SSE) | test_invocation_*_streams_sse (2) | 🟦 |
| `WS /ws` (no-handler 1011 / echo) | test_websocket_* (2) | 🟦 |

Not covered: `@app.async_task`, `has_running_tasks()`, `run()`.

### IdentityClient

| Method | Test | HTTP | Status |
|---|---|---|---|
| `list_workload_identities` | readonly + lifecycle | GET /v1/workload-identities | ✅ |
| `create_workload_identity` | fixture | POST /v1/workload-identities | ✅ |
| `get_workload_identity` | test_get_created_workload_identity | GET …/{name} | ✅ |
| `update_workload_identity` | test_update_workload_identity | PUT …/{name} | ✅ |
| `create_api_key_credential_provider` | fixture | POST /v1/api-key-credential-providers | ✅ |
| `get_api_key_credential_provider` | test_get_api_key_… | GET …/{name} | ✅ |
| `list_api_key_credential_providers` | test_list_api_key_…_contains | GET … | ✅ |
| `create_workload_access_token` | test_create_workload_access_token / test_get_resource_api_key | POST …/for-user-id | ✅ |
| `get_resource_api_key` | test_get_resource_api_key | POST /v1/api-key | ✅ |
| `create/get_oauth2_credential_provider` | test_create_and_delete_oauth2… | POST/GET …/oauth2… | ⏭ (slow) |
| `create/get_sts_credential_provider` | test_create_and_delete_sts… | POST/GET …/sts… | ⏭ |
| `get_workload_identity` / `create_workload_access_token` (pre-provisioned) | test_get_and_token… | GET/POST | ⏭ |
| raw `delete_workload_identity` / `delete_*_credential_provider` | resource_registry teardown | DELETE … | ✅ (implicit) |

Not covered: `get_resource_oauth2_token` (3LO), `get_resource_sts_token`, `complete_resource_token_auth`, `update_*_credential_provider`.

### MemoryClient (sync) — full coverage ✅

| Method | Test | HTTP | Status |
|---|---|---|---|
| `create_space` (with `memory_strategies_builtin`) | fixture | POST /v1/core/spaces (+space-keys) | ✅ |
| `get_space` | test_get_space | GET /v1/core/spaces/{id} | ✅ |
| `list_spaces` | test_list_spaces_contains_created | GET /v1/core/spaces | ✅ |
| `update_space` | test_update_space | PUT /v1/core/spaces/{id} | ✅ |
| `delete_space` | teardown | DELETE /v1/core/spaces/{id} | ✅ (implicit) |
| `create_memory_session` | fixture | POST …/sessions | ✅ |
| `add_messages` (2× `TextMessage`) | fixture | POST …/messages | ✅ |
| `list_messages` | test_list_messages | GET …/messages | ✅ |
| `get_last_k_messages` | test_get_last_k_messages | GET …/messages ×2 | ✅ |
| `get_message` | test_get_message | GET …/messages/{id} | ✅ |
| `search_memories` | test_search_memories | POST …/memories/search | ✅ |
| `list_memories` | test_list_memories | GET …/memories | ✅ |
| `delete_memory` | test_delete_memory_if_any | DELETE …/memories/{id} | ⏭ (no extracted memories) |

### AsyncMemoryClient

| Method | Test | Status |
|---|---|---|
| `create_memory_session` (async) | test_async_create_session_and_add_messages | ✅ |
| `add_messages` (async) | same | ✅ |
| `list_messages` (async) | test_async_list_messages + above | ✅ |
| `get_last_k_messages` (async) | test_async_get_last_k_messages | ✅ |
| `get_message` (async) | test_async_get_message | ✅ |
| `search_memories` (async) | test_async_search_memories | ✅ |
| `list_memories` (async) | test_async_list_memories | ✅ |
| `delete_memory` (async) | test_async_delete_memory_if_any | ⏭ |

Not covered: AsyncMemoryClient's control-plane methods (`create_space`/`get_space`/`list_spaces`/`update_space`/`delete_space` — sync on this class) are not exercised on the async instance; they share `_ControlPlane` with the sync client, so coverage is transitive.

### MemorySession / AsyncMemorySession wrappers

| Method | Test | Status |
|---|---|---|
| constructor (auto-create session) | test_memory_session_wrapper / test_async_session_wrapper | ✅ |
| `add_messages` | same | ✅ |
| `get_last_k_messages` | same | ✅ |
| `list_messages` | same | ✅ |

Not covered: wrapper `get_message` / `search_memories` / `list_memories` / `get_memory` / `delete_memory`, `of()` factory.

### MCPGatewayClient (⚠️ xfail — SDK `trust_policy` bug)

| Method | HTTP | Status |
|---|---|---|
| `create_mcp_gateway` (+ auto IAM agency) | POST /v1/core/gateways | ⚠️ xfail |
| `get_/list_/update_mcp_gateway` | GET/GET/PUT …/gateways | ⚠️ xfail |
| `create/get/list/update/delete_mcp_gateway_target` | …/targets | ⚠️ xfail |
| `delete_mcp_gateway` | DELETE …/gateways/{id} | ⚠️ xfail |
| `list_mcp_gateways(limit=1)` read-only | GET …/gateways | ✅ (test_readonly_lists) |

The bug only manifests on accounts where the shared agency `AgentArtsCoreGateway` does **not** already exist (the malformed `trust_policy` is rejected, PAP5.0011). On accounts where it exists, `create_agency` returns 409 and the SDK swallows it, masking the bug. Fix the `trust_policy` in `src/agentarts/sdk/mcpgateway/mcp_gateway_client.py` (an agency trust policy `Action` should grant `sts:agencies:assumeRole` to the service principal, not resource actions); remove this marker once fixed.

### RuntimeClient

Control plane (🚫 skip — backend requires `artifact_source_config` + `identity_configuration`; read-only `get_agents` ✅):

| Method | Status |
|---|---|
| `create_agent` / `update_agent` / `create_or_update_agent` | 🚫 skip |
| `find_agent_by_name` / `find_agent_by_id` / `delete_agent_by_name` | 🚫 skip |
| `create/update/delete/find_agent_endpoint` | 🚫 skip |
| `get_agents(limit=10)` read-only | ✅ (test_readonly_lists) |

Data plane (💰 `RUN_BILLABLE`):

| Method | Test | HTTP | Status |
|---|---|---|---|
| `start_session` | test_runtime_session_upload_download | POST …/sessions-start | 💰 |
| `exec_command` | same | POST …/commands | 💰 |
| `upload_files` | same | POST …/upload-files | 💰 |
| `download_files` | same | GET …/download-files | 💰 |
| `stop_session` | same + teardown | POST …/sessions-stop | 💰 |

Not covered: `invoke_agent`, `create_or_update_agent` (control plane).

### CodeInterpreter

Control plane (✅ full):

| Method | Test | HTTP | Status |
|---|---|---|---|
| `create_code_interpreter` | fixture | POST /v1/core/code-interpreters | ✅ |
| `get_code_interpreter` | test_get_code_interpreter | GET …/{id} | ✅ |
| `list_code_interpreters` | test_list_… + read-only | GET … | ✅ |
| `update_code_interpreter` | test_update_code_interpreter | PUT …/{id} | ✅ |
| `delete_code_interpreter` | teardown | DELETE …/{id} | ✅ (implicit) |

Data plane (💰 `RUN_BILLABLE`, all in one `code_session`):

| Method | Test | Status |
|---|---|---|
| `code_session` ctx manager | test_code_session_full_workflow | 💰 |
| `start_session` / `stop_session` (via code_session) | same | 💰 |
| `execute_code` | same | 💰 |
| `execute_command` | same | 💰 |
| `upload_file` / `download_file` (round-trip) | same | 💰 |
| `get_session` | same | 💰 |
| `clear_context` | same | 💰 |

Not covered: `upload_files` / `download_files` (multi-file), `install_packages`, `invoke` (raw).

### Auth decorators + Config

| Method | Test | Status |
|---|---|---|
| `require_api_key` | test_require_api_key_injects_key | ✅ |
| `require_sts_token` | test_require_sts_token_injects_credentials | ⏭ |
| `require_access_token` (3LO) | test_require_access_token_3lo_is_manual | ⏭ (slow) |
| `Config.load` / `Config.save` | seeded_identity_config fixture | ✅ (implicit) |

### Coverage by tier

| Client | Read-only | Lifecycle | Billable |
|---|---|---|---|
| AgentArtsRuntimeApp | 🟦 full | — | — |
| IdentityClient | ✅ list | ✅ CRUD + token | — |
| MemoryClient (sync) | — | ✅ full (13) | — |
| AsyncMemoryClient | — | ✅ 8 | — |
| MemorySession / Async | — | ✅ 4 + 4 | — |
| MCPGatewayClient | ✅ list | ⚠️ xfail | — |
| RuntimeClient control | ✅ get_agents | 🚫 skip | — |
| RuntimeClient data | — | — | 💰 5 |
| CodeInterpreter control | ✅ list | ✅ full (5) | — |
| CodeInterpreter data | — | — | 💰 8 |
| Auth decorators | — | ✅ api_key | — |
| Config | — | ✅ | — |

### SDK bugs found by this suite

| # | Bug | Fix commit | Status |
|---|---|---|---|
| 1 | `MemoryClient` control-plane methods referenced `self._data_plane._region_name` (non-existent) → AttributeError | `f82c936` | ✅ fixed + cloud-verified |
| 2 | `MemorySession.__repr__` referenced `self.region_name` (no property) → AttributeError | `f82c936` | ✅ fixed + local-verified |
| 3 | `MemorySession` / `AsyncMemorySession` passed `session_config.to_dict()` (dict) to data-plane `create_memory_session`, which expects a `SessionCreateRequest` object → AttributeError | `e5a330d` | ✅ fixed + cloud-verified |
| 4 | `MCPGatewayClient` auto-agency `trust_policy` rejected by IAM (PAP5.0011) | — | ⚠️ xfail, pending fix |

### Remaining coverage gaps

1. `AgentArtsRuntimeApp`: `@app.async_task`, `has_running_tasks()`, `run()`.
2. `IdentityClient`: `get_resource_oauth2_token` (3LO), `get_resource_sts_token`, `complete_resource_token_auth`, `update_*_credential_provider`.
3. `AsyncMemoryClient` control-plane methods (transitive coverage only).
4. `MemorySession` / `AsyncMemorySession`: `get_message` / `search_memories` / `list_memories` / `get_memory` / `delete_memory`, `of()` factory.
5. MCP gateway full lifecycle (pending `trust_policy` fix).
6. Runtime agent control-plane CRUD (pending deployable artifact); `create_or_update_agent`, `update_agent`.
7. Runtime data-plane `invoke_agent`.
8. CodeInterpreter: `upload_files` / `download_files` (multi-file), `install_packages`, `invoke` (raw).
9. `IAMClient.create_agency` (only touched indirectly via MCP, broken by the policy bug).

## Toolkit (CLI) tests

Tests under `tests/integration/toolkit/` exercise the real `agentarts` CLI
(Typer app) end-to-end — no mocking of operations or SDK clients. They cover the
`toolkit` layer that the SDK-only tests above do not.

### Invocation styles

Two ways the CLI is driven, chosen per test:

- **`cli_runner` (in-process `typer.testing.CliRunner`)** — fast; used for local
  commands (`init`, `config`) where assertions are on generated files, not stdout
  (rich output capture is unreliable under CliRunner).
- **`agentarts_cmd` + `cli_env` (subprocess)** — invokes the real console entry
  (`python -c "from agentarts.toolkit.main import app; app()" …`). Reliable
  stdout capture (no TTY → rich emits plain text); used for cloud commands whose
  output must be parsed (`memory create --output json`) and for the blocking
  `dev` server.

### Completion handling

The CLI's `_auto_install_completion` touches `~/.agentarts` on first run, and
setting `_AGENTARTS_COMPLETE` (the obvious skip) instead trips click's
completion protocol ("Invalid completion instruction"). So:

- in-process (`cli_runner`): `monkeypatch.setattr` `_auto_install_completion` to
  a no-op;
- subprocess (`cli_env`): `HOME` is redirected to a temp dir with the
  `.agentarts/.completion_shown` marker pre-created, so the install is skipped
  and no tip text pollutes stdout (important for `--output json` parsing).

For `config`/`init`, every flag the callback would otherwise `Prompt.ask` for is
passed explicitly (CliRunner has no stdin → an unhandled prompt aborts with
exit 1). For `dev` (blocking uvicorn), the test scaffolds a basic project via
`init`, launches `agentarts dev` in a subprocess on a free port, polls `/ping`,
POSTs `/invocations`, then terminates the process.

### Toolkit command coverage

Status: ✅ real-cloud/local pass · ⏭ conditional skip · ⚠️ xfail (SDK bug) ·
💰 requires `RUN_BILLABLE=1` · 🚫 skip (prereq).

| CLI command | Style | Test | Status |
|---|---|---|---|
| `--version` / `--help` | CliRunner | test_cli_version / test_cli_help | ✅ |
| `init -n … -t {basic,langgraph,langchain,google-adk}` | CliRunner | test_init_creates_project_files (×4) | ✅ |
| `init -p` / invalid name | CliRunner | test_init_path_option / test_init_invalid_name_fails | ✅ |
| `config` (add agent) | CliRunner | test_config_add_writes_yaml_and_lists | ✅ |
| `config set` / `config get` | CliRunner | test_config_set_get_roundtrip | ✅ |
| `config set-env` / `list-env` / `remove-env` | CliRunner | test_config_env_lifecycle | ✅ |
| `config set-default` / `remove` | CliRunner | test_config_set_default_and_remove | ✅ |
| `dev` (uvicorn server) | subprocess | test_dev_server_serves_ping_and_invocations | ✅ |
| `memory list` | subprocess | test_cli_memory_list_readonly | ✅ |
| `memory create/list/get/update/delete` | subprocess | test_cli_memory_lifecycle | ✅ (ALLOW_CREATE) |
| `mcp-gateway list-mcp-gateways` | subprocess | test_cli_mcp_gateway_list_readonly | ✅ |
| `mcp-gateway create-mcp-gateway …` | subprocess | test_cli_mcp_gateway_lifecycle | ⚠️ xfail (SDK trust_policy) |
| `invoke --mode cloud` | subprocess | test_cli_invoke_cloud | 💰 |
| `runtime start/exec/upload/download/stop-session` | subprocess | test_cli_runtime_session_lifecycle | 💰 |

### Toolkit not covered

- `deploy` / `launch` — needs Docker daemon + SWR push + cloud runtime create;
  too heavy and residue-prone for the suite (the underlying `RuntimeClient`
  control-plane path is itself skipped pending an artifact).
- `destroy` — destructive cloud op; covered transitively as the teardown tool
  for `deploy`, not exercised standalone.
- `mcp-gateway` target subcommands and full gateway lifecycle — xfailed pending
  the SDK `trust_policy` fix.
- `runtime`/`memory`/`mcp-gateway` subcommands beyond the ones listed above
  (e.g. `memory status`, `mcp-gateway *-target` CRUD) — not yet added.

### Toolkit test results

Real-cloud run (`ALLOW_CREATE=1`, no `RUN_BILLABLE`): **16 passed / 2 skipped
(runtime billable) / 1 xfailed (mcp-gateway)**. Combined with the SDK suite the
whole `tests/integration` tree is **64 passed / 15 skipped / 7 xfailed / 2
deselected** (counts vary slightly with conditional skips).
