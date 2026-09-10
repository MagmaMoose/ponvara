# Roadmap

<!-- sources: README.md, charts/ponvara -->

Ponvara's status is claimed here and nowhere else. If a maturity claim appears in
another file in this repository, that file is wrong.

## Where it is now

Phase 1: Dependency-Track and GitHub Advanced Security syncs to DefectDojo, ported off
the Django ORM onto the DefectDojo REST API. Shipping as a Helm chart with two CronJobs
(Dependency-Track sync and GitHub Advanced Security sync) plus ExternalSecrets.

## Implemented

**Core sync engine:**

- Dependency-Track → DefectDojo via REST API (no Django ORM coupling)
- GitHub Advanced Security → DefectDojo (code scanning, Dependabot, secret scanning)
- Full test suite with mocked HTTP clients
- Configuration via environment variables (pydantic-settings)
- Helm chart with CronJob templates for both Dependency-Track and GitHub Advanced Security syncs

**Next phases (TODO):**

- Phase 2: Zero-touch GitHub-issue push for High/Critical findings (tag-based dedup in DefectDojo)
- Phase 3: Long-lived FastAPI + APScheduler service with `/metrics`, `/sync/{source}` endpoints
- Phase 4: SonarQube connector and generalized source plugin architecture

## Phased migration

Low-risk and reversible; each phase leaves the previous one running until it's green.
Full detail (risk + reversibility columns) in [`../DESIGN.md`](../DESIGN.md).

| Phase | Change | Status |
| --- | --- | --- |
| **0. Lift-and-shift** | New repo; move `sync.py` verbatim; add tests around the pure bits (target parsing, severity floor, issue body). Still the DefectDojo-image CronJob, still deployed from infra. | ✅ DONE |
| **1. Slim the image + GHAS** | Provision a `ponvara` DefectDojo API token (OCI Vault); replace the ORM token-mint with it; switch to `python:3.12-slim`. Add GitHub Advanced Security sync (code scanning, Dependabot, secret scanning). | ✅ DONE |
| **2. GitHub-issue push** | Implement zero-touch GitHub-issue push for High/Critical findings. Requires DefectDojo findings query and tag-based state tracking. Now fully version-decoupled. | 📋 TODO |
| **3. Long-lived service** | Convert to the FastAPI + APScheduler Deployment; add `/metrics`, `/sync/{source}`, ServiceMonitor; Helm chart; Flux app dir. Retire the infra CronJobs/ConfigMaps. | 📋 TODO |
| **4. Generalize** | Fold SonarQube in as a connector; document how a new source plugs in. Point future non-native sources here; leave native-parser tools pushing straight to DefectDojo. | 📋 TODO |

You can stop after Phase 1 or 2 and already have a tested, reviewable, slim,
version-decoupled job — most of the value is there. Phases 3–4 deliver the long-lived
backend and the reuse.

## Open decisions

Unresolved questions for future phases. Each should become an ADR with
`Status: Proposed` once it has a shape.

Tracked in [`../DESIGN.md § Open decisions`](../DESIGN.md#open-decisions):

1. **Tag-based dedup for GitHub push** (Phase 2). Recommended: validate that
   `reimport-scan` preserves finding tags so GitHub-issue dedup can use them; fall back to
   finding hash if reimport recreates findings.
2. **Deployment vs CronJob-from-own-image** (Phase 3) — "long-lived backend" points to
   **Deployment**; the chart supports both.
3. **Dedup state** (Phase 2) — stateless via DefectDojo tags (recommended) vs a tiny
   service-owned Postgres (only if cross-source correlation/SLA is tracked here).
4. **Scope beyond Phase 1** — confirmed: Phase 2 adds GitHub-issue push; Phase 3 adds
   long-lived service; Phase 4 adds SonarQube connector and generalization.
