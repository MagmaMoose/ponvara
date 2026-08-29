# Ponvara

<!-- sources: src/ponvara, charts/ponvara -->

A **finding bus**: a long-lived backend that pulls security findings from sources that
cannot push to [DefectDojo](https://github.com/DefectDojo/django-DefectDojo) themselves,
reimports them, and does the one cross-cutting thing DefectDojo cannot do generically —
zero-touch GitHub-issue push for High and Critical findings, resolving the target repo by
name across multiple GitHub accounts.

It promotes an existing, working-but-fragile in-cluster CronJob (`dt-defectdojo-sync`)
into a tested, versioned service, and generalises it so a new source is a new connector
module rather than a new CronJob.

## Architecture

```
 Dependency-Track ─┐
 GitHub Adv. Sec. ─┤                         ┌─→ DefectDojo (reimport-scan, dedupe, SLA)
 SonarQube ────────┤──▶  Ponvara  ────┤
 DAST (ZAP/Nuclei)─┤     (connectors +       └─→ GitHub Issues (zero-touch, High/Crit)
 <future source> ──┘      scheduler + API)
```

- **Sources** (Dependency-Track, SonarQube, …) are read-only connectors that pull
  findings.
- **Sinks** are DefectDojo (via `reimport-scan`) and GitHub Issues (zero-touch push).
- A single long-lived **Deployment** runs an in-process **APScheduler** (replacing the
  CronJobs) plus a small **FastAPI** surface: `/healthz`, `/readyz`, `/metrics`, and
  `POST /sync/{source}` for on-demand runs (and a future "DT analysis finished →
  sync now" webhook).

## Why the REST API, not the Django ORM

The single decision that unlocks everything. The legacy job reaches into DefectDojo's
**private Django data model** for exactly two things; both become REST calls:

| Django ORM usage today | REST replacement |
| --- | --- |
| Mint a superuser API token via `Token.objects.get_or_create` | Provision **one** DefectDojo API token for a dedicated `ponvara` service user, once, stored in OCI Vault. No ORM, no password. |
| `Finding.objects.filter(...)` + `GITHUB_Issue.objects.create(...)` for dedupe | `GET /api/v2/findings/` (filter by product/severity/active); dedupe by writing a **finding tag** `gh-issue:<url>` via `PATCH /api/v2/findings/{id}/`. State lives **in DefectDojo**, so the service stays stateless. |

**Result:** Ponvara runs on a **slim `python:3.12-slim` image (~80 MB)** and is
**fully decoupled from DefectDojo's version** — DefectDojo chart upgrades no longer
force a lockstep bump. This removes the biggest fragility of the current setup.

## How it fits the security programme

Ponvara is the **runtime / continuous** half of the security tooling estate; it
complements the others rather than overlapping them:

- **[MagmaMoose/chargate](https://github.com/MagmaMoose/chargate)** — the **PR-time**
  SAST/SCA/IaC gate (a MegaLinter wrapper with net-new gating). Chargate acts *before
  merge* on a single PR; Ponvara acts *continuously* on deployed/portfolio-wide
  findings. Chargate already ships full SARIF to DefectDojo and BOMs to
  Dependency-Track; Ponvara moves what those tools produce onward.
- **[MagmaMoose/draventis](https://github.com/MagmaMoose/draventis)** — scheduled DAST
  (ZAP + Nuclei) → DefectDojo. ZAP/Nuclei have native DefectDojo parsers, so draventis
  pushes straight to DefectDojo; if a bespoke DAST result shape ever needs
  orchestration/enrichment, it becomes a Ponvara connector.
- **[MagmaMoose/security-platform](https://github.com/MagmaMoose/security-platform)** —
  the program index and security-tooling roadmap that ties chargate, draventis,
  Ponvara, DefectDojo, and Dependency-Track together.
- **DefectDojo** (self-hosted, private infra repo) — the aggregation/dedupe/SLA system
  of record. Ponvara is its **feeder** for sources that can't push themselves.
- **Dependency-Track** (self-hosted, private infra repo) — the SBOM/SCA source.
  Dependency-Track has no "push to DefectDojo"; Ponvara pulls its FPF export and
  reimports it. This is the original job the bus was born from.

## Next

- [Design](DESIGN.md) — the full design document
- [Roadmap](explanation/roadmap.md) — what is built, what is next, what is undecided
