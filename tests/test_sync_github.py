import json

from securitybridge.sync_github import (
    dependabot_to_generic,
    run_github_sync,
    secret_scanning_to_generic,
)


def test_dependabot_transform_maps_severity_and_fixes():
    alerts = [
        {
            "number": 7,
            "html_url": "https://github.com/o/r/security/dependabot/7",
            "security_advisory": {
                "summary": "Prototype pollution",
                "description": "bad",
                "severity": "high",
                "cve_id": "CVE-2024-1",
                "ghsa_id": "GHSA-xxxx",
                "references": [{"url": "https://example.test/adv"}],
            },
            "security_vulnerability": {
                "package": {"name": "lodash"},
                "vulnerable_version_range": "< 4.17.21",
                "first_patched_version": {"identifier": "4.17.21"},
            },
            "dependency": {"manifest_path": "package.json"},
        }
    ]
    doc = json.loads(dependabot_to_generic(alerts))
    f = doc["findings"][0]

    assert f["severity"] == "High"
    assert f["cve"] == "CVE-2024-1"
    assert f["component_name"] == "lodash"
    assert f["file_path"] == "package.json"
    assert "4.17.21" in f["mitigation"]
    assert f["unique_id_from_tool"] == "GHSA-xxxx"


def test_secret_scanning_transform_is_high_severity():
    alerts = [
        {
            "number": 3,
            "secret_type_display_name": "AWS Access Key ID",
            "html_url": "https://github.com/o/r/security/secret-scanning/3",
        }
    ]
    doc = json.loads(secret_scanning_to_generic(alerts))
    f = doc["findings"][0]

    assert f["severity"] == "High"
    assert "AWS Access Key ID" in f["title"]
    assert f["unique_id_from_tool"] == "secret-scanning-3"


_UNSET = object()


class _FakeGitHub:
    def __init__(self, *, sarif=b"{}", dependabot=_UNSET, secret=_UNSET, raise_on=None):
        self._sarif = sarif
        # None means "feed disabled" (returns None to caller); _UNSET defaults to [].
        self._dependabot = [] if dependabot is _UNSET else dependabot
        self._secret = [] if secret is _UNSET else secret
        self._raise_on = raise_on or set()

    def code_scanning_sarif(self, owner, repo):
        if "code" in self._raise_on:
            raise RuntimeError("boom")
        return self._sarif

    def dependabot_alerts(self, owner, repo):
        return self._dependabot

    def secret_scanning_alerts(self, owner, repo):
        return self._secret


class _FakeDojo:
    def __init__(self):
        self.calls = []

    def reimport(self, **kwargs):
        self.calls.append(kwargs)
        return {"ok": True}


def test_run_github_sync_imports_three_feeds():
    gh = _FakeGitHub(sarif=b'{"runs":[]}', dependabot=[{"number": 1}], secret=[{"number": 2}])
    dd = _FakeDojo()

    summary = run_github_sync(
        gh, dd, repos=["o/r"], product_type="GHAS", engagement="GHAS", log=lambda _m: None
    )

    assert summary.repos == 1
    assert summary.imported == 3
    scan_types = {c["scan_type"] for c in dd.calls}
    assert scan_types == {"SARIF", "Generic Findings Import"}
    # Dependabot and secret scanning share a scan_type but are split by test_title.
    titles = {c["test_title"] for c in dd.calls}
    assert titles == {"GHAS code scanning", "GHAS Dependabot", "GHAS secret scanning"}
    assert all(c["product_name"] == "o/r" for c in dd.calls)


def test_run_github_sync_isolates_feed_errors():
    gh = _FakeGitHub(dependabot=[{"number": 1}], secret=[{"number": 2}], raise_on={"code"})
    dd = _FakeDojo()

    summary = run_github_sync(
        gh, dd, repos=["o/r"], product_type="GHAS", engagement="GHAS", log=lambda _m: None
    )

    assert summary.skipped == 1  # code scanning blew up
    assert summary.imported == 2  # dependabot + secret still landed


def test_run_github_sync_skips_bad_repo_names():
    gh = _FakeGitHub()
    dd = _FakeDojo()

    summary = run_github_sync(
        gh, dd, repos=["not-a-repo"], product_type="GHAS", engagement="GHAS", log=lambda _m: None
    )

    assert dd.calls == []
    assert summary.imported == 0


def test_run_github_sync_disabled_feed_does_not_wipe_dojo():
    """None from dependabot_alerts/secret_scanning_alerts must never reach reimport.

    A scoped-down token (or a repo where a surface is off) causes _paginate to
    return None.  The sync must count that as empty, not call reimport with an
    empty findings list — which would tell DefectDojo to close all known findings.
    """
    gh = _FakeGitHub(sarif=b'{"runs":[]}', dependabot=None, secret=None)
    dd = _FakeDojo()

    summary = run_github_sync(
        gh, dd, repos=["o/r"], product_type="GHAS", engagement="GHAS", log=lambda _m: None
    )

    # Only code scanning was available; Dependabot and secret scanning were disabled.
    assert summary.imported == 1
    assert summary.empty == 2
    assert len(dd.calls) == 1
    assert dd.calls[0]["scan_type"] == "SARIF"
