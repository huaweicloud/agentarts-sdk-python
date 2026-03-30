"""Dev command implementation"""

import os
import sys
from pathlib import Path
from typing import Optional
import click
import yaml


def run_dev_server(
    port: int,
    host: str,
    reload: bool,
    config_path: Optional[str]
):
    """
    Run development server
    
    Args:
        port: Server port
        host: Server host
        reload: Enable auto-reload
        config_path: Configuration file path
    """
    config = load_config(config_path)
    
    agent_file = Path("agent.py")
    if not agent_file.exists():
        click.echo("Error: agent.py not found", err=True)
        click.echo("Please run 'agentarts init' first")
        return
    
    os.environ["AGENTARTS_ENV"] = "development"
    os.environ["AGENTARTS_CONFIG"] = config_path or "agentarts.yaml"
    
    click.echo(f"\n🚀 Starting development server on {host}:{port}")
    click.echo(f"📝 Config: {config_path or 'agentarts.yaml'}")
    click.echo(f"🔄 Auto-reload: {'enabled' if reload else 'disabled'}")
    click.echo(f"\n📚 API Documentation: http://{host}:{port}/docs")
    click.echo(f"🔍 Health Check: http://{host}:{port}/health\n")
    
    try:
        import uvicorn
        from agentarts.wrapper.service import HTTPServer
        
        sys.path.insert(0, os.getcwd())
        
        server = HTTPServer(
            title=config.get("project", {}).get("name", "AgentArts"),
            version=config.get("project", {}).get("version", "1.0.0")
        )
        
        uvicorn.run(
            server.app,
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except ImportError as e:
        click.echo(f"Error: Failed to start server - {e}", err=True)
        click.echo("Make sure all dependencies are installed: pip install -e .")


def load_config(config_path: Optional[str]) -> dict:
    """Load configuration file"""
    if config_path:
        path = Path(config_path)
    else:
        path = Path("agentarts.yaml")
    
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    return {}
