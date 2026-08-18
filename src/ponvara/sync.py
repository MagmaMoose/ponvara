"""Orchestrate the Dependency-Track → DefectDojo sync (pure control flow).

Per-project errors are logged and skipped (one bad project never aborts the run);
only a failure to *list* projects is fatal (raised to the caller).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


class _DTrack(Protocol):
    def projects(self) -> list[dict]: ...
    def export_fpf(self, uuid: str) -> bytes: ...


class _Dojo(Protocol):
    def reimport_fpf(
        self, *, product_name: str, product_type: str, engagement: str, fpf_bytes: bytes
    ) -> dict: ...


@dataclass(frozen=True)
class SyncSummary:
    projects: int
    synced: int
    skipped: int


def run_sync(
    dt: _DTrack,
    dd: _Dojo,
    *,
    product_type: str,
    engagement: str,
    log: Callable[[str], None] = print,
) -> SyncSummary:
    """Reimport every Dependency-Track project's findings into DefectDojo."""
    projects = dt.projects()  # a failure here is fatal — let it raise
    log(f"found {len(projects)} active Dependency-Track project(s)")

    synced = skipped = 0
    for proj in projects:
        name, uuid = proj.get("name"), proj.get("uuid")
        version = proj.get("version")
        label = f"{name} ({version})" if version else name
        if not name or not uuid:
            continue
        try:
            fpf = dt.export_fpf(uuid)
            dd.reimport_fpf(
                product_name=name,
                product_type=product_type,
                engagement=engagement,
                fpf_bytes=fpf,
            )
            log(f"[{label}] imported into DefectDojo")
            synced += 1
        except Exception as exc:  # per-project isolation (mirrors the legacy sync)
            log(f"[{label}] sync failed; skipping: {exc}")
            skipped += 1

    log(f"done: {synced} synced, {skipped} skipped")
    return SyncSummary(projects=len(projects), synced=synced, skipped=skipped)
