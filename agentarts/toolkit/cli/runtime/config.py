"""Config command definitions"""

from typing import Annotated, Optional

import typer

from agentarts.toolkit.operations.runtime import config as config_op


def set(
    key: Annotated[str, typer.Argument(help="Configuration key")],
    value: Annotated[str, typer.Argument(help="Configuration value")],
):
    """
    Set configuration value.

    Examples:
        agentarts config set region cn-north-4
    """
    config_op.set_config(key, value)


def get(
    key: Annotated[Optional[str], typer.Argument(help="Configuration key")] = None,
):
    """
    Get configuration value.

    Examples:
        agentarts config get region
    """
    success = config_op.get_config(key)
    if not success:
        raise typer.Exit(1)


def list():
    """
    List all configuration values.

    Examples:
        agentarts config list
    """
    config_op.list_config()
