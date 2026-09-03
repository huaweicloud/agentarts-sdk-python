"""
Unit tests for User-Agent construction utilities
"""

from importlib.metadata import PackageNotFoundError

from agentarts.sdk.utils.user_agent import (
    build_user_agent,
    get_os_metadata,
    get_sdk_version,
)


def _raise_package_not_found(_name: str) -> str:
    raise PackageNotFoundError()


class TestUserAgent:
    """Test User-Agent construction utilities"""

    def test_get_sdk_version_is_not_placeholder(self):
        """Version should come from package metadata, not the 0.0.1 placeholder."""
        assert get_sdk_version() != "0.0.1"

    def test_get_sdk_version_fallback(self, monkeypatch):
        """Fallback version is returned when the package is not installed."""
        import agentarts.sdk.utils.user_agent as ua_module

        monkeypatch.setattr(ua_module, "version", _raise_package_not_found)
        assert get_sdk_version() == "0.1.0"

    def test_get_os_metadata_format(self):
        """OS metadata uses the os/<system>/<release> format."""
        meta = get_os_metadata()
        assert meta.startswith("os/")
        assert meta.count("/") == 2

    def test_build_user_agent_without_original(self):
        """Without an original value, output is exactly os metadata + version."""
        assert build_user_agent() == (
            f"{get_os_metadata()} agentarts-sdk-python/{get_sdk_version()}"
        )

    def test_build_user_agent_preserves_original(self):
        """The original User-Agent value is preserved, not replaced."""
        original = "python-requests/2.31.0"
        ua = build_user_agent(original)
        assert ua == (
            f"{original} {get_os_metadata()} agentarts-sdk-python/{get_sdk_version()}"
        )

    def test_build_user_agent_ordering(self):
        """Format is <original> os/<system>/<release> agentarts-sdk-python/<version>."""
        ua = build_user_agent("python-requests/2.31.0")
        assert ua.startswith("python-requests/2.31.0 os/")
        assert " agentarts-sdk-python/" in ua
        assert ua.count("agentarts-sdk-python/") == 1
