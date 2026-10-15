# Repository Guidelines

## Project Structure & Module Organization
- `src/agentarts/sdk/` — core SDK: `runtime/` (HTTP server), `memory/`, `tools/`, `gateway/`, `identity/`, `integration/langgraph/`, `service/` (cloud HTTP clients), `utils/`.
- `src/agentarts/toolkit/` — Typer CLI (`cli/` declares options, `operations/` holds business logic), `utils/templates/`, `plugins/memory/` (installer, MCP server, platform assets).
- CLI layering is one-way and must be preserved: `cli/<group>/<cmd>.py` defines the Typer command and its options, `operations/<group>/<cmd>.py` implements it, and `cli/<group>/__init__.py` plus `toolkit/main.py` register it. `main.py` only wires commands together — never put logic there.
- `tests/unit/` mirrors the `src/` tree; `tests/integration/` covers cross-component flows; `tests/conftest.py` adds the project root to `sys.path`.
- `examples/` and `docs/cn/` hold sample projects and user guides; `docs/agents/` holds agent-facing docs (see [Agent skills](#agent-skills)). Dependencies flow one way: `toolkit → sdk`.

## Build, Test, and Development Commands
- Python floor is **3.10** (`requires-python = ">=3.10"`, CI matrix 3.10–3.13). Let `uv` own the interpreter: the system `python3` on macOS is 3.9 and cannot run this package.
- `uv sync --dev` — install runtime and dev dependencies. Add an optional extra with `uv sync --extra langgraph` (also `web`, `langchain`, `database`, `monitoring`, `huaweicloud`, …); `all` pulls every extra.
- **Always pass `--frozen` to `uv run`** — a bare `uv run` re-resolves and rewrites `uv.lock`.
- `uv run --frozen pytest tests/` — full suite. Narrow it: `uv run --frozen pytest tests/unit/toolkit/operations/runtime/test_deploy.py -k vpc`. Deselect slow work with `-m "not slow"`; `--strict-markers` is enabled, so an unregistered marker fails the run.
- `uv run --frozen ruff check .` — lint. **The repository is not ruff-clean**: expect roughly 250 pre-existing findings (most of them `PTH*` pathlib migration, `SIM115`, `I001`), split across `tests/`, `src/`, and `examples/`. Treat lint output as advisory and never rewrite unrelated findings inside a focused change.
- `uv run --frozen mypy src` — type check (the same invocation CI uses).
- `uv run --frozen black . && uv run --frozen isort .` — format (100 columns, isort `profile = "black"`).
- There is no `agentarts-check.sh`; run the four commands above in order.
- `uv run --frozen agentarts init -n my_agent -t langgraph` scaffolds a project; `agentarts dev` starts the local server (`POST /invocations`, `GET /ping`); `agentarts launch` deploys to Huawei Cloud (`deploy` is a hidden alias).

## Coding Style & Naming Conventions
- 4-space indent, 100-char lines (Black + isort `profile = "black"`); Ruff selects `E,F,I,N,W,UP,B` plus the broader set and the project-specific ignore list in `pyproject.toml` (§`[tool.ruff.lint]`).
- `snake_case` for functions and modules, `PascalCase` for classes, `UPPER_SNAKE` for constants, leading underscore for private helpers.
- Public functions require type hints (`disallow_untyped_defs`). Read config from environment/Pydantic settings; never hardcode credentials or endpoints.

## Testing Guidelines
- pytest with pytest-asyncio/pytest-cov; mark slow, integration, and e2e tests. Coverage is reported via `--cov=agentarts` with no enforced threshold — CI uploads it to Codecov and does not fail on it.
- Name files `test_<module>.py` and tests `test_<behavior>`. Cloud integration tests skip automatically without credentials.
- `tests/e2e/` is referenced by `CONTRIBUTING.md` but does not exist; the real tiers are `tests/unit/` and `tests/integration/`.
- What actually gates CI: `.github/workflows/test.yml` runs `uv run ruff check .` and `uv run mypy src` with `continue-on-error: true`, and gates only on `pytest` plus a wheel build/import smoke test. `.github/workflows/integration-readonly.yml` runs the read-only integration tier and stays green without secrets.

## Commit & Pull Request Guidelines
- Conventional Commits: `<type>(<scope>): <subject>` — lowercase, imperative, ≤50 chars. Types: `feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert`; scopes: `runtime|memory|identity|gateway|tools|service|integration|cli|docs|test` (e.g. `fix(memory): resolve vector store connection timeout`). Full rules live in [CONTRIBUTING.md](CONTRIBUTING.md).
- Branch from `main` as `feature/<description>` or `fix/<description>`.
- PRs need a description, test evidence, linked issues, and one maintainer approval; merges are squash-only.

## Agent skills

### Issue tracker

Issues live as GitHub issues on `huaweicloud/agentarts-sdk-python`, driven with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical triage roles use their default label strings (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

single-context — one root `CONTEXT.md` plus `docs/adr/`, both created lazily. See `docs/agents/domain.md`.
