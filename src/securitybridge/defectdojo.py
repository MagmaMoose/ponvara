"""DefectDojo REST client (httpx): reimport a Dependency-Track FPF export.

Uses a **provisioned** API token (no Django ORM token-minting), which is what lets
securitybridge run on a slim image decoupled from DefectDojo's version.
"""

from __future__ import annotations

import httpx

from securitybridge import __version__

FPF_SCAN_TYPE = "Dependency Track Finding Packaging Format (FPF) Export"
_USER_AGENT = f"securitybridge/{__version__} (+https://github.com/MagmaMoose/securitybridge)"


class DefectDojoClient:
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

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Token {self._token}", "User-Agent": _USER_AGENT}

    def reimport_fpf(
        self,
        *,
        product_name: str,
        product_type: str,
        engagement: str,
        fpf_bytes: bytes,
    ) -> dict:
        """reimport-scan the FPF export; auto-creates product/engagement/test, dedups."""
        data = {
            "scan_type": FPF_SCAN_TYPE,
            "product_type_name": product_type,
            "product_name": product_name,
            "engagement_name": engagement,
            "auto_create_context": "true",
            "active": "true",
            "close_old_findings": "true",
            "minimum_severity": "Info",
        }
        files = {"file": ("findings.json", fpf_bytes, "application/json")}
        resp = self._client.post(
            f"{self._base}/api/v2/reimport-scan/",
            headers=self._headers(),
            data=data,
            files=files,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()
