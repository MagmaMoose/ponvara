# Configuration

<!-- sources: src/ponvara/config.py, charts/ponvara/values.yaml -->

Ponvara reads configuration from environment variables. In Kubernetes, the chart sets them from its values, and the secrets come from an ExternalSecret that pulls from OCI Vault.

## Environment variables

| Variable | Type | Default | Required | Description |
| --- | --- | --- | --- | --- |
| `DTRACK_API_URL` | string | `http://dependency-track-api-server.security.svc.cluster.local:8080` | no | Dependency-Track API base URL. Defaults to in-cluster service. |
| `DTRACK_API_KEY` | string | (empty) | **yes** | Dependency-Track API key. Required for `ponvara sync`. |
| `DEFECTDOJO_URL` | string | `http://defectdojo-django.security.svc.cluster.local` | no | DefectDojo base URL. Defaults to in-cluster service. |
| `DEFECTDOJO_TOKEN` | string | (empty) | **yes** | DefectDojo API token. Required for `ponvara sync` and `ponvara sync-github`. Must be provisioned in advance (not minted at runtime). |
| `DD_PRODUCT_TYPE` | string | `Dependency-Track` | no | DefectDojo product type for Dependency-Track findings. |
| `DD_ENGAGEMENT` | string | `Dependency Track` | no | DefectDojo engagement name for Dependency-Track findings. |
| `DD_SITE_URL` | string | `https://defectdojo.magmamoose.com` | no | Not read by any command yet. |
| `GITHUB_API_URL` | string | `https://api.github.com` | no | GitHub API base URL. Use for self-hosted GitHub Enterprise. |
| `GITHUB_TOKEN` | string | (empty) | yes (if using `sync-github`) | GitHub personal access token. Required for `ponvara sync-github`. |
| `GITHUB_REPOS` | string | (empty) | no | Explicit comma-separated list of repositories (e.g., `owner/repo,owner/repo2`). Takes precedence over `GITHUB_ORG`. |
| `GITHUB_ORG` | string | (empty) | no | GitHub organization to enumerate all repositories from. Used only if `GITHUB_REPOS` is empty. At least one of these must be set for `ponvara sync-github`. |
| `DD_GITHUB_PRODUCT_TYPE` | string | `GitHub Advanced Security` | no | DefectDojo product type for GitHub findings. |
| `DD_GITHUB_ENGAGEMENT` | string | `GHAS` | no | DefectDojo engagement name for GitHub findings. |
| `HTTP_TIMEOUT` | float | `300.0` | no | HTTP request timeout in seconds. |
| `VERIFY_SSL` | boolean | `true` | no | Whether to verify SSL certificates. Set to `false` for self-signed certificates. |

## Loading precedence

Configuration is loaded from `.env` file first (if present), then environment variables override it. Case is insensitive; extra variables are ignored.

## Helm defaults

The Ponvara Helm chart sets defaults for the CronJob. See the [values.yaml](https://github.com/MagmaMoose/ponvara/blob/main/charts/ponvara/values.yaml) in the repository for the complete configuration, including:

- CronJob schedule (hourly for Dependency-Track, every 6 hours for GitHub)
- Requests of 50m CPU and 128Mi memory, and a 256Mi memory limit
- Security context (non-root, no privilege escalation, read-only filesystem)
- ExternalSecret references to OCI Vault

## Secrets handling

All secret values (`DTRACK_API_KEY`, `DEFECTDOJO_TOKEN`, `GITHUB_TOKEN`) are sourced from OCI Vault via ExternalSecrets Operator. The DefectDojo token **must be provisioned in advance** as a DefectDojo service user: Ponvara does not mint tokens.

## Example: Docker

```bash
docker run -e DTRACK_API_URL=https://dtrack.example.com \
  -e DTRACK_API_KEY=<your-key> \
  -e DEFECTDOJO_URL=https://defectdojo.example.com \
  -e DEFECTDOJO_TOKEN=<your-token> \
  ghcr.io/magmamoose/ponvara:latest
```

The image's default command is `sync`; pass `sync-github` to run the GitHub sync.

## Example: Kubernetes (via Helm)

The Helm chart configures ExternalSecrets to pull secrets from OCI Vault:

```bash
helm install ponvara charts/ponvara \
  --set image.tag=vX.Y.Z \
  --set defectDojo.url=https://defectdojo.example.com \
  --set dependencyTrack.url=https://dtrack.example.com
```

The chart's ExternalSecret reads `dependency-track-api-key` and `ponvara-dd-token` from OCI Vault, plus `ponvara-github-token` when `github.enabled` is true.
