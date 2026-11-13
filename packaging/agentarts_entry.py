"""PyInstaller entry point for the standalone agentarts CLI binary.

Invokes the typer app exactly like the ``agentarts`` console script
(``agentarts.toolkit.main:cli``), so sys.argv is parsed naturally.
"""

from agentarts.toolkit.main import cli

if __name__ == "__main__":
    cli()
