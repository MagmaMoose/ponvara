"""GitHub Advanced Security REST client (httpx).

Pulls the three GHAS finding surfaces for a repository:

* **code scanning** (CodeQL & friends) — fetched as **SARIF** from the latest
  analysis, so DefectDojo's first-class ``SARIF`` parser ingests it verbatim.
* **Dependabot** alerts — the REST alert list (transformed to Generic Findings
  Import by :mod:`ponvara.sync_github`).
* **secret scanning** alerts — the REST alert list (likewise transformed).

Every call is failure-isolated at the feed level: a repo with a surface disabled
(or a token lacking that scope) returns ``403``/``404``, which we translate to an
empty result rather than an error, so one missing feed never aborts a repo.
"""

from __future__ import annotations

import httpx

from ponvara import __version__

_USER_AGENT = f"ponvara/{__version__} (+https://github.com/MagmaMoose/ponvara)"
_API_VERSION = "2022-11-28"

# GitHub returns these when a GHAS surface is disabled for the repo, or the token
# lacks the scope. Treated as "no findings from this feed", never a hard error.
_DISABLED_STATUSES = frozenset({403, 404})


class GitHubClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        client: httpx.Client,
        timeout: float = 300.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._token = token
        self._client = client
        self._timeout = timeout

    def _headers(self, accept: str = "application/vnd.github+json") -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": accept,
            "X-GitHub-Api-Version": _API_VERSION,
            "User-Agent": _USER_AGENT,
        }

    def _paginate(self, url: str, params: dict[str, str | int]) -> list[dict] | None:
        """Follow RFC-5988 ``Link: rel="next"`` pagination; None if feed is disabled."""
        out: list[dict] = []
        page: str | None = url
        first = True
        while page:
            resp = self._client.get(
                page,
                headers=self._headers(),
                params=params if first else None,
                timeout=self._timeout,
            )
            if resp.status_code in _DISABLED_STATUSES:
                return None
            resp.raise_for_status()
            out.extend(resp.json())
            page = resp.links.get("next", {}).get("url")
            first = False
        return out

    def list_org_repos(self, org: str) -> list[str]:
        """``owner/repo`` for every non-archived repo in the org (paginated)."""
        repos = self._paginate(
            f"{self._base}/orgs/{org}/repos",
            {"per_page": 100, "type": "all"},
        )
        return [r["full_name"] for r in repos if not r.get("archived")]

    def code_scanning_sarif(self, owner: str, repo: str) -> bytes | None:
        """SARIF of the most recent code-scanning analysis, or None if unavailable.

        Lists analyses (newest first), then fetches that analysis with the
        ``application/sarif+json`` media type so the payload is a SARIF log.
        """
        analyses = self._client.get(
            f"{self._base}/repos/{owner}/{repo}/code-scanning/analyses",
            headers=self._headers(),
            params={"per_page": 1, "sort": "created", "direction": "desc"},
            timeout=self._timeout,
        )
        if analyses.status_code in _DISABLED_STATUSES:
            return None
        analyses.raise_for_status()
        items = analyses.json()
        if not items:
            return None
        analysis_id = items[0]["id"]
        sarif = self._client.get(
            f"{self._base}/repos/{owner}/{repo}/code-scanning/analyses/{analysis_id}",
            headers=self._headers(accept="application/sarif+json"),
            timeout=self._timeout,
        )
        if sarif.status_code in _DISABLED_STATUSES:
            return None
        sarif.raise_for_status()
        return sarif.content

    def dependabot_alerts(self, owner: str, repo: str) -> list[dict] | None:
        """Open Dependabot (SCA) alerts for the repo; None if feed is disabled."""
        return self._paginate(
            f"{self._base}/repos/{owner}/{repo}/dependabot/alerts",
            {"state": "open", "per_page": 100},
        )

    def secret_scanning_alerts(self, owner: str, repo: str) -> list[dict] | None:
        """Open secret-scanning alerts for the repo; None if feed is disabled."""
        return self._paginate(
            f"{self._base}/repos/{owner}/{repo}/secret-scanning/alerts",
            {"state": "open", "per_page": 100},
        )
