# Roadmap

<!-- sources: README.md, charts/ponvara -->

Ponvara's status is claimed here and nowhere else. If a maturity claim appears in
another file in this repository, that file is wrong.

## Where it is now

Phase 1: the Dependency-Track to DefectDojo sync, ported off the Django ORM onto the
DefectDojo REST API and shipping as a Helm chart (an hourly CronJob plus an
ExternalSecret).

## Implemented

**Core sync engine:**
- Dependency-Track → DefectDojo via REST API (no Django ORM coupling)
- GitHub Advanced Security → DefectDojo (code scanning, Dependabot, secret scanning)
- Full test suite with mocked HTTP clients
- Configuration via environment variables (pydantic-settings)
- Helm chart with CronJob templates for both Dependency-Track and GitHub Advanced Security syncs

**Next phases (TODO):**
- Phase 2: ORM → REST API migration completion (tag-based dedup validation)
- Phase 3: Long-lived FastAPI + APScheduler service with `/metrics`, `/sync/{source}` endpoints
- Phase 4: SonarQube connector and generalized source plugin architecture

## Phased migration

Low-risk and reversible; each phase leaves the previous one running until it's green.
Full detail (risk + reversibility columns) in [`../DESIGN.md`](../DESIGN.md).

| Phase | Change | Status |
| --- | --- | --- |
| **0. Lift-and-shift** | New repo; move `sync.py` verbatim; add tests around the pure bits (target parsing, severity floor, issue body). Still the DefectDojo-image CronJob, still deployed from infra. | ✅ DONE |
| **1. Slim the image** | Provision a `ponvara` DefectDojo API token (OCI Vault); replace the ORM token-mint with it; switch to `python:3.12-slim`. Add GitHub Advanced Security sync. | ✅ DONE |
| **2. Drop the ORM** | Replace `Finding`/`GITHUB_Issue` ORM with the DefectDojo REST API (`/findings/` + tag-based dedupe). Now fully version-decoupled. | 🔄 IN PROGRESS |
| **3. Long-lived service** | Convert to the FastAPI + APScheduler Deployment; add `/metrics`, `/sync/{source}`, ServiceMonitor; Helm chart; Flux app dir. Retire the infra CronJobs/ConfigMaps. | 📋 TODO |
| **4. Generalize** | Fold SonarQube in as a connector; document how a new source plugs in. Point future non-native sources here; leave native-parser tools pushing straight to DefectDojo. | 📋 TODO |

You can stop after Phase 1 or 2 and already have a tested, reviewable, slim,
version-decoupled job — most of the value is there. Phases 3–4 deliver the long-lived
backend and the reuse.

## Open decisions

These are unresolved rather than forgotten. Each should become an ADR with
`Status: Proposed` once it has a shape, which makes staleness visible in a way a
list like this never does.

Tracked in [`../DESIGN.md § Open decisions`](../DESIGN.md#open-decisions):

1. **ORM → REST** — recommended **yes** (Phase 2). Validate that tag/note-based dedupe
   survives `reimport-scan` (reimport can recreate findings; confirm tags persist, or
   dedupe on a stable finding hash instead).
2. **Deployment vs CronJob-from-own-image** — "long-lived backend" points to
   **Deployment**; the chart supports both, so it's reversible.
3. **Dedup state** — stateless via DefectDojo tags (recommended) vs a tiny
   service-owned Postgres (only if cross-source correlation/SLA is tracked here later).
4. **Launch scope** — parity first (DT + SonarQube + GitHub push, Phases 0–3),
   generalize into the full finding bus in Phase 4.
