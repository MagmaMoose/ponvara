# SecurityBridge

> **Status: Phase 1 — REST Dependency-Track → DefectDojo sync.** The core sync is
> ported off the Django ORM onto the DefectDojo **REST API** (httpx) and runs on a
> slim `python:3.12-slim` image: for each Dependency-Track project it exports the
> findings (FPF) and `reimport-scan`s them into DefectDojo. Ships as a Helm chart
> (an hourly CronJob + ExternalSecret). The zero-touch **GitHub-issue push** (the
> other Django-ORM user) is the next phase; the long-lived FastAPI service is later.
> See [Running](#running-phase-1) and [`docs/DESIGN.md`](docs/DESIGN.md).

SecurityBridge is a **finding bus**: a long-lived backend that pulls security
findings from sources that can't push to [DefectDojo](https://github.com/DefectDojo/django-DefectDojo)
themselves, **reimports** them into DefectDojo, and does the one cross-cutting thing
DefectDojo can't do generically — **zero-touch GitHub-issue auto-push** for
High/Critical findings, resolving the target repo by name across multiple GitHub
accounts.

It promotes an existing, working-but-fragile in-cluster CronJob
(`dt-defectdojo-sync`) into its own tested, versioned, slim service — and generalizes
it so a new source is a new connector module.

## Running (Phase 1)

Cluster (Helm — an hourly CronJob + ExternalSecret; DT key + a **provisioned**
DefectDojo API token come from OCI Vault via External Secrets Operator):

```sh
helm template securitybridge charts/securitybridge      # render/inspect
```

Container / locally (needs `DTRACK_API_KEY` + a provisioned `DEFECTDOJO_TOKEN`):

```sh
docker build -t ghcr.io/magmamoose/securitybridge:0.1.0 .
docker run --rm \
  -e DTRACK_API_URL -e DTRACK_API_KEY \
  -e DEFECTDOJO_URL -e DEFECTDOJO_TOKEN \
  ghcr.io/magmamoose/securitybridge:0.1.0 sync
```

`securitybridge sync` reimports every active Dependency-Track project into DefectDojo
once, then exits (the CronJob schedules it). Per-project failures are logged and
skipped; only an unreachable Dependency-Track or a missing token is fatal.

> **Phase 1 needs one new secret:** a **provisioned DefectDojo API token** (a service
> user), stored in the OCI Vault key `securitybridge-dd-token`. This replaces the old
> ORM token-minting — the whole reason the image can now be slim + version-decoupled.

## What & why

Today a ~180-line `sync.py` lives **embedded in a Kubernetes ConfigMap** and runs
hourly as a CronJob **inside the 1 GB `defectdojo/defectdojo-django` image**, using
the DefectDojo **Django ORM**. It works, but it has no tests, no CI, no linting, and —
worst of all — it is **pinned in lockstep to DefectDojo's version**: every DefectDojo
chart upgrade forces a matching image bump so the ORM keeps matching the live DB
schema. A security-critical integration deserves the same rigor as
[MagmaMoose/chargate](https://github.com/MagmaMoose/chargate).

SecurityBridge fixes that:

- **A real repo** — Python 3.11+, uv + Ruff + pytest, full type hints, unit-tested
  pure connectors, CI, and semantic-release versioning (mirrors chargate's conventions).
- **A slim, version-decoupled service** — see the key refactor below.
- **A finding bus, not a one-off** — DT and SonarQube today; a new source is a new
  connector. Sources with native DefectDojo parsers (Trivy Operator, Prowler, ZAP,
  Nuclei) keep pushing straight to DefectDojo; the bus only earns its keep for
  movement DefectDojo can't do itself.

## Architecture

```
 Dependency-Track ─┐
 SonarQube ────────┤                         ┌─→ DefectDojo (reimport-scan, dedupe, SLA)
 DAST (ZAP/Nuclei)─┤──▶  SecurityBridge  ────┤
 <future source> ──┘     (connectors +       └─→ GitHub Issues (zero-touch, High/Crit)
                          scheduler + API)
```

- **Sources** (Dependency-Track, SonarQube, …) are read-only connectors that pull
  findings.
- **Sinks** are DefectDojo (via `reimport-scan`) and GitHub Issues (zero-touch push).
- A single long-lived **Deployment** runs an in-process **APScheduler** (replacing the
  CronJobs) plus a small **FastAPI** surface: `/healthz`, `/readyz`, `/metrics`, and
  `POST /sync/{source}` for on-demand runs (and a future "DT analysis finished →
  sync now" webhook).

## The key refactor: drop the Django ORM, use the DefectDojo REST API

The single decision that unlocks everything. The legacy job reaches into DefectDojo's
**private Django data model** for exactly two things; both become REST calls:

| Django ORM usage today | REST replacement |
| --- | --- |
| Mint a superuser API token via `Token.objects.get_or_create` | Provision **one** DefectDojo API token for a dedicated `securitybridge` service user, once, stored in OCI Vault. No ORM, no password. |
| `Finding.objects.filter(...)` + `GITHUB_Issue.objects.create(...)` for dedupe | `GET /api/v2/findings/` (filter by product/severity/active); dedupe by writing a **finding tag** `gh-issue:<url>` via `PATCH /api/v2/findings/{id}/`. State lives **in DefectDojo**, so the service stays stateless. |

**Result:** SecurityBridge runs on a **slim `python:3.12-slim` image (~80 MB)** and is
**fully decoupled from DefectDojo's version** — DefectDojo chart upgrades no longer
force a lockstep bump. This removes the biggest fragility of the current setup.

## Phased migration

Low-risk and reversible; each phase leaves the previous one running until it's green.
Full detail (risk + reversibility columns) in [`docs/DESIGN.md`](docs/DESIGN.md).

| Phase | Change |
| --- | --- |
| **0. Lift-and-shift** | New repo; move `sync.py` verbatim; add tests around the pure bits (target parsing, severity floor, issue body). Still the DefectDojo-image CronJob, still deployed from infra. |
| **1. Slim the image** | Provision a `securitybridge` DefectDojo API token (OCI Vault); replace the ORM token-mint with it; switch to `python:3.12-slim`. |
| **2. Drop the ORM** | Replace `Finding`/`GITHUB_Issue` ORM with the DefectDojo REST API (`/findings/` + tag-based dedupe). Now fully version-decoupled. |
| **3. Long-lived service** | Convert to the FastAPI + APScheduler Deployment; add `/metrics`, `/sync/{source}`, ServiceMonitor; Helm chart; Flux app dir. Retire the infra CronJobs/ConfigMaps. |
| **4. Generalize** | Fold SonarQube in as a connector; document how a new source plugs in. Point future non-native sources here; leave native-parser tools pushing straight to DefectDojo. |

You can stop after Phase 1 or 2 and already have a tested, reviewable, slim,
version-decoupled job — most of the value is there. Phases 3–4 deliver the long-lived
backend and the reuse.

## Not yet implemented

SecurityBridge has **no working code yet**. This repo currently contains only the
design doc, project scaffolding (`pyproject.toml`, an empty `0.0.0` package), and a
stub Helm chart. Follow the [phased migration](#phased-migration) above — the first PR
is Phase 0 (lift-and-shift `sync.py` with tests, zero production risk). The existing
in-cluster CronJob keeps running untouched until SecurityBridge is cut over.

## How it fits the security program

SecurityBridge is the **runtime / continuous** half of the security tooling estate; it
complements the others rather than overlapping them:

- **[MagmaMoose/chargate](https://github.com/MagmaMoose/chargate)** — the **PR-time**
  SAST/SCA/IaC gate (a MegaLinter wrapper with net-new gating). Chargate acts *before
  merge* on a single PR; SecurityBridge acts *continuously* on deployed/portfolio-wide
  findings. Chargate already ships full SARIF to DefectDojo and BOMs to
  Dependency-Track; SecurityBridge moves what those tools produce onward.
- **[MagmaMoose/dastgate](https://github.com/MagmaMoose/dastgate)** — scheduled DAST
  (ZAP + Nuclei) → DefectDojo. ZAP/Nuclei have native DefectDojo parsers, so dastgate
  pushes straight to DefectDojo; if a bespoke DAST result shape ever needs
  orchestration/enrichment, it becomes a SecurityBridge connector.
- **[MagmaMoose/security-platform](https://github.com/MagmaMoose/security-platform)** —
  the program index and security-tooling roadmap that ties chargate, dastgate,
  SecurityBridge, DefectDojo, and Dependency-Track together.
- **DefectDojo** (self-hosted, private infra repo) — the aggregation/dedupe/SLA system
  of record. SecurityBridge is its **feeder** for sources that can't push themselves.
- **Dependency-Track** (self-hosted, private infra repo) — the SBOM/SCA source.
  Dependency-Track has no "push to DefectDojo"; SecurityBridge pulls its FPF export and
  reimports it. This is the original job the bus was born from.

## Conventions

Mirrors [MagmaMoose/chargate](https://github.com/MagmaMoose/chargate):

- Python **≥ 3.11**, **uv + Ruff + pytest**, full type hints; tests mirror modules 1:1
  under `tests/`.
- External GitHub Actions are **SHA-pinned** with a `# vX.Y.Z` comment.
- Releases are automated (Conventional Commits → semantic-release); never bump the
  version by hand.
- Deployed to a **k3s** cluster via **FluxCD**, with **External Secrets Operator**
  (OCI Vault) for secrets and a **cloudflared** tunnel for any external exposure.

## Open decisions

Tracked in [`docs/DESIGN.md § Open decisions`](docs/DESIGN.md#open-decisions):

1. **ORM → REST** — recommended **yes** (Phase 2). Validate that tag/note-based dedupe
   survives `reimport-scan` (reimport can recreate findings; confirm tags persist, or
   dedupe on a stable finding hash instead).
2. **Deployment vs CronJob-from-own-image** — "long-lived backend" points to
   **Deployment**; the chart supports both, so it's reversible.
3. **Dedup state** — stateless via DefectDojo tags (recommended) vs a tiny
   service-owned Postgres (only if cross-source correlation/SLA is tracked here later).
4. **Launch scope** — parity first (DT + SonarQube + GitHub push, Phases 0–3),
   generalize into the full finding bus in Phase 4.

## License

MIT © 2026 Caleb Sargeant. See [LICENSE](LICENSE).
