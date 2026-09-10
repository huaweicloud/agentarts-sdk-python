"""AgentArts LangGraph 集成层自定义异常体系。

提供 LangGraph 集成模块（saver.py / store.py）的统一异常类型，
使用户可以按异常类型做差异化处理（如重试网络错误、不重试验证错误）。

异常类命名加 ``AgentArts`` 前缀，避免与 pydantic.ValidationError、
requests.ConnectionError 等第三方库同名类冲突。

底层异常（``MemoryAPIException``，即 ``APIException`` 子类）通过
``map_exception`` 转换为本模块异常：
- 网络错误（status_code==0 / is_network_error）→ AgentArtsNetworkError
- 401 / 403 → AgentArtsAuthenticationError
- 400 / 422 → AgentArtsValidationError
- 404 → AgentArtsResourceNotFoundError
- 429 / 其余 5xx → AgentArtsServiceError
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentarts.sdk.service import APIException


class AgentArtsIntegrationError(Exception):
    """LangGraph 集成模块所有异常的基类。

    用户可用 ``except AgentArtsIntegrationError`` 捕获所有集成层错误。

    Attributes:
        cause: 触发本次失败的底层异常（通常是 ``APIException``），无则为 None。
            由 ``map_exception`` 填充，同时也作为 ``__cause__`` 链接，便于
            ``raise ... from ...`` 的追溯。
    """

    def __init__(self, message: str, *, cause: Exception | None = None):
        self.cause = cause
        super().__init__(message)


class AgentArtsNetworkError(AgentArtsIntegrationError):
    """网络波动、超时等错误。

    可重试。checkpointer 异常不适用 LangGraph retry_policy，用户可在
    ``graph.invoke()`` 外层自行重试（如 tenacity）。
    """


class AgentArtsAuthenticationError(AgentArtsIntegrationError):
    """鉴权失败、API Key 无效等。不可重试，需用户检查配置。"""


class AgentArtsValidationError(AgentArtsIntegrationError):
    """数据格式错误、参数无效等。不可重试，需用户修改代码。"""


class AgentArtsServiceError(AgentArtsIntegrationError):
    """服务端 5xx 错误。可能适合重试（如 503 限流）。"""


class AgentArtsResourceNotFoundError(AgentArtsIntegrationError):
    """404 资源不存在。

    读取类操作（get / list / search）把 404 视为"无数据"并返回 None / []，
    不会抛出本异常；写入、删除等操作的 404 则由本异常向上抛出。
    """


def map_exception(exc: APIException) -> AgentArtsIntegrationError:
    """将底层 ``APIException`` 映射为集成层自定义异常。

    基于 ``status_code`` / ``error_code`` / ``is_network_error`` 判断
    （底层已用 status_code==0 区分网络错误）。

    注意：本函数只处理 ``APIException``。调用方应只在
    ``except APIException`` 分支内调用它，其他异常（ValueError 等编程错误）
    保持原样抛出，不包装、不吞没。
    """
    if getattr(exc, "is_network_error", False) or exc.status_code == 0:
        cls: type[AgentArtsIntegrationError] = AgentArtsNetworkError
    elif exc.status_code in (401, 403):
        cls = AgentArtsAuthenticationError
    elif exc.status_code in (400, 422):
        cls = AgentArtsValidationError
    elif exc.status_code == 404:
        cls = AgentArtsResourceNotFoundError
    elif exc.status_code == 429 or exc.status_code >= 500:
        cls = AgentArtsServiceError
    else:
        cls = AgentArtsIntegrationError

    message = f"[{exc.error_code}] HTTP {exc.status_code}: {exc.error_msg}"
    mapped = cls(message)
    mapped.cause = exc
    return mapped


__all__ = [
    "AgentArtsIntegrationError",
    "AgentArtsNetworkError",
    "AgentArtsAuthenticationError",
    "AgentArtsValidationError",
    "AgentArtsServiceError",
    "AgentArtsResourceNotFoundError",
    "map_exception",
]
