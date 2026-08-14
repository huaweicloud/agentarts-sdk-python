# agentarts-memory-hermes

A Hermes Memory Provider plugin that uses Huawei Cloud AgentArts Memory as the long-term memory backend for Hermes Agent.

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
| `AGENTARTS_MEMORY_SPACE_ID`     | AgentArts memory space ID          |
| `HUAWEICLOUD_SDK_MEMORY_API_KEY`| AgentArts memory space API Key     |
| `HUAWEICLOUD_SDK_REGION`        | Region (default `cn-southwest-2`)  |

## Installation

There are two installation methods — choose either one.

### Option 1: Install as a memory provider

Copy the plugin directory to Hermes' memory provider plugin path:

```bash
cp -r agentarts-memory-hermes  ~/.hermes/hermes-agent/plugins/memory/
```

Configure interactively via `hermes memory setup`, or manually set the environment variables above. Follow the prompts to select `agentarts_memory` and complete configuration.

### Option 2: Install as a general plugin

Copy the plugin directory to Hermes' general plugin path and register via the `hermes plugins` command:

```bash
cp -r agentarts-memory-hermes ~/.hermes/plugins/
```

Configure interactively via `hermes plugins`, or manually set the environment variables above. Follow the prompts to select `agentarts_memory` and complete configuration.

## Configuration

During configuration, you will be prompted to enter the API Key, Space ID, etc. Sensitive fields (API Key) are written to `.env`, while non-sensitive config (`space_id`, `region`) is written to `$HERMES_HOME/agentarts.json`.

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

| Command | Description |
|---|---|
| `hermes agentarts_memory status` | Show provider status and environment variable configuration |
| `hermes agentarts_memory config` | Show saved non-sensitive configuration |
| `hermes agentarts_memory test` | Test provider connectivity |

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
pytest tests/unit/ -v
```
