"""Runtime configuration (environment / ExternalSecret → env).

Field names map to the same env vars the in-cluster sync used (``DTRACK_API_KEY``,
``DEFECTDOJO_URL``, …) so the migration is drop-in. In k8s these come from an
ExternalSecret (OCI Vault) via ``envFrom`` / ``valueFrom``.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Dependency-Track (source). In-cluster service DNS by default (no edge round-trip).
    dtrack_api_url: str = "http://dependency-track-api-server.security.svc.cluster.local:8080"
    dtrack_api_key: str = ""

    # DefectDojo (sink). A **provisioned** API token — no ORM token-minting.
    defectdojo_url: str = "http://defectdojo-django.security.svc.cluster.local"
    defectdojo_token: str = ""
    dd_product_type: str = "Dependency-Track"
    dd_engagement: str = "Dependency Track"
    dd_site_url: str = "https://defectdojo.magmamoose.com"

    # GitHub Advanced Security (source, for the `sync-github` command). Pulls code
    # scanning (SARIF) + Dependabot + secret scanning and reimports into DefectDojo.
    github_api_url: str = "https://api.github.com"
    github_token: str = ""
    # Explicit "owner/repo" list (comma-separated) OR an org to enumerate. If both
    # are set, the explicit list wins.
    github_repos: str = ""
    github_org: str = ""
    dd_github_product_type: str = "GitHub Advanced Security"
    dd_github_engagement: str = "GHAS"

    http_timeout: float = 300.0
    verify_ssl: bool = True

    def github_repo_list(self) -> list[str]:
        """Explicit `github_repos` (comma/whitespace separated) if set, else []."""
        return [r.strip() for r in self.github_repos.replace(",", " ").split() if r.strip()]
