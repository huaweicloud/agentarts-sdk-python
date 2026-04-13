"""Dev command definition"""

from typing import Annotated, Optional

import typer

from agentarts.toolkit.operations.runtime import dev as dev_op


def dev(
    port: Annotated[int, typer.Option("--port", "-p", help="Server port")] = 8080,
    host: Annotated[str, typer.Option("--host", "-h", help="Server host")] = "0.0.0.0",
    reload: Annotated[bool, typer.Option("--reload", help="Enable auto-reload")] = False,
    config: Annotated[
        Optional[str],
        typer.Option("--config", "-c", help="Configuration file path"),
    ] = None,
):
    """
    Run local development server.

    Examples:
        agentarts dev --port 8080 --reload
    """
    success = dev_op.run_dev_server(port=port, host=host, reload=reload, config_path=config)
    if not success:
        raise typer.Exit(1)
