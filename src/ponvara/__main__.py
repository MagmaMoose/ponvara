"""ponvara CLI.

    ponvara sync          # Dependency-Track → DefectDojo (all projects)
    ponvara sync-github   # GitHub Advanced Security → DefectDojo (all repos)

Each command runs once and exits (the k8s CronJob schedules it). The long-lived
service + scheduler + metrics are a later phase; see docs/DESIGN.md.

Exit codes: ``0`` ok · ``1`` setup / fatal error (no token, source unreachable).
Per-project / per-repo / per-feed failures are logged and skipped, not fatal.
"""

from __future__ import annotations

import argparse
import logging

import httpx

from ponvara import __version__
from ponvara.config import Config
from ponvara.defectdojo import DefectDojoClient
from ponvara.dependencytrack import DependencyTrackClient
from ponvara.github import GitHubClient
from ponvara.sync import run_sync
from ponvara.sync_github import run_github_sync

log = logging.getLogger("ponvara")


def _run_dt_sync(config: Config) -> int:
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


def _run_github_sync(config: Config) -> int:
    if not config.github_token:
        log.error("GITHUB_TOKEN is empty; aborting")
        return 1
    if not config.defectdojo_token:
        log.error("DEFECTDOJO_TOKEN is empty; aborting")
        return 1
    if not config.github_repo_list() and not config.github_org:
        log.error("set GITHUB_REPOS (owner/repo,...) or GITHUB_ORG; aborting")
        return 1

    with httpx.Client(verify=config.verify_ssl) as client:
        gh = GitHubClient(
            config.github_api_url,
            config.github_token,
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
            repos = config.github_repo_list() or gh.list_org_repos(config.github_org)
        except httpx.HTTPError as exc:
            log.error("failed to resolve the GitHub repo list; aborting: %s", exc)
            return 1
        run_github_sync(
            gh,
            dd,
            repos=repos,
            product_type=config.dd_github_product_type,
            engagement=config.dd_github_engagement,
            log=log.info,
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ponvara", description="Security finding bus.")
    parser.add_argument("--version", action="version", version=f"ponvara {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sync", help="Sync all Dependency-Track projects into DefectDojo (once).")
    sub.add_parser(
        "sync-github", help="Sync GitHub Advanced Security findings into DefectDojo (once)."
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="ponvara: %(message)s")
    config = Config()

    if args.command == "sync":
        return _run_dt_sync(config)
    if args.command == "sync-github":
        return _run_github_sync(config)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
