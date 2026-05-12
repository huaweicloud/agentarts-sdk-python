# Huawei Cloud AgentArts SDK

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Build, deploy and manage AI agents with Huawei Cloud capabilities.

## Overview

Huawei Cloud AgentArts SDK is a comprehensive toolkit for developing, deploying, and managing AI agents. It provides seamless integration with Huawei Cloud services while supporting mainstream agent frameworks.

### Key Features

- **Framework Agnostic** - Compatible with LangChain, LangGraph, AutoGen, CrewAI, Google ADK, and any custom agent framework
- **One-Click Deployment** - Deploy agents to Huawei Cloud with a single command
- **Built-in Tools** - Code interpreter sandbox, memory management, MCP gateway support
- **Cloud Integration** - Seamless integration with Huawei Cloud authentication, monitoring, and logging
- **CLI Toolkit** - Complete command-line tools for project initialization, local development, and cloud deployment

### Repository Structure

```
agentarts-sdk-python/
├── src/agentarts/
│   ├── sdk/                    # Core SDK modules
│   │   ├── runtime/            # HTTP server runtime (AgentArtsRuntimeApp)
│   │   ├── memory/             # Conversation memory management
│   │   ├── tools/              # Built-in tools (Code Interpreter)
│   │   ├── mcpgateway/         # MCP Gateway client
│   │   ├── identity/           # Authentication & authorization
│   │   ├── integration/        # Framework adapters (LangGraph, etc.)
│   │   └── service/            # HTTP clients for cloud services
│   └── toolkit/                # CLI toolkit
│       ├── cli/                # Command-line interface
│       ├── operations/         # CLI operation handlers
│       └── utils/templates/    # Project templates
├── docs/                       # Documentation
│   └── cn/                     # Chinese documentation
│       ├── sdk_user_guide/     # SDK usage guides
│       └── toolkit_user_guide/ # CLI usage guides
└── tests/                      # Test suites
```

## Wrapping Your Agent as HTTP Server

The SDK provides `AgentArtsRuntimeApp` to wrap your agent logic as a standard HTTP server, exposing:

- `POST /invocations` - Main agent invocation endpoint
- `GET /ping` - Health check endpoint
- `WS /ws` - WebSocket endpoint for streaming

### Example: LangGraph Agent

```python
# agent.py
import os
from typing import Dict, Any, TypedDict, Annotated
from operator import add

from agentarts.sdk import AgentArtsRuntimeApp, RequestContext

app = AgentArtsRuntimeApp()


class State(TypedDict):
    messages: Annotated[list, add]
    query: str
    response: str


class LangGraphAgent:
    def __init__(self):
        self.model_name = os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini")
        self._graph = None

    def _build_graph(self):
        from langgraph.graph import StateGraph, END
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, AIMessage

        llm = ChatOpenAI(
            model=self.model_name,
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL")
        )

        async def process_node(state: State) -> Dict[str, Any]:
            query = state.get("query", "")
            messages = state.get("messages", []) or [HumanMessage(content=query)]
            response = await llm.ainvoke(messages)
            return {
                "messages": [AIMessage(content=response.content)],
                "response": response.content,
            }

        workflow = StateGraph(State)
        workflow.add_node("process", process_node)
        workflow.set_entry_point("process")
        workflow.add_edge("process", END)
        return workflow.compile()

    async def run(self, query: str) -> Dict[str, Any]:
        graph = self._graph or self._build_graph()
        self._graph = graph
        result = await graph.ainvoke({"messages": [], "query": query, "response": ""})
        return {"response": result.get("response", "")}


_agent = LangGraphAgent()


@app.entrypoint
async def handler(payload: Dict[str, Any], context: RequestContext = None) -> Dict[str, Any]:
    query = payload.get("message", "")
    return await _agent.run(query)


if __name__ == "__main__":
    app.run()
```

### Key Points

1. **Focus on Agent Logic** - You only need to implement the agent logic; the SDK handles HTTP server, request parsing, and response formatting
2. **Framework Agnostic** - Works with any agent framework (LangChain, LangGraph, AutoGen, CrewAI, or custom implementations)
3. **Simple Decorator** - Use `@app.entrypoint` to mark your handler function
4. **Context Support** - Optional `RequestContext` parameter provides session info and request metadata
5. **Configurable Model** - Model name can be configured via environment variable (e.g., `OPENAI_MODEL_NAME`)

## Installation

### Requirements

- Python 3.10 or higher
- pip or uv package manager

### Create Virtual Environment (Recommended)

It is recommended to install the SDK in a virtual environment to avoid dependency conflicts.

**Windows:**

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Or using Command Prompt
.\venv\Scripts\activate.bat
```

**Linux/macOS:**

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### Install via pip

**Windows:**

```powershell
pip install agentarts-sdk
```

**Linux/macOS:**

```bash
pip install agentarts-sdk
```

### Install with Optional Dependencies

```bash
# With LangChain support
pip install agentarts-sdk[langchain]

# With LangGraph support
pip install agentarts-sdk[langgraph]

# With all optional dependencies
pip install agentarts-sdk[all]
```

### Install from Source

**Windows:**

```powershell
git clone https://github.com/huaweicloud/agentarts-sdk-python.git
cd agentarts-sdk-python

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install in development mode
pip install -e ".[dev]"
```

**Linux/macOS:**

```bash
git clone https://github.com/huaweicloud/agentarts-sdk-python.git
cd agentarts-sdk-python

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

### Configure Huawei Cloud Credentials

Set environment variables for Huawei Cloud authentication:

**Windows (PowerShell):**

```powershell
$env:HUAWEICLOUD_SDK_AK = "your-access-key"
$env:HUAWEICLOUD_SDK_SK = "your-secret-key"
```

**Windows (Command Prompt):**

```cmd
set HUAWEICLOUD_SDK_AK=your-access-key
set HUAWEICLOUD_SDK_SK=your-secret-key
```

**Linux/macOS:**

```bash
export HUAWEICLOUD_SDK_AK="your-access-key"
export HUAWEICLOUD_SDK_SK="your-secret-key"
```

> **Note:** Get your AK/SK from [Huawei Cloud Console](https://console.huaweicloud.com/) -> My Credentials -> Access Keys.

For complete environment variable configuration, see [Environment Variables Guide](docs/cn/sdk_user_guide/environment_variables.md).

## Quick Start

### 1. Initialize a New Project

```bash
# Create a new agent project with LangGraph template
agentarts init -n my_agent -t langgraph

# Available templates: basic, langchain, langgraph, google-adk
```

This creates:

```
my_agent/
├── agent.py              # Agent implementation
├── requirements.txt      # Python dependencies
├── .agentarts_config.yaml # Project configuration
└── Dockerfile            # Docker build file
```

### 2. Configure Environment

Edit `.agentarts_config.yaml` to set environment variables:

```yaml
runtime:
  environment_variables:
    - key: OPENAI_API_KEY
      value: "your-openai-api-key"
    - key: OPENAI_MODEL_NAME
      value: "gpt-4o-mini"  # Optional: gpt-4o, gpt-4-turbo, etc.
    - key: OPENAI_BASE_URL
      value: ""  # Optional: custom API endpoint
```

### 3. Local Development

```bash
# Start local development server
agentarts dev

# Server runs at http://127.0.0.1:8080
# Endpoints:
#   POST /invocations - Invoke agent
#   GET  /ping        - Health check
```

### 4. Deploy to Huawei Cloud

```bash
# Configure region
agentarts config set region cn-southwest-2

# Deploy to cloud
agentarts deploy

# Check deployment status
agentarts status

# Invoke deployed agent
agentarts invoke '{"message": "Hello, AgentArts!"}'

# Destroy deployment
agentarts destroy
```

## CLI Commands Reference

| Command                 | Description                                    |
| ----------------------- | ---------------------------------------------- |
| `agentarts init`        | Initialize a new agent project                 |
| `agentarts dev`         | Start local development server                 |
| `agentarts config`      | Configure SDK settings (alias: `configure`)    |
| `agentarts deploy`      | Deploy agent to Huawei Cloud (alias: `launch`) |
| `agentarts invoke`      | Invoke deployed agent                          |
| `agentarts status`      | Check deployment status                        |
| `agentarts destroy`     | Remove deployed agent                          |
| `agentarts mcp-gateway` | Manage MCP gateways                            |

## Limitations & Requirements

### Python Version

- **Minimum:** Python 3.10
- **Recommended:** Python 3.10 or 3.11

### Framework Versions

When using optional framework dependencies, ensure the following minimum versions:

| Framework      | Minimum Version | Install Command                        |
| -------------- | --------------- | -------------------------------------- |
| LangGraph      | 1.0.0           | `pip install agentarts-sdk[langgraph]` |
| LangChain      | 0.1.0           | `pip install agentarts-sdk[langchain]` |
| langchain-core | 0.1.0           | Included with langgraph/langchain      |

> **Note:** LangGraph 1.0+ introduces a new Checkpoint format with required fields (`step`, `pending_sends`, `parents`). The SDK's integration module is compatible with LangGraph 1.0 and above.

### Docker

Docker is required for:

- Building and deploying agents with `agentarts deploy` (alias: `launch`)

**Install Docker:**

- [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
- [Docker Engine for Linux](https://docs.docker.com/engine/install/)

### Resource Quotas

Refer to [Huawei Cloud AgentArts Documentation](https://docs.huaweicloud.com/agentarts) for resource quotas and limits.

## Documentation

- [SDK User Guides](docs/cn/sdk_user_guide/) - Memory, Code Interpreter, MCP Gateway
- [CLI User Guides](docs/cn/toolkit_user_guide/) - init, config, deploy, invoke, status, destroy
- [Contributing Guide](CONTRIBUTING.md) - Development setup and guidelines
- [Architecture](ARCHITECTURE.md) - System architecture overview

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting
black . && isort .

# Type checking
mypy agentarts

# Linting
ruff check .
```

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Support

- **Issues:** [GitHub Issues](https://github.com/huaweicloud/agentarts-sdk-python/issues)
- **Documentation:** <https://support.huaweicloud.com/productdesc-agentarts/agentarts_03_0002.html>
- **Email:** <hwagentartssdk@huawei.com>

