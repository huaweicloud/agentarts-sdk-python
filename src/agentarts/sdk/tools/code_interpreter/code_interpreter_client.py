"""Client for interacting with the Code Interpreter sandbox service.

This module provides a client for Huawei Cloud Code Interpreter, supporting
operations like starting, stopping, and invoking code in a managed sandbox environment.

Control Plane:
    Manages the full lifecycle of code interpreters
    (create, list, update, get, delete)

Data Plane:
    Manages the full lifecycle of code interpreter sessions
    (create, stop, get, invoke)
"""
import base64
import logging
import os
import re
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from agentarts.sdk.service.tools_http import ControlToolsHttpClient, DataToolsHttpClient
from agentarts.sdk.utils.constant import (
    get_code_interpreter_data_plane_endpoint,
    get_control_plane_endpoint,
    get_region,
)

DEFAULT_TIMEOUT = 900  # Default 15 minutes
DEFAULT_PATH = "/home/user"  # Default path, currently only supports upload/download in this path

logger = logging.getLogger(__name__)


class CodeInterpreter:
    """Client for interacting with the Code Interpreter sandbox service.

    This client handles the full lifecycle and method invocations for code interpreter
    sandbox sessions, providing interfaces for executing code, uploading/downloading files,
    installing dependencies, and more in a secure, managed environment.

    Attributes:
        control_plane_client: Client for interacting with control plane API
        data_plane_client: Client for interacting with data plane API
    """

    def __init__(self, region: str | None, data_endpoint: str | None = None) -> None:
        """Initialize the code interpreter client in the specified region.

        Args:
            region: The specified region
            data_endpoint: Data plane endpoint, optional. If not provided,
                will be retrieved from environment variable AGENTARTS_CODEINTERPRETER_DATA_ENDPOINT
        """
        region = region or get_region()

        # Control plane client for managing code interpreters
        self.control_plane_client = ControlToolsHttpClient(
            region_name=region,
            endpoint_url=get_control_plane_endpoint()
        )

        # Data plane client for managing code interpreter sessions
        # Priority: environment variable > parameter > default value
        endpoint_url = get_code_interpreter_data_plane_endpoint(endpoint=data_endpoint)

        self.data_plane_client = DataToolsHttpClient(
            region_name=region,
            endpoint_url=endpoint_url
        )

        self._code_interpreter_name = None
        self._session_id = None

    @property
    def code_interpreter_name(self) -> str | None:
        """Get the current code interpreter name.

        Returns:
            Optional[str]: The current code interpreter name, or None if not set
        """
        return self._code_interpreter_name

    @code_interpreter_name.setter
    def code_interpreter_name(self, name: str) -> None:
        """Set the current code interpreter name.

        Args:
            name (str): The code interpreter name
        """
        self._code_interpreter_name = name

    @property
    def session_id(self) -> str | None:
        """Get the current session ID.

        Returns:
            Optional[str]: The current session ID, or None if not set
        """
        return self._session_id

    @session_id.setter
    def session_id(self, session_id: str) -> None:
        """Set the current session ID.

        Args:
            session_id (str): The session ID
        """
        self._session_id = session_id

    def create_code_interpreter(
        self,
        name: str,
        api_key_name: str,
        description: str | None = None,
        auth_type: str | None = None,
        execution_agency_name: str | None = None,
        observability: dict | None = None,
        network_config: dict | None = None,
        agent_gateway_id: str | None = None,
        tags: list[dict] | None = None,
    ) -> dict:
        """Create a custom code interpreter.

        Creates a new code interpreter through the control plane.

        Args:
            name (str): The code interpreter name, must follow specific naming rules
            api_key_name (str): The API Key name
            description (Optional[str]): The code interpreter description
            auth_type (Optional[str]): Authentication type, e.g., "API_KEY"
            execution_agency_name (Optional[str]): IAM agency name
            observability (Optional[Dict]): Observability configuration, e.g., logging and monitoring settings
            network_config (Optional[Dict]): Network configuration, e.g., VPC and security group settings
            agent_gateway_id (Optional[str]): Associated Agent Gateway ID
            tags (Optional[List[Dict]]): Tag list, each tag is a dict containing "key" and "value"

        Returns:
            Dict: Dictionary containing the newly created code interpreter information
                - id(str): Code interpreter ID
                - name(str): Code interpreter name
                - description(str): Code interpreter description
                - created_at(str): Code interpreter creation time
                - updated_at(str): Code interpreter update time
                - execution_agency_name(str): IAM agency name
                - workload_identity(Dict): Workload identity information
                - access_endpoint(str): Code interpreter access endpoint
                - observability(Dict): Observability configuration (logs + metrics)
                - tags(List[Dict]): Tag list, each tag is a dict containing "key" and "value"
                - network_config(Dict): Network configuration, e.g., VPC and security group settings

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
            msg = "Name must match the pattern, please check your code_interpreter_name."
            raise ValueError(msg)

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

        return self.control_plane_client.create_code_interpreter(
            request_params=request_params
        )

    def list_code_interpreters(
        self,
        name: str | None = None,
        limit: int = 10,
        offset: int = 0,
        sort_key: str | None = None,
        sort_dir: str | None = None,
    ) -> dict:
        """List code interpreters.

        Args:
            name (str): Fuzzy search by name
            limit (int): Number of code interpreters per page, default 10
            offset (int): Pagination offset, default 0
            sort_key (str): Sort field, must be 'created_at' or 'updated_at'
            sort_dir (str): Sort direction, must be 'asc' or 'desc'

        Returns:
            Dict: Dictionary containing code interpreter list and pagination info
                - total_count(int): Total number of code interpreters matching the query
                - items(List[Dict]): Code interpreter list

        Example:
            >>> result = client.list_code_interpreters(
            ...     name="my-code-interpreter",
            ...     sort_key="created_at",
            ...     sort_dir="asc"
            >>> )

        """
        logging.info("Listing code interpreters")
        if sort_key and sort_key not in ["created_at", "updated_at"]:
            msg = "sort_key must be either 'created_at' or 'updated_at'"
            raise ValueError(msg)
        if sort_dir and sort_dir not in ["asc", "desc"]:
            msg = "sort_dir must be either 'asc' or 'desc'"
            raise ValueError(msg)
        request_params = {
            "name": name,
            "limit": limit,
            "offset": offset,
            "sort_key": sort_key,
            "sort_dir": sort_dir,
        }

        # Remove None values
        request_params = {k: v for k, v in request_params.items() if v is not None}

        return self.control_plane_client.list_code_interpreters(
            request_params=request_params
        )

    def update_code_interpreter(
        self,
        code_interpreter_id: str,
        observability: dict | None = None,
        tags: list[dict] | None = None,
    ) -> dict:
        """Update code interpreter observability configuration and tags.

        Args:
            code_interpreter_id (str): The code interpreter ID
            observability (Dict): Observability configuration (logs + metrics), optional
            tags (List[Dict]): Tag list, each tag is a dict containing "key" and "value", optional

        Returns:
            Dict: Dictionary containing the updated code interpreter information
                - id(str): Code interpreter ID
                - name(str): Code interpreter name
                - description(str): Code interpreter description
                - created_at(str): Code interpreter creation time
                - updated_at(str): Code interpreter update time
                - execution_agency_name(str): IAM agency name
                - agent_gateway_id(str): Agent Gateway ID that the code interpreter belongs to
                - workload_identity(Dict): Workload identity information
                - access_endpoint(str): Code interpreter access endpoint
                - observability(Dict): Observability configuration (logs + metrics)
                - tags(List[Dict]): Tag list, each tag is a dict containing "key" and "value"

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
        return self.control_plane_client.update_code_interpreter(
            code_interpreter_id=code_interpreter_id,
            request_params=request_params
        )

    def get_code_interpreter(self, code_interpreter_id: str) -> dict:
        """Get code interpreter details.

        Args:
            code_interpreter_id (str): The code interpreter ID

        Returns:
            Dict: Dictionary containing code interpreter details
                - id(str): Code interpreter ID
                - name(str): Code interpreter name
                - description(str): Code interpreter description
                - created_at(str): Code interpreter creation time
                - updated_at(str): Code interpreter update time
                - execution_agency_name(str): IAM agency name
                - agent_gateway_id(str): Agent Gateway ID that the code interpreter belongs to
                - workload_identity(Dict): Workload identity information
                - access_endpoint(str): Code interpreter access endpoint
                - observability(Dict): Observability configuration (logs + metrics)
                - tags(List[Dict]): Tag list, each tag is a dict containing "key" and "value"
                - auth_type(str): Tool authentication method
                - api_key_name(str): API Key name
                - network_config(Dict): Network configuration, e.g., VPC and security group settings

        Example:
            >>> result = client.get_code_interpreter(
            ...     code_interpreter_id="my-code-interpreter-id"
            >>> )
        """
        logging.info(f"Getting code interpreter {code_interpreter_id}")
        return self.control_plane_client.get_code_interpreter(
            code_interpreter_id=code_interpreter_id
        )

    def delete_code_interpreter(self, code_interpreter_id: str) -> None:
        """Delete a specified code interpreter.

        Args:
            code_interpreter_id (str): The code interpreter ID

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
        session_name: str,
        api_key: str | None = None,
        session_timeout: int | None = DEFAULT_TIMEOUT
    ) -> str:
        """Start a code interpreter session.

        Initializes a new code interpreter session with the provided parameters
        and returns the session ID.

        Args:
            code_interpreter_name (str): The code interpreter name, used to identify and manage sessions, must be unique
            session_name (str): The session name
            api_key (Optional[str]): API Key for authentication, if not provided will be retrieved from environment variable API_KEY
            session_timeout (Optional[int]): Session timeout in seconds,
                default 15 minutes, minimum 60 seconds, maximum 86400 seconds (24 hours)

        Returns:
            session_id (str): The session ID

        Example:
            >>> session_id = client.start_session(
            ...     code_interpreter_name="my-code-interpreter-name",
            ...     session_name="my-session-name"
            >>> )
        """
        logging.info("Starting codeinterpreter session...")
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
            session_id: str | None = None,
            api_key: str | None = None
    ) -> dict:
        """Get code interpreter session details.

        Args:
            code_interpreter_name (str): The code interpreter name, used to identify and manage sessions, must be unique
            session_id (Optional[str]): The session ID, defaults to current session ID
            api_key (Optional[str]): API Key for authentication, if not provided will be retrieved from environment variable API_KEY

        Returns:
            Dict: Dictionary containing session details
                - code_interpreter_id(str): Code interpreter ID
                - created_at(str): Session creation time
                - session_name(str): Session name
                - session_id(str): Session ID
                - session_timeout(int): Session timeout in seconds

        Example:
            >>> session_info = client.get_session(
            ...     code_interpreter_name="my-code-interpreter-name"
            >>> )
        """
        logging.info("Getting codeinterpreter session...")

        session_id = session_id or self.session_id
        if not code_interpreter_name or not session_id:
            msg = "code_interpreter_name and session_id are required"
            raise ValueError(msg)
        if api_key is None:
            api_key = os.getenv("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")
        return self.data_plane_client.get_session(
            code_interpreter_name=code_interpreter_name,
            session_id=session_id,
            api_key=api_key
        )

    def stop_session(self, api_key: str | None = None) -> bool:
        """Stop the current code interpreter session.

        Terminates any active session and clears session state.

        Args:
            api_key (Optional[str]): API Key for authentication, if not provided will be retrieved from environment variable API_KEY

        Returns:
            bool: Returns True when no active session, otherwise False after stopping

        Example:
            >>> client.stop_session()
        """
        logging.info("Stopping codeinterpreter session...")
        if not self.session_id or not self.code_interpreter_name:
            return True

        if api_key is None:
            api_key = os.getenv("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

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
            arguments: dict,
            api_key: str | None = None
    ) -> dict[str, Any]:
        """Invoke a code interpreter session.

        If there is no active session, one will be automatically started before the invocation.

        Args:
            operate_type (str): The operation method name, e.g., "execute_code" or "execute_command"
            arguments (Dict): Invocation arguments, varies based on operate_type
            api_key (Optional[str]): API Key for authentication, if not provided will be retrieved from environment variable API_KEY

        Returns:
            result[Dict]: Dictionary containing the invocation result

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
            msg = "No Code Interpreter exists, use create_code_interpreter method first"
            raise ValueError(msg)

        request_params = {
            "operate_type": operate_type,
            "arguments": arguments
        }

        if api_key is None:
            api_key = os.getenv("HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY")

        return self.data_plane_client.invoke(
            code_interpreter_name=self.code_interpreter_name,
            session_id=self.session_id,
            api_key=api_key,
            arguments=request_params
        )

    def execute_code(
            self,
            code: str,
            language: str = "python",
            clear_context: bool = False,
    ) -> dict[str, Any]:
        """Execute code in the code interpreter.

        Args:
            code (str): The code to execute
            language (str): The programming language, default "python", currently supports python
            clear_context (bool): Whether to clear context before execution, default False

        Returns:
            result[Dict]: Dictionary containing stdout, stderr, and exit_code information

        Example:
            >>> result = client.execute_code('''
            ...     import pandas as pd
            ...     df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
            ...     print(df.describe())
            ... '''
            >>> )
            >>> # Clear context
            >>> result = client.execute_code("x = 10", clear_context=True)
        """
        valid_languages = ["python"]
        if language not in valid_languages:
            msg = f"Invalid language. Supported languages are: {', '.join(valid_languages)}"
            raise ValueError(msg)

        logger.info(f"Executing {language} code")

        return self.invoke(
            operate_type="execute_code",
            arguments={
                "code": code,
                "language": language,
                "clear_context": clear_context
            }
        )

    def execute_command(self, command: str) -> dict[str, Any]:
        """Execute a command in the code interpreter.

        Args:
            command (str): The command to execute

        Returns:
            result[Dict]: Dictionary containing the command execution result

        Example:
            >>> # List all files
            >>> result = client.execute_command("ls -la")

            >>> # Check python version
            >>> result = client.execute_command("python --version")
        """
        # Define allowed safe characters
        pattern = r"^[a-zA-Z0-9_\-\.=\s\/\.:]+$"
        if not re.match(pattern, command):
            msg = "Invalid command format"
            raise ValueError(msg)

        # Check for common injection patterns
        strict_block_pattrns = [
        ]

        for pattern in strict_block_pattrns:
            if re.search(pattern, command):
                msg = "Command contains potentially dangerous patterns"
                raise ValueError(msg)

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
            content: str | bytes,
            description: str = "",
    ) -> dict[str, Any]:
        """Upload a file to the code interpreter.

        Args:
            path (str): File path, supports absolute and relative paths, must start with "/",
                currently only supports file upload under /home/user path
            content (Union[str, bytes]): File content, can be string or binary data,
                binary content will be Base64 encoded
            description (str): File description, this field can be used for LLMs to understand data structure
                                (e.g., "CSV with columns: date, revenue, product_id")

        Returns:
            result[Dict]: Dictionary containing the file upload result

        Example:
            >>> # Upload a CSV file
            ... result = client.upload_file(
            ...     path="/home/user/my-file.csv",
            ...     content="date, revenue\\n2026-01-01, 1000\\n2026-01-02, 2000"),
            >>>     description='Daily sales data with columns: date, revenue')
        """

        if not path.startswith("/"):
            path = os.path.normpath(path)
            path = os.path.join(DEFAULT_PATH, path)
        elif not path.startswith(DEFAULT_PATH):
            msg = f"Invalid path. Path must start with {DEFAULT_PATH}"
            raise ValueError(msg)

        # Handle binary content
        if isinstance(content, bytes):
            file_content = {"path": path, "blob": base64.b64encode(content).decode("utf-8")}
        else:
            file_content = {"path": path, "text": content}

        if description:
            logger.info(f"Uploading file to {path} with description: {description}")
        else:
            logger.info(f"Uploading file to {path} without description")

        return self.invoke(
            operate_type="write_files",
            arguments={
                "write_contents": [file_content]
            }
        )

    def upload_files(
            self,
            files: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Upload multiple files to the code interpreter.

        This operation is atomic, all files will be uploaded successfully or fail together,
        no partial uploads.

        Args:
            files (List[Dict[str, str]]): List of file paths and contents, each file contains "path" and "content" keys
                - "path": File path, supports absolute and relative paths, must start with "/",
                    currently only supports file upload under /home/user path
                - "content": File content (string or bytes)
                - "description": File description, this field can be used for LLMs to understand data structure

        Returns:
            result[Dict]: Dictionary containing the file upload result

        Example:
            >>> # Upload multiple files
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
            elif not path.startswith(DEFAULT_PATH):
                msg = f"Invalid path. Path must start with {DEFAULT_PATH}"
                raise ValueError(msg)

            # Handle binary content
            if isinstance(content, bytes):
                file_content = {"path": path, "blob": base64.b64encode(content).decode("utf-8")}
            else:
                file_content = {"path": path, "text": content}

            file_contents.append(file_content)

        logger.info(f"Uploading {len(file_contents)} files")

        return self.invoke(
            operate_type="write_files",
            arguments={
                "write_contents": file_contents
            }
        )

    def download_file(
            self,
            path: str
    ) -> str | bytes:
        """Download a file from the code interpreter.

        Args:
            path (str): File path, must start with "/",
                currently only supports file download under /home/user path

        Returns:
            content[Union[str, bytes]]: File content, text file or binary file (images, PDFs, etc.)

        Example:
            >>> # Download a file
            ... content = client.download_file("/home/user/data.txt")
        """

        if not path.startswith(DEFAULT_PATH):
            msg = f"Invalid path. Path must start with {DEFAULT_PATH}"
            raise ValueError(msg)

        logger.info(f"Downloading file from {path}")
        result = self.invoke(
            operate_type="read_files",
            arguments={
                "paths": [path]
            }
        )

        # Extract file content
        if "stream" not in result:
            msg = f"Could not read file: {path}"
            raise FileNotFoundError(msg)

        for event in result["stream"]:
            if "result" not in event:
                msg = f"Could not read file: {path}"
                raise FileNotFoundError(msg)
            for content_item in event["result"].get("contents", []):
                if content_item.get("type") != "resource":
                    msg = f"Could not read file: {path}"
                    raise FileNotFoundError(msg)
                resource = content_item.get("resource", {})
                if "text" in resource:
                    return resource["text"]
                if "blob" in resource:
                    raw = base64.b64decode(resource["blob"])
                    try:
                        return raw.decode("utf-8")
                    except ValueError:
                        return raw
        msg = f"Could not read file: {path}"
        raise FileNotFoundError(msg)

    def download_files(
            self,
            paths: list[str]
    ) -> dict[str, str | bytes]:
        """Download multiple files from the code interpreter.

        Args:
            paths (List[str]): List of file paths, each path must start with "/",
                currently only supports file download under /home/user path

        Returns:
            files[Dict[str, Union[str, bytes]]]: Dictionary containing file paths and contents,
                keys are file paths, values are file contents (text or bytes)

        Example:
            >>> # Download multiple files
            >>> files = client.download_files(["/home/user/data.txt", "/home/user/my-binary-file"])
        """

        logger.info(f"Downloading {len(paths)} files")
        for path in paths:
            if not path.startswith(DEFAULT_PATH):
                msg = f"Invalid path. Path must start with {DEFAULT_PATH}"
                raise ValueError(msg)
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
            packages: list[str],
            upgrade: bool = False
    ) -> dict[str, Any]:
        """Install Python packages in the code interpreter.

        Args:
            packages (List[str]): List of Python packages to install, supports version specification,
                e.g., ["requests", "numpy==1.24.3"]
            upgrade (bool, optional): Whether to upgrade installed packages, default False

        Returns:
            result[Dict[str, Any]]: Dictionary containing the command execution result

        Example:
            >>> # Install multiple Python packages
            >>> result = client.install_packages(["requests", "numpy"])

            >>> # Install specific versions
            >>> result = client.install_packages(["requests==2.26.0", "numpy==1.24.3"])

            >>> # Upgrade installed packages
            >>> result = client.install_packages(["requests", "numpy"], upgrade=True)
        """

        if not packages:
            msg = "Package list cannot be empty"
            raise ValueError(msg)

        for pkg in packages:
            if any(char in pkg for char in [";", "&", "|", "`", "$"]):
                msg = f"Invalid package name: {pkg}"
                raise ValueError(msg)

        package_str = " ".join(packages)
        upgrade_flag = "--upgrade" if upgrade else ""
        command = f"pip install {package_str} {upgrade_flag}"

        logger.info(f"Installing packages: {package_str}")
        return self.invoke(
            operate_type="execute_command",
            arguments={
                "command": command
            }
        )

    def clear_context(self) -> dict[str, Any]:
        """Clear the code interpreter context.

        Resets the code interpreter to a fresh state, clearing all previously
        defined variables, package imports, and function definitions.

        Note: Only effective for Python code.

        Returns:
            result[Dict[str, Any]]: Dictionary containing the command execution result

        Example:
            >>> client.execute_code("x = 10")
            >>> client.execute_code("print(x)")
            >>> # Clear context
            >>> result = client.clear_context()
            >>> client.execute_code("print(x)")
        """
        logger.info("Clearing code interpreter context")
        return self.invoke(
            operate_type="execute_code",
            arguments={
                "code": "# Context cleared",
                "language": "python",
                "clear_context": True
            }
        )

@contextmanager
def code_session(
    region: str,
    code_interpreter_name: str,
    api_key: str | None = None
) -> Generator[CodeInterpreter, None, None]:
    """Code interpreter session context manager.

    Args:
        region (str): Region name, e.g., "cn-southwest-2"
        code_interpreter_name (str): Code interpreter name
        api_key (Optional[str]): API Key, if not provided will be retrieved from
            environment variable HUAWEICLOUD_SDK_CODE_INTERPRETER_API_KEY

    Yields:
        CodeInterpreter: Code interpreter instance with session started

    Example:
        >>> with code_session("cn-southwest-2", "my-code-interpreter-name") as client:
        >>>     client.execute_code("print('Hello, World!')")
        >>>
        >>> # With API Key
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
