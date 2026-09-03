"""User-Agent construction utilities.

Builds a User-Agent suffix of the form
``os/<system>/<release> agentarts-sdk-python/<version>`` and appends it to an
existing value rather than replacing it.
"""

import platform
from importlib.metadata import PackageNotFoundError, version

SDK_DISTRIBUTION = "agentarts-sdk"
SDK_PRODUCT = "agentarts-sdk-python"
_FALLBACK_VERSION = "0.1.0"


def get_sdk_version() -> str:
    """Return the installed SDK version from package metadata."""
    try:
        return version(SDK_DISTRIBUTION)
    except PackageNotFoundError:
        return _FALLBACK_VERSION


def get_os_metadata() -> str:
    """Return the operating system metadata in ``os/<system>/<release>`` form."""
    return f"os/{platform.system()}/{platform.release()}"


def build_user_agent(original: str | None = None) -> str:
    """Append the SDK version and OS metadata to an existing User-Agent.

    Args:
        original: The pre-existing User-Agent value to preserve. When omitted,
            the returned string contains only the SDK version and OS metadata.

    Returns:
        A combined User-Agent string.
    """
    suffix = f"{get_os_metadata()} {SDK_PRODUCT}/{get_sdk_version()}"
    if original:
        return f"{original} {suffix}"
    return suffix
