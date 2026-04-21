"""Tests for SDK logging configuration utilities."""

import logging
from pathlib import Path

from agentarts.sdk.utils.logging import (
    DEFAULT_LOG_LEVEL,
    ENV_LOG_LEVEL,
    get_log_level,
    get_logger,
    setup_logging,
)


class TestGetLogLevel:
    """Tests for get_log_level function."""

    def test_returns_default_when_env_not_set(self, monkeypatch):
        """Returns default level when environment variable is not set."""
        monkeypatch.delenv(ENV_LOG_LEVEL, raising=False)
        assert get_log_level() == DEFAULT_LOG_LEVEL

    def test_returns_env_value_when_set(self, monkeypatch):
        """Returns environment variable value when set."""
        monkeypatch.setenv(ENV_LOG_LEVEL, "DEBUG")
        assert get_log_level() == "DEBUG"

    def test_returns_env_value_uppercase(self, monkeypatch):
        """Returns uppercase version of environment variable."""
        monkeypatch.setenv(ENV_LOG_LEVEL, "debug")
        assert get_log_level() == "DEBUG"

    def test_returns_default_for_invalid_level(self, monkeypatch):
        """Returns default for invalid level value."""
        monkeypatch.setenv(ENV_LOG_LEVEL, "INVALID")
        assert get_log_level() == DEFAULT_LOG_LEVEL

    def test_supports_all_valid_levels(self, monkeypatch):
        """Supports all valid log levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            monkeypatch.setenv(ENV_LOG_LEVEL, level)
            assert get_log_level() == level


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_sets_sdk_logger_level(self):
        """Sets the SDK logger level correctly."""
        sdk_logger = logging.getLogger("agentarts")
        sdk_logger.handlers.clear()
        setup_logging(level="DEBUG")
        assert sdk_logger.level == logging.DEBUG

    def test_adds_stream_handler_by_default(self):
        """Adds StreamHandler by default when no handler provided."""
        sdk_logger = logging.getLogger("agentarts")
        sdk_logger.handlers.clear()
        setup_logging(level="INFO")
        assert len(sdk_logger.handlers) == 1
        assert isinstance(sdk_logger.handlers[0], logging.StreamHandler)

    def test_does_not_add_duplicate_handlers(self):
        """Does not add duplicate handlers when called multiple times."""
        sdk_logger = logging.getLogger("agentarts")
        sdk_logger.handlers.clear()
        setup_logging(level="INFO")
        setup_logging(level="DEBUG")
        assert len(sdk_logger.handlers) == 1

    def test_uses_custom_handler(self):
        """Uses custom handler when provided."""
        sdk_logger = logging.getLogger("agentarts")
        sdk_logger.handlers.clear()
        custom_handler = logging.FileHandler("test.log", mode="w")
        setup_logging(level="INFO", handler=custom_handler)
        assert len(sdk_logger.handlers) == 1
        assert isinstance(sdk_logger.handlers[0], logging.FileHandler)
        custom_handler.close()
        Path("test.log").unlink()

    def test_uses_env_level_when_none_provided(self, monkeypatch):
        """Uses environment variable level when None provided."""
        monkeypatch.setenv(ENV_LOG_LEVEL, "WARNING")
        sdk_logger = logging.getLogger("agentarts")
        sdk_logger.handlers.clear()
        setup_logging()
        assert sdk_logger.level == logging.WARNING

    def test_suppresses_urllib3_warnings(self):
        """Suppresses urllib3 logger to WARNING level."""
        setup_logging(level="DEBUG")
        urllib3_logger = logging.getLogger("urllib3")
        assert urllib3_logger.level == logging.WARNING

    def test_suppresses_huaweicloudsdkcore_warnings(self):
        """Suppresses huaweicloudsdkcore logger to WARNING level."""
        setup_logging(level="DEBUG")
        sdk_logger = logging.getLogger("huaweicloudsdkcore")
        assert sdk_logger.level == logging.WARNING


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger_with_sdk_namespace(self):
        """Returns logger with agentarts namespace."""
        logger = get_logger("test")
        assert logger.name == "agentarts.test"

    def test_returns_logger_with_nested_namespace(self):
        """Returns logger with nested namespace."""
        logger = get_logger("runtime.app")
        assert logger.name == "agentarts.runtime.app"

    def test_returns_same_logger_for_same_name(self):
        """Returns same logger instance for same name."""
        logger1 = get_logger("test")
        logger2 = get_logger("test")
        assert logger1 is logger2


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    def test_logger_inherits_sdk_level(self, monkeypatch):
        """Child logger inherits SDK logger level."""
        monkeypatch.delenv(ENV_LOG_LEVEL, raising=False)
        sdk_logger = logging.getLogger("agentarts")
        sdk_logger.handlers.clear()
        setup_logging(level="DEBUG")

        child_logger = get_logger("runtime.app")
        assert child_logger.getEffectiveLevel() == logging.DEBUG

    def test_debug_messages_visible_at_debug_level(self, caplog):
        """Debug messages are visible at DEBUG level."""
        sdk_logger = logging.getLogger("agentarts")
        sdk_logger.handlers.clear()
        setup_logging(level="DEBUG")

        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG, logger="agentarts.test"):
            logger.debug("Debug message")
        assert "Debug message" in caplog.text

    def test_debug_messages_hidden_at_info_level(self, caplog):
        """Debug messages are hidden at INFO level."""
        sdk_logger = logging.getLogger("agentarts")
        sdk_logger.handlers.clear()
        setup_logging(level="INFO")

        logger = get_logger("test")
        logger.debug("Debug message")
        assert "Debug message" not in caplog.text

    def test_info_messages_visible_at_info_level(self, caplog):
        """Info messages are visible at INFO level."""
        sdk_logger = logging.getLogger("agentarts")
        sdk_logger.handlers.clear()
        setup_logging(level="INFO")

        logger = get_logger("test")
        with caplog.at_level(logging.INFO, logger="agentarts.test"):
            logger.info("Info message")
        assert "Info message" in caplog.text
