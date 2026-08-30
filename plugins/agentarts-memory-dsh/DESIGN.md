# AgentArts Memory integration design for DeepSeek Harness

## Goals

The plugin has two independent responsibilities with one shared configuration: synchronize completed DSH turn material into AgentArts Memory, and make AgentArts long-term-memory search available to the model. It does not replace DSH session persistence, replay, fork, compaction, or crash repair.

## Architecture

```text
DSH session/event (turn/end)
        |
        v
turn projector -- direct HTTPS --> AgentArts Memory data plane
        |                              create/reuse session + add messages
        |
        +-- excludes reasoning, tool protocol, and plugin injections

DSH tools <-- dsh-mcp-client <-- stdio --> agentarts-memory-mcp
                                              |
                                              +--> AgentArts ltm_search
```

Committed-turn synchronization is not routed through MCP. The Node plugin uses the small, stable data-plane subset already implemented by the Python SDK: Bearer authentication, `POST /sessions`, and `POST /sessions/{id}/messages`. This keeps durable turn ingestion independent from model tool selection. The MCP server bundled with `agentarts-sdk` provides the model-callable memory tools. Following DSH's `examples/mcp-memory` contract, the plugin provisions an already-installed `agentarts-memory-mcp` command; it does not embed a second server, run a package manager, or create a Memory Space.

## Identity and idempotency

`actorId` is required because it defines who may share extracted memory across remote
sessions. `actorId` and `assistantId` are attached to synchronized sessions/messages and
passed to the MCP child as process-bound search filters, so ingestion and recall use the
same identity scope. AgentArts requires a UUID session id, so the normal DSH
`session-<uuid>` form uses its suffix and any other opaque DSH id maps deterministically
to UUIDv8. The original id is retained in metadata. This makes resume and hot reload
converge on the same remote session; a create conflict is treated as reuse.

A remote add-message batch uses a SHA-256 idempotency key derived from `(dshSessionId, turn, turnEndSeq)`. Network retries and repeated delivery of the same durable turn therefore converge without requiring local mutable checkpoints. Forked DSH sessions have different ids and only publish their new live turns; constructor seed history is not emitted again by DSH.

## Projection policy

The projector reads the exact interval between the matching `turn/start` and `turn/end`:

- direct `user/message` events (`source.kind === 'user'`) become user text;
- `assistant/message` visible text becomes assistant text;
- user images become a stable `[image]` marker;
- reasoning, tool calls/results, plugin-injected context, and unknown assistant blocks are omitted.

This policy gives the extraction service human conversation rather than DSH's internal execution transcript. Event order is preserved. Error, aborted, blocked, and max-token turns are not special-cased: any committed eligible message is useful evidence, while an empty turn creates no write.

## Lifecycle and failures

`session/event` cannot block the append hot path, so each turn is queued. A per-session promise chain preserves ordering. The `session/flush` listener waits for accepted work, session disposal retires state after its tail settles, and plugin disposal drains all tails before closing the client.

Network failures, `429`, and `5xx` responses retry with bounded exponential backoff. Authentication and other client failures fail immediately. Exhausted sync errors are logged and contained so an optional long-term-memory service cannot invalidate the DSH turn that already committed. Request timeout, retry count, delay, and forced extraction are configuration fields rather than hidden deployment policy.

The DSH MCP client owns child-process start, discovery, reconnect, tool registration, and teardown. The plugin passes the MCP server's supported environment explicitly because DSH deliberately scrubs credential-like ambient variables before starting stdio MCP children. MCP discovery failure rejects plugin activation by default so the integration cannot appear healthy without recall.

## Security

Configuration stores an API-key credential reference rather than expanding the secret
into Cordis YAML. A literal key remains an optional compatibility override. The plugin
resolves the reference through `ctx.credentials` for every data-plane request, falling
back to the launch-environment snapshot only when no credentials service is mounted.
Credentials are never included in errors, metadata, or idempotency keys. HTTP diagnostics
expose only status, service error code, and service message.

The MCP child receives only the resolved AgentArts key plus the connection and identity
variables. Because stdio child environment is process-bound, a rotated key reaches turn
writes immediately but requires plugin reload to reach MCP tools. Its Space,
Actor, and Assistant filters are also fixed at process startup and cannot be overridden by
a model tool call. The MCP tool schemas are owned by `agentarts-memory-mcp`.
