# agentarts-memory-hermes

A Hermes Memory Provider plugin that uses Huawei Cloud AgentArts Memory as the cloud memory backend for Hermes Agent.

## Overview

- **Cross-session memory persistence**: Automatically writes conversation content to AgentArts Memory after each turn (non-blocking)
- **Context injection**: Automatically injects relevant memories before each LLM call (user profile / episodic / semantic + history summary)
- **Compression protection**: Re-injects relevant memories before context compression to prevent key information from being dropped
- **MEMORY.md mirroring**: Syncs Hermes built-in `MEMORY.md` writes to AgentArts
- **Active retrieval tools**:
  - `ltm_search` — Search long-term memory and return entries relevant to the query
  - `ltm_search_summary` — Get a list of memory summaries

## Prerequisites

1. Install Hermes (installation guide: https://hermes-agent.nousresearch.com/docs/getting-started/installation)
2. Create a Huawei Cloud AgentArts memory space, and obtain the region (`HUAWEICLOUD_SDK_REGION`), memory space ID (`AGENTARTS_MEMORY_SPACE_ID`), and API Key (`HUAWEICLOUD_SDK_MEMORY_API_KEY`)

| Parameter                       | Description                        |
|---------------------------------|------------------------------------|
| `AGENTARTS_MEMORY_SPACE_ID`     | AgentArts memory space ID           |
| `HUAWEICLOUD_SDK_MEMORY_API_KEY`| AgentArts memory space API Key       |
| `HUAWEICLOUD_SDK_REGION`        | Region (default `cn-southwest-2`)   |

## Installation

Copy the plugin directory `agentarts-memory-hermes` to Hermes' memory provider plugin path and rename it to `agentarts`:

```bash
cp -r agentarts-memory-hermes  ~/.hermes/hermes-agent/plugins/memory/agentarts
```

## Configuration

Configure interactively via the `hermes memory setup` command. Follow the prompts to select `agentarts`, then enter the correct parameters to complete configuration.

## Tools

### ltm_search

Search AgentArts long-term memory and return entries relevant to the query.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | string | Yes | — | Search query string |
| `top_k` | integer | No | 5 | Return top K results |

### ltm_search_summary

Get a list of AgentArts memory summaries.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `limit` | integer | No | 10 | Number of entries to return |

## CLI Commands

After the plugin is registered, the following CLI subcommands are available (only when the provider is active):

| Command                | Description              |
|------------------------|--------------------------|
| `hermes memory status` | Show provider status     |
| `hermes memory setup`  | Configure the provider   |
| `hermes memory off`    | Disable the provider     |

## Architecture

- **Client mode**: Uses `MemoryClient` (Client mode), not Session mode
- **Non-blocking sync**: `sync_turn` executes `add_messages` in a daemon thread, not blocking the Hermes main loop
- **Profile isolation**: All paths use the `hermes_home` kwarg from `initialize()`
- **Thread safety**: `_lock` protects concurrent read/write to `_client`

## Lifecycle Hooks

| Hook | When | Responsibility |
|---|---|---|
| `system_prompt_block` | System prompt assembly | Inject memory capability description |
| `prefetch` | Before each LLM call | Search and inject relevant memories |
| `sync_turn` | After each conversation turn | Non-blocking write of conversation content |
| `on_pre_compress` | Before context compression | Re-inject relevant memories |
| `on_memory_write` | On built-in memory write | Mirror MEMORY.md to AgentArts |
| `on_session_end` | On session end | No-op (turns already persisted per-turn) |
| `shutdown` | On process exit | Clean up connections |

## FAQ

### No search results?

AgentArts Memory takes time to generate memories from conversation messages (about 30 seconds). Content written by `sync_turn` is not immediately searchable; `prefetch` searches memories generated from earlier turns.

### Authentication failure?

Check:
1. Whether the API Key is valid
2. Whether the region configuration is correct
3. Whether the Space status is `running`

## Development

```bash
pip install -e ".[dev]"
pytest tests/unit/toolkit/plugins/memory/hermes/ -v
```

## About AgentArts Memory

Huawei Cloud AgentArts Memory is a cloud-based memory solution for AI agents, providing full-lifecycle management of agent memory data.

### Advantages of AgentArts Memory

1. **Out of the box**: Supports both short-term memory (7–365 days) and long-term memory (persistent storage), meeting different time-span memory requirements.

2. **Multiple memory strategies**: Supports strategies such as semantic memory, user preferences, session summaries, and episodic memory to meet various scenario needs.

3. **Multi-dimensional isolation**: Supports memory isolation by space, session, and user dimension, ensuring data security and independence.

4. **Fully managed, zero maintenance**: Fully managed on the cloud — no need to manage databases or memory processing engines, enabling fast business launch and reducing operational costs and complexity.

> Official documentation: [Memory Space Overview](https://support.huaweicloud.com/highcode-agentarts/agentarts_10_015.html)
