# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2026-06-06

### Added
- LangGraph memory store integration (`AgentArtsMemoryStore`) with sync/async support for put, get, search, batch operations
- Async `MemoryClient` for non-blocking memory operations
- Runtime CLI commands: `exec-command`, `upload-files`, `download-files`
- `file_transfer_config` in `invoke_config` for enabling file upload/download
- `url_match_type` in `invoke_config` (`ACCURATE_MATCH` / `PREFIX_MATCH`)
- `arch` field in runtime config with auto-detection (`arm64` / `x86_64`)
- `--custom-path` parameter for `invoke` command (replaces `--suffix`)
- Agent name validation (lowercase, digits, hyphens only)
- SWR URL support in deployment config
- Unit tests for runtime CLI commands and LangGraph store

### Changed
- `exec-command` API path fixed to `/runtimes/{agent_name}/commands`
- `invoke --suffix` renamed to `--custom-path` for clarity
- Upload file path handling: support remote directory path with trailing `/`
- Multi-file upload support via repeated `-f` flag
- Code interpreter name pattern validation
- Runtime CLI parameter optimization
- `init` command template content improvements

### Fixed
- Deploy parameter handling
- Removed deprecated `status` command
- Upload file messaging and error handling
- Architecture parameter passing

## [0.1.2] - 2026-05-26

### Added
- SWR organization name auto-generation with random string
- `skip_ssl_verification` parameter for Gateway

### Changed
- Adapt invoke URL format
- Code session parameter passing (api_key as keyword argument)
- Gateway removed `authorizer_configuration` parameter

### Fixed
- License headers
- Code session `api_key` parameter passing
- `agent_chat` function payload parameter support

## [0.1.1] - 2026-05-08

### Added
- IAM authentication support for tools
- `user-id` parameter for invoke CLI
- Request context for ping
- SSL verification enabled by default with custom certificate support
- Secure runtime binding with eth0 IP detection in Docker
- SDK logging configuration

### Changed
- Code interpreter authentication refactored for better code quality
- Default agent name handling
- Dockerfile improvements
- Server host detection

### Fixed
- `contextvars` propagation in sync handlers
- Async contextvar copying
- SSL verification for toolkit
- Memory client `close` method
- Context clear
- `create_agency` parameter
- JSON format adaptation on Windows

## [0.1.0] - 2026-03-28

### Added
- Initial release
- Basic SDK structure
- Core functionality
