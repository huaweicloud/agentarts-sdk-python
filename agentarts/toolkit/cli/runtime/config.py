"""Config command implementation"""

import os
import json
from pathlib import Path
from typing import Optional
import click
import yaml


CONFIG_FILE = Path.home() / ".agentarts" / "config.yaml"


def ensure_config_dir():
    """Ensure config directory exists"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """Load configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(config: dict):
    """Save configuration"""
    ensure_config_dir()
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False)


def set_config(key: str, value: str):
    """
    Set configuration value
    
    Args:
        key: Configuration key
        value: Configuration value
    """
    config = load_config()
    
    keys = key.split('.')
    current = config
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    
    current[keys[-1]] = value
    save_config(config)
    
    click.echo(f"✓ Set {key} = {value}")


def get_config(key: Optional[str]):
    """
    Get configuration value
    
    Args:
        key: Configuration key (optional)
    """
    config = load_config()
    
    if key is None:
        list_config()
        return
    
    keys = key.split('.')
    current = config
    try:
        for k in keys:
            current = current[k]
        click.echo(f"{key} = {current}")
    except (KeyError, TypeError):
        click.echo(f"Config key '{key}' not found", err=True)


def list_config():
    """List all configuration values"""
    config = load_config()
    
    if not config:
        click.echo("No configuration found")
        return
    
    click.echo("\n📋 Configuration:")
    click.echo(yaml.dump(config, default_flow_style=False))
