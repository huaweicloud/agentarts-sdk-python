"""
Runtime CLI Commands

Provides CLI commands for runtime operations (cloud only):
- invoke: Invoke agent with JSON payload
- exec-command: Execute command with streaming response
- upload-files: Upload files to runtime
- download-files: Download files from runtime
- stop-session: Stop runtime session
"""

import typer

from agentarts.toolkit.cli.runtime.download_files import download_files_cmd
from agentarts.toolkit.cli.runtime.exec_command import exec_command_cmd
from agentarts.toolkit.cli.runtime.invoke import invoke
from agentarts.toolkit.cli.runtime.stop_session import stop_session_cmd
from agentarts.toolkit.cli.runtime.upload_files import upload_files_cmd

runtime_app = typer.Typer(
    name="runtime",
    help="Runtime operations (cloud only): invoke, exec-command, upload-files, download-files, stop-session",
    add_completion=False,
)

runtime_app.command(name="invoke")(invoke)
runtime_app.command(name="exec-command")(exec_command_cmd)
runtime_app.command(name="upload-files")(upload_files_cmd)
runtime_app.command(name="download-files")(download_files_cmd)
runtime_app.command(name="stop-session")(stop_session_cmd)
