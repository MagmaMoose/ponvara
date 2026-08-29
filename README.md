# Ponvara

[![CI](https://github.com/MagmaMoose/ponvara/actions/workflows/ci.yml/badge.svg)](https://github.com/MagmaMoose/ponvara/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-ponvara-3f51b5)](https://magmamoose.github.io/ponvara/)
[![License](https://img.shields.io/github/license/MagmaMoose/ponvara)](LICENSE)

> **A finding bus: pull findings from sources that cannot reach DefectDojo, and push the
> serious ones to GitHub issues.**

## What it is

Ponvara pulls security findings from sources that cannot push to
[DefectDojo](https://github.com/DefectDojo/django-DefectDojo) themselves, reimports them,
and does the one cross-cutting thing DefectDojo cannot do generically: zero-touch
GitHub-issue push for High and Critical findings, resolving the target repo by name
across multiple GitHub accounts.

It promotes an existing, working-but-fragile in-cluster CronJob into a tested, versioned
service, and generalises it so a new source is a new connector module rather than a new
CronJob.

Two surfaces: connectors that read from sources, and sinks that write to DefectDojo and
GitHub. They meet at a scheduler; neither imports the other.

## Run it

```sh
helm install ponvara charts/ponvara \
  --namespace security --create-namespace \
  --set defectDojo.url=https://defectdojo.example.com \
  --set dependencyTrack.url=https://dtrack.example.com
```

An hourly CronJob plus an ExternalSecret. The Dependency-Track key and a provisioned
DefectDojo API token come from OCI Vault through External Secrets Operator. Render it
first with `helm template ponvara charts/ponvara`.

## Documentation

| | |
| --- | --- |
| [Overview](https://magmamoose.github.io/ponvara/) | Architecture, why the REST API rather than the Django ORM, how it fits the security programme |
| [Design](https://magmamoose.github.io/ponvara/DESIGN/) | The full design document |
| [Roadmap](https://magmamoose.github.io/ponvara/explanation/roadmap/) | What is built, what is next, and what is still undecided |

## Status

Phase 1: the Dependency-Track to DefectDojo sync, ported off the Django ORM onto the
DefectDojo REST API. The GitHub-issue push and the long-lived FastAPI service are next.
Maturity is claimed on the roadmap and nowhere else.

## Where it sits

**Ponvara** routes findings between systems ·
[draventis](https://github.com/MagmaMoose/draventis) scans what is deployed ·
[Chargate](https://github.com/MagmaMoose/chargate) gates security at the pull request

## Security · Contributing · License

[Report a vulnerability](https://github.com/MagmaMoose/ponvara/security/advisories/new) ·
[Contributing](https://github.com/MagmaMoose/.github/blob/main/CONTRIBUTING.md) ·
Apache-2.0, see [LICENSE](LICENSE).
