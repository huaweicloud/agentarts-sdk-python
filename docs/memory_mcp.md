# AgentArts Memory MCP Server

`agentarts-memory-mcp` is the stdio MCP server distributed with
`agentarts-sdk`. Its canonical implementation is
`agentarts.toolkit.plugins.memory.mcp`; there is no separate MCP Python
distribution or lockfile.

## Configuration

The MCP host supplies configuration when it starts the process. The Memory
Space, Actor, and Assistant are fixed for the life of that process and cannot
be overridden by a model tool call.

| Variable | Required | Purpose |
| --- | :---: | --- |
| `HUAWEICLOUD_SDK_MEMORY_API_KEY` | Yes | Data-plane API key |
| `AGENTARTS_MEMORY_SPACE_ID` | Yes | Bound Memory Space |
| `HUAWEICLOUD_SDK_REGION` | No | Huawei Cloud region; the SDK default applies when absent |
| `AGENTARTS_MEMORY_ACTOR_ID` | No | Actor filter applied to searches and lists |
| `AGENTARTS_MEMORY_ASSISTANT_ID` | No | Assistant filter and write identity |
| `AGENTARTS_MEMORY_PROJECT_NAME` | No | Session-cache scope for message ingestion |
The existing `AGENTARTS_MEMORY_USER_ID` and platform-derived actor defaults
remain supported for installed code-agent integrations.

Missing required values stop startup with exit code 2. Only variable names are
included in configuration errors.

## Tools

The server preserves the original toolkit tools and adds the portable search
contract:

- `ltm_search(query, top_k=5)`
- `search_memories(query, num=5, threshold=0.7)`
- `add_messages(messages)`
- `list_memories(limit=10, offset=0)`
- `search_summary(query, num=3)`

All inputs have MCP JSON Schema bounds. Read tools carry read-only and
idempotent annotations; `add_messages` is marked non-read-only and
non-idempotent. Successful responses use structured Pydantic models. Upstream
exception details are logged to stderr while MCP callers receive stable,
sanitized tool errors.

## Lifecycle

One `AsyncMemoryClient` is created for each MCP process and closed when the
stdio transport stops. Search, list, session creation, and message ingestion
share this client. Message ingestion retains the existing project-and-actor
session cache so MCP writes and capture hooks reuse compatible sessions.

The server is available through either launch form:

```bash
agentarts-memory-mcp
```

```bash
python -m agentarts.toolkit.plugins.memory.mcp.server
```
