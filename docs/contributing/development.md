# Local development

Set up a development environment to run tests and build Ponvara from source.

## Prerequisites

- **Python 3.11 or later**
- **Git**
- **uv** (package and environment manager) — install from [astral.sh/uv](https://astral.sh/uv)

## Clone and install

```bash
git clone https://github.com/MagmaMoose/ponvara
cd ponvara
uv sync
```

This creates a virtual environment and installs all dependencies (both runtime and development).

## Run tests

```bash
uv run pytest
```

Tests mock all HTTP clients, so no external services are required. The test suite covers:

- Configuration loading
- Dependency-Track and DefectDojo client behavior
- GitHub Advanced Security client behavior
- End-to-end sync logic

## Linting and type checking

The project uses **Ruff** for linting and formatting:

```bash
uv run ruff check src tests          # lint
uv run ruff format src tests         # auto-format
```

All code must pass linting before PR.

## Building the Docker image

```bash
docker build -t ponvara:dev .
docker run \
  -e DTRACK_API_URL=https://dtrack.example.com \
  -e DTRACK_API_KEY=<key> \
  -e DEFECTDOJO_URL=https://defectdojo.example.com \
  -e DEFECTDOJO_TOKEN=<token> \
  ponvara:dev ponvara sync
```

The Dockerfile builds on `python:3.12-slim` (~80 MB) and installs dependencies with `uv`.

## Running against live services

To test against actual Dependency-Track and DefectDojo instances:

1. Ensure they're reachable from your machine.
2. Set the environment variables:

   ```bash
   export DTRACK_API_URL=https://dtrack.example.com
   export DTRACK_API_KEY=<your-key>
   export DEFECTDOJO_URL=https://defectdojo.example.com
   export DEFECTDOJO_TOKEN=<your-token>
   ```

3. Run the sync:

   ```bash
   uv run ponvara sync
   ```

   Or for GitHub:

   ```bash
   export GITHUB_TOKEN=<your-token>
   export GITHUB_ORG=my-org
   uv run ponvara sync-github
   ```

⚠️ This will create/update products and findings in your DefectDojo instance. Use a dev or staging instance for testing.

## Code structure

- `src/ponvara/__main__.py` — CLI entry point and argument parsing
- `src/ponvara/config.py` — environment variable loading (pydantic-settings)
- `src/ponvara/defectdojo.py` — DefectDojo REST API client
- `src/ponvara/dependencytrack.py` — Dependency-Track API client
- `src/ponvara/github.py` — GitHub API client
- `src/ponvara/sync.py` — core logic for Dependency-Track sync
- `src/ponvara/sync_github.py` — core logic for GitHub Advanced Security sync
- `tests/` — test suite with mocked HTTP responses

## Contributing

Follow the house conventions:

- **Branch naming:** `type/category/description` (e.g., `feat/sync/add-sonarqube-connector`)
- **Commit messages:** semantic-release format (`feat(sync): add SonarQube connector`)
- **Code style:** Ruff formatting (run `uv run ruff format` before committing)
- **Type hints:** Full type annotations on all functions
- **Tests:** Every feature must have a passing test

See [CONTRIBUTING.md](https://github.com/MagmaMoose/.github/blob/main/CONTRIBUTING.md) for the full contributing guide.
