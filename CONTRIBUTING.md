# Contributing to Echo Substrate v4

First off, thank you for considering contributing. It's people like you that make open source such a great community.

## Where to Start

- **Bug Reports:** If you find a bug, please open an issue and provide detailed steps to reproduce it.
- **Feature Requests:** Open an issue to discuss new features. We are particularly interested in new agent types and organ integrations.
- **Pull Requests:** For small fixes, feel free to open a PR directly. For larger changes, please open an issue first to discuss the approach.

## Development Setup

1.  **Fork & Clone:** Fork the repository and clone it locally.
2.  **Environment:** This project uses Python 3.11+ and `pyproject.toml` for dependencies. We recommend using a virtual environment.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -e .[dev]
    ```
3.  **Database:** The system requires a PostgreSQL database. You can use the provided `docker-compose.yml` for an easy setup:
    ```bash
    docker-compose up -d db
    ```
4.  **Configuration:** Copy `.env.example` to `.env` and update the `DATABASE_URL`.

## Running Tests

Before submitting a pull request, please ensure all tests pass:

```bash
source venv/bin/activate
pytest
```

## Code Style

We use `ruff` for linting and formatting. Please run it before committing:

```bash
ruff check . --fix
ruff format .
```

## Submitting a Pull Request

1.  Create a new branch for your feature or fix.
2.  Add a clear description of your changes.
3.  Ensure all tests pass and the code is linted.
4.  Link the PR to any relevant issues.

Thank you for your contribution!
