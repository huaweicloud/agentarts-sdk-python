# init 命令使用文档

## 命令用途

`init` 命令用于初始化一个新的 AgentArts 项目。该命令会创建完整的项目结构，包括 Agent 实现代码、依赖文件和配置文件，帮助开发者快速开始 Agent 应用开发。

## 参数解释

### 必选参数

无必选参数。如果不提供任何参数，命令将以交互式方式引导用户完成项目初始化。

### 可选参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--name` | `-n` | 项目名称 | 交互式提示输入 |
| `--template` | `-t` | 项目模板类型 | 交互式选择 |
| `--path` | `-p` | 项目创建路径 | `.` (当前目录) |
| `--region` | `-r` | 华为云区域 | `cn-southwest-2` |
| `--swr-org` | 无 | SWR 组织名称 | `agentarts-org` |
| `--swr-repo` | 无 | SWR 仓库名称 | 与项目名称相同 |

### 模板类型

| 模板名称 | 说明 |
|---------|------|
| `basic` | 基础模板，适合快速开始 |
| `langgraph` | LangGraph 框架模板，支持状态工作流 |
| `langchain` | LangChain 框架模板，支持工具集成 |
| `google-adk` | Google ADK 框架模板，支持 Gemini 模型 |

## 执行效果

执行 `init` 命令后，会在指定路径下创建以下项目结构：

```
{project_name}/
├── agent.py              # Agent 实现代码
├── requirements.txt      # 项目依赖文件
├── .agentarts_config.yaml # AgentArts 配置文件
└── Dockerfile            # Docker 构建文件
```

### 文件说明

1. **agent.py**: Agent 的主要实现文件，包含入口函数和业务逻辑
2. **requirements.txt**: 项目依赖列表，包括 SDK 和框架包
3. **.agentarts_config.yaml**: AgentArts 配置文件，包含部署和运行配置
4. **Dockerfile**: Docker 镜像构建文件，用于容器化部署

## 使用示例

### 示例 1: 交互式创建项目

```bash
agentarts init
```

执行后会提示：
1. 选择模板类型（输入数字选择）
2. 输入项目名称
3. 输入华为云区域（默认 cn-southwest-2）

### 示例 2: 使用 LangGraph 模板创建项目

```bash
agentarts init --name my-agent --template langgraph
```

### 示例 3: 指定路径和区域创建项目

```bash
agentarts init -n my-agent -t langchain --path ./projects --region cn-southwest-2
```

### 示例 4: 完整参数示例

```bash
agentarts init \
  --name my-agent \
  --template langgraph \
  --path ./my-projects \
  --region cn-southwest-2 \
  --swr-org my-organization \
  --swr-repo my-repository
```

## 后续步骤

项目创建完成后，建议按以下步骤操作：

1. **进入项目目录**
   ```bash
   cd {project_name}
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   
   根据模板类型，在 `.agentarts_config.yaml` 中配置必要的环境变量：
   - LangGraph/LangChain: `OPENAI_API_KEY`
   - Google ADK: `GOOGLE_API_KEY`

4. **本地开发测试**
   ```bash
   agentarts dev
   ```

5. **部署到华为云**
   ```bash
   agentarts deploy
   ```

## 注意事项

1. 项目名称应使用小写字母、数字和连字符，避免使用特殊字符
2. 选择模板时，请确保已了解各框架的特点和依赖要求
3. 区域参数影响服务部署位置，请根据业务需求选择合适的区域
4. SWR 组织和仓库用于存储 Docker 镜像，首次使用会自动创建
