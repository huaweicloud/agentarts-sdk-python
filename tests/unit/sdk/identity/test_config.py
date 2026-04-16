import json
from pathlib import Path

import pytest

from agentarts.sdk.identity.config import Config


def test_config_default_values():
    config = Config()
    assert config.workload_identity_name is None
    assert config.user_id is None
    assert config.path == Path(".agent_identity.json")


def test_config_save_load(tmp_path):
    config_file = tmp_path / "config.json"
    config = Config(
        workload_identity_name="test-identity", user_id="test-user", path=config_file
    )

    # Save to file
    config.save()

    # Check if file exists and has correct content
    assert config_file.exists()
    with open(config_file) as f:
        data = json.load(f)
    assert data["workload_identity_name"] == "test-identity"
    assert data["user_id"] == "test-user"
    assert "path" not in data  # Path should be excluded

    # Load from file
    loaded_config = Config.load(str(config_file))
    assert loaded_config.workload_identity_name == "test-identity"
    assert loaded_config.user_id == "test-user"
    assert loaded_config.path == config_file


def test_config_load_non_existent(tmp_path):
    config_file = tmp_path / "non_existent.json"
    config = Config.load(str(config_file))
    assert config.workload_identity_name is None
    assert config.user_id is None
    assert config.path == config_file


def test_config_validation():
    config = Config()
    with pytest.raises(ValueError):
        # Use setattr to bypass static type checking for intentional invalid assignment
        config.user_id = {"not": "a string"}
