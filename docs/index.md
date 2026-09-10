# Ponvara

<!-- sources: src/ponvara, charts/ponvara -->

A **finding bus**: pulls security findings from sources that cannot push to
[DefectDojo](https://github.com/DefectDojo/django-DefectDojo) themselves and reimports
them. Runs as a CronJob; will be generalized to a long-lived scheduler with zero-touch
GitHub-issue push for High and Critical findings (future).

It promotes an existing, working-but-fragile in-cluster CronJob (`dt-defectdojo-sync`)
into a tested, versioned service, and generalises it so a new source is a new connector
module rather than a new CronJob.

## Architecture

```text
 Dependency-Track ─┐
 GitHub Adv. Sec. ─┤                    ┌─→ DefectDojo (reimport-scan, dedupe, SLA)
 SonarQube ────────┤──▶  Ponvara ───────┤
 DAST (ZAP/Nuclei)─┤     (connectors)   └─→ GitHub Issues (zero-touch, High/Crit — future)
 <future source> ──┘
```

- **Sources:** Dependency-Track, GitHub Advanced Security, and future connectors pull findings.
- **Sink:** DefectDojo (via `reimport-scan`). GitHub Issues push is Phase 2 work.
- **Current phase:** CLI with `ponvara sync` and `ponvara sync-github` commands (CronJob-based).
  Each command runs once and exits, scheduled via Kubernetes CronJob and Helm chart.
- **Future phases:** long-lived Deployment with APScheduler, on-demand endpoints, GitHub-issue push.

## Why the REST API, not the Django ORM

The legacy job reaches into DefectDojo's **private Django data model** for two things.
The first has been replaced; the second is future work:

| Django ORM usage | REST replacement | Status |
| --- | --- | --- |
| Mint a superuser API token via `Token.objects.get_or_create` | Provision **one** DefectDojo API token for a dedicated `ponvara` service user, once, stored in OCI Vault. No ORM, no password. | ✅ Done (Phase 1) |
| `Finding.objects.filter(...)` + `GITHUB_Issue.objects.create(...)` for GitHub-issue dedupe | `GET /api/v2/findings/` (filter by product/severity/active); dedupe by writing a **finding tag** `gh-issue:<url>` via `PATCH /api/v2/findings/{id}/`. State lives in DefectDojo, service stays stateless. | 📋 Phase 2 (GitHub-issue push feature) |

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
