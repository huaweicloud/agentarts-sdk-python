"""Comprehensive unit tests for constant.py module"""

import os
import pytest

from agentarts.wrapper.utils.constant import (
    HUAWEICLOUD_SDK_AK,
    HUAWEICLOUD_SDK_SK,
    HUAWEICLOUD_SDK_SECURITY_TOKEN,
    HUAWEICLOUD_SDK_IDP_ID,
    HUAWEICLOUD_SDK_ID_TOKEN_FILE,
    HUAWEICLOUD_SDK_PROJECT_ID,
    AGENTARTS_CONTROL_ENDPOINT,
    AGENTARTS_RUNTIME_DATA_ENDPOINT,
    AGENTARTS_MEMORY_DATA_ENDPOINT,
    HUAWEICLOUD_SDK_IAM_ENDPOINT,
    HUAWEICLOUD_SDK_SWR_ENDPOINT,
    PYTHON_BASE_IMAGE,
    get_region,
    get_control_plane_endpoint,
    get_data_plane_endpoint,
    get_memory_endpoint,
)


# ============================================================
# get_region Tests
# ============================================================

class TestGetRegion:
    """Tests for get_region() function."""

    def test_returns_huaweicloud_sdk_region(self, monkeypatch):
        """HUAWEICLOUD_SDK_REGION takes highest priority."""
        monkeypatch.setenv("HUAWEICLOUD_SDK_REGION", "cn-north-1")
        monkeypatch.setenv("HUAWEICLOUD_REGION", "cn-north-4")
        monkeypatch.setenv("OS_REGION_NAME", "cn-southwest-2")
        assert get_region() == "cn-north-1"

    def test_returns_huaweicloud_region(self, monkeypatch):
        """HUAWEICLOUD_REGION takes second priority."""
        monkeypatch.delenv("HUAWEICLOUD_SDK_REGION", raising=False)
        monkeypatch.setenv("HUAWEICLOUD_REGION", "cn-north-4")
        monkeypatch.setenv("OS_REGION_NAME", "cn-southwest-2")
        assert get_region() == "cn-north-4"

    def test_returns_os_region_name(self, monkeypatch):
        """OS_REGION_NAME takes third priority."""
        monkeypatch.delenv("HUAWEICLOUD_SDK_REGION", raising=False)
        monkeypatch.delenv("HUAWEICLOUD_REGION", raising=False)
        monkeypatch.setenv("OS_REGION_NAME", "cn-southwest-2")
        assert get_region() == "cn-southwest-2"

    def test_returns_default_when_no_env_set(self, monkeypatch):
        """Returns default 'cn-southwest-2' when no env vars are set."""
        monkeypatch.delenv("HUAWEICLOUD_SDK_REGION", raising=False)
        monkeypatch.delenv("HUAWEICLOUD_REGION", raising=False)
        monkeypatch.delenv("OS_REGION_NAME", raising=False)
        assert get_region() == "cn-southwest-2"

    def test_returns_empty_string_when_sdk_region_is_empty(self, monkeypatch):
        """Returns default when HUAWEICLOUD_SDK_REGION is set but empty."""
        monkeypatch.setenv("HUAWEICLOUD_SDK_REGION", "")
        monkeypatch.setenv("HUAWEICLOUD_REGION", "cn-north-4")
        assert get_region() == "cn-north-4"


# ============================================================
# get_control_plane_endpoint Tests
# ============================================================

class TestGetControlPlaneEndpoint:
    """Tests for get_control_plane_endpoint() function."""

    def test_returns_custom_control_endpoint(self, monkeypatch):
        """Returns AGENTARTS_CONTROL_ENDPOINT when set."""
        monkeypatch.setenv("AGENTARTS_CONTROL_ENDPOINT", "https://custom.example.com")
        monkeypatch.setenv("HUAWEICLOUD_SDK_REGION", "cn-north-4")
        assert get_control_plane_endpoint() == "https://custom.example.com"

    def test_constructs_from_explicit_region(self, monkeypatch):
        """Constructs endpoint from explicit region parameter."""
        monkeypatch.delenv("AGENTARTS_CONTROL_ENDPOINT", raising=False)
        monkeypatch.setenv("HUAWEICLOUD_SDK_REGION", "cn-north-4")
        result = get_control_plane_endpoint("cn-southwest-2")
        assert result == "https://agentarts.cn-southwest-2.myhuaweicloud.com"

    def test_constructs_from_env_region(self, monkeypatch):
        """Constructs endpoint from environment region."""
        monkeypatch.delenv("AGENTARTS_CONTROL_ENDPOINT", raising=False)
        monkeypatch.setenv("HUAWEICLOUD_SDK_REGION", "cn-north-4")
        result = get_control_plane_endpoint()
        assert result == "https://agentarts.cn-north-4.myhuaweicloud.com"

    def test_uses_default_region(self, monkeypatch):
        """Uses default region when no region is provided or set."""
        monkeypatch.delenv("AGENTARTS_CONTROL_ENDPOINT", raising=False)
        monkeypatch.delenv("HUAWEICLOUD_SDK_REGION", raising=False)
        monkeypatch.delenv("HUAWEICLOUD_REGION", raising=False)
        monkeypatch.delenv("OS_REGION_NAME", raising=False)
        result = get_control_plane_endpoint()
        assert result == "https://agentarts.cn-southwest-2.myhuaweicloud.com"

    def test_explicit_region_overrides_env(self, monkeypatch):
        """Explicit region parameter overrides environment variable."""
        monkeypatch.delenv("AGENTARTS_CONTROL_ENDPOINT", raising=False)
        monkeypatch.setenv("HUAWEICLOUD_SDK_REGION", "cn-north-4")
        result = get_control_plane_endpoint("cn-east-3")
        assert result == "https://agentarts.cn-east-3.myhuaweicloud.com"


# ============================================================
# get_data_plane_endpoint Tests
# ============================================================

class TestGetDataPlaneEndpoint:
    """Tests for get_data_plane_endpoint() function."""

    def test_returns_explicit_endpoint(self, monkeypatch):
        """Returns the explicit endpoint parameter when provided."""
        monkeypatch.setenv("AGENTARTS_RUNTIME_DATA_ENDPOINT", "https://env.example.com")
        result = get_data_plane_endpoint("https://custom.example.com")
        assert result == "https://custom.example.com"

    def test_returns_env_endpoint(self, monkeypatch):
        """Returns AGENTARTS_RUNTIME_DATA_ENDPOINT from environment."""
        monkeypatch.setenv("AGENTARTS_RUNTIME_DATA_ENDPOINT", "https://env.example.com")
        result = get_data_plane_endpoint()
        assert result == "https://env.example.com"

    def test_returns_empty_when_not_configured(self, monkeypatch):
        """Returns empty string when no endpoint is configured."""
        monkeypatch.delenv("AGENTARTS_RUNTIME_DATA_ENDPOINT", raising=False)
        result = get_data_plane_endpoint()
        assert result == ""


# ============================================================
# get_memory_endpoint Tests
# ============================================================

class TestGetMemoryEndpoint:
    """Tests for get_memory_endpoint() function."""

    def test_control_type_returns_control_plane(self, monkeypatch):
        """Returns control plane endpoint for 'control' type."""
        monkeypatch.delenv("AGENTARTS_CONTROL_ENDPOINT", raising=False)
        monkeypatch.setenv("HUAWEICLOUD_SDK_REGION", "cn-north-4")
        result = get_memory_endpoint("control")
        assert result == "https://agentarts.cn-north-4.myhuaweicloud.com"

    def test_control_type_with_explicit_region(self, monkeypatch):
        """Returns control plane endpoint with explicit region."""
        monkeypatch.delenv("AGENTARTS_CONTROL_ENDPOINT", raising=False)
        result = get_memory_endpoint("control", "cn-southwest-2")
        assert result == "https://agentarts.cn-southwest-2.myhuaweicloud.com"

    def test_data_type_returns_env_endpoint(self, monkeypatch):
        """Returns AGENTARTS_MEMEORY_DATA_ENDPOINT for 'data' type when set."""
        monkeypatch.setenv("AGENTARTS_MEMEORY_DATA_ENDPOINT", "https://memory.example.com")
        result = get_memory_endpoint("data")
        assert result == "https://memory.example.com"

    def test_data_type_constructs_from_region_and_space(self, monkeypatch):
        """Constructs data endpoint from region and space_id."""
        monkeypatch.delenv("AGENTARTS_MEMEORY_DATA_ENDPOINT", raising=False)
        monkeypatch.delenv("AGENTARTS_CONTROL_ENDPOINT", raising=False)
        monkeypatch.setenv("HUAWEICLOUD_SDK_REGION", "cn-north-4")
        result = get_memory_endpoint("data", "cn-north-4", "my-workspace")
        assert result == "https://my-workspace.memory.cn-north-4.agentarts.myhuaweicloud.com"

    def test_data_type_uses_default_region(self, monkeypatch):
        """Uses default region when not provided for data endpoint."""
        monkeypatch.delenv("AGENTARTS_MEMEORY_DATA_ENDPOINT", raising=False)
        monkeypatch.delenv("AGENTARTS_CONTROL_ENDPOINT", raising=False)
        monkeypatch.delenv("HUAWEICLOUD_SDK_REGION", raising=False)
        monkeypatch.delenv("HUAWEICLOUD_REGION", raising=False)
        monkeypatch.delenv("OS_REGION_NAME", raising=False)
        result = get_memory_endpoint("data", space_id="my-workspace")
        assert result == "https://my-workspace.memory.cn-southwest-2.agentarts.myhuaweicloud.com"

    def test_data_type_raises_without_space_id(self, monkeypatch):
        """Raises ValueError when space_id is not provided for 'data' type."""
        monkeypatch.delenv("AGENTARTS_MEMEORY_DATA_ENDPOINT", raising=False)
        with pytest.raises(ValueError, match="space_id is required"):
            get_memory_endpoint("data")

    def test_invalid_type_raises(self, monkeypatch):
        """Raises ValueError for invalid endpoint_type."""
        with pytest.raises(ValueError, match="Invalid endpoint type: invalid"):
            get_memory_endpoint("invalid")

    def test_data_type_env_endpoint_overrides_construction(self, monkeypatch):
        """AGENTARTS_MEMEORY_DATA_ENDPOINT takes priority over constructed URL."""
        monkeypatch.setenv("AGENTARTS_MEMEORY_DATA_ENDPOINT", "https://custom-memory.example.com")
        result = get_memory_endpoint("data", "cn-north-4", "my-workspace")
        assert result == "https://custom-memory.example.com"

    def test_data_type_with_explicit_region(self, monkeypatch):
        """Uses explicit region parameter for data endpoint construction."""
        monkeypatch.delenv("AGENTARTS_MEMEORY_DATA_ENDPOINT", raising=False)
        monkeypatch.setenv("HUAWEICLOUD_SDK_REGION", "cn-north-4")
        result = get_memory_endpoint("data", "cn-southwest-2", "my-workspace")
        assert result == "https://my-workspace.memory.cn-southwest-2.agentarts.myhuaweicloud.com"


# ============================================================
# Environment Variable Loading Tests
# ============================================================

class TestEnvironmentVariableLoading:
    """Tests that environment variables are correctly read by os.getenv."""

    def test_ak_loaded_from_env(self, monkeypatch):
        """HUAWEICLOUD_SDK_AK is read from environment via os.getenv."""
        monkeypatch.setenv("HUAWEICLOUD_SDK_AK", "test-ak")
        assert os.getenv("HUAWEICLOUD_SDK_AK") == "test-ak"

    def test_sk_loaded_from_env(self, monkeypatch):
        """HUAWEICLOUD_SDK_SK is read from environment via os.getenv."""
        monkeypatch.setenv("HUAWEICLOUD_SDK_SK", "test-sk")
        assert os.getenv("HUAWEICLOUD_SDK_SK") == "test-sk"

    def test_security_token_loaded_from_env(self, monkeypatch):
        """HUAWEICLOUD_SDK_SECURITY_TOKEN is read from environment via os.getenv."""
        monkeypatch.setenv("HUAWEICLOUD_SDK_SECURITY_TOKEN", "test-token")
        assert os.getenv("HUAWEICLOUD_SDK_SECURITY_TOKEN") == "test-token"

    def test_idp_id_loaded_from_env(self, monkeypatch):
        """HUAWEICLOUD_SDK_IDP_ID is read from environment via os.getenv."""
        monkeypatch.setenv("HUAWEICLOUD_SDK_IDP_ID", "test-idp")
        assert os.getenv("HUAWEICLOUD_SDK_IDP_ID") == "test-idp"

    def test_id_token_file_loaded_from_env(self, monkeypatch):
        """HUAWEICLOUD_SDK_ID_TOKEN_FILE is read from environment via os.getenv."""
        monkeypatch.setenv("HUAWEICLOUD_SDK_ID_TOKEN_FILE", "/path/to/token")
        assert os.getenv("HUAWEICLOUD_SDK_ID_TOKEN_FILE") == "/path/to/token"

    def test_project_id_loaded_from_env(self, monkeypatch):
        """HUAWEICLOUD_SDK_PROJECT_ID is read from environment via os.getenv."""
        monkeypatch.setenv("HUAWEICLOUD_SDK_PROJECT_ID", "proj-123")
        assert os.getenv("HUAWEICLOUD_SDK_PROJECT_ID") == "proj-123"

    def test_control_endpoint_loaded_from_env(self, monkeypatch):
        """AGENTARTS_CONTROL_ENDPOINT is read from environment via os.getenv."""
        monkeypatch.setenv("AGENTARTS_CONTROL_ENDPOINT", "https://control.example.com")
        assert os.getenv("AGENTARTS_CONTROL_ENDPOINT") == "https://control.example.com"

    def test_runtime_data_endpoint_loaded_from_env(self, monkeypatch):
        """AGENTARTS_RUNTIME_DATA_ENDPOINT is read from environment via os.getenv."""
        monkeypatch.setenv("AGENTARTS_RUNTIME_DATA_ENDPOINT", "https://data.example.com")
        assert os.getenv("AGENTARTS_RUNTIME_DATA_ENDPOINT") == "https://data.example.com"

    def test_memory_data_endpoint_loaded_from_env(self, monkeypatch):
        """AGENTARTS_MEMEORY_DATA_ENDPOINT is read from environment via os.getenv."""
        monkeypatch.setenv("AGENTARTS_MEMEORY_DATA_ENDPOINT", "https://memory.example.com")
        assert os.getenv("AGENTARTS_MEMEORY_DATA_ENDPOINT") == "https://memory.example.com"

    def test_iam_endpoint_loaded_from_env(self, monkeypatch):
        """HUAWEICLOUD_SDK_IAM_ENDPOINT is read from environment via os.getenv."""
        monkeypatch.setenv("HUAWEICLOUD_SDK_IAM_ENDPOINT", "https://iam.example.com")
        assert os.getenv("HUAWEICLOUD_SDK_IAM_ENDPOINT") == "https://iam.example.com"

    def test_swr_endpoint_loaded_from_env(self, monkeypatch):
        """HUAWEICLOUD_SDK_SWR_ENDPOINT is read from environment via os.getenv."""
        monkeypatch.setenv("HUAWEICLOUD_SDK_SWR_ENDPOINT", "https://swr.example.com")
        assert os.getenv("HUAWEICLOUD_SDK_SWR_ENDPOINT") == "https://swr.example.com"

    def test_python_base_image_loaded_from_env(self, monkeypatch):
        """PYTHON_BASE_IMAGE is read from environment via os.getenv."""
        monkeypatch.setenv("PYTHON_BASE_IMAGE", "python:3.12-slim")
        assert os.getenv("PYTHON_BASE_IMAGE") == "python:3.12-slim"
