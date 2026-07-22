"""SecurityBridge — a finding bus between security sources and DefectDojo.

Phase 0 scaffold: this package is intentionally empty. SecurityBridge will promote
the in-cluster ``dt-defectdojo-sync`` CronJob into a long-lived, tested, versioned
service — a *finding bus* with pluggable source connectors (Dependency-Track,
SonarQube, and future DAST) that reimport into DefectDojo over its REST API and
auto-push High/Critical findings to GitHub Issues.

Nothing here runs yet. The migration is planned in phases; see ``docs/DESIGN.md``
and the "Not yet implemented" note in ``README.md``.
"""

__version__ = "0.0.0"
