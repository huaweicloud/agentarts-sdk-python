# Contributing to Huawei Cloud AgentArts SDK

Thank you for your interest in contributing to the Huawei Cloud AgentArts SDK!

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Git Commit Guidelines](#git-commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Branch Naming Convention](#branch-naming-convention)

---

## Code of Conduct

Please be respectful and constructive in all interactions. We are committed to providing a welcoming and inspiring community for all.

---

## Development Setup

1. Fork and clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Install development dependencies: `pip install -e ".[dev]"`

---

## Code Style

We follow strict code quality standards to maintain consistency across the codebase.

### Tools

| Tool | Purpose |
|------|---------|
| [Black](https://github.com/psf/black) | Code formatting |
| [isort](https://github.com/PyCQA/isort) | Import sorting |
| [mypy](https://github.com/python/mypy) | Static type checking |
| [Ruff](https://github.com/astral-sh/ruff) | Fast Python linter |

### Run All Checks

```bash
# Format code
black .
isort .

# Type checking
mypy agentarts

# Linting
ruff check .

# Or run all at once
black . && isort . && mypy agentarts && ruff check .
```

### Pre-commit Hooks

We recommend setting up pre-commit hooks to automatically run checks before each commit:

```bash
pip install pre-commit
pre-commit install
```

---

## Testing

- Write tests for all new functionality
- Maintain or improve code coverage
- Follow the existing test structure

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agentarts --cov-report=html

# Run specific test file
pytest tests/unit/test_core.py

# Run specific test
pytest tests/unit/test_core.py::test_import
```

### Test Categories

| Directory | Purpose |
|-----------|---------|
| `tests/unit/` | Unit tests for individual components |
| `tests/integration/` | Integration tests between components |
| `tests/e2e/` | End-to-end tests for complete workflows |

---

## Git Commit Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages.

### Commit Message Format

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only changes |
| `style` | Changes that do not affect the meaning of the code (white-space, formatting, etc.) |
| `refactor` | A code change that neither fixes a bug nor adds a feature |
| `perf` | A code change that improves performance |
| `test` | Adding missing tests or correcting existing tests |
| `build` | Changes that affect the build system or external dependencies |
| `ci` | Changes to CI configuration files and scripts |
| `chore` | Other changes that don't modify src or test files |
| `revert` | Reverts a previous commit |

### Scopes

| Scope | Description |
|-------|-------------|
| `runtime` | Agent runtime module |
| `memory` | Memory module |
| `identity` | Identity management |
| `mcp` | MCP gateway |
| `tools` | Built-in tools |
| `service` | Service wrapper |
| `integration` | Framework adapters |
| `cli` | CLI toolkit |
| `docs` | Documentation |
| `test` | Testing infrastructure |

### Examples

```bash
# Feature
feat(runtime): add async context support

# Bug fix
fix(memory): resolve vector store connection timeout

# Documentation
docs(readme): update installation instructions

# Refactoring
refactor(tools): simplify code interpreter sandbox

# Performance
perf(memory): optimize vector search algorithm

# Breaking change
feat(runtime)!: change AgentRuntime API signature

BREAKING CHANGE: The `execute` method now requires an explicit `context` parameter.
```

### Commit Message Rules

1. **Subject line** must be lowercase and not end with a period
2. **Subject line** should be 50 characters or less
3. **Body** should be wrapped at 72 characters
4. Use **imperative mood** in the subject line (e.g., "add" not "added")
5. Reference **issues and pull requests** liberally in the footer

---

## Pull Request Process

### Before Submitting

1. **Create a feature branch** from `main`
2. **Make your changes** following code style guidelines
3. **Add tests** for new functionality
4. **Update documentation** if needed
5. **Run all checks** locally:
   ```bash
   black . && isort . && mypy agentarts && ruff check . && pytest
   ```

### PR Title Format

PR titles should follow the same format as commit messages:

```
<type>(<scope>): <description>
```

Examples:
- `feat(runtime): add async context support`
- `fix(memory): resolve vector store connection timeout`
- `docs: update API reference`

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran

## Checklist:
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
```

### Review Process

1. At least **one approval** from a maintainer is required
2. All **CI checks must pass**
3. No **merge conflicts**
4. **Squash and merge** will be used to merge PRs

---

## Branch Naming Convention

Use descriptive branch names following these patterns:

| Pattern | Example | Description |
|---------|---------|-------------|
| `feature/<description>` | `feature/async-runtime` | New features |
| `fix/<description>` | `fix/memory-leak` | Bug fixes |
| `refactor/<description>` | `refactor/tools-sandbox` | Code refactoring |
| `docs/<description>` | `docs/api-reference` | Documentation |
| `test/<description>` | `test/runtime-coverage` | Adding tests |
| `chore/<description>` | `chore/update-dependencies` | Maintenance tasks |

### Rules

- Use **lowercase** letters
- Use **hyphens** to separate words
- Keep names **short and descriptive**
- Include **issue number** if applicable: `feature/async-runtime-#123`

---

## Questions?

If you have questions, feel free to:
- Open a [Discussion](https://github.com/huaweicloud/agentarts-sdk-python/discussions)
- Ask in your pull request
- Email: agentarts@huawei.com

Thank you for contributing! 🎉
