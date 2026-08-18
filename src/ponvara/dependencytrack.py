"""Dependency-Track REST client (httpx): list projects + export findings (FPF)."""

from __future__ import annotations

import httpx

from ponvara import __version__

_USER_AGENT = f"ponvara/{__version__} (+https://github.com/MagmaMoose/ponvara)"


class DependencyTrackClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        client: httpx.Client,
        timeout: float = 300.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._key = api_key
        self._client = client
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self._key, "Accept": "application/json", "User-Agent": _USER_AGENT}

    def projects(self) -> list[dict]:
        """All active projects (paginated)."""
        out: list[dict] = []
        page, size = 1, 100
        while True:
            resp = self._client.get(
                f"{self._base}/api/v1/project",
                headers=self._headers(),
                params={"excludeInactive": "true", "pageSize": size, "pageNumber": page},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            batch = resp.json()
            out.extend(batch)
            if len(batch) < size:
                break
            page += 1
        return out

    def export_fpf(self, uuid: str) -> bytes:
        """Export a project's findings in Finding Packaging Format (FPF)."""
        resp = self._client.get(
            f"{self._base}/api/v1/finding/project/{uuid}/export",
            headers=self._headers(),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.content
