# Huawei Cloud AgentArts SDK

[!\[License\](https://img.shields.io/badge/License-Apache%202.0-blue.svg null)](https://opensource.org/licenses/Apache-2.0)
[!\[Python\](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg null)](https://www.python.org/)
[!\[Code style: black\](https://img.shields.io/badge/code%20style-black-000000.svg null)](https://github.com/psf/black)

Huawei Cloud AgentArts SDK - Build, deploy and manage AI agents with cloud capabilities.

## ✨ Key Features

- 🚀 **Rapid Development** - Support for mainstream Agent frameworks (LangChain, LangGraph, AutoGen, CrewAI)
- 🧠 **Intelligent Memory** - Built-in short-term and long-term memory systems with vector retrieval
- 🔧 **Code Interpreter** - Secure sandbox environment for code execution
- 🔐 **Identity Management** - Complete authentication and permission management system
- 🌐 **MCP Gateway** - Model Context Protocol support
- 📡 **Service Wrapper** - Automatically wrap Agents as HTTP/WebSocket services
- 📊 **Monitoring & Alerting** - Comprehensive monitoring and logging system
- ☁️ **Cloud Deployment** - Seamless integration with Huawei Cloud platform

## 📦 Installation

```bash
# Basic installation
pip install huaweicloud-agentarts-sdk

# Install with LangChain support
pip install huaweicloud-agentarts-sdk[langchain]

# Install with LangGraph support
pip install huaweicloud-agentarts-sdk[langgraph]

# Install all optional dependencies
pip install huaweicloud-agentarts-sdk[all]
```

## 🚀 Quick Start

### Basic Usage

```python
from agentarts import AgentRuntime
from agentarts.tools import CodeInterpreter
from agentarts.memory import ShortTermMemory

async def main():
    # Create runtime
    runtime = AgentRuntime()
    await runtime.initialize()
    
    # Register tools
    runtime.register_tool(CodeInterpreter())
    
    # Configure memory
    runtime.set_memory(ShortTermMemory(max_size=100))
    
    # Execute Agent
    result = await runtime.execute(
        agent=my_agent,
        input_data={"query": "Hello, AgentArts!"}
    )
    
    print(result)
    
    await runtime.shutdown()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### LangChain Integration

```python
from langchain.agents import initialize_agent, AgentType
from langchain.llms import OpenAI
from agentarts import AgentRuntime
from agentarts.integration import LangChainAdapter
from agentarts.tools import CodeInterpreter

async def main():
    # Create runtime
    runtime = AgentRuntime()
    await runtime.initialize()
    
    # Register tools
    code_interpreter = CodeInterpreter()
    runtime.register_tool(code_interpreter)
    
    # Use adapter
    adapter = LangChainAdapter()
    lc_tools = [adapter.convert_tool(code_interpreter)]
    
    # Create LangChain Agent
    llm = OpenAI(temperature=0)
    agent = initialize_agent(
        tools=lc_tools,
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION
    )
    
    # Wrap and execute
    wrapped_agent = adapter.wrap_agent(agent, runtime)
    result = await wrapped_agent.run({"input": "Calculate fibonacci(10)"})
    
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Service Wrapper

```python
from agentarts import AgentRuntime
from agentarts.service import HTTPServer

# Create runtime
runtime = AgentRuntime()

# Create HTTP server
server = HTTPServer(title="My Agent API")

@server.app.post("/chat")
async def chat(request):
    body = await request.json()
    result = await runtime.execute(agent, body)
    return result

# Start server
server.run(host="0.0.0.0", port=8000)
```

## 🛠️ CLI Tools

```bash
# Initialize project
agentarts init -n my_agent -t langchain

# Local development
agentarts dev --port 8080 --reload

# Build project
agentarts build --platform docker

# Deploy to cloud
agentarts deploy -r cn-north-4 -e production

# View logs
agentarts logs -f --tail 100

# Configuration management
agentarts config set region cn-north-4
```

## 📚 Documentation

- [Quick Start Guide](docs/guides/quickstart.md)
- [API Reference](docs/api/)
- [Examples](examples/)
- [Architecture Design](ARCHITECTURE.md)

## 🔧 Development

```bash
# Clone repository
git clone https://github.com/huaweicloud/agentarts-sdk-python.git
cd agentarts-sdk-python

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting
black .
isort .

# Type checking
mypy agentarts
```

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📮 Contact

- Issues: [GitHub Issues](https://github.com/huaweicloud/agentarts-sdk-python/issues)
- Documentation: <https://docs.huaweicloud.com/agentarts>

