#!/usr/bin/env python3
"""Per-site session routines: one Claude session per website, scheduled SEO/AEO/GEO and link building runs.

Each client site gets its own Claude session with two repos attached: the site's repo and this engine repo.
This script makes that setup identical for every site:

    locate        find the engine repo and the candidate site repos in this session
    init          write the site's state folder (.seo/) inside the SITE repo: site.json, README, link-building dir
    schedule      print the scheduled-task specs (name, cron or one-off time, prompt) for the session to create
    state-check   prove the live site does not serve the .seo/ folder (it holds contacts and outreach drafts)

State never goes into the engine repo, which is public. The scheduled prompts are short pointers to the routine
files in templates/site-session/, so improving a routine here improves every site's next run.

Usage:
    python scripts/site_routine.py locate
    python scripts/site_routine.py init --site-dir /home/user/acme-site --url https://acme.com --name Acme \\
        --industry saas --region US --timezone America/New_York --topics "invoice software,ap automation"
    python scripts/site_routine.py schedule --site-dir /home/user/acme-site --start 2026-10-19
    python scripts/site_routine.py state-check --url https://acme.com

All commands print JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_DIR = os.path.dirname(SCRIPTS_DIR)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

STATE_DIRNAME = ".seo"
ROUTINES_DIR = os.path.join("templates", "site-session")
MIDWEEK_SPRINT_DAYS = 60
CHECKPOINT_DAYS = (30, 60)
LOCAL_RUN_HOUR = 9  # runs land just before 09:00 in the site's own timezone

STATE_README = """# .seo (private SEO state for this site)

Written by the SEO engine (jishhnnuu/seo-aeo-geo, scripts/site_routine.py) and read by every scheduled run.

- `site.json`: site profile and schedule settings
- `link-building/`: the link-building campaign (prospects, contacts, drafts, program, scorecard)
- `runs.md`: one line per scheduled run

This folder holds outreach contacts and drafts. It must never be served by the live website. Every run checks
this with `site_routine.py state-check`. If your host publishes the repository root, block `/.seo/` in the host
config (for Netlify, see the routine file `templates/site-session/SETUP.md`).
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def is_git_repo(path: str) -> bool:
    return os.path.isdir(os.path.join(path, ".git"))


def locate(search_root: Optional[str] = None) -> dict:
    """Engine repo is where this script lives; site repos are the other git repos beside it."""
    root = search_root or os.path.dirname(ENGINE_DIR)
    sites = []
    try:
        names = sorted(os.listdir(root))
    except OSError:
        names = []
    for name in names:
        path = os.path.join(root, name)
        if os.path.abspath(path) == os.path.abspath(ENGINE_DIR) or not is_git_repo(path):
            continue
        sites.append({"dir": path, "has_state": os.path.isfile(os.path.join(path, STATE_DIRNAME, "site.json"))})
    return {"engine_dir": ENGINE_DIR, "site_repos": sites,
            "note": "" if sites else "No site repo found beside the engine repo. Attach the website repo to this session."}


def load_site(site_dir: str) -> dict:
    path = os.path.join(site_dir, STATE_DIRNAME, "site.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise SystemExit(f"No {path}. Run `site_routine.py init` first.")


def init_state(site_dir: str, *, url: str, name: str, industry: str, region: str, tz: str, topics: list,
               deploy_branch: str = "main", force: bool = False) -> dict:
    if not is_git_repo(site_dir):
        raise SystemExit(f"{site_dir} is not a git repository.")
    if os.path.abspath(site_dir) == os.path.abspath(ENGINE_DIR):
        raise SystemExit("Refusing to write client state into the engine repo, which is public.")
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise SystemExit(f"Unknown timezone {tz!r}; use an IANA name such as Asia/Dubai or America/New_York.")
    state = os.path.join(site_dir, STATE_DIRNAME)
    site_json = os.path.join(state, "site.json")
    if os.path.exists(site_json) and not force:
        raise SystemExit(f"{site_json} exists. Use --force to overwrite.")
    os.makedirs(os.path.join(state, "link-building"), exist_ok=True)
    site = {"url": url, "name": name, "industry": industry, "region": region.upper() if region else "",
            "timezone": tz, "topics": topics, "deploy_branch": deploy_branch,
            "campaign_dir": os.path.join(STATE_DIRNAME, "link-building"), "created": _now()}
    with open(site_json, "w", encoding="utf-8") as fh:
        json.dump(site, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(state, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(STATE_README)
    runs = os.path.join(state, "runs.md")
    if not os.path.exists(runs):
        with open(runs, "w", encoding="utf-8") as fh:
            fh.write("# Scheduled runs\n\n")
    return {"written": [site_json, os.path.join(state, "README.md"), runs], "site": site}


def _jitter_minute(name: str) -> int:
    """Land 1 to 15 minutes before the hour, spread by task name, so runs avoid the :00 rush."""
    return 60 - (len(name) % 15 + 1)


def _local_cron(tz: str, weekday: str, name: str) -> str:
    return f"CRON_TZ={tz} {_jitter_minute(name)} {LOCAL_RUN_HOUR - 1} * * {weekday}"


def _one_off(tz: str, day: date) -> str:
    local = datetime.combine(day, time(LOCAL_RUN_HOUR, 0), tzinfo=ZoneInfo(tz))
    return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:00Z")


def _pointer(routine: str, site: dict, site_dir: str, engine_dir: str, extra: str = "") -> str:
    branch = site.get("deploy_branch", "main")
    return (
        f"Scheduled {routine} run for {site['name']} ({site['url']}). Site repo: {site_dir}. Engine repo: {engine_dir}. "
        f"First update both: in the engine repo run `git checkout main && git pull origin main`; in the site repo run "
        f"`git checkout {branch} && git pull origin {branch}` (the session can restart on another branch). Then read and "
        f"follow {engine_dir}/{ROUTINES_DIR}/{routine}.md exactly, with {site_dir}/{STATE_DIRNAME}/site.json as the "
        f"site config. The owner set this schedule up on purpose; it is an unattended run, so make sound judgment "
        f"calls, never send outreach or buy anything, and end with the owner report the routine describes.{extra}"
    )


def schedule_specs(site: dict, site_dir: str, start: date, engine_dir: str = ENGINE_DIR) -> list:
    tz = site["timezone"]
    n = site["name"]
    specs = [
        {"routine": "weekly", "name": f"{n}: weekly SEO, AEO, GEO and link building",
         "cron_expression": None, "prompt": _pointer("weekly", site, site_dir, engine_dir),
         "why": "Main run. Search data refreshes with a 2 to 3 day lag, so weekly is the useful rhythm; the first run "
                "in each calendar month also does the monthly deep steps."},
        {"routine": "midweek", "name": f"{n}: midweek link building sprint",
         "cron_expression": None,
         "prompt": _pointer("midweek", site, site_dir, engine_dir,
                            f" This sprint run is meant for the first {MIDWEEK_SPRINT_DAYS} days; the day-60 checkpoint decides whether it continues."),
         "why": f"Second outreach slot for the first {MIDWEEK_SPRINT_DAYS} days: follow-ups due, next batch, new links verified."},
    ]
    specs[0]["cron_expression"] = _local_cron(tz, "1", specs[0]["name"])
    specs[1]["cron_expression"] = _local_cron(tz, "4", specs[1]["name"])
    for d in CHECKPOINT_DAYS:
        name = f"{n}: day {d} checkpoint"
        specs.append({"routine": "checkpoint", "name": name, "run_once_at": _one_off(tz, start + timedelta(days=d)),
                      "prompt": _pointer("checkpoint", site, site_dir, engine_dir, f" This is the day {d} checkpoint."),
                      "why": f"Go or no-go verdict at day {d} against the scorecard checks."})
    return specs


def state_check(url: str, fetch: Optional[Callable] = None) -> dict:
    """The state folder must not be readable on the live site. Any 2xx with content is a leak."""
    if fetch is None:
        from url_safety import safe_requests_get

        def fetch(u):  # type: ignore[no-redef]
            r = safe_requests_get(u, timeout=15, allow_redirects=False)
            return r.status_code, r.text[:2000]
    probes = [f"{url.rstrip('/')}/{STATE_DIRNAME}/site.json", f"{url.rstrip('/')}/{STATE_DIRNAME}/README.md",
              f"{url.rstrip('/')}/{STATE_DIRNAME}/link-building/prospects.json"]
    results, leak, unknown = [], False, False
    for p in probes:
        try:
            code, body = fetch(p)
        except Exception as exc:  # noqa: BLE001 - an unreachable probe is reported, not hidden
            results.append({"url": p, "status": None, "error": f"{type(exc).__name__}: {exc}"[:160]})
            unknown = True
            continue
        exposed = 200 <= code < 300 and ('"campaign_dir"' in body or "private SEO state" in body or '"prospects"' in body)
        leak = leak or exposed
        results.append({"url": p, "status": code, "exposed": exposed})
    verdict = "LEAK" if leak else ("UNVERIFIED" if unknown else "PRIVATE")
    return {"verdict": verdict, "probes": results,
            "fix": "" if verdict == "PRIVATE" else "Block /.seo/ at the host (see templates/site-session/SETUP.md) and re-run."}


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Per-site session routines for the SEO engine.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("locate")
    sp = sub.add_parser("init")
    sp.add_argument("--site-dir", required=True); sp.add_argument("--url", required=True); sp.add_argument("--name", required=True)
    sp.add_argument("--industry", default="general"); sp.add_argument("--region", default="")
    sp.add_argument("--timezone", required=True); sp.add_argument("--topics", default="")
    sp.add_argument("--deploy-branch", default="main"); sp.add_argument("--force", action="store_true")
    sp = sub.add_parser("schedule")
    sp.add_argument("--site-dir", required=True); sp.add_argument("--start", help="YYYY-MM-DD, default today")
    sp = sub.add_parser("state-check")
    sp.add_argument("--url", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "locate":
        out = locate()
    elif a.cmd == "init":
        out = init_state(a.site_dir, url=a.url, name=a.name, industry=a.industry, region=a.region, tz=a.timezone,
                         topics=[t.strip() for t in a.topics.split(",") if t.strip()], deploy_branch=a.deploy_branch,
                         force=a.force)
    elif a.cmd == "schedule":
        site = load_site(a.site_dir)
        start = date.fromisoformat(a.start) if a.start else datetime.now(timezone.utc).date()
        out = {"site": site["name"], "timezone": site["timezone"], "specs": schedule_specs(site, os.path.abspath(a.site_dir), start)}
    else:
        out = state_check(a.url)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
