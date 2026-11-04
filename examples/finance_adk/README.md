# Finance Agent Demo (Google ADK + AgentArts Memory/Code Interpreter)

A personal finance assistant demo built with Google ADK, integrating AgentArts Memory (cross-session preference tracking) and Code Interpreter (pandas data analysis + matplotlib chart generation).

## Features

- **Expense tracking** — Record and query expenses by date/category (local JSON storage)
- **Data analysis** — pandas-based spending analysis in a Code Interpreter sandbox (summary, trend, compare)
- **Chart generation** — matplotlib pie/bar/line charts via Code Interpreter
- **Cross-session memory** — Remembers user budget, spending habits, and preferences across conversations
- **Dual-channel memory** — Auto-injection via `before_model_callback` + on-demand recall via `recall_memory` tool

## How AgentArts Memory Works Here

LLM agents are stateless — each session starts with a blank context. AgentArts
Memory closes this gap by giving the agent a long-term store it can read from
and write to across sessions:

- **Four builtin extraction strategies** (semantic, episodic, user_preference,
  summary) run on the backend and turn conversation history into structured,
  searchable memory entries automatically.
- **Auto-injection** — `before_model_callback` searches the memory store before
  every LLM call and injects the top-3 relevant entries into the context, so the
  agent already "knows" the user's budget and habits without being told again.
- **On-demand recall** — the `recall_memory` tool lets the agent dig deeper with
  a targeted query when the auto-injected preview isn't enough.
- **Async extraction** — `after_agent_callback` writes the conversation to the
  memory service without blocking the response, accepting eventual consistency.

## Architecture

```
User Input
  │
  ▼
ADK Runner
  ├── before_model_callback  → search_memory → inject [Memory Context]
  ├── LlmAgent (LiteLLM)     → calls tools as needed
  │     ├── record_expense / query_expenses  (local JSON)
  │     ├── analyze_spending / generate_chart (Code Interpreter)
  │     └── recall_memory                     (Memory Service)
  └── after_agent_callback   → add_session_to_memory (async extraction)
```

## Setup

### 0. Install the AgentArts SDK (from repository root)

`requirements.txt` references `agentarts-sdk`, which is the package in this
repository (not published to PyPI). Install it first from the project root:

```bash
uv sync            # or: pip install -e .
```

### 1. Install demo dependencies

```bash
uv pip install -r examples/finance_adk/requirements.txt
```

### 2. Configure environment

```bash
cd examples/finance_adk
cp .env.example .env
```

Edit `.env` and fill in your LLM API Key and Base URL.

### 3. Create Memory Space

```bash
uv run python examples/finance_adk/setup_memory.py
```

This creates an AgentArts Memory space with all 4 builtin strategies (semantic, episodic, user_preference, summary) and writes credentials to `.env`.

### 4. Create Code Interpreter resource

```bash
uv run python examples/finance_adk/setup_code_interpreter.py
```

This creates a Code Interpreter resource and writes its name to `.env`.

## Usage

```bash
# Normal mode
uv run python examples/finance_adk/finance_agent.py

# Debug mode (verbose memory search/extraction logs)
uv run python examples/finance_adk/finance_agent.py --debug
```

### Demo Flow

**Session 1:**
```
You: I spent 35 on lunch, 18 on a taxi, and 49 on a book today.
Assistant: Recorded 3 expenses: dining 35, transport 18, shopping 49, total 102 CNY.

You: My monthly budget is 5,000 CNY, and I want to keep dining under 1,500.
Assistant: Got it. Monthly budget 5,000 CNY, dining budget 1,500 CNY.
  → after_agent_callback triggers memory extraction

You: Analyze my spending structure this month.
Assistant: [calls analyze_spending → Code Interpreter pandas]
  This month's total spending is 3,245 CNY: dining 37%, shopping 27%, transport 14%, other 22%

You: Draw a pie chart.
Assistant: [calls generate_chart → Code Interpreter matplotlib]
  Pie chart saved to chart_pie_this_month.png
```

**Session 2 (next day):**
```
You: How much can I still spend this month?
  → before_model_callback auto-injects: "User monthly budget 5,000 CNY"
Assistant: Your monthly budget is 5,000 CNY, you've spent 3,245 CNY, 1,755 CNY remaining.
```

## File Structure

| File | Description |
|------|-------------|
| `config.py` | Environment variables, constants |
| `prompts.py` | System prompt |
| `expense_store.py` | Local JSON expense storage |
| `finance_tools.py` | 5 tool functions (expense, analysis, chart, memory) |
| `memory_tools.py` | `recall_memory` tool |
| `finance_agent.py` | ADK Agent + callbacks + CLI entry |
| `session_manager.py` | Multi-session management |
| `setup_memory.py` | Memory Space creation (run once) |
| `setup_code_interpreter.py` | Code Interpreter resource creation (run once) |
| `cli_flags.py` | Debug flag |

## Key Design Decisions

- **`before_model_callback`** for memory injection (ADK native, no custom node needed)
- **`after_agent_callback`** for memory extraction (Runner doesn't auto-call `add_session_to_memory`)
- **`code_session`** context manager per tool call (auto cleanup, no long-lived sessions)
- **`auto_create_session=True`** in Runner (ADK default is False)
- **LiteLLM format** model names (`openai/deepseek-v4-flash`) via config auto-prefix
- **Async memory extraction** — accepts eventual consistency, doesn't block responses

## FAQ

### Code Interpreter session start times out

`analyze_spending` / `generate_chart` open a sandbox session on each call. The
SDK's default HTTP request timeout is 30 seconds, but `start_session` can take
60+ seconds on a cold start (first call in a while, or when the sandbox needs
to be provisioned), causing a timeout error.

The demo ships with the SDK defaults. If you hit this, a known workaround is
to raise the data-plane request timeout to 180s. In
`finance_tools.py`, uncomment the block inside `_code_session()`:

```python
# 恢复 180s 超时的备选方案（默认使用 SDK 的 30s）：
#   from agentarts.sdk.service.http_client import RequestConfig
#   client.data_plane_client._config = RequestConfig(
#       base_url=client.data_plane_client._config.base_url,
#       timeout=180.0,
#       headers=client.data_plane_client._config.headers,
#       verify_ssl=client.data_plane_client._config.verify_ssl,
#   )
```

Note: `CodeInterpreter` / `DataToolsHttpClient` do not currently expose a
`timeout` parameter, so this touches an internal attribute. Once the SDK adds
a public timeout option, the workaround can be removed.

### Multi-turn error `Missing reasoning_content`

Reasoning models (e.g. DeepSeek-V4-Flash) return a `reasoning_content` field
in assistant messages. Some platforms require that field on every historical
assistant message; ADK doesn't persist it, so multi-turn conversations can
fail around the 3rd-4th turn with:

```
BadRequestError: Missing `reasoning_content` field in the assistant message at index N
```

The demo does **not** enable any workaround by default. If you hit this with a
reasoning model, uncomment the `generate_config` block in `build_agent()`
(`finance_agent.py`) and re-enable the `generate_content_config` argument:

```python
generate_config = types.GenerateContentConfig(
    http_options=types.HttpOptions(
        extra_body={"thinking": {"type": "disabled"}}
    )
)
```

**Important:** the exact parameter name and value differ across models and
platforms (`thinking.type`, `enable_thinking`, `thinking_budget`, ...). Always
check the API documentation of the model/platform you are actually using.