"""Toolkit (agentarts CLI) integration / e2e tests.

These exercise the real `agentarts` CLI (Typer app) end-to-end — no mocking of
operations or SDK clients. Local commands (init/config/dev) need no credentials;
cloud commands (memory/mcp-gateway/runtime) reuse the parent suite's gating
fixtures (cloud_credentials / allow_create / allow_billable / resource_registry).
"""
