# CLI reference

<!-- sources: src/ponvara/__main__.py -->

Ponvara runs as one-shot commands scheduled by a CronJob. Each command reads configuration from environment variables, syncs findings once, and exits.

## Commands

### ponvara sync

Syncs Dependency-Track projects into DefectDojo via the REST API.

```bash
ponvara sync
```

Requires `DTRACK_API_KEY` and `DEFECTDOJO_TOKEN`. Reads every project from Dependency-Track, exports its findings as FPF, and reimports them into DefectDojo under a product named after the project.

Exit codes:
- `0` — success or skipped projects (partial failures are logged, not fatal)
- `1` — setup/fatal error (missing token, network unreachable)

### ponvara sync-github

Syncs GitHub Advanced Security findings into DefectDojo.

```bash
ponvara sync-github
```

Requires `GITHUB_TOKEN` and `DEFECTDOJO_TOKEN`. Must also set either `GITHUB_REPOS` (explicit list) or `GITHUB_ORG` (enumerate all repositories). Reads code scanning (SARIF), Dependabot, and secret scanning from each repository and reimports into DefectDojo.

Exit codes:
- `0` — success or skipped repositories
- `1` — setup/fatal error (missing token, no repos configured)

### Global options

```bash
ponvara --version
```

Prints the version and exits.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success (all or partial runs; per-source failures are logged) |
| `1` | Setup or fatal network error (missing token, source unreachable) |

## Logging

Both commands log to stderr with the prefix `ponvara: ` at `INFO` level by default. Run via `docker run` or `kubectl logs` to capture output.
