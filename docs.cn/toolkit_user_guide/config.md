# config 命令使用文档

## 命令用途

`config` 命令用于管理 AgentArts 项目配置。支持创建、更新、查看和管理 Agent 配置信息，包括基本配置、SWR 配置和运行时配置等。

## 子命令列表

| 子命令 | 说明 |
|--------|------|
| `config` (无子命令) | 交互式配置 Agent |
| `config list` | 列出所有已配置的 Agent |
| `config get` | 获取配置值或 Agent 详情 |
| `config set` | 设置配置值 |
| `config set-default` | 设置默认 Agent |
| `config remove` | 删除 Agent 配置 |

## 参数解释

### config (交互式配置)

| 参数 | 简写 | 说明 | 是否必填 |
|------|------|------|----------|
| `--name` | `-n` | Agent 名称 | 否，交互式提示 |
| `--entrypoint` | `-e` | Agent 入口函数 | 否，交互式提示 |
| `--region` | `-r` | 华为云区域 | 否，默认 cn-southwest-2 |
| `--dependency-file` | `-d` | 依赖文件路径 | 否，自动检测 |
| `--swr-org` | 无 | SWR 组织名称 | 否，默认 agentarts-org |
| `--swr-repo` | 无 | SWR 仓库名称 | 否，默认与 Agent 名称相同 |
| `--set-default` | 无 | 设置为默认 Agent | 否，默认是 |

### config get

| 参数 | 简写 | 说明 | 是否必填 |
|------|------|------|----------|
| `key` | 无 | 配置键（点分隔格式） | 否，不提供则显示完整配置 |
| `--agent` | `-a` | Agent 名称 | 否，使用默认 Agent |

### config set

| 参数 | 简写 | 说明 | 是否必填 |
|------|------|------|----------|
| `key` | 无 | 配置键（点分隔格式） | 是 |
| `value` | 无 | 配置值 | 是 |
| `--agent` | `-a` | Agent 名称 | 否，使用默认 Agent |

### config set-default

| 参数 | 说明 | 是否必填 |
|------|------|----------|
| `name` | Agent 名称 | 是 |

### config remove

| 参数 | 说明 | 是否必填 |
|------|------|----------|
| `name` | Agent 名称 | 是 |

## 配置键格式

配置键使用点分隔格式，支持以下路径：

### 基本配置 (base.*)

| 配置键 | 说明 | 示例值 |
|--------|------|--------|
| `base.name` | Agent 名称 | `my-agent` |
| `base.entrypoint` | 入口函数 | `agent:create_app` |
| `base.region` | 华为云区域 | `cn-southwest-2` |
| `base.dependency_file` | 依赖文件 | `requirements.txt` |
| `base.platform` | 目标平台 | `linux/amd64` |
| `base.language` | 编程语言 | `python3` |
| `base.base_image` | 基础镜像 | `python:3.10-slim` |

### SWR 配置 (swr_config.*)

| 配置键 | 说明 | 示例值 |
|--------|------|--------|
| `swr_config.organization` | SWR 组织 | `my-org` |
| `swr_config.repository` | SWR 仓库 | `my-repo` |
| `swr_config.organization_auto_create` | 自动创建组织 | `true` |
| `swr_config.repository_auto_create` | 自动创建仓库 | `true` |

### 运行时配置 (runtime.*)

| 配置键 | 说明 | 示例值 |
|--------|------|--------|
| `runtime.invoke_config.protocol` | 调用协议 | `HTTP` |
| `runtime.invoke_config.port` | 服务端口 | `8080` |
| `runtime.identity_configuration.authorizer_type` | 认证类型 | `IAM` |

## 执行效果

### 交互式配置

执行 `agentarts config` 后，会依次提示输入：
1. Agent 名称（显示已有 Agent 列表）
2. 入口函数（格式：module:function）
3. 华为云区域（默认 cn-southwest-2）
4. 依赖文件（自动检测 requirements.txt）
5. SWR 组织名称
6. SWR 仓库名称

配置完成后会：
- 保存配置到 `.agentarts_config.yaml`
- 自动生成 Dockerfile（如果不存在）

## 使用示例

### 示例 1: 交互式配置

```bash
agentarts config
```

按提示输入配置信息，适合首次配置或不确定参数时使用。

### 示例 2: 快速配置

```bash
agentarts config --name my-agent --entrypoint agent:create_app
```

仅提供必要参数，其他使用默认值。

### 示例 3: 完整参数配置

```bash
agentarts config \
  --name my-agent \
  --entrypoint agent:create_app \
  --region cn-southwest-2 \
  --dependency-file requirements.txt \
  --swr-org my-organization \
  --swr-repo my-repository
```

### 示例 4: 列出所有 Agent

```bash
agentarts config list
```

输出示例：
```
Configured Agents:
  my-agent (default)
    Entrypoint: agent:create_app
    Region: cn-southwest-2
```

### 示例 5: 查看 Agent 完整配置

```bash
agentarts config get
```

或指定 Agent：
```bash
agentarts config get --agent my-agent
```

### 示例 6: 获取特定配置值

```bash
agentarts config get base.region
```

输出：`cn-southwest-2`

### 示例 7: 设置配置值

```bash
agentarts config set base.region cn-southwest-2
```

或指定 Agent：
```bash
agentarts config set base.region cn-southwest-2 --agent my-agent
```

### 示例 8: 设置默认 Agent

```bash
agentarts config set-default my-agent
```

### 示例 9: 删除 Agent 配置

```bash
agentarts config remove my-agent
```

## 配置文件示例

`.agentarts_config.yaml` 文件结构：

```yaml
default_agent: my-agent

agents:
  my-agent:
    base:
      name: my-agent
      entrypoint: agent:create_app
      dependency_file: requirements.txt
      platform: linux/amd64
      language: python3
      base_image: python:3.10-slim
      region: cn-southwest-2

    swr_config:
      organization: my-org
      repository: my-repo
      organization_auto_create: true
      repository_auto_create: true

    runtime:
      invoke_config:
        protocol: HTTP
        port: 8080

      identity_configuration:
        authorizer_type: IAM
```

## 注意事项

1. **入口函数格式**: 必须为 `module:function` 格式，例如 `agent:create_app`
2. **区域选择**: 请选择离用户最近的区域以降低延迟
3. **SWR 配置**: 首次使用会自动创建组织和仓库
4. **默认 Agent**: 设置默认 Agent 后，其他命令可省略 `--agent` 参数
5. **配置文件**: 配置保存在项目根目录的 `.agentarts_config.yaml` 文件中
