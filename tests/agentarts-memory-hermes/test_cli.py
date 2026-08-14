"""Tests for the agentarts_memory CLI subcommands."""

import argparse
import json
from unittest.mock import MagicMock, patch

import pytest
from cli import _config, _handle_command, _status, _test_connection, register_cli
from provider import AgentArtsMemoryProvider

ENV_VARS = {
    "HUAWEICLOUD_SDK_MEMORY_API_KEY": "test-api-key",
    "HUAWEICLOUD_SDK_REGION": "cn-southwest-2",
    "AGENTARTS_MEMORY_SPACE_ID": "test-space-id",
}


@pytest.fixture
def env_vars(monkeypatch):
    for key, val in ENV_VARS.items():
        monkeypatch.setenv(key, val)


@pytest.fixture
def no_env_vars(monkeypatch):
    for key in ENV_VARS:
        monkeypatch.delenv(key, raising=False)


# ── register_cli ──


class TestRegisterCli:
    def test_creates_subcommands(self):
        parser = argparse.ArgumentParser(prog="hermes")
        subparser = parser.add_subparsers(dest="agentarts_memory")
        agentarts_parser = subparser.add_parser("agentarts_memory")
        register_cli(agentarts_parser)

        args = parser.parse_args(["agentarts_memory", "status"])
        assert args.agentarts_memory_command == "status"

        args = parser.parse_args(["agentarts_memory", "config"])
        assert args.agentarts_memory_command == "config"

        args = parser.parse_args(["agentarts_memory", "test"])
        assert args.agentarts_memory_command == "test"

    def test_sets_default_func(self):
        parser = argparse.ArgumentParser(prog="hermes")
        subparser = parser.add_subparsers(dest="agentarts_memory")
        agentarts_parser = subparser.add_parser("agentarts_memory")
        register_cli(agentarts_parser)

        args = parser.parse_args(["agentarts_memory", "status"])
        assert hasattr(args, "func")
        assert callable(args.func)

    def test_no_subcommand(self):
        parser = argparse.ArgumentParser(prog="hermes")
        subparser = parser.add_subparsers(dest="agentarts_memory")
        agentarts_parser = subparser.add_parser("agentarts_memory")
        register_cli(agentarts_parser)

        args = parser.parse_args(["agentarts_memory"])
        assert args.agentarts_memory_command is None

    def test_func_is_handle_command(self):
        parser = argparse.ArgumentParser(prog="hermes")
        subparser = parser.add_subparsers(dest="agentarts_memory")
        agentarts_parser = subparser.add_parser("agentarts_memory")
        register_cli(agentarts_parser)

        args = parser.parse_args(["agentarts_memory", "status"])
        assert args.func is _handle_command


# ── _handle_command dispatch ──


class TestHandleCommandDispatch:
    def test_dispatches_status(self, env_vars, capsys):
        args = argparse.Namespace(agentarts_memory_command="status")
        _handle_command(args)
        out = capsys.readouterr().out
        assert "Status" in out

    def test_dispatches_config(self, env_vars, capsys, tmp_path, monkeypatch):
        config_path = tmp_path / "agentarts.json"
        config_path.write_text(json.dumps({"space_id": "s1", "region": "r1"}), encoding="utf-8")
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))

        args = argparse.Namespace(agentarts_memory_command="config")
        _handle_command(args)
        out = capsys.readouterr().out
        assert "Configuration" in out
        assert "s1" in out

    def test_dispatches_test(self, env_vars, capsys):
        mock_provider = MagicMock(spec=AgentArtsMemoryProvider)
        mock_provider.is_available.return_value = True

        with patch("cli.AgentArtsMemoryProvider", return_value=mock_provider):
            args = argparse.Namespace(agentarts_memory_command="test")
            _handle_command(args)
            out = capsys.readouterr().out
            assert "PASSED" in out
            mock_provider.initialize.assert_called_once()
            mock_provider.shutdown.assert_called_once()

    def test_no_subcommand_prints_usage(self, capsys):
        args = argparse.Namespace(agentarts_memory_command=None)
        _handle_command(args)
        out = capsys.readouterr().out
        assert "Usage" in out
        assert "status" in out
        assert "config" in out
        assert "test" in out


# ── _status ──


class TestStatusCommand:
    def test_shows_available_when_env_set(self, env_vars, capsys):
        _status(argparse.Namespace())
        out = capsys.readouterr().out
        assert "Available" in out
        assert "yes" in out

    def test_shows_unavailable_when_env_missing(self, no_env_vars, capsys):
        _status(argparse.Namespace())
        out = capsys.readouterr().out
        assert "Available" in out
        assert "no" in out

    def test_lists_all_env_vars(self, env_vars, capsys):
        _status(argparse.Namespace())
        out = capsys.readouterr().out
        assert "HUAWEICLOUD_SDK_MEMORY_API_KEY" in out
        assert "AGENTARTS_MEMORY_SPACE_ID" in out
        assert "HUAWEICLOUD_SDK_REGION" in out

    def test_shows_warning_for_missing_vars(self, no_env_vars, capsys):
        _status(argparse.Namespace())
        out = capsys.readouterr().out
        assert "MISSING" in out
        assert "Warning" in out

    def test_masks_secret_values(self, env_vars, capsys):
        _status(argparse.Namespace())
        out = capsys.readouterr().out
        assert "test-api-key" not in out

    def test_shows_region_in_plaintext(self, env_vars, capsys):
        _status(argparse.Namespace())
        out = capsys.readouterr().out
        assert "cn-southwest-2" in out

    def test_missing_optional_var_shows_optional_label(self, monkeypatch, capsys):
        for key, val in ENV_VARS.items():
            if key == "HUAWEICLOUD_SDK_REGION":
                continue
            monkeypatch.setenv(key, val)
        monkeypatch.delenv("HUAWEICLOUD_SDK_REGION", raising=False)

        _status(argparse.Namespace())
        out = capsys.readouterr().out
        assert "optional" in out


# ── _config ──


class TestConfigCommand:
    def test_shows_config_file_content(self, env_vars, tmp_path, monkeypatch, capsys):
        config_path = tmp_path / "agentarts.json"
        config_path.write_text(
            json.dumps({"space_id": "space-xyz", "region": "cn-north-4"}), encoding="utf-8"
        )
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))

        _config(argparse.Namespace())
        out = capsys.readouterr().out
        assert "Configuration" in out
        assert "space-xyz" in out
        assert "cn-north-4" in out

    def test_no_hermes_home(self, monkeypatch, capsys):
        monkeypatch.delenv("HERMES_HOME", raising=False)
        _config(argparse.Namespace())
        out = capsys.readouterr().out
        assert "HERMES_HOME is not set" in out

    def test_no_config_file(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        _config(argparse.Namespace())
        out = capsys.readouterr().out
        assert "No configuration file found" in out

    def test_empty_config_file(self, tmp_path, monkeypatch, capsys):
        config_path = tmp_path / "agentarts.json"
        config_path.write_text("{}", encoding="utf-8")
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))

        _config(argparse.Namespace())
        out = capsys.readouterr().out
        assert "empty" in out


# ── _test_connection ──


class TestConnectionCommand:
    def test_passes_when_available(self, env_vars, capsys):
        mock_provider = MagicMock(spec=AgentArtsMemoryProvider)
        mock_provider.is_available.return_value = True

        with patch("cli.AgentArtsMemoryProvider", return_value=mock_provider):
            _test_connection(argparse.Namespace())
            out = capsys.readouterr().out
            assert "PASSED" in out
            assert "OK" in out
            mock_provider.initialize.assert_called_once()
            mock_provider.shutdown.assert_called_once()

    def test_fails_when_not_available(self, no_env_vars, capsys):
        _test_connection(argparse.Namespace())
        out = capsys.readouterr().out
        assert "FAILED" in out
        assert "not set" in out

    def test_fails_on_init_error(self, env_vars, capsys):
        mock_provider = MagicMock(spec=AgentArtsMemoryProvider)
        mock_provider.is_available.return_value = True
        mock_provider.initialize.side_effect = RuntimeError("connection refused")

        with patch("cli.AgentArtsMemoryProvider", return_value=mock_provider):
            _test_connection(argparse.Namespace())
            out = capsys.readouterr().out
            assert "FAILED" in out
            assert "connection refused" in out

    def test_calls_shutdown_even_on_error(self, env_vars, capsys):
        mock_provider = MagicMock(spec=AgentArtsMemoryProvider)
        mock_provider.is_available.return_value = True
        mock_provider.initialize.side_effect = RuntimeError("init failed")

        with patch("cli.AgentArtsMemoryProvider", return_value=mock_provider):
            _test_connection(argparse.Namespace())
            mock_provider.initialize.assert_called_once()
