"""ponvara — a finding bus between security sources and DefectDojo.

Phase 1: the Dependency-Track → DefectDojo sync, ported out of the in-cluster
ConfigMap script and **off the Django ORM** onto the DefectDojo REST API (so it
runs on a slim image, decoupled from DefectDojo's version). For each Dependency-Track
project it exports the findings (FPF) and ``reimport-scan``s them into DefectDojo.

The zero-touch GitHub-issue auto-push is the next phase (it was the other Django-ORM
user); see ``docs/DESIGN.md``.
"""

__version__ = "0.1.0"
