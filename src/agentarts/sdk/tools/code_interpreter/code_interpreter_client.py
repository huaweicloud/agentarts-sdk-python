"""与代码解释器沙箱服务交互的客户端

此模块用于提供一个客户端给华为与代码解释器，支持应用在一个受管理的沙箱环境中启动，停止，调用代码等操作

控制面
管理代码解释器的全生命周期
（创建、列表、更新、获取、删除）

数据面
管理代码解释器会话的全生命周期
（创建、停止、获取、调用）
"""
import base64
import logging
import os
import re
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Union

from agentarts.sdk.service.tools_http import ControlToolsHttpClient, DataToolsHttpClient
from agentarts.sdk.utils.constant import get_control_plane_endpoint, get_code_interpreter_data_plane_endpoint, get_region


DEFAULT_TIMEOUT = 900  # 默认15分
DEFAULT_PATH = "/home/user" # 默认路径，当前仅能在此路径下载上传等操作

logger = logging.getLogger(__name__)


class CodeInterpreter:
    """与代码解释器沙箱服务交互的客户端

    客户端能处理代码解释器沙箱会话的整个生命周期和方法调用，在一个安全，受管理的环境中提供执行代码，上传下载文件，安装依赖等功能的接口

    Attributes:
        control_plane_client : 用于与控制面API交互
        data_plane_client : 用于与数据面API交互
    """
    def __init__(self, region: Optional[str], data_endpoint: Optional[str] = None) -> None:
        """支持在指定的region中初始化代码解释器客户端

        Args:
            region: 指定的区域
            data_endpoint: 数据面端点，可选，如果不提供则从环境变量AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT中获取

        """
        region = region or get_region()
        
        # 管理代码解释器的控制面客户端
        self.control_plane_client = ControlToolsHttpClient(
            region_name=region,
            endpoint_url=get_control_plane_endpoint()
        )

        # 管理代码解释器的数据面客户端
        # 优先级：环境变量 > 参数 > 默认值
        endpoint_url = get_code_interpreter_data_plane_endpoint(endpoint=data_endpoint)
        
        self.data_plane_client = DataToolsHttpClient(
            region_name=region,
            endpoint_url=endpoint_url
        )
        
        self._code_interpreter_name = None
        self._session_id = None

    @property
    def code_interpreter_name(self) -> Optional[str]:
        """获取当前代码解释器的名称
        
        Returns:
            Optional[str]: 当前代码解释器的名称，如果没有则返回None
        """
        return self._code_interpreter_name
    
    @code_interpreter_name.setter
    def code_interpreter_name(self, name: str) -> None:
        """设置当前代码解释器的名称

        Args:
            name (str): 代码解释器的名称
        """
        self._code_interpreter_name = name
        
    @property
    def session_id(self) -> Optional[str]:
        """获取当前会话的ID
        
        Returns:
            Optional[str]: 当前会话的ID，如果没有则返回None
        """ 
        return self._session_id
    
    @session_id.setter
    def session_id(self, session_id: str) -> None:
        """设置当前会话的ID

        Args:
            session_id (str): 会话ID
        """
        self._session_id = session_id

    def create_code_interpreter(
        self,
        name: str,
        api_key_name: str,
        description: Optional[str] = None,
        auth_type: Optional[str] = None,
        execution_agency_name: Optional[str] = None,
        observability: Optional[Dict] = None,
        network_config: Optional[Dict] = None,
        agent_gateway_id: Optional[str] = None,
        tags: Optional[List[Dict]] = None,
    ) -> Dict:
        """创建自定义代码解释器

        通过控制面创建一个新的代码解释器

        Args:
            name (str): 代码解释器的名称，必须符合特定的命名规则
            api_key_name (str): API Key 的名称
            description (Optional[str]): 代码解释器的描述信息
            auth_type (Optional[str]): 认证类型，例如 "API_KEY"
            execution_agency_name (Optional[str]): IAM委托名
            observability (Optional[Dict]): 可观测性配置，例如日志和监控设置
            network_config (Optional[Dict]): 网络配置，例如 VPC 和安全组设置
            agent_gateway_id (Optional[str]): 关联的 Agent Gateway ID
            tags (Optional[List[Dict]]): 标签列表，每个标签是一个包含 "key" 和 "value" 的字典
        
        Returns:
            Dict: 包含新创建的代码解释器信息的字典
                - id(str): 代码解释器的ID
                - name(str): 代码解释器的名称
                - description(str): 代码解释器的描述信息
                - created_at(str): 代码解释器的创建时间
                - updated_at(str): 代码解释器的更新时间
                - execution_agency_name(str): IAM委托名
                - workload_identity(Dict): 工作负载认证信息
                - access_endpoint(str): 代码解释器的访问域名
                - observability(Dict): 可观测性配置(日志+指标)
                - tags(List[Dict]): 标签列表，每个标签是一个包含 "key" 和 "value" 的字典
                - network_config(Dict): 网络配置，例如 VPC 和安全组设置

        Example:
            >>> code_interpreter = client.create_code_interpreter(
            ...     name="my-code-interpreter",
            ...     api_key_name="my-api-key-name",
            ... )
            >>> code_interpreter_id = code_interpreter["id"]
        """
        logging.info(f"Creating code interpreter with name: {name}")
        pattern = r"[a-z][a-z0-9-]{0,46}[a-z0-9]$"
        if not bool(re.match(pattern, name)):
            raise ValueError("Name must match the pattern, please check your code_interpreter_name.")
        
        request_params = {
            "name": name,
            "api_key_name": api_key_name,
        }

        if description:
            request_params["description"] = description
        if auth_type:
            request_params["auth_type"] = auth_type
        if execution_agency_name:
            request_params["execution_agency_name"] = execution_agency_name
        if observability:
            request_params["observability"] = observability
        if network_config:
            request_params["network_config"] = network_config
        if agent_gateway_id:
            request_params["agent_gateway_id"] = agent_gateway_id
        if tags:
            request_params["tags"] = tags

        result = self.control_plane_client.create_code_interpreter(
            request_params=request_params
        )
        return result
    
    def list_code_interpreters(
        self,
        name: str = None,
        limit: int = 10,
        offset: int = 0,
        sort_key: str = None,
        sort_dir: str = None,
    ) -> Dict:
        """查询代码解释器列表
        
        Args:
            name (str): 根据名称模糊查询代码解释器列表
            limit (int): 每页返回的代码解释器数量，默认10
            offset (int): 分页偏移量，默认0
            sort_key (str): 排序字段，必须是created_at或updated_at
            sort_dir (str): 排序方向，必须是asc或desc
        
        Returns:
            Dict: 包含代码解释器列表和分页信息的字典
                - total_count(int): 符合查询条件的代码解释器总数
                - items(List[Dict]): 代码解释器列表
        
        Example:
            >>> result = client.list_code_interpreters(
            ...     name="my-code-interpreter",
            ...     sort_key="created_at",
            ...     sort_dir="asc"
            >>> )

        """
        logging.info("Listing code interpreters")
        if sort_key and sort_key not in ["created_at", "updated_at"]:
            raise ValueError("sort_key must be either 'created_at' or 'updated_at'")
        if sort_dir and sort_dir not in ["asc", "desc"]:
            raise ValueError("sort_dir must be either 'asc' or 'desc'")
        request_params = {
            "name": name,
            "limit": limit,
            "offset": offset,
            "sort_key": sort_key,
            "sort_dir": sort_dir,
        }

        result = self.control_plane_client.list_code_interpreters(
            request_params=request_params
        )
        return result
    
    def update_code_interpreter(
        self,
        code_interpreter_id: str,
        observability: Optional[Dict] = None,
        tags: Optional[List[Dict]] = None,
    ) -> Dict:
        """更新代码解释器的可观测性配置和标签信息

        Args:
            code_interpreter_id (str): 代码解释器的ID
            observability (Dict): 可观测性配置(日志+指标)，可选
            tags (List[Dict]): 标签列表，每个标签是一个包含 "key" 和 "value" 的字典，可选
        
        Returns:
            Dict: 包含更新后代码解释器信息的字典
                - id(str): 代码解释器的ID
                - name(str): 代码解释器的名称
                - description(str): 代码解释器的描述信息
                - created_at(str): 代码解释器的创建时间
                - updated_at(str): 代码解释器的更新时间
                - execution_agency_name(str): IAM委托名
                - agent_gateway_id(str): 代码解释器所属的智能体网关ID
                - workload_identity(Dict): 工作负载认证信息
                - access_endpoint(str): 代码解释器的访问域名
                - observability(Dict): 可观测性配置(日志+指标)
                - tags(List[Dict]): 标签列表，每个标签是一个包含 "key" 和 "value" 的字典
        
        Example:
            >>> result = client.update_code_interpreter(
            ...     code_interpreter_id="my-code-interpreter",
            ...     observability=None,
            ...     tags=[{"key": "env", "value": "dev"}]
            >>> )
        """
        logging.info(f"Updating code interpreter with {code_interpreter_id}")
        request_params = {}
        if observability is not None:
            request_params["observability"] = observability
        if tags is not None:
            request_params["tags"] = tags
        result = self.control_plane_client.update_code_interpreter(
            code_interpreter_id=code_interpreter_id,
            request_params=request_params
        )
        return result

    def get_code_interpreter(self, code_interpreter_id: str) -> Dict:
        """获取代码解释器详情
        
        Args:
            code_interpreter_id (str): 代码解释器的ID
        
        Returns:
            Dict: 包含代码解释器详情的字典
                - id(str): 代码解释器的ID
                - name(str): 代码解释器的名称
                - description(str): 代码解释器的描述信息
                - created_at(str): 代码解释器的创建时间
                - updated_at(str): 代码解释器的更新时间
                - execution_agency_name(str): IAM委托名
                - agent_gateway_id(str): 代码解释器所属的智能体网关ID
                - workload_identity(Dict): 工作负载认证信息
                - access_endpoint(str): 代码解释器的访问域名
                - observability(Dict): 可观测性配置(日志+指标)
                - tags(List[Dict]): 标签列表，每个标签是一个包含 "key" 和 "value" 的字典
                - auth_tyoe(str): 工具认证方式
                - api_key_name(str): API Key名称
                - network_config(Dict): 网络配置，例如 VPC 和安全组设置
        
        Example:
            >>> result = client.get_code_interpreter(
            ...     code_interpreter_id="my-code-interpreter-id"
            >>> )
        """
        logging.info(f"Getting code interpreter {code_interpreter_id}")
        result = self.control_plane_client.get_code_interpreter(
            code_interpreter_id=code_interpreter_id
        )
        return result

    def delete_code_interpreter(self, code_interpreter_id: str) -> None:
        """删除指定代码解释器
        
        Args:
            code_interpreter_id (str): 代码解释器的ID

        Example:
            >>> client.delete_code_interpreter(
            ...     code_interpreter_id="my-code-interpreter-id"
            >>> )
        """
        logging.info(f"Deleting code interpreter {code_interpreter_id}")
        self.control_plane_client.delete_code_interpreter(
            code_interpreter_id=code_interpreter_id
        )
    
    def start_session(
        self,
        code_interpreter_name: str,
        session_name: str = str,
        api_key: Optional[str] = None,
        session_timeout: Optional[int] = DEFAULT_TIMEOUT
    ) -> str:
        """启动代码解释器会话

        根据提供的参数初始化一个新的代码解释器会话，并返回会话ID

        Args:
            code_interpreter_name (str): 代码解释器的名称，用于识别和管理会话，名称唯一
            session_name (str): 会话名称
            api_key (Optional[str]): 认证使用的API Key，如果不提供则从环境变量API_KEY中获取
            session_timeout (Optional[int]): 会话超时时间，单位为秒，
                默认15分钟，最小值为60秒，最大值为86400秒（24小时）
        
        Returns:
            session_id (str): 会话ID
        
        Example:
            >>> session_id = client.start_session(
            ...     code_interpreter_name="my-code-interpreter-name",
            ...     session_name="my-session-name"
            >>> )
        """
        logging.info(f"Starting codeinterpreter session...")
        request_params = {
            "name": session_name,
            "session_timeout": session_timeout,
        }
        if api_key is None:
            api_key = os.getenv("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")
        response = self.data_plane_client.start_session(
            code_interpreter_name=code_interpreter_name,
            api_key=api_key,
            request_params=request_params
        )
        self.session_id = response["session_id"]
        self.code_interpreter_name = code_interpreter_name
        return self.session_id
    
    def get_session(
            self,
            code_interpreter_name: str,
            session_id: Optional[str] = None,
            api_key: Optional[str] = None
    ) -> Dict:
        """获取代码解释器会话详情
        
        Args:
            code_interpreter_name (str): 代码解释器的名称，用于识别和管理会话，名称唯一
            session_id (Optional[str]): 会话ID，默认使用当前会话ID
            api_key (Optional[str]): 认证使用的API Key，如果不提供则从环境变量API_KEY中获取
        
        Returns:
            Dict: 包含会话详情的字典
                - code_interpreter_id(str): 代码解释器的ID
                - created_at(str): 会话的创建时间
                - session_name(str): 会话名称
                - session_id(str): 会话ID
                - session_timeout(int): 会话超时时间，单位为秒

        Example:
            >>> session_info = client.get_session(
            ...     code_interpreter_name="my-code-interpreter-name"
            >>> )
        """
        logging.info(f"Getting codeinterpreter session...")

        session_id = session_id or self.session_id
        if not code_interpreter_name or not session_id:
            raise ValueError("code_interpreter_name and session_id are required")
        if api_key is None:
            api_key = os.getenv("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")
        result = self.data_plane_client.get_session(
            code_interpreter_name=code_interpreter_name,
            session_id=session_id,
            api_key=api_key
        )
        return result
    
    def stop_session(self, api_key: Optional[str] = None) -> bool:
        """停止当前代码解释器会话

        终止任何活跃的会话并清除会话状态
        
        Args:
            api_key (Optional[str]): 认证使用的API Key，如果不提供则从环境变量API_KEY中获取
        
        Returns:
            bool: 没有活跃会话时返回True，否则返回False
        
        Example:
            >>> client.stop_session()
        """
        logging.info(f"Stopping codeinterpreter session...")
        if not self.session_id or not self.code_interpreter_name:
            return True

        if api_key is None:
            api_key = os.getenv("API_KEY")

        self.data_plane_client.stop_session(
            code_interpreter_name=self.code_interpreter_name,
            session_id=self.session_id,
            api_key=api_key
        )

        self.code_interpreter_name = None
        self.session_id = None
        return True

    def invoke(
            self,
            operate_type: str,
            arguments: Dict,
            api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """调用代码解释器会话

        如果没有活跃会话，将在调用请求前自动启动一个会话

        Args:
            operate_type (str): 调用方法名，"execute_code"或"execute_command"等
            arguments (Dict): 调用参数，根据operate_type不同而不同
            api_key (Optional[str]): 认证使用的API Key，如果不提供则从环境变量API_KEY中获取
        
        Returns:
            result[Dict]: 包含调用结果的字典
        
        Example:
            >>> result = client.invoke(
            ...     operate_type="execute_code",
            ...     arguments={
            ...         "clear_context": False,
            ...         "code": "print('Hello, World!')",
            ...         "language": "python"
            ...     }
            >>> )
        """
        if not self.session_id or not self.code_interpreter_name:
            raise ValueError("No Code Interpreter exists, use create_code_interpreter method first")

        request_params = {
            "operate_type": operate_type,
            "arguments": arguments
        }

        if api_key is None:
            api_key = os.getenv("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")
        
        result = self.data_plane_client.invoke(
            code_interpreter_name=self.code_interpreter_name,
            session_id=self.session_id,
            api_key=api_key,
            arguments=request_params
        )
        return result

    def execute_code(
            self,
            code: str,
            language: str = "python",
            clear_context: bool = False,
    ) -> Dict[str, Any]:
        """在代码解释器中执行代码
        
        Args:
            code (str): 要执行的代码
            language (str): 代码的语言，默认"python"，当前支持python
            clear_context (bool): 是否在执行前清除上下文，默认False
        
        Returns:
            result[Dict]: 包含stdout， stderr， exitcode信息的字典
        
        Example: # 执行Python代码
            >>> result = client.execute_code('''
            ...     import pandas as pd
            ...     df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
            ...     print(df.describe())
            ... '''
            >>> )
            >>> # 清除上下文
            >>> result = client.execute_code("x = 10", clear_context=True)
        """
        valid_languages = ["python"]
        if language not in valid_languages:
            raise ValueError(f"Invalid language. Supported languages are: {', '.join(valid_languages)}")

        logger.info(f"Executing {language} code")

        result = self.invoke(
            operate_type="execute_code",
            arguments={
                "code": code,
                "language": language,
                "clear_context": clear_context
            }
        )
        return result
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """在代码解释器中执行命令
        
        Args:
            command (str): 要执行的命令
        
        Returns:
            result[Dict]: 包含命令执行结果的字典
        
        Example: 
            >>> # 列出所有文件
            >>> result = client.execute_command("ls -la")

            >>> # 检查python版本
            >>> result = client.execute_command("python --version")
        """
        # 定义允许的安全字符
        pattern = r"^[a-zA-Z0-9_\-\.=\s\/\.:]+$"
        if not re.match(pattern, command):
            raise ValueError("Invalid command format")

        # 检查常见的注入模式
        strict_block_pattrns = [
        ]

        for pattern in strict_block_pattrns:
            if re.search(pattern, command):
                raise ValueError("Command contains potentially dangerous patterns")
        
        logger.info(f"Executing command: {command}")

        return self.invoke(
            operate_type="execute_command",
            arguments={
                "command": command
            }
        )

    def upload_file(
            self,
            path: str,
            content: Union[str, bytes],
            description: str = "",
    ) -> Dict[str, Any]:
        """上传文件到代码解释器
        
        Args:
            path (str): 文件路径，支持绝对路径和相对路径，必须以"/"开头，当前仅支持/home/user路径下文件上传
            content (Union[str, bytes]): 文件内容，可以是字符串或二进制数据，二进制内容将被Base64编码
            description (str): 文件描述，此字段可用于LLMs理解数据结构
                                （例如： "CSV" with columns: data, revenue, product_id）
        
        Returns:
            result[Dict]: 包含文件上传结果的字典
        
        Example:
            >>> # 上传CSV文件
            ... result = client.upload_file(
            ...     path="/home/user/my-file.csv",
            ...     content="data, revenue\\n2026-01-01, 1000\\n2026-01-02, 2000"),
            >>>     description='Daily sales data with columns: data, revenue')
        """
        
        if not path.startswith("/"):
            path = os.path.normpath(path)
            path = os.path.join(DEFAULT_PATH, path)
        else:
            if not path.startswith(DEFAULT_PATH):
                raise ValueError(f"Invalid path. Path must start with {DEFAULT_PATH}")
        
        # 处理二进制内容
        if isinstance(content, bytes):
            file_content = {"path": path, "blob": base64.b64encode(content).decode("utf-8")}
        else:
            file_content = {"path": path, "text": content}
        
        if description:
            logger.info(f"Uploading file to {path} with description: {description}")
        else:
            logger.info(f"Uploading file to {path} without description")
        
        result = self.invoke(
            operate_type="write_files",
            arguments={
                "write_contents": [file_content]
            }
        )
        return result

    def upload_files(
            self,
            files: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """上传多个文件到代码解释器
        
        此操作为原子化，所有文件上传成功或失败，不会部分上传
        
        Args:
            files (List[Dict[str, str]]): 文件路径和内容的列表，每个文件包含"path"和"content"键
                - "path": 文件路径，支持绝对路径和相对路径，必须以"/"开头，当前仅支持/home/user路径下文件上传
                - "content": 文件内容（string 或 bytes）
                - "description": 文件描述，此字段可用于LLMs理解数据结构
        
        Returns:
            result[Dict]: 包含文件上传结果的字典
        
        Example:
            >>> # 上传多个文件
            ... result = client.upload_files([
            ...     {"path": "/data.txt", "content": "Hello, World!"},
            ...     {"path": "/home/user/my-binary-file", "content": b"123456"}
            >>> ])
        """
        file_contents = []
        for file_spec in files:
            path = file_spec.get("path")
            content = file_spec.get("content")

            if not path.startswith("/"):
                path = os.path.normpath(path)
                path = os.path.join(DEFAULT_PATH, path)
            else:
                if not path.startswith(DEFAULT_PATH):
                    raise ValueError(f"Invalid path. Path must start with {DEFAULT_PATH}")
            
            # 处理二进制内容
            if isinstance(content, bytes):
                file_content = {"path": path, "blob": base64.b64encode(content).decode("utf-8")}
            else:
                file_content = {"path": path, "text": content}
            
            file_contents.append(file_content)
        
        logger.info(f"Uploading {len(file_contents)} files")

        result = self.invoke(
            operate_type="write_files",
            arguments={
                "write_contents": file_contents
            }
        )
        return result
    
    def download_file(
            self,
            path: str
    ) -> Union[str, bytes]:
        """从代码解释器下载文件
        
        Args:
            path (str): 文件路径，必须以"/"开头，当前仅支持/home/user路径下文件下载
        
        Returns:
            content[Union[str, bytes]]: 文件内容, 文本文件或字节文件（图片，PDF等）
        
        Example:
            >>> # 下载文件
            ... content = client.download_file("/home/user/data.txt")
        """
        
        if not path.startswith(DEFAULT_PATH):
            raise ValueError(f"Invalid path. Path must start with {DEFAULT_PATH}")
        
        logger.info(f"Downloading file from {path}")
        result = self.invoke(
            operate_type="read_files",
            arguments={
                "paths": [path]
            }
        )

        # 提取文件内容
        if "stream" not in result:
            raise FileNotFoundError(f"Cloud not read file: {path}")

        for event in result["stream"]:
            if "result" not in event:
                raise FileNotFoundError(f"Cloud not read file: {path}")
            for content_item in event["result"].get("contents", []):
                if content_item.get("type") != "resource":
                    raise FileNotFoundError(f"Cloud could not read file: {path}")
                resource = content_item.get("resource", {})
                if "text" in resource:
                    return resource["text"]
                elif "blob" in resource:
                    raw = base64.b64decode(resource["blob"])
                    try:
                        return raw.decode("utf-8")
                    except ValueError:
                        return raw
        raise FileNotFoundError(f"Cloud not read file: {path}")
    
    def download_files(
            self,
            paths: List[str]
    ) -> Dict[str, Union[str, bytes]]:
        """从代码解释器下载多个文件（仅支持/home/user路径下文件下载）
        
        Args:
            paths (List[str]): 文件路径列表，每个路径必须以"/"开头，当前仅支持/home/user路径下文件下载
        
        Returns:
            files[Dict[str, Union[str, bytes]]]: 包含文件路径和内容的字典，键为文件路径，值为文件内容（文本或字节）
        
        Example:
            >>> # 下载多个文件
            >>> files = client.download_files(["/home/user/data.txt", "/home/user/my-binary-file"])
        """
        
        logger.info(f"Downloading {len(paths)} files")
        for path in paths:
            if not path.startswith(DEFAULT_PATH):
                raise ValueError(f"Invalid path. Path must start with {DEFAULT_PATH}")
        result = self.invoke(
            operate_type="read_files",
            arguments={
                "paths": paths
            }
        )

        files = {}
        for event in result["stream"]:
            if "result" not in event:
                return files
            for content_item in event["result"].get("contents", []):
                if content_item.get("type") != "resource":
                    return files
                resource = content_item.get("resource", {})
                uri = resource.get("uri", "")
                file_path = uri.replace("file://", "")

                if "text" in resource:
                    files[file_path] = resource["text"]
                elif "blob" in resource:
                    raw = base64.b64decode(resource["blob"])
                    try:
                        files[file_path] = raw.decode("utf-8")
                    except ValueError:
                        files[file_path] = raw
        return files

    def install_packages(
            self,
            packages: List[str],
            upgrade: bool = False
    ) -> Dict[str, Any]:
        """在代码解释器中安装Python包
        
        Args:
            packages (List[str]): 要安装的Python包列表，支持版本指定，如["requests", "numpy==1.24.3"]
            upgrade (bool, optional): 是否升级已安装的包，默认False
        
        Returns:
            result[Dict[str, Any]]: 包含命令执行结果的字典
        
        Example:
            >>> # 安装多个Python包
            >>> result = client.install_packages(["requests", "numpy"])

            >>> # 安装指定版本的包
            >>> result = client.install_packages(["requests==2.26.0", "numpy==1.24.3"])

            >>> # 升级已安装的包
            >>> result = client.install_packages(["requests", "numpy"], upgrade=True)
        """
        
        if not packages:
            raise ValueError("Package list cannot be empty")
        
        for pkg in packages:
            if any(char in pkg for char in [';', '&', '|', '`', '$']):
                raise ValueError(f"Invalid package name: {pkg}")
        
        package_str = " ".join(packages)
        upgrade_flag = "--upgrade" if upgrade else ""
        command = f"pip install {package_str} {upgrade_flag}"

        logger.info(f"Installing packages: {package_str}")
        result = self.invoke(
            operate_type="execute_command",
            arguments={
                "command": command
            }
        )
        return result
    
    def clear_context(self) -> Dict[str, Any]:
        """清除代码解释器上下文

        重置代码解释器到一个全新的状态，清除所有之前已经定义的变量，包导入和函数定义

        注意：仅对Python代码有效
        
        Returns:
            result[Dict[str, Any]]: 包含命令执行结果的字典
        
        Example:
            >>> client.execute_code("x = 10")
            >>> client.execute_code("print(x)")
            >>> # 清除上下文
            >>> result = client.clear_context()
            >>> client.execute_code("print(x)")
        """
        logger.info("Clearing code interpreter context")
        result = self.invoke(
            operate_type="execute_code",
            arguments={
                "code": "# Context cleared",
                "language": "python",
                "clear_context": True
            }
        )
        return result
    
@contextmanager
def code_session(
    region: str, 
    code_interpreter_name: str,
    api_key: Optional[str] = None
) -> Generator[CodeInterpreter, None, None]:
    """代码解释器会话上下文管理器
    
    Args:
        region (str): region名称，如"cn-southwest-2"
        code_interpreter_name (str): 代码解释器名称
        api_key (Optional[str]): API Key，如果不提供则从环境变量HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY中获取
    
    Yields:
        CodeInterpreter: 会话启动完成的代码解释器实例
        
    Example:
        >>> with code_session("cn-southwest-2", "my-code-interpreter-name") as client:
        >>>     client.execute_code("print('Hello, World!')")
        >>> 
        >>> # 传入 API Key
        >>> with code_session("cn-southwest-2", "my-code-interpreter-name", api_key="your-api-key") as client:
        >>>     client.execute_code("print('Hello, World!')")
    """

    client = CodeInterpreter(region=region)
    default_session_name = "default-session-name"
    client.start_session(
        code_interpreter_name=code_interpreter_name, 
        session_name=default_session_name,
        api_key=api_key
    )

    try:
        yield client
    finally:
        client.stop_session(api_key=api_key)