"""SDK logging configuration utilities."""

import logging
import os
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

ENV_LOG_LEVEL = "AGENTARTS_LOG_LEVEL"

DEFAULT_LOG_LEVEL: LogLevel = "INFO"


def get_log_level() -> LogLevel:
    """Get log level from environment variable or default.

    Returns:
        Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    level = os.getenv(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL).upper()
    valid_levels: tuple[LogLevel, ...] = (
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    )
    if level not in valid_levels:
        level = DEFAULT_LOG_LEVEL
    return level


def setup_logging(
    level: LogLevel | None = None,
    format: str | None = None,
    handler: logging.Handler | None = None,
) -> None:
    """Configure SDK logging.

    Args:
        level: Log level. If None, use environment variable AGENTARTS_LOG_LEVEL.
        format: Log format string.
        handler: Custom handler. If None, use StreamHandler.

    Example:
        >>> setup_logging(level="DEBUG")
        >>> setup_logging()  # Use AGENTARTS_LOG_LEVEL env var

        # Or via environment variable:
        >>> import os
        >>> os.environ["AGENTARTS_LOG_LEVEL"] = "DEBUG"
    """
    if level is None:
        level = get_log_level()

    if format is None:
        format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    sdk_logger = logging.getLogger("agentarts")
    sdk_logger.setLevel(level)

    if not sdk_logger.handlers:
        if handler is None:
            handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(format))
        sdk_logger.addHandler(handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("huaweicloudsdkcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the SDK namespace.

    Args:
        name: Logger name (will be prefixed with 'agentarts.').

    Returns:
        Configured logger instance.

    Example:
        >>> logger = get_logger("runtime.app")
        >>> logger.info("Application started")
    """
    return logging.getLogger(f"agentarts.{name}")
