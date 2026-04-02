"""
Common utility functions for CLI
"""

import click


def echo_error(message: str):
    """Echo error message in red
    
    Args:
        message: Error message to display
    """
    click.echo(click.style(f"[ERROR] {message}", fg="red"), err=True)


def echo_success(message: str):
    """Echo success message in green
    
    Args:
        message: Success message to display
    """
    click.echo(click.style(f"[SUCCESS] {message}", fg="green"))


def echo_warning(message: str):
    """Echo warning message in yellow
    
    Args:
        message: Warning message to display
    """
    click.echo(click.style(f"[WARNING] {message}", fg="yellow"))
