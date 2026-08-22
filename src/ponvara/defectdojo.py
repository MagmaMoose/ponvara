"""DefectDojo REST client (httpx): reimport a Dependency-Track FPF export.

Uses a **provisioned** API token (no Django ORM token-minting), which is what lets
ponvara run on a slim image decoupled from DefectDojo's version.
"""

from __future__ import annotations

import httpx

from ponvara import __version__

FPF_SCAN_TYPE = "Dependency Track Finding Packaging Format (FPF) Export"
_USER_AGENT = f"ponvara/{__version__} (+https://github.com/MagmaMoose/ponvara)"


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
    ) -> dict:
        """reimport-scan any report; auto-creates product/engagement/test, dedups.

        ``test_title`` disambiguates multiple tests that share a ``scan_type`` in
        the same engagement (e.g. Dependabot vs secret scanning, both imported as
        ``Generic Findings Import``).
        """
        data = {
            "scan_type": scan_type,
            "product_type_name": product_type,
            "product_name": product_name,
            "engagement_name": engagement,
            "auto_create_context": "true",
            "active": "true",
            "close_old_findings": "true",
            "minimum_severity": "Info",
        }
        if test_title:
            data["test_title"] = test_title
        files = {"file": (filename, file_bytes, "application/json")}
        resp = self._client.post(
            f"{self._base}/api/v2/reimport-scan/",
            headers=self._headers(),
            data=data,
            files=files,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def reimport_fpf(
        self,
        *,
        product_name: str,
        product_type: str,
        engagement: str,
        fpf_bytes: bytes,
    ) -> dict:
        """reimport-scan a Dependency-Track FPF export (thin wrapper over reimport)."""
        return self.reimport(
            scan_type=FPF_SCAN_TYPE,
            file_bytes=fpf_bytes,
            filename="findings.json",
            product_name=product_name,
            product_type=product_type,
            engagement=engagement,
        )
