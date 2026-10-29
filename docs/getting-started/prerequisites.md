# Prerequisites

## Runtime

- **Python 3.11 or later** (for running from source; the container image uses Python 3.12-slim)
- **Kubernetes 1.19+** (for Helm chart deployment)

## Services

- **Dependency-Track 4.8+** — for `ponvara sync`
- **DefectDojo 2.16+** — required for all sync operations
- **GitHub** (cloud or self-hosted) — for `ponvara sync-github`

## Credentials and provisioning

Before running Ponvara, provision the required credentials:

### Dependency-Track

- A Dependency-Track API key with read access to all projects you want to sync.

### DefectDojo

- A **provisioned DefectDojo API token** for a service user account. This must be created manually in DefectDojo (User Management → Add User → set as API user, then copy the token). Ponvara does not mint tokens.
- The service user must have permission to create products and findings.

### GitHub (optional, only for `ponvara sync-github`)

- A GitHub personal access token (or fine-grained token) with read access to code scanning alerts, Dependabot alerts, and secret scanning alerts for the repositories you want to sync.
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
