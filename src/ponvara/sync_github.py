"""Orchestrate the GitHub Advanced Security → DefectDojo sync.

For each repository, three feeds are pushed into DefectDojo under one product
(the repo) and one engagement, kept apart by ``test_title``:

* **code scanning** → ``SARIF`` scan type (imported verbatim).
* **Dependabot** → ``Generic Findings Import`` (transformed here).
* **secret scanning** → ``Generic Findings Import`` (transformed here).

Per-repo *and* per-feed isolation: a disabled surface yields nothing, and a feed
that errors is logged and skipped so it never aborts the repo or the run. Only a
failure to *resolve the repo list* is fatal (raised to the caller).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

# GitHub severities (lowercase) → DefectDojo severities.
_SEVERITY = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "moderate": "Medium",
    "low": "Low",
    "info": "Info",
    "warning": "Low",
    "note": "Info",
    "error": "High",
}


def _severity(value: str | None) -> str:
    return _SEVERITY.get((value or "").lower(), "Medium")


class _GitHub(Protocol):
    def code_scanning_sarif(self, owner: str, repo: str) -> bytes | None: ...
    def dependabot_alerts(self, owner: str, repo: str) -> list[dict] | None: ...
    def secret_scanning_alerts(self, owner: str, repo: str) -> list[dict] | None: ...


class _Dojo(Protocol):
    def reimport(
        self,
        *,
        scan_type: str,
        file_bytes: bytes,
        filename: str,
        product_name: str,
        product_type: str,
        engagement: str,
        test_title: str | None = None,
    ) -> dict: ...


@dataclass(frozen=True)
class GitHubSyncSummary:
    repos: int
    imported: int  # feeds successfully reimported
    skipped: int  # feeds that errored
    empty: int  # feeds with nothing to report


def dependabot_to_generic(alerts: list[dict]) -> bytes:
    """Dependabot alert list → DefectDojo Generic Findings Import JSON bytes."""
    findings = []
    for a in alerts:
        adv = a.get("security_advisory", {})
        vuln = a.get("security_vulnerability", {})
        pkg = vuln.get("package", {})
        patched = (vuln.get("first_patched_version") or {}).get("identifier")
        findings.append(
            {
                "title": adv.get("summary") or f"Dependabot alert #{a.get('number')}",
                "description": adv.get("description", ""),
                "severity": _severity(adv.get("severity")),
                "cve": adv.get("cve_id"),
                "component_name": pkg.get("name"),
                "component_version": vuln.get("vulnerable_version_range"),
                "file_path": (a.get("dependency") or {}).get("manifest_path"),
                "mitigation": (f"Upgrade to {patched} or later." if patched else None),
                "references": "\n".join(
                    r.get("url", "") for r in adv.get("references", []) if r.get("url")
                )
                or a.get("html_url"),
                "unique_id_from_tool": adv.get("ghsa_id") or f"dependabot-{a.get('number')}",
            }
        )
    return json.dumps({"findings": findings}).encode()


def secret_scanning_to_generic(alerts: list[dict]) -> bytes:
    """Secret-scanning alert list → DefectDojo Generic Findings Import JSON bytes."""
    findings = []
    for a in alerts:
        kind = a.get("secret_type_display_name") or a.get("secret_type") or "secret"
        findings.append(
            {
                "title": f"Exposed secret: {kind}",
                "description": (
                    f"GitHub secret scanning detected an exposed {kind}. See {a.get('html_url')}"
                ),
                # An exposed live credential is high-severity by default.
                "severity": "High",
                "references": a.get("html_url"),
                "unique_id_from_tool": f"secret-scanning-{a.get('number')}",
            }
        )
    return json.dumps({"findings": findings}).encode()


def _split(full_name: str) -> tuple[str, str]:
    owner, _, repo = full_name.partition("/")
    return owner, repo


def run_github_sync(
    gh: _GitHub,
    dd: _Dojo,
    *,
    repos: list[str],
    product_type: str,
    engagement: str,
    log: Callable[[str], None] = print,
) -> GitHubSyncSummary:
    """Pull GHAS findings for each repo and reimport them into DefectDojo."""
    log(f"syncing {len(repos)} repo(s) from GitHub Advanced Security")
    imported = skipped = empty = 0

    for full_name in repos:
        owner, repo = _split(full_name)
        if not owner or not repo:
            log(f"[{full_name}] not an owner/repo; skipping")
            continue

        # (feed label, scan_type, test_title, producer -> bytes|None). owner/repo are
        # bound as lambda defaults so each closure keeps this iteration's repo (B023).
        feeds: list[tuple[str, str, str, Callable[[], bytes | None]]] = [
            (
                "code-scanning",
                "SARIF",
                "GHAS code scanning",
                lambda o=owner, r=repo: gh.code_scanning_sarif(o, r),
            ),
            (
                "dependabot",
                "Generic Findings Import",
                "GHAS Dependabot",
                lambda o=owner, r=repo: (
                    None
                    if (alerts := gh.dependabot_alerts(o, r)) is None
                    else dependabot_to_generic(alerts)
                ),
            ),
            (
                "secret-scanning",
                "Generic Findings Import",
                "GHAS secret scanning",
                lambda o=owner, r=repo: (
                    None
                    if (alerts := gh.secret_scanning_alerts(o, r)) is None
                    else secret_scanning_to_generic(alerts)
                ),
            ),
        ]

        for label, scan_type, test_title, produce in feeds:
            try:
                payload = produce()
                if payload is None:
                    empty += 1
                    continue
                dd.reimport(
                    scan_type=scan_type,
                    file_bytes=payload,
                    filename=f"{label}.sarif" if scan_type == "SARIF" else f"{label}.json",
                    product_name=full_name,
                    product_type=product_type,
                    engagement=engagement,
                    test_title=test_title,
                )
                log(f"[{full_name}] {label} imported into DefectDojo")
                imported += 1
            except Exception as exc:  # per-feed isolation
                log(f"[{full_name}] {label} failed; skipping: {exc}")
                skipped += 1

    log(f"done: {imported} imported, {skipped} skipped, {empty} empty")
    return GitHubSyncSummary(repos=len(repos), imported=imported, skipped=skipped, empty=empty)
