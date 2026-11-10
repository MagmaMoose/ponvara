# Prerequisites

## Runtime

- **Python 3.11 or later** (for running from source; the container image uses Python 3.12-slim)
- **Kubernetes 1.21+** (for the Helm chart; its CronJobs use `batch/v1`)

## Services

- **Dependency-Track** — for `ponvara sync`
- **DefectDojo** — the sink for every command
- **GitHub** (cloud or self-hosted) — for `ponvara sync-github`

## Credentials and provisioning

Before running Ponvara, provision the required credentials:

### Dependency-Track

- A Dependency-Track API key with read access to all projects you want to sync.

### DefectDojo

- A **provisioned DefectDojo API v2 key** for a dedicated user. Create the user in DefectDojo and copy its API v2 key. Ponvara does not mint tokens.
- That user must be allowed to create products and engagements and to import scans: Ponvara calls `reimport-scan` with `auto_create_context`.

### GitHub (optional, only for `ponvara sync-github`)

- A GitHub personal access token (or fine-grained token) with read access to code scanning alerts, Dependabot alerts, and secret scanning alerts for the repositories you want to sync, and to list the organization's repositories if you use `GITHUB_ORG`.
- For GitHub Enterprise, you'll also need to set `GITHUB_API_URL` to your GHE instance.

## In Kubernetes

When deploying via Helm chart:

- **ExternalSecrets Operator** must be installed and configured with a ClusterSecretStore pointing to OCI Vault (or another secret store).
- Vault keys must be provisioned before the chart is deployed:
  - `dependency-track-api-key` — the Dependency-Track API key
  - `ponvara-dd-token` — the DefectDojo service-user API token
  - `ponvara-github-token` — the GitHub token (only required if `github.enabled=true`)

## Network

- Ponvara must reach Dependency-Track, DefectDojo, and (optionally) GitHub APIs.
- In-cluster defaults use Kubernetes service DNS; adjust if services are in different namespaces.
