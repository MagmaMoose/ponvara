"""securitybridge CLI.

    securitybridge sync      # sync all Dependency-Track projects into DefectDojo once

Runs once and exits (the k8s CronJob schedules it). The long-lived service +
scheduler + metrics are a later phase; see docs/DESIGN.md.

Exit codes: ``0`` ok · ``1`` setup / fatal error (no token, Dependency-Track
unreachable). Per-project failures are logged and skipped, not fatal.
"""

from __future__ import annotations

import argparse
import logging

import httpx

from securitybridge import __version__
from securitybridge.config import Config
from securitybridge.defectdojo import DefectDojoClient
from securitybridge.dependencytrack import DependencyTrackClient
from securitybridge.sync import run_sync

log = logging.getLogger("securitybridge")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="securitybridge", description="Security finding bus.")
    parser.add_argument("--version", action="version", version=f"securitybridge {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sync", help="Sync all Dependency-Track projects into DefectDojo (once).")
    parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="securitybridge: %(message)s")
    config = Config()

    if not config.dtrack_api_key:
        log.error("DTRACK_API_KEY is empty; aborting")
        return 1
    if not config.defectdojo_token:
        log.error("DEFECTDOJO_TOKEN is empty; aborting")
        return 1

    with httpx.Client(verify=config.verify_ssl) as client:
        dt = DependencyTrackClient(
            config.dtrack_api_url,
            config.dtrack_api_key,
            client=client,
            timeout=config.http_timeout,
        )
        dd = DefectDojoClient(
            config.defectdojo_url,
            config.defectdojo_token,
            client=client,
            timeout=config.http_timeout,
        )
        try:
            run_sync(
                dt,
                dd,
                product_type=config.dd_product_type,
                engagement=config.dd_engagement,
                log=log.info,
            )
        except httpx.HTTPError as exc:
            log.error("failed to list Dependency-Track projects; aborting: %s", exc)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
