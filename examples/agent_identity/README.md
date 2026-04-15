# Basic SDK Usage Examples

This directory contains interactive Jupyter Notebook examples demonstrating how to use the `agent-identity-dev-sdk` in various scenarios.

## Examples

- `oauth2_example.ipynb`: A full OAuth2 flow implementation. Demonstrates how to handle token exchange, session management, and running a background callback server natively inside the notebook.
- `api_key_example.ipynb`: Demonstrates basic API Key usage in a notebook environment.
- `sts_token_example.ipynb`: Shows how to use STS (Security Token Service) tokens dynamically with Workload Identities.
- `client_manual_example.ipynb`: Manual usage of the `IdentityClient` for more control over identity operations.
- `context_usage_example.ipynb`: Demonstrates the usage and state isolation capabilities of `AgentIdentityContext`.
- `utility_tools.ipynb`: Utility and Cleanup Tools: Provides helper functions for cleaning up resources created during testing and demonstrates update operations for credential providers.

## How to Run

These examples are set up to run interactively as Jupyter Notebooks within the project's `uv` environment.

1. Ensure you have `uv` installed.
2. From the root of the repository, you can start Jupyter Lab or open the notebooks in VS Code:

```bash
uv run jupyter lab
```

Or, simply open the `.ipynb` files in an IDE that supports Jupyter Notebooks (like VS Code or PyCharm).

### OAuth2 Example Note

The `oauth2_example.ipynb` spins up a lightweight FastAPI server in a background thread on `http://localhost:8000` to handle callbacks without blocking the notebook's execution flow.
When running the example, it will provide an authorization URL. Click the URL, complete the dummy authorization, and your notebook execution will seamlessly resume.

You will need to provide your Huawei Cloud AK/SK environment variables at the top of the notebooks for authentication.
