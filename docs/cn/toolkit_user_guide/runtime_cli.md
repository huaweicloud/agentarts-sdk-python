# runtime 命令使用文档

## 命令用途

`runtime` 命令用于操作华为云 AgentArts 运行时，提供会话管理、文件传输、命令执行等数据平面操作能力。所有 runtime 子命令均仅支持云端模式（已部署的 Agent）。

## 子命令概览

| 子命令 | 说明 | 是否需要会话 |
|--------|------|-------------|
| `start-session` | 创建运行时会话，获取 session_id | 否 |
| `invoke` | 调用 Agent 发送 JSON 请求 | 可选 |
| `exec-command` | 在运行时中执行命令 | 可选 |
| `upload-files` | 上传文件到运行时 | 是 |
| `download-files` | 从运行时下载文件 | 是 |
| `stop-session` | 停止运行时会话 | 是 |

## 后端 API 路径

| 子命令 | HTTP 方法 | API 路径 |
|--------|----------|----------|
| `start-session` | POST | `/runtimes/{agent-name}/sessions-start` |
| `stop-session` | POST | `/runtimes/{agent-name}/sessions-stop` |
| `invoke` | POST | `/runtimes/{agent-name}/invocations` |
| `exec-command` | POST | `/runtimes/{agent-name}/commands` |
| `upload-files` | POST | `/runtimes/{agent-name}/upload-files` |
| `download-files` | GET | `/runtimes/{agent-name}/download-files` |

## 通用参数

所有 runtime 子命令支持以下通用参数：

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--agent` | `-a` | Agent 名称 | 使用默认 Agent |
| `--region` | `-r` | 华为云区域 | 从配置文件读取 |
| `--endpoint` | `-e` | 指定端点名称 | 无 |
| `--bearer-token` | `-bt` | Bearer 认证令牌 | 无 |
| `--skip-ssl-verification` | `-k` | 跳过 SSL 证书验证 | `false` |
| `--user-id` | `-u` | 用户 ID（用于 OAuth2 出站凭据） | 无 |

---

## start-session

### 命令用途

创建运行时会话，返回 session_id 用于后续有状态操作（如文件传输、命令执行）。

### 参数解释

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--agent` | `-a` | Agent 名称（必填） | 无 |
| `--region` | `-r` | 华为云区域 | 从配置文件读取 |
| `--bearer-token` | `-bt` | Bearer 认证令牌 | 无 |
| `--endpoint` | `-e` | 指定端点名称 | 无 |
| `--skip-ssl-verification` | `-k` | 跳过 SSL 证书验证 | `false` |
| `--user-id` | `-u` | 用户 ID（用于 OAuth2 出站凭据） | 无 |

### 响应格式

```json
{
  "data": {
    "session_id": "session-xxxx-xxxx-xxxx"
  }
}
```

### 使用示例

#### 示例 1: 基本会话创建

```bash
agentarts runtime start-session --agent my-agent
```

#### 示例 2: 指定区域

```bash
agentarts runtime start-session -a my-agent -r cn-southwest-2
```

#### 示例 3: 使用 Bearer Token

```bash
agentarts runtime start-session -a my-agent -bt your-token
```

#### 示例 4: 指定端点

```bash
agentarts runtime start-session -a my-agent -e my-endpoint
```

#### 示例 5: 跳过 SSL 验证

```bash
agentarts runtime start-session -a my-agent --skip-ssl-verification
```

---

## stop-session

### 命令用途

停止运行时会话，释放会话资源。

### 参数解释

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--agent` | `-a` | Agent 名称（必填） | 无 |
| `--session` | `-s` | 会话 ID（必填） | 无 |
| `--region` | `-r` | 华为云区域 | 从配置文件读取 |
| `--bearer-token` | `-bt` | Bearer 认证令牌 | 无 |
| `--endpoint` | `-e` | 指定端点名称 | 无 |
| `--skip-ssl-verification` | `-k` | 跳过 SSL 证书验证 | `false` |
| `--user-id` | `-u` | 用户 ID（用于 OAuth2 出站凭据） | 无 |

### 使用示例

#### 示例 1: 基本会话停止

```bash
agentarts runtime stop-session --agent my-agent --session session-xxx
```

#### 示例 2: 使用简写参数

```bash
agentarts runtime stop-session -a my-agent -s session-xxx
```

#### 示例 3: 使用 Bearer Token

```bash
agentarts runtime stop-session -a my-agent -s session-xxx -bt your-token
```

---

## invoke

### 命令用途

调用 Agent 发送 JSON 请求，获取响应。支持自定义路径扩展。

> **注意**: 此命令与顶层 `agentarts invoke` 命令功能相同。

### 参数解释

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `payload` | 无 | JSON 请求数据（位置参数，必填） | 无 |
| `--agent` | `-a` | Agent 名称 | 使用默认 Agent |
| `--region` | `-r` | 华为云区域 | 从配置文件读取 |
| `--endpoint` | `-e` | 指定端点名称 | 无 |
| `--session` | `-s` | 会话 ID（用于有状态 Agent） | 无 |
| `--bearer-token` | `-bt` | Bearer 认证令牌 | 无 |
| `--timeout` | 无 | 请求超时时间（秒） | `900` |
| `--skip-ssl-verification` | `-k` | 跳过 SSL 证书验证 | `false` |
| `--user-id` | `-u` | 用户 ID（用于 OAuth2 出站凭据） | 无 |
| `--custom-path` | 无 | 自定义路径追加到 /invocations | 无 |

### custom-path 参数说明

`--custom-path` 允许在 `/invocations` 路径后追加自定义路径段：

- **有效格式**: 字母、数字、连字符、下划线、点、斜杠（用于嵌套路径）
- **无效字符**: `!`、`@`、`#`、`$`、`%`、`^`、`&`、`*`、`(`、`)`、空格
- **路径遍历**: 不允许 `..` 序列

**示例**:
- `--custom-path stream` → `/invocations/stream`
- `--custom-path api/v2` → `/invocations/api/v2`

### 配置要求

使用 `--custom-path` 需要在配置文件中设置 `url_match_type: PREFIX_MATCH`：

```yaml
runtime:
  invoke_config:
    url_match_type: PREFIX_MATCH
```

若配置为 `ACCURATE_MATCH`（默认），使用 `--custom-path` 会因后端期望精确路径匹配而失败。

### 使用示例

#### 示例 1: 基本调用

```bash
agentarts runtime invoke '{"message": "hello"}' --agent my-agent
```

#### 示例 2: 使用会话 ID

```bash
agentarts runtime invoke '{"message": "hello"}' -a my-agent -s session-xxx
```

#### 示例 3: 使用自定义路径

```bash
agentarts runtime invoke '{"message": "hello"}' -a my-agent --custom-path stream
```

#### 示例 4: 设置超时时间

```bash
agentarts runtime invoke '{"message": "hello"}' -a my-agent --timeout 60
```

---

## exec-command

### 命令用途

在运行时环境中执行命令（如 ls、cat、pip install 等）。

### 参数解释

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `command` | 无 | 要执行的命令（位置参数，必填） | 无 |
| `--agent` | `-a` | Agent 名称（必填） | 无 |
| `--session` | `-s` | 会话 ID | 无 |
| `--chunked` | 无 | 启用流式响应（application/x-ndjson） | `false` |
| `--region` | `-r` | 华为云区域 | 从配置文件读取 |
| `--bearer-token` | `-bt` | Bearer 认证令牌 | 无 |
| `--endpoint` | `-e` | 指定端点名称 | 无 |
| `--skip-ssl-verification` | `-k` | 跳过 SSL 证书验证 | `false` |
| `--user-id` | `-u` | 用户 ID（用于 OAuth2 出站凭据） | 无 |
| `--timeout` | 无 | 请求超时时间（秒） | `60`（最大 300） |

### Timeout 说明

- 默认超时: 60 秒
- 最大超时: 300 秒
- 超时参数直接传递给 HTTP 客户端，超出后请求将被终止

### Chunked 模式说明

启用 `--chunked` 后：
- 请求头: `Command-Type: chunked`
- 响应格式: `application/x-ndjson`（每行一个 JSON 对象）

### 使用示例

#### 示例 1: 基本命令执行

```bash
agentarts runtime exec-command "ls -la" --agent my-agent --session session-xxx
```

#### 示例 2: 流式输出

```bash
agentarts runtime exec-command "ls -la" -a my-agent -s session-xxx --chunked
```

#### 示例 3: 设置超时时间

```bash
agentarts runtime exec-command "pip install pandas" -a my-agent -s session-xxx --timeout 120
```

#### 示例 4: 使用 Bearer Token

```bash
agentarts runtime exec-command "cat /home/user/data.txt" -a my-agent -s session-xxx -bt your-token
```

---

## upload-files

### 命令用途

上传本地文件到运行时环境。

### 参数解释

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--agent` | `-a` | Agent 名称（必填） | 无 |
| `--session` | `-s` | 会话 ID（必填） | 无 |
| `--files` | `-f` | 本地文件路径（可多次指定，必填） | 无 |
| `--path` | `-p` | 远程目录路径，必须以 `/` 结尾（如 `/home/user/`） | `/home/user/` |
| `--file-user-id` | 无 | 文件所有者用户 ID | `1000` |
| `--file-group-id` | 无 | 文件所有者组 ID | `1000` |
| `--file-mode` | `-m` | 文件权限（八进制格式） | `0644` |
| `--region` | `-r` | 华为云区域 | 从配置文件读取 |
| `--bearer-token` | `-bt` | Bearer 认证令牌 | 无 |
| `--endpoint` | `-e` | 指定端点名称 | 无 |
| `--skip-ssl-verification` | `-k` | 跳过 SSL 证书验证 | `false` |
| `--user-id` | `-u` | 用户 ID（用于 OAuth2 出站凭据） | 无 |
| `--timeout` | 无 | 请求超时时间（秒） | `900` |

### 文件路径格式

#### 默认目录上传

文件上传到默认目录 `/home/user/`：

```bash
agentarts runtime upload-files -a my-agent -s session-xxx -f local_file.txt
```

#### 指定远程目录

使用 `--path` / `-p` 参数指定远程目录，路径必须以 `/` 结尾：

```bash
agentarts runtime upload-files -a my-agent -s session-xxx -f local_file.txt -p /app/data/
```

#### 多文件上传

多次使用 `-f` 参数，所有文件上传到同一目录：

```bash
agentarts runtime upload-files -a my-agent -s session-xxx -f file1.txt -f file2.txt -f file3.txt
```

#### 多文件上传到自定义目录

```bash
agentarts runtime upload-files -a my-agent -s session-xxx \
  -f file1.txt -f file2.txt -f file3.txt \
  -p /app/data/
```

### 配置要求

使用 `upload-files` 需要在配置文件中启用文件传输：

```yaml
runtime:
  invoke_config:
    file_transfer_config:
      enabled: true
```

若配置为 `false`（默认），上传操作将失败。

### 使用示例

#### 示例 1: 单文件上传（默认目录）

```bash
agentarts runtime upload-files --agent my-agent --session session-xxx -f data.txt
```

#### 示例 2: 多文件上传

```bash
agentarts runtime upload-files -a my-agent -s session-xxx -f file1.txt -f file2.txt
```

#### 示例 3: 指定远程目录

```bash
agentarts runtime upload-files -a my-agent -s session-xxx -f file1.txt -f file2.txt -p /app/data/
```

#### 示例 4: 自定义文件权限

```bash
agentarts runtime upload-files -a my-agent -s session-xxx -f script.sh --file-mode 0755
```

#### 示例 5: 自定义所有者

```bash
agentarts runtime upload-files -a my-agent -s session-xxx -f data.txt --file-user-id 1001 --file-group-id 1001
```

---

## download-files

### 命令用途

从运行时环境下载文件或目录。

### 参数解释

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--agent` | `-a` | Agent 名称（必填） | 无 |
| `--session` | `-s` | 会话 ID（必填） | 无 |
| `--path` | `-p` | 远程文件/目录路径（必填） | 无 |
| `--output` | `-o` | 本地输出路径 | 使用文件名 |
| `--recursive` | | 下载目录为 tar 归档 | `false` |
| `--region` | 无 | 华为云区域 | 从配置文件读取 |
| `--bearer-token` | `-bt` | Bearer 认证令牌 | 无 |
| `--endpoint` | `-e` | 指定端点名称 | 无 |
| `--skip-ssl-verification` | `-k` | 跳过 SSL 证书验证 | `false` |
| `--user-id` | `-u` | 用户 ID（用于 OAuth2 出站凭据） | 无 |
| `--timeout` | 无 | 请求超时时间（秒） | `900` |

### 配置要求

使用 `download-files` 需要在配置文件中启用文件传输：

```yaml
runtime:
  invoke_config:
    file_transfer_config:
      enabled: true
```

若配置为 `false`（默认），下载操作将失败。

### 使用示例

#### 示例 1: 下载单个文件

```bash
agentarts runtime download-files --agent my-agent --session session-xxx --path /home/user/data.txt
```

#### 示例 2: 指定输出路径

```bash
agentarts runtime download-files -a my-agent -s session-xxx -p /home/user/data.txt -o ./local_data.txt
```

#### 示例 3: 下载目录

```bash
agentarts runtime download-files -a my-agent -s session-xxx -p /home/user/project --recursive
```

#### 示例 4: 使用 Bearer Token

```bash
agentarts runtime download-files -a my-agent -s session-xxx -p /home/user/data.txt -bt your-token
```

---

## 会话管理流程

### 标准流程

1. **创建会话**

```bash
agentarts runtime start-session --agent my-agent
# 输出: {"data": {"session_id": "session-xxx"}}
```

2. **执行操作**（使用会话 ID）

```bash
# 上传文件
agentarts runtime upload-files -a my-agent -s session-xxx -f data.txt

# 执行命令
agentarts runtime exec-command "pip install pandas" -a my-agent -s session-xxx

# 下载文件
agentarts runtime download-files -a my-agent -s session-xxx -p /home/user/result.txt
```

3. **停止会话**

```bash
agentarts runtime stop-session --agent my-agent --session session-xxx
```

### 会话作用

- **有状态操作**: upload-files、download-files、exec-command 可使用会话保持状态
- **文件传输**: 同一会话中的文件操作共享文件系统状态
- **命令执行**: 同一会话中的命令共享执行环境（如已安装的包）

---

## 常见问题

### Q1: 会话创建失败

**原因**: Agent 未部署或认证失败

**解决方案**:
1. 确认 Agent 已成功部署
2. 检查 AK/SK 或 Bearer Token 配置
3. 验证区域配置是否正确

### Q2: 文件上传/下载失败

**原因**: 文件传输未启用

**解决方案**:
1. 在配置文件中设置 `file_transfer_config.enabled: true`
2. 重新部署 Agent
3. 或在华为云控制台直接更新配置

### Q3: exec-command 超时

**原因**: 命令执行时间超过限制

**解决方案**:
1. 设置 `--timeout` 参数（最大 300 秒）
2. 优化命令执行效率
3. 将长时间任务拆分为多个命令

### Q4: invoke --custom-path 失败

**原因**: URL 匹配类型配置错误

**解决方案**:
1. 在配置文件中设置 `url_match_type: PREFIX_MATCH`
2. 重新部署 Agent

### Q5: 认证失败

**原因**: AK/SK 配置错误或 Token 过期

**解决方案**:
1. 检查环境变量 `HUAWEICLOUD_SDK_AK` 和 `HUAWEICLOUD_SDK_SK`
2. 更新 Bearer Token
3. 确认 Agent 认证类型配置正确

---

## 注意事项

1. **会话 ID**: upload-files 和 download-files 必须提供会话 ID
2. **文件大小**: 单文件最大 100MB
3. **超时限制**: exec-command 最大超时 300 秒
4. **配置依赖**: 文件传输和自定义路径需要特定配置
5. **认证类型**: IAM 认证使用 AK/SK 签名，其他认证类型使用 Bearer Token
6. **会话生命周期**: 建议在操作完成后停止会话释放资源
7. **文件权限**: 上传文件时注意设置正确的用户 ID、组 ID 和权限
8. **远程目录**: upload-files 的 `--path` 参数必须以 `/` 结尾，多文件上传到同一目录