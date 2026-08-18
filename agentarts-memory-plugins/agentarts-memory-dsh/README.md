# agentarts-memory-dsh

`agentarts-memory-dsh` connects DeepSeek Harness (DSH) to Huawei Cloud AgentArts Memory in both directions:

- after each closed DSH turn, it asynchronously writes the turn's human and visible assistant text to AgentArts Memory;
- it starts the search-only `agentarts-memory-mcp` stdio server through DSH's generic MCP client, exposing `mcp__agentarts-memory__ltm_search` to the model.

Writes are implemented inside the plugin and are never exposed as a model tool. Recall stays on the read-only MCP surface.

## Prerequisites

- Node.js `^22.19` or `>=24`;
- a DSH installation compatible with `0.1.0-rc.5`;
- an existing AgentArts Memory Space and its data-plane API key;
- the sibling `agentarts-memory-mcp` executable installed on `PATH`.

Install the MCP server and this plugin:

```bash
uv tool install agentarts-memory-mcp
npm install agentarts-memory-dsh
```

When the DSH resolver uses an explicit package manifest, add `agentarts-memory-dsh` there as a dependency as well.

## Configuration

Set credentials outside source control:

```bash
export HUAWEICLOUD_SDK_MEMORY_API_KEY='<data-plane-api-key>'
export AGENTARTS_MEMORY_SPACE_ID='<space-id>'
export AGENTARTS_MEMORY_ACTOR_ID='<stable-user-or-tenant-id>'
export HUAWEICLOUD_SDK_REGION='cn-southwest-2'
```

`AGENTARTS_MEMORY_ACTOR_ID` must remain stable across the DSH sessions that should share long-term memory. In a multi-user deployment, resolve a distinct value per user or tenant; a shared constant would mix their memory scopes.

Apply [`agentarts-memory.cordis.yml`](agentarts-memory.cordis.yml) as an opt-in profile overlay, or insert the equivalent row:

```yaml
- insert:
    - id: agentarts-memory
      name: agentarts-memory-dsh
      config:
        apiKey: !!js process.env.HUAWEICLOUD_SDK_MEMORY_API_KEY
        spaceId: !!js process.env.AGENTARTS_MEMORY_SPACE_ID
        actorId: !!js process.env.AGENTARTS_MEMORY_ACTOR_ID
        region: !!js process.env.HUAWEICLOUD_SDK_REGION || 'cn-southwest-2'
```

Like DSH's `examples/mcp-memory` overlays, this plugin provisions an already-installed stdio server; it does not run a package manager or initialize the upstream Memory Space. The default command is `agentarts-memory-mcp`. For repository-local development, point it at the virtual-environment entry point:

```yaml
        mcpCommand: /absolute/path/to/agentarts-memory-mcp/.venv/bin/agentarts-memory-mcp
        mcpArgs: []
```

The current `agentarts-memory-mcp` process binds recall to a Space, while `actorId` is attached to synchronized sessions and messages. If a Space contains mutually untrusted actors, use a separate Space/plugin instance per recall boundary; `actorId` alone does not narrow the current MCP search tool.

## Options

| Field | Required | Default | Purpose |
|---|---:|---|---|
| `apiKey` | yes | — | AgentArts Memory data-plane API key; also passed explicitly to the scrubbed MCP child environment |
| `spaceId` | yes | — | Existing AgentArts Memory Space |
| `actorId` | yes | — | Stable user/tenant identity attached to synchronized sessions and messages |
| `assistantId` | no | `deepseek-harness` | Assistant identity on remote sessions and messages |
| `region` | no | `cn-southwest-2` | Region used to derive the data endpoint |
| `dataEndpoint` | no | region-derived | Explicit HTTP(S) data endpoint |
| `requestTimeoutMs` | no | `30000` | Timeout for create-session and add-message requests |
| `maxRetries` | no | `2` | Retries for network, `429`, and `5xx` failures |
| `retryBaseDelayMs` | no | `250` | Initial exponential retry delay |
| `forceExtract` | no | `false` | Request immediate memory extraction after each turn |
| `mcpEnabled` | no | `true` | Mount the search-only MCP server |
| `mcpServerName` | no | `agentarts-memory` | DSH MCP tool namespace |
| `mcpCommand` | no | `agentarts-memory-mcp` | Installed MCP child executable |
| `mcpArgs` | no | `[]` | MCP child arguments |
| `mcpCwd` | no | DSH process cwd at plugin load | MCP child working directory |
| `mcpToolCallTimeoutMs` | no | `60000` | Per-search timeout |
| `mcpFailOnStartupError` | no | `true` | Reject activation when search discovery fails |

## Turn synchronization behavior

The plugin listens to DSH's committed `session/event` feed and acts on `turn/end`. It preserves event order, includes only direct user-source messages and visible assistant text, represents user images as `[image]`, and excludes injected plugin context, tool protocol payloads, and private reasoning. A turn with no eligible content produces no remote write.

Each DSH session maps deterministically to the UUID required by AgentArts: the normal
`session-<uuid>` form uses its UUID suffix, while any other opaque id maps to a stable UUIDv8.
The original DSH id remains in session/message metadata. A `409` during remote session
creation means a resume or reload and reuses the mapped id. Each turn write has a
deterministic idempotency key based on DSH session id, turn number, and closing event
sequence, so retries do not duplicate accepted batches.

Writes are serialized per session. `session/flush` and plugin teardown drain accepted work, while an AgentArts outage is logged without breaking the agent turn. MCP startup is strict by default because a successfully activated integration is expected to expose recall.

## Development

```bash
npm install
npm run check
```

See [`DESIGN.md`](DESIGN.md) for the integration boundaries and failure model.
