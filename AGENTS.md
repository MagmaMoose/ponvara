CLAUDE.md is canonical. Keep both files edited together when rules change.

ponvara is a security finding bus: Dependency-Track and GitHub Advanced Security → DefectDojo over the REST API (no Django ORM), running as Kubernetes CronJobs. Breaking it silently drops vulnerability findings from the security programme.

## Commands

```
uv run pytest                        # test suite
uv run ruff check .                  # lint
uv run ruff format --check .         # format check (CI uses this)
uv run ruff format .                 # format
uv run --group docs mkdocs serve     # docs dev server
uv run --group docs mkdocs build     # docs build (strict)
ponvara sync                         # Dependency-Track → DefectDojo
ponvara sync-github                  # GHAS → DefectDojo
```

## Architecture

Two independent sync paths, no shared state between them:

- `sync.py`: DependencyTrackClient → FPF export → DefectDojoClient reimport
- `sync_github.py`: GitHubClient (SARIF, Dependabot, secret-scanning) → transform → DefectDojoClient reimport
- `config.py`: single pydantic-settings Config; all env vars live here
- `defectdojo.py` / `dependencytrack.py` / `github.py`: thin httpx clients, no business logic

Connectors read; sinks write; they never import each other. `src/ponvara/__main__.py` is the only CLI entry point.

Before locating unfamiliar code, read PROJECT_INDEX.json first.

[tooling]
- Prefer targeted line-range reads over whole files; use PROJECT_INDEX.json to find the location.
- grep/find/glob: return matching paths and matched lines only, never whole-file dumps.
- After a successful write or edit, trust it. Don't re-read the file to "verify" it.

[maintenance]
- Bug that took more than an hour: append it to .claude/COMMON_MISTAKES.md.
- Architectural decision: write it to .claude/decisions/.
- Public behaviour, API, config or setup changed: sync ./docs.
- PROJECT_INDEX.json stale after a new module or a big refactor: regenerate the affected modules section only, and update "generated" in that same edit. Never change "generated" on its own.
