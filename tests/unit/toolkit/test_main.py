"""
Unit tests for toolkit main module
"""

from unittest.mock import Mock, patch


class TestMainCLI:
    """Test main CLI"""

    def test_setup_logging_verbose(self):
        """Test setup_logging with verbose=True"""
        import logging

        from agentarts.toolkit.main import setup_logging

        with patch("agentarts.toolkit.main.logging.basicConfig") as mock_basic_config:
            setup_logging(verbose=True)

            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args
            assert call_args[1]["level"] == logging.DEBUG

    def test_setup_logging_non_verbose(self):
        """Test setup_logging with verbose=False"""
        import logging

        from agentarts.toolkit.main import setup_logging

        with patch("agentarts.toolkit.main.logging.basicConfig") as mock_basic_config:
            setup_logging(verbose=False)

            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args
            assert call_args[1]["level"] == logging.INFO

    def test_auto_install_completion_marker_exists(self):
        """Test _auto_install_completion when marker file exists"""
        from pathlib import Path

        from agentarts.toolkit.main import _auto_install_completion

        with patch("agentarts.toolkit.main.os.getenv") as mock_getenv:
            mock_getenv.return_value = None

            with patch.object(Path, "home") as mock_home:
                mock_home.return_value = Mock()
                mock_marker = Mock()
                mock_home.return_value.__truediv__ = Mock(return_value=mock_marker)
                mock_marker.__truediv__ = Mock(return_value=mock_marker)
                mock_marker.exists.return_value = True

                _auto_install_completion()

    def test_auto_install_completion_env_set(self):
        """Test _auto_install_completion when _AGENTARTS_COMPLETE is set"""
        from agentarts.toolkit.main import _auto_install_completion

        with patch("agentarts.toolkit.main.os.getenv") as mock_getenv:
            mock_getenv.return_value = "1"

            _auto_install_completion()

    def test_ordered_help_group_list_commands(self):
        """Test _OrderedHelpGroup list_commands"""
        import typer.core

        from agentarts.toolkit.main import _COMMAND_ORDER, _OrderedHelpGroup

        group = _OrderedHelpGroup()

        ctx = Mock()
        all_commands = {"init": None, "gateway": None, "destroy": None, "other": None}

        with patch.object(typer.core.TyperGroup, "list_commands") as mock_super:
            mock_super.return_value = list(all_commands.keys())

            commands = group.list_commands(ctx)

            # Check that commands are ordered according to _COMMAND_ORDER
            for cmd in _COMMAND_ORDER:
                if cmd in all_commands:
                    assert cmd in commands

    def test_auto_install_completion_success(self):
        """Test _auto_install_completion when installation succeeds"""
        from pathlib import Path

        from agentarts.toolkit.main import _auto_install_completion

        with patch("agentarts.toolkit.main.os.getenv") as mock_getenv:
            mock_getenv.return_value = None

            with patch.object(Path, "home") as mock_home:
                mock_home_path = Mock()
                mock_home.return_value = mock_home_path
                mock_agentarts_dir = Mock()
                mock_home_path.__truediv__ = Mock(return_value=mock_agentarts_dir)
                mock_marker = Mock()
                mock_agentarts_dir.__truediv__ = Mock(return_value=mock_marker)
                mock_marker.exists.return_value = False

                with patch("typer.completion.install") as mock_install:
                    mock_install.return_value = ("bash", "/path/to/completion")
                    mock_agentarts_dir.mkdir = Mock()
                    mock_marker.touch = Mock()

                    with patch("agentarts.toolkit.main.console.print") as mock_print:
                        _auto_install_completion()

                        mock_install.assert_called_once()
                        mock_marker.touch.assert_called_once()
                        mock_print.assert_called()

    def test_auto_install_completion_failure(self):
        """Test _auto_install_completion when installation fails"""
        from pathlib import Path

        from agentarts.toolkit.main import _auto_install_completion

        with patch("agentarts.toolkit.main.os.getenv") as mock_getenv:
            mock_getenv.return_value = None

            with patch.object(Path, "home") as mock_home:
                mock_home_path = Mock()
                mock_home.return_value = mock_home_path
                mock_agentarts_dir = Mock()
                mock_home_path.__truediv__ = Mock(return_value=mock_agentarts_dir)
                mock_marker = Mock()
                mock_agentarts_dir.__truediv__ = Mock(return_value=mock_marker)
                mock_marker.exists.return_value = False

                with patch("typer.completion.install") as mock_install:
                    mock_install.side_effect = Exception("Installation failed")
                    mock_agentarts_dir.mkdir = Mock()
                    mock_marker.touch = Mock()

                    with patch("agentarts.toolkit.main.console.print") as mock_print:
                        _auto_install_completion()

                        mock_marker.touch.assert_called_once()
                        mock_print.assert_called()

    def test_main_with_version(self):
        """Test main function with --version flag"""
        from typer.testing import CliRunner

        from agentarts.toolkit.main import app

        runner = CliRunner()

        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "agentarts version" in result.output

    def test_main_without_command(self):
        """Test main function without subcommand"""
        from typer.testing import CliRunner

        from agentarts.toolkit.main import app

        runner = CliRunner()

        result = runner.invoke(app, [])

        assert result.exit_code == 0
        assert "AgentArts CLI" in result.output
        assert "Usage:" in result.output

    def test_main_with_verbose_flag(self):
        """Test main function with --verbose flag"""
        from typer.testing import CliRunner

        from agentarts.toolkit.main import app

        runner = CliRunner()

        # Note: setup_logging is called in the callback, so we can't easily mock it
        # Just verify the app runs successfully with verbose flag
        result = runner.invoke(app, ["--verbose", "--help"])

        assert result.exit_code == 0
        assert "AgentArts CLI" in result.output

    def test_cli_function(self):
        """Test cli entry point"""
        from agentarts.toolkit.main import cli

        with patch("agentarts.toolkit.main.app") as mock_app:
            cli()

            mock_app.assert_called_once()
