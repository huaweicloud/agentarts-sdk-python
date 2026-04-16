"""Dev command definition"""

from typing import Annotated

import typer

from agentarts.toolkit.operations.runtime import dev as dev_op


def parse_env_var(env_str: str) -> tuple:
    """Parse environment variable string KEY=VALUE."""
    if "=" in env_str:
        key, value = env_str.split("=", 1)
        return key.strip(), value.strip()
    return env_str.strip(), ""


def dev(
    port: Annotated[int, typer.Option("--port", "-p", help="Server port")] = 8080,
    host: Annotated[str, typer.Option("--host", "-h", help="Server host")] = "0.0.0.0",
    reload: Annotated[bool, typer.Option("--reload", help="Enable auto-reload")] = False,
    config: Annotated[
        str | None,
        typer.Option("--config", "-c", help="Configuration file path"),
    ] = None,
    env: Annotated[
        list[str] | None,
        typer.Option("--env", "-e", help="Environment variables (KEY=VALUE). Can be used multiple times."),
    ] = None,
):
    """
    Run local development server.

    Environment variables can be set via --env option or in .agentarts_config.yaml.
    Command-line --env takes precedence over config file.

    Examples:
        agentarts dev --port 8080 --reload
        agentarts dev --env OPENAI_API_KEY=sk-xxx --env OPENAI_MODEL_NAME=gpt-4o
    """
    env_vars = {}
    if env:
        for env_str in env:
            key, value = parse_env_var(env_str)
            if key:
                env_vars[key] = value

    success = dev_op.run_dev_server(
        port=port,
        host=host,
        reload=reload,
        config_path=config,
        env_vars=env_vars if env_vars else None,
    )
    if not success:
        raise typer.Exit(1)
