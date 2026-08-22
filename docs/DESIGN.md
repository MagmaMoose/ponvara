# Ponvara — Design

**Status:** Planning (Phase 0) · **Date:** 2026-07-22

Promote the in-cluster `dt-defectdojo-sync` CronJob (and its SonarQube sibling) into
its own repo, container, and Helm chart — a long-lived, tested, versioned backend
deployed separately via Flux — and generalize it into a **finding bus**. Scope is
deliberately bounded: this does **not** widen [chargate](https://github.com/MagmaMoose/chargate)'s
PR-time gate; Ponvara is the continuous/runtime counterpart.

---

## 1. What exists today

In the private infra repo (`kubernetes/apps/security-integrations/`):

| Resource | What it does |
| --- | --- |
| `configmap-sync-script.yaml` | ~180-line `sync.py` **embedded in YAML** |
| `cronjob-dt-sync.yaml` | Hourly CronJob; runs `sync.py` inside `defectdojo/defectdojo-django:2.58.4` |
| `cronjob-sonarqube-sync.yaml` | Sibling, +30m offset, own embedded script |
| `configmap-sonarqube-sync.yaml` | The SonarQube script |
| `externalsecret-sync.yaml` | `DTRACK_API_KEY`, `SONARQUBE_TOKEN` from OCI Vault |
| `externalsecret-github-targets.yaml` | `GITHUB_TARGETS` JSON (server + owners + PAT) from OCI Vault |

**`sync.py` does two jobs per Dependency-Track project:**

1. Export findings as **FPF** → DefectDojo **`reimport-scan`** (`auto_create_context`,
   `close_old_findings`, dedupe). One DefectDojo product per Dependency-Track project.
2. **Zero-touch GitHub issue auto-push**: resolve a repo by matching the
   Dependency-Track project name to `<owner>/<name>` across configured GitHub accounts
   (github.com first, then GHE), open issues for new **High/Critical** Active findings,
   and record a `GITHUB_Issue` so re-runs dedupe.

**The critical coupling:** it runs *inside the DefectDojo Django image* and uses the
**Django ORM** for exactly two things — (a) minting a superuser API token without a
password (`Token.objects.get_or_create`), and (b) the GitHub-issue dedupe/query
(`Finding.objects.filter(...)`, `GITHUB_Issue.objects.create(...)`).

---

## 2. Why promote it (the problems)

- **Code-in-YAML.** No tests, no linting, no type-checking, no CI, painful review and
  diffs. A security-critical integration deserves the same rigor as chargate.
- **Image coupling + version lockstep.** Pinned to `defectdojo-django:2.58.4` so the
  ORM matches the live DB schema — **every DefectDojo chart upgrade forces a lockstep
  bump**, and the image is ~1 GB. This is the single biggest fragility.
- **ORM coupling to DefectDojo internals.** Importing `dojo.models` /
  `dojo.github.models` ties the job to DefectDojo's private data model across versions.
- **Mixed concerns, no reuse.** DT sync, SonarQube sync, and GitHub push are three
  copies/variants with no shared library, no versioning, no release artifact.
- **Batch-only.** CronJobs can't be triggered on demand, expose no health/metrics, and
  there's nowhere to add a webhook (e.g. "DT analysis finished → sync now").

The goal is a **long-lived backend, in a repo, with a Helm chart, deployed separately.**
That's the right call — and it unlocks a bigger idea below.

---

## 3. The bigger framing: a *finding bus*, not just a DT sync

Once it's a real service, generalize it slightly. It becomes the **orchestration +
enrichment layer** that sits beside DefectDojo:

```
 Dependency-Track ─┐
 SonarQube ────────┤                         ┌─→ DefectDojo (reimport-scan, dedupe, SLA)
 DAST (ZAP/Nuclei)─┤──▶  Ponvara  ────┤
 <future source> ──┘     (connectors +       └─→ GitHub Issues (zero-touch, High/Crit)
                          scheduler + API)
```

Not everything needs this bus — **Trivy Operator, Prowler, ZAP, Nuclei have native
DefectDojo parsers** (see the
[security-tooling roadmap](https://github.com/MagmaMoose/security-platform)), so those
push straight to DefectDojo. Scheduled DAST is owned by
[draventis](https://github.com/MagmaMoose/draventis), which uses those native parsers.
The bus earns its keep for exactly the cases the current CronJob handles:

- **Movement DefectDojo can't do itself** — Dependency-Track has no "push to
  DefectDojo"; *something* must pull FPF and reimport. Same for any source lacking a
  native DefectDojo path.
- **Cross-cutting enrichment** — the **zero-touch GitHub-issue auto-push** (repo
  resolution by name across owners) is logic DefectDojo's per-product GitHub config
  can't do generically. This is the real value-add and belongs in one place.

So: keep it focused (DT + SonarQube + GitHub-issue push at launch), but structure it so
a new source is a new connector module.

---

## 4. Target architecture

**Language:** Python 3.11+ (the runtime image targets 3.12-slim), packaged with **uv +
Ruff + pytest + full type hints** — mirror chargate's conventions exactly (and its
`broker/` deploy pattern).

**The one design decision that unlocks everything: drop the Django ORM, use the
DefectDojo REST API v2.** Replace the two ORM usages:

| ORM usage today | REST replacement |
| --- | --- |
| Mint superuser token via `Token.objects` | **Provision one DefectDojo API token** (a dedicated `ponvara` service user) once, store in OCI Vault. No ORM, no password. |
| `Finding.objects.filter(...)` + `GITHUB_Issue.objects.create(...)` for dedupe | Query `GET /api/v2/findings/` (filter by product/severity/active); dedupe by writing a **finding tag** `gh-issue:<url>` (or a note) via `PATCH /api/v2/findings/{id}/`. State lives *in DefectDojo*, so the service stays stateless. |

**Result:** run on a **slim `python:3.12-slim` image (~80 MB)**, fully **decoupled from
DefectDojo's version**. This alone removes the worst fragility.

### Repo layout

```
ponvara/
  pyproject.toml                # uv; deps: httpx, pydantic-settings, apscheduler,
                                #   fastapi+uvicorn, PyGithub (or raw httpx), prometheus-client
  src/ponvara/
    config.py                   # pydantic-settings: sources, schedules, thresholds, secret refs
    app.py                      # FastAPI: /healthz /readyz /metrics + POST /sync/{source}
    scheduler.py                # APScheduler: interval jobs per enabled source
    connectors/
      dependencytrack.py        # list projects, export FPF            (SOURCE)
      sonarqube.py              # pull findings                        (SOURCE)
      defectdojo.py             # reimport-scan + findings query/tag   (SINK, REST)
      github_issues.py          # zero-touch repo resolve + issue push (SINK)
    sync.py                     # orchestrator: for each source -> DefectDojo; then GH push
    models.py                   # typed Finding/Project DTOs
  charts/ponvara/        # Helm chart (below)
  tests/                        # mirror modules 1:1 (pure connectors, injected HTTP)
  Dockerfile                    # slim, non-root, distroless-ish
  .github/workflows/            # ci.yml (ruff+pytest), release.yml (semantic-release + GHCR image)
```

> **Phase 0 note.** The tree above is the *target*. Today the repo contains only this
> design doc, `pyproject.toml` (an empty `0.0.0` package under `src/ponvara/`),
> and the stub chart. The module files, Dockerfile, and workflows do not exist yet.

### Runtime shape — long-lived Deployment

A single **Deployment** (replicas: 1, `Recreate`) running `uvicorn`:

- **In-process scheduler** (APScheduler) runs each source on its interval — replaces
  the two CronJobs, keeps offsets, adds jitter.
- **HTTP surface:** `/healthz`, `/readyz`, `/metrics` (Prometheus), and
  `POST /sync/{source}` for on-demand runs (handy for testing + future DT webhooks).
- **`concurrency: Forbid` semantics** via an in-process lock per source.
- Emits metrics: `ponvara_sync_findings_total{source}`,
  `..._github_issues_total`, `..._last_success_timestamp{source}`, `..._errors_total`.

> Simpler alternative if a daemon isn't wanted: keep **CronJobs but from our own slim
> image** (chart `kind: CronJob`). You still get the repo/tests/CI/decoupling wins; you
> lose on-demand triggers + metrics. The Helm chart can support **both** via a
> `mode: deployment|cronjob` value. **Recommendation: Deployment** — it's literally the
> "long-lived backend" described here, and the incremental ops cost is tiny.

### Helm chart (`charts/ponvara/`)

`values.yaml` sketch (the full stub lives in
[`charts/ponvara/values.yaml`](../charts/ponvara/values.yaml)):

```yaml
image: { repository: ghcr.io/magmamoose/ponvara, tag: "" }  # Flux ImagePolicy fills tag
mode: deployment                 # or "cronjob"
schedule: { dependencyTrack: "0 * * * *", sonarqube: "30 * * * *" }  # cron OR interval secs
defectDojo:
  url: http://defectdojo-django.security.svc.cluster.local
  productType: Dependency-Track
sources:
  dependencyTrack:
    enabled: true
    url: http://dependency-track-api-server.security.svc.cluster.local:8080
  sonarqube: { enabled: true, url: https://sonarqube.magmamoose.com }
github: { minSeverity: High, maxIssuesPerRun: 50 }
externalSecrets:                 # ESO -> OCI Vault (unchanged keys)
  store: oci-vault
  keys: { dtrackApiKey: dependency-track-api-key, ddApiToken: ponvara-dd-token,
          githubTargets: github-issue-targets, sonarToken: defectdojo-api-key }
resources: { requests: { cpu: 50m, memory: 128Mi }, limits: { memory: 256Mi } }
serviceMonitor: { enabled: true }
ingress: { enabled: false }      # cloudflared tunnel if the trigger API is exposed
podSecurityContext: { runAsNonRoot: true, runAsUser: 10001, seccompProfile: { type: RuntimeDefault } }
```

Templates: `deployment.yaml` **or** `cronjob.yaml` (by `mode`), `service.yaml`,
`servicemonitor.yaml`, `externalsecret.yaml`, `serviceaccount.yaml`
(`automountServiceAccountToken: false` — it never calls the k8s API), `_helpers.tpl`.
Ship the same hardening the SonarQube CronJob already uses (non-root high UID, RO
rootfs, seccomp RuntimeDefault, no SA token).

### Deploy via Flux (mirror chargate/broker)

- `infra/kubernetes/apps/ponvara/{base,prod}/` with a `HelmRelease` pointing at
  the chart (or a Flux `Kustomization` if the chart is vendored), an `ImagePolicy`
  autobumping the tag on each GHCR release, and the `ExternalSecret`s (reuse the
  existing OCI Vault keys; add one new key: `ponvara-dd-token`).
- Retire `kubernetes/apps/security-integrations/` once cut over.

### Image + release (mirror chargate)

GHCR image `ghcr.io/magmamoose/ponvara`, built by a `release.yml` that runs
python-semantic-release (version-from-commits) and a multi-arch `docker buildx` push —
the exact pattern chargate already uses for its `broker` image. Flux's `ImagePolicy`
rewrites the chart tag on publish. External GitHub Actions are **SHA-pinned** with a
`# vX.Y.Z` comment.

---

## 5. Migration plan (low-risk, phased)

| Phase | Change | Risk | Reversible? |
| --- | --- | --- | --- |
| **0. Lift-and-shift** | New repo; move `sync.py` verbatim; add tests around the pure bits (target parsing, severity floor, issue body). Still the DefectDojo-image CronJob, still deployed from infra. | none | trivially |
| **1. Slim the image** | Provision a `ponvara` DefectDojo API token (OCI Vault); replace ORM token-mint with it; switch to `python:3.12-slim`. | low | keep old CronJob until green |
| **2. Drop the ORM** | Replace `Finding`/`GITHUB_Issue` ORM with DefectDojo REST (`/findings/` + tag-based dedupe). Now fully version-decoupled from DefectDojo. | med (verify tag/note dedupe survives reimport) | run both in parallel one cycle |
| **3. Long-lived service** | Convert to the FastAPI+APScheduler Deployment; add `/metrics`, `/sync/{source}`, ServiceMonitor; Helm chart; Flux app dir. Retire the infra CronJobs/ConfigMaps. | med | Flux rollback |
| **4. Generalize** | Fold SonarQube in as a connector; document how a new source plugs in. Point future non-native sources (e.g. a bespoke DAST result shape) here; leave native-parser tools (Trivy Operator, Prowler, ZAP, Nuclei) pushing straight to DefectDojo. | low | per-connector toggle |

You can stop after Phase 1 or 2 and already have a tested, reviewable, slim,
version-decoupled job — most of the value is there. Phases 3–4 deliver the "long-lived
backend" and the reuse.

---

## 6. Open decisions

1. **Name.** `ponvara` (descriptive) — chosen, matching the sibling repos
   [draventis](https://github.com/MagmaMoose/draventis) and
   [security-platform](https://github.com/MagmaMoose/security-platform) under the
   MagmaMoose org.
2. **ORM → REST?** Recommended **yes** (Phase 2) — it's the whole point (slim image,
   version-decoupled). The only thing to validate is that **tag/note-based dedupe
   survives `reimport-scan`** (reimport can recreate findings; confirm tags persist, or
   dedupe on a stable finding hash instead).
3. **Deployment vs CronJob-from-own-image.** "Long-lived backend" → **Deployment**. The
   chart supports both, so this is reversible.
4. **Dedup state:** stateless via DefectDojo tags (recommended) vs a tiny CNPG Postgres
   the service owns (needed only if cross-source correlation/SLA is later tracked here).
5. **Scope at launch:** DT + SonarQube + GitHub-issue push (parity), or go straight to
   the generalized "finding bus". Recommendation: **parity first (Phases 0–3),
   generalize in 4.**

---

## 7. First PR (crawl)

Create `MagmaMoose/ponvara` (this repo), `uv init`, drop `sync.py` in as
`src/ponvara/sync.py`, split the GitHub-target parsing + severity-floor logic
into pure functions, add `tests/` for them, wire `ci.yml` (ruff + pytest). Keep the
existing infra CronJob running untouched. That's Phase 0 — zero production risk, and it
gives every later phase a tested base to refactor against.

---

## Related work

- **[MagmaMoose/chargate](https://github.com/MagmaMoose/chargate)** — PR-time SAST/SCA/IaC
  gate (MegaLinter wrapper with net-new gating). Ponvara mirrors its conventions
  and `broker/` deploy pattern, and is the continuous/runtime counterpart to chargate's
  pre-merge gate.
- **[MagmaMoose/draventis](https://github.com/MagmaMoose/draventis)** — scheduled DAST
  (ZAP + Nuclei) → DefectDojo via native parsers.
- **[MagmaMoose/security-platform](https://github.com/MagmaMoose/security-platform)** —
  the program index and security-tooling roadmap.
- **DefectDojo** and **Dependency-Track** — self-hosted in the private infra repo;
  DefectDojo is the system of record, Dependency-Track the SBOM/SCA source this bus was
  born to feed.
