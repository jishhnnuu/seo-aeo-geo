#!/usr/bin/env python3
"""
Thin wrapper around the Screaming Frog SEO Spider CLI.

The other crawl paths in this plugin (seo-audit's ~500-page subagent
crawl, seo-firecrawl's API-driven scrape) are not built for
enterprise-scale sites — hundreds of thousands to millions of URLs with
XPath extraction, redirect-chain mapping, and bulk CSV export the way
Screaming Frog does. This wrapper exists for users who already have (or
are willing to buy) a Screaming Frog SEO Spider licence — it does not
attempt to replace or crack the paid product; it just automates the
already-licensed desktop app's headless CLI mode.

This wrapper:
  - Validates the target via url_safety before any subprocess starts.
  - Requires the `screamingfrogseospider` CLI binary already on $PATH
    (installed + licensed separately by the user — see
    extensions/screaming-frog/docs/SCREAMING-FROG-SETUP.md).
  - Runs a headless crawl with bulk CSV export enabled, then parses the
    key exports (internal_all.csv, response_codes.csv,
    canonicals.csv, redirects.csv) into a single JSON summary.

Prerequisites
=============
A purchased Screaming Frog SEO Spider licence (screamingfrog.co.uk) with
the CLI on $PATH. The free version of Screaming Frog caps crawls at 500
URLs — same ceiling as this plugin's own seo-audit — so this wrapper
only becomes useful once a licence is in place.

Usage::

    python scripts/screaming_frog_run.py https://example.com
    python scripts/screaming_frog_run.py https://example.com --max-urls 50000 --json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
from url_safety import URLSafetyError, validate_url_strict  # noqa: E402


def _check_binary() -> str | None:
    """Return None if the CLI is on PATH, else an error message."""
    binary = shutil.which("screamingfrogseospider")
    if not binary:
        return (
            "screamingfrogseospider not found on PATH. This requires a "
            "purchased Screaming Frog SEO Spider licence "
            "(https://www.screamingfrog.co.uk/seo-spider/) installed "
            "locally, with its CLI binary on $PATH. See "
            "extensions/screaming-frog/docs/SCREAMING-FROG-SETUP.md."
        )
    return None


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def run(
    target: str,
    *,
    max_urls: int | None = 50000,
    output_dir: str | None = None,
    timeout: int = 3600,
) -> dict:
    try:
        target, _ = validate_url_strict(target)
    except URLSafetyError as exc:
        return {"ok": False, "error": f"url_safety: {exc}"}

    binary_err = _check_binary()
    if binary_err:
        return {"ok": False, "error": binary_err}

    out_dir = Path(output_dir) if output_dir else Path(
        tempfile.mkdtemp(prefix="claude-seo-screamingfrog-")
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "screamingfrogseospider",
        "--crawl", target,
        "--headless",
        "--output-folder", str(out_dir),
        "--overwrite",
        "--export-tabs",
        "Internal:All,Response Codes:All,Canonicals:All,Response Codes:Redirection (3xx)",
        "--save-crawl",
    ]
    if max_urls is not None:
        cmd.extend(["--config-var", f"limits.maxUrls={max_urls}"])

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Crawl timed out after {timeout}s. Try a smaller --max-urls."}
    except OSError as exc:
        return {"ok": False, "error": f"Failed to launch screamingfrogseospider: {exc}"}

    if proc.returncode != 0:
        return {
            "ok": False,
            "error": f"screamingfrogseospider exited {proc.returncode}",
            "stderr": proc.stderr[-2000:],
        }

    internal = _read_csv(out_dir / "internal_all.csv")
    response_codes = _read_csv(out_dir / "response_codes_all.csv")
    canonicals = _read_csv(out_dir / "canonicals_all.csv")
    redirects = _read_csv(out_dir / "response_codes_redirection_3xx.csv")

    status_counts: dict[str, int] = {}
    for row in response_codes:
        code = row.get("Status Code", "unknown")
        status_counts[code] = status_counts.get(code, 0) + 1

    return {
        "ok": True,
        "target": target,
        "output_dir": str(out_dir),
        "urls_crawled": len(internal),
        "status_code_breakdown": status_counts,
        "redirect_count": len(redirects),
        "canonical_rows": len(canonicals),
        "note": (
            "Full CSV exports are in output_dir for detailed analysis "
            "(internal_all.csv, response_codes_all.csv, "
            "canonicals_all.csv, response_codes_redirection_3xx.csv)."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url")
    parser.add_argument("--max-urls", type=int, default=50000)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--json", action="store_true", help="No-op; output is always JSON.")
    args = parser.parse_args()

    result = run(
        args.url,
        max_urls=args.max_urls,
        output_dir=args.output_dir,
        timeout=args.timeout,
    )
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
