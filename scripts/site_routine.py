#!/usr/bin/env python3
"""Per-site session routines: one Claude session per website, scheduled SEO/AEO/GEO and link building runs.

Each client site gets its own Claude session with two repos attached: the site's repo and this engine repo.
This script makes that setup identical for every site:

    locate        find the engine repo and the candidate site repos in this session
    init          write the site's state folder (.seo/) inside the SITE repo: site.json, README, link-building dir
    schedule      print the scheduled-task specs (name, cron or one-off time, prompt) for the session to create
    state-check   prove the live site does not serve the .seo/ folder (it holds contacts and outreach drafts)
    set           update fields in .seo/site.json (gsc_property, ga4_property_id, ...)
    access        prove each connection works (service account, Search Console, GA4, keys, push) and list fixes
    pull          fetch this and the previous 28 days of Search Console data into .seo/weekly/<date>/
    analyze       rank this week's on-site changes from that data by fixed rules (or fall back to the audit list)
    log-change    record a shipped change; mark-indexed records whether Google indexed it
    health        leading indicators (schedule, access, approvals, sending, reply and bounce rate, pace, shipping, privacy)
    report        write the owner report from the recorded files
    check-page    pre-ship gate for a changed page (title, description, one H1, valid JSON-LD, no dashes or placeholders)
    monthly-due   true when this is the first weekly run of the calendar month (do the monthly block)
    mark-run      append a run line to .seo/runs.md

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
               deploy_branch: str = "main", force: bool = False, gsc_property: str = "", ga4_property_id: str = "") -> dict:
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
            "gsc_property": gsc_property, "ga4_property_id": ga4_property_id,
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


# --------------------------------------------------------------------------------------
# Weekly machinery: access, pull, analyze, change log, health, report
# The goal is that every judgment a weekly run needs is made here, by rules, so any model can run it.
# --------------------------------------------------------------------------------------

STRIKING_POS = (8.0, 20.0)
STRIKING_MIN_IMPR = 30
QUESTION_MIN_IMPR = 10
ZERO_CLICK_MIN_IMPR = 200
LOW_CTR_MAX_POS = 5.0
LOW_CTR_MIN_IMPR = 100
LOW_CTR_PCT = 2.0
GAP_MIN_IMPR = 30
GAP_POS = 20.0
LOW_DATA_IMPRESSIONS = 300
RECENT_CHANGE_DAYS = 28
QUESTION_RE = r"^(how|what|why|when|where|which|who|can|does|do|is|are|should|will)\b|\?$"


def _state(site_dir: str, *parts: str) -> str:
    return os.path.join(site_dir, STATE_DIRNAME, *parts)


def _read_json(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def set_fields(site_dir: str, pairs: list) -> dict:
    site = load_site(site_dir)
    for kv in pairs:
        k, _, v = kv.partition("=")
        if not k or not _:
            raise SystemExit(f"Expected key=value, got {kv!r}")
        site[k.strip()] = v.strip()
    _write_json(_state(site_dir, "site.json"), site)
    return site


# ---- access -------------------------------------------------------------------------------------

ACCESS_FIXES = {
    "service_account": ("Google service account key in the session environment",
                        "Owner: in the Claude environment settings add GOOGLE_APPLICATION_CREDENTIALS_JSON with the agency "
                        "service account key (one key serves every client). 10 minutes, once."),
    "gsc_property": ("Search Console property recorded for this site",
                     "Claude: run `site_routine.py set --site-dir <site> gsc_property=sc-domain:<domain>` (or the URL-prefix form)."),
    "gsc_access": ("Service account can read this site's Search Console",
                   "Client or owner: Search Console > Settings > Users and permissions > Add user, paste the service account "
                   "email, permission Full. 3 minutes."),
    "ga4_property": ("GA4 property ID recorded for this site",
                     "Owner: GA4 > Admin > Property details, copy the numeric property ID; Claude runs "
                     "`site_routine.py set --site-dir <site> ga4_property_id=<id>`."),
    "ga4_access": ("Service account can read this site's GA4",
                   "Client or owner: GA4 > Admin > Property access management > Add, paste the service account email, role Viewer. 3 minutes."),
    "psi_key": ("PageSpeed API key", "Owner: add GOOGLE_API_KEY (PageSpeed Insights API enabled) to the environment. Optional, 5 minutes."),
    "bing_key": ("Bing Webmaster API key", "Owner: Bing Webmaster Tools > import the site from Search Console > Settings > API access, "
                 "add BING_WEBMASTER_API_KEY to the environment. Optional, 10 minutes."),
    "push": ("Session can push to the site repo", "Owner: make sure the GitHub app has write access to the site repo."),
}


def check_access(site_dir: str, probes: Optional[dict] = None) -> dict:
    """Each item is ok, missing or failed. `probes` overrides the live checks (tests, offline runs)."""
    site = load_site(site_dir)
    probes = probes or {}
    items = {}

    def put(key, status, detail=""):
        label, fix = ACCESS_FIXES[key]
        items[key] = {"label": label, "status": status, "detail": detail, "fix": "" if status == "ok" else fix}

    sa = probes.get("service_account")
    if sa is None:
        try:
            from google_auth import check_credentials
            sa = check_credentials("gsc")
        except Exception as exc:  # noqa: BLE001
            sa = {"available": False, "error": str(exc)}
    put("service_account", "ok" if sa.get("available") else "missing", sa.get("client_email") or sa.get("error") or "")
    put("gsc_property", "ok" if site.get("gsc_property") else "missing", site.get("gsc_property", ""))
    if items["service_account"]["status"] == "ok" and site.get("gsc_property"):
        listed = probes.get("gsc_sites")
        if listed is None:
            try:
                from gsc_query import list_sites
                res = list_sites()
                listed = [x.get("url") for x in res.get("sites", [])] if not res.get("error") else None
                err = res.get("error")
            except Exception as exc:  # noqa: BLE001
                listed, err = None, str(exc)
        else:
            err = ""
        if listed is None:
            put("gsc_access", "failed", err or "could not list properties")
        else:
            put("gsc_access", "ok" if site["gsc_property"] in listed else "missing",
                f"{len(listed)} properties visible")
    else:
        put("gsc_access", "missing", "needs the service account and property first")
    put("ga4_property", "ok" if site.get("ga4_property_id") else "missing", site.get("ga4_property_id", ""))
    ga4 = probes.get("ga4_ok")
    if ga4 is None and site.get("ga4_property_id") and items["service_account"]["status"] == "ok":
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "ga4_report.py"), "--property",
                            str(site["ga4_property_id"]), "--days", "7", "--json"], capture_output=True, text=True, timeout=120)
        try:
            ga4 = r.returncode == 0 and not json.loads(r.stdout).get("error")
        except (json.JSONDecodeError, AttributeError):
            ga4 = False
    put("ga4_access", "ok" if ga4 else "missing", "")
    put("psi_key", "ok" if probes.get("psi", bool(os.environ.get("GOOGLE_API_KEY"))) else "missing")
    put("bing_key", "ok" if probes.get("bing", bool(os.environ.get("BING_WEBMASTER_API_KEY"))) else "missing")
    push = probes.get("push")
    if push is None:
        import subprocess
        r = subprocess.run(["git", "-C", site_dir, "push", "--dry-run", "origin", f"HEAD:{site.get('deploy_branch', 'main')}"],
                           capture_output=True, text=True, timeout=120)
        push = r.returncode == 0
    put("push", "ok" if push else "failed")
    essential = ("service_account", "gsc_property", "gsc_access", "push")
    out = {"checked": _now(), "items": items,
           "essential_ok": all(items[k]["status"] == "ok" for k in essential),
           "needs_owner": [v["fix"] for k, v in items.items() if v["status"] != "ok" and not v["fix"].startswith("Claude")]}
    _write_json(_state(site_dir, "access.json"), out)
    return out


# ---- pull ---------------------------------------------------------------------------------------

def pull_gsc(site_dir: str, day: date, runner: Optional[Callable] = None) -> dict:
    """Run gsc_query.py for this and the previous 28 days; save raw JSON under .seo/weekly/<day>/."""
    site = load_site(site_dir)
    prop = site.get("gsc_property")
    if not prop:
        raise SystemExit("No gsc_property in site.json. Run access first.")
    end = day - timedelta(days=3)
    cur = (end - timedelta(days=27), end)
    prev = (cur[0] - timedelta(days=28), cur[0] - timedelta(days=1))

    def default_runner(args):
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "gsc_query.py"), *args, "--json"],
                           capture_output=True, text=True, timeout=600)
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            return {"error": (r.stderr or r.stdout)[-400:]}

    run = runner or default_runner
    folder = _state(site_dir, "weekly", day.isoformat())
    out = {}
    for name, (a, b), dims in (("queries", cur, "query,page"), ("pages", cur, "page"), ("previous_pages", prev, "page")):
        res = run(["--property", prop, "--start-date", a.isoformat(), "--end-date", b.isoformat(),
                   "--dimensions", dims, "--limit", "5000"])
        _write_json(os.path.join(folder, f"gsc-{name}.json"), res)
        out[name] = {"rows": len(res.get("rows", [])), "error": res.get("error")}
    summary = summarize(site_dir, day)
    return {"saved": folder, "pulls": out, "summary": summary}


def _totals(res: dict) -> dict:
    rows = (res or {}).get("rows", [])
    clicks = sum(r.get("clicks", 0) for r in rows)
    impr = sum(r.get("impressions", 0) for r in rows)
    pos = (sum(r.get("position", 0) * r.get("impressions", 0) for r in rows) / impr) if impr else None
    return {"clicks": clicks, "impressions": impr, "avg_position": round(pos, 1) if pos else None, "pages": len(rows)}


def summarize(site_dir: str, day: date) -> dict:
    folder = _state(site_dir, "weekly", day.isoformat())
    cur = _totals(_read_json(os.path.join(folder, "gsc-pages.json"), {}))
    prev = _totals(_read_json(os.path.join(folder, "gsc-previous_pages.json"), {}))
    summary = {"date": day.isoformat(), "current_28d": cur, "previous_28d": prev,
               "change": {k: (cur[k] - prev[k]) if isinstance(cur.get(k), (int, float)) and isinstance(prev.get(k), (int, float)) else None
                          for k in ("clicks", "impressions", "avg_position")}}
    _write_json(os.path.join(folder, "summary.json"), summary)
    return summary


# ---- analyze ------------------------------------------------------------------------------------

def load_changes(site_dir: str) -> list:
    return _read_json(_state(site_dir, "changes.json"), []) or []


def log_change(site_dir: str, *, url: str, kind: str, summary: str, commit: str = "", day: Optional[date] = None) -> dict:
    changes = load_changes(site_dir)
    entry = {"date": (day or datetime.now(timezone.utc).date()).isoformat(), "url": url, "kind": kind,
             "summary": summary, "commit": commit, "indexed": None}
    changes.append(entry)
    _write_json(_state(site_dir, "changes.json"), changes)
    return entry


def mark_indexed(site_dir: str, url: str, indexed: bool) -> None:
    changes = load_changes(site_dir)
    for c in changes:
        if c["url"] == url:
            c["indexed"] = indexed
    _write_json(_state(site_dir, "changes.json"), changes)


def analyze(site_dir: str, day: date) -> dict:
    """Turn this week's Search Console rows into a ranked list of on-site changes. Pure rules, no judgment."""
    import re as _re
    folder = _state(site_dir, "weekly", day.isoformat())
    q = _read_json(os.path.join(folder, "gsc-queries.json"), {}) or {}
    pg = _read_json(os.path.join(folder, "gsc-pages.json"), {}) or {}
    rows = q.get("rows", [])
    total_impr = sum(r.get("impressions", 0) for r in pg.get("rows", [])) or sum(r.get("impressions", 0) for r in rows)
    recent = {c["url"] for c in load_changes(site_dir)
              if (day - date.fromisoformat(c["date"])).days < RECENT_CHANGE_DAYS}
    cands = []

    def add(kind, priority, page, query, impr, pos, ctr, action):
        cands.append({"kind": kind, "priority": priority, "page": page, "query": query, "impressions": impr,
                      "position": pos, "ctr": ctr, "action": action, "recently_changed": page in recent})

    qre = _re.compile(QUESTION_RE, _re.I)
    by_query: dict = {}
    for r in rows:
        by_query.setdefault(r.get("query", ""), []).append(r)
    for query, rs in by_query.items():
        best = min(rs, key=lambda r: r.get("position", 99))
        impr = sum(r.get("impressions", 0) for r in rs)
        pos, page, ctr = best.get("position", 99), best.get("page", ""), best.get("ctr", 0)
        if qre.search(query) and impr >= QUESTION_MIN_IMPR and pos > 5:
            add("answer", 1, page, query, impr, pos, ctr,
                f"Add a section headed with the question \"{query}\" on {page}: a 40 to 60 word direct answer first, then "
                f"detail; add it to the page's FAQ and FAQPage schema.")
        elif STRIKING_POS[0] <= pos <= STRIKING_POS[1] and impr >= STRIKING_MIN_IMPR:
            add("striking", 2, page, query, impr, pos, ctr,
                f"Strengthen {page} for \"{query}\": use the phrase in the title or an H2, answer it in the first 100 words, "
                f"add 2 internal links to this page from related pages with descriptive anchors.")
        elif pos > GAP_POS and impr >= GAP_MIN_IMPR:
            add("gap", 3, page, query, impr, pos, ctr,
                f"No page ranks well for \"{query}\". If an existing page covers the topic, add a dedicated section to it; "
                f"otherwise create a page on the site's best template and link it from the hub and footer.")
    for r in pg.get("rows", []):
        page, impr, clicks, pos, ctr = r.get("page", ""), r.get("impressions", 0), r.get("clicks", 0), r.get("position", 99), r.get("ctr", 0)
        if impr >= ZERO_CLICK_MIN_IMPR and clicks == 0:
            add("zero_click", 4, page, "", impr, pos, ctr,
                f"{page} has {impr} impressions and no clicks: rewrite the title (under 60 characters, the main query first) "
                f"and the meta description (a concrete benefit and the next step).")
        elif pos <= LOW_CTR_MAX_POS and impr >= LOW_CTR_MIN_IMPR and ctr < LOW_CTR_PCT:
            add("low_ctr", 4, page, "", impr, pos, ctr,
                f"{page} ranks around {pos} but only {ctr}% click: rewrite the title and meta description to match the intent.")
    seen, ranked = set(), []
    for c in sorted(cands, key=lambda c: (c["recently_changed"], c["priority"], -c["impressions"])):
        if c["page"] in seen:
            continue
        seen.add(c["page"])
        ranked.append(c)
    picks = [c for c in ranked if not c["recently_changed"]][:3]
    low = total_impr < LOW_DATA_IMPRESSIONS
    result = {"date": day.isoformat(), "total_impressions_28d": total_impr, "low_data": low, "candidates": ranked,
              "this_week": picks,
              "fallback": ("Search data is too thin to rank changes. This week, ship the top unshipped items from the latest "
                           "audit file in .seo/ (technical blockers first, then missing answers on service pages, then schema, "
                           "then llms.txt and Organization sameAs).") if low or not picks else ""}
    _write_json(os.path.join(folder, "candidates.json"), result)
    return result


# ---- health -------------------------------------------------------------------------------------

def _runs(site_dir: str) -> list:
    out = []
    try:
        with open(_state(site_dir, "runs.md"), encoding="utf-8") as fh:
            for line in fh:
                parts = line.strip().split(" ", 2)
                if len(parts) >= 2 and len(parts[0]) == 10 and parts[0][4] == "-":
                    out.append({"date": parts[0], "routine": parts[1].rstrip(":"), "text": parts[2] if len(parts) > 2 else ""})
    except FileNotFoundError:
        pass
    return out


def mark_run(site_dir: str, routine: str, status: str, note: str = "", day: Optional[date] = None) -> str:
    d = (day or datetime.now(timezone.utc).date()).isoformat()
    line = f"{d} {routine}: {status}" + (f". {note}" if note else "")
    with open(_state(site_dir, "runs.md"), "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return line


def health(site_dir: str, day: date) -> dict:
    """Leading indicators that show trouble in week 1 or 2, long before the day-30 scorecard."""
    import linkbuilding as lb
    site = load_site(site_dir)
    checks = []

    def add(cid, status, msg, action="", who="claude"):
        checks.append({"id": cid, "status": status, "message": msg, "action": action if status != "green" else "",
                       "who": who})

    runs = [r for r in _runs(site_dir) if r["routine"] == "weekly" and r["text"].startswith("done")]
    last = max((date.fromisoformat(r["date"]) for r in runs), default=None)
    age = (day - last).days if last else None
    add("schedule", "green" if age is not None and age <= 8 else ("amber" if age is None else "red"),
        f"last completed weekly run: {last or 'none yet'}",
        "Owner: check this site's scheduled tasks are enabled (the Monday run has not completed in 8 days).", "owner")

    acc = _read_json(_state(site_dir, "access.json"), {}) or {}
    add("access", "green" if acc.get("essential_ok") else "red",
        "Search Console and push access " + ("working" if acc.get("essential_ok") else "missing or unproven"),
        "Run `site_routine.py access`; its fixes appear under Needs you.")

    camp_dir = os.path.join(site_dir, site.get("campaign_dir", os.path.join(STATE_DIRNAME, "link-building")))
    prog = None
    if os.path.exists(os.path.join(camp_dir, "campaign.json")):
        c = lb.Campaign(camp_dir)
        prog = _read_json(os.path.join(camp_dir, "program.json"))

        def older(ts_key, status, days):
            n = 0
            for p in c.prospects:
                ts = p.get(ts_key)
                if p["status"] == status and ts and (day - datetime.fromisoformat(ts).date()).days > days:
                    n += 1
            return n
        stale_prop_14, stale_prop_7 = older("proposed_at", "proposed", 14), older("proposed_at", "proposed", 7)
        add("approvals", "red" if stale_prop_14 else "amber" if stale_prop_7 else "green",
            f"{stale_prop_7} prospects waiting for approval over 7 days ({stale_prop_14} over 14)",
            "Owner: a 10-minute approval pass on the waiting prospects (you can approve a whole tier at once).", "owner")
        stale_draft = older("drafted_at", "drafted", 7)
        add("sending", "red" if stale_draft >= 10 else "amber" if stale_draft else "green",
            f"{stale_draft} drafted emails not sent after 7 days",
            "Owner: send the drafted emails in outreach-approved.csv and tell Claude who replied.", "owner")
        f = lb.funnel(c)
        sent = f["contacted"]
        bounced = f["counts"].get("bounced", 0)
        if sent >= 20:
            rr = f["reply_rate"] or 0
            add("reply_rate", "green" if rr >= 0.05 else "red", f"reply rate {rr:.0%} after {sent} sends",
                "Rewrite hooks, check each contact is the right person, and lead with the strongest asset before sending more.")
        else:
            add("reply_rate", "amber" if sent else "amber", f"{sent} sends so far; reply rate is judged after 20",
                "Keep sending the approved batches.")
        if sent:
            br = bounced / sent
            add("bounces", "red" if br > 0.05 else "green", f"bounce rate {br:.0%}",
                "Owner: pause sending until Claude replaces the bounced contacts.", "owner")
        if prog:
            wk = lb.week_view(prog, day)["week"]
            expected = max(0, wk - (1 if prog.get("mode") == "fast" else 4)) * prog.get("pitches_per_week", 0)
            ratio = (sent / expected) if expected else 1
            add("pace", "green" if ratio >= 0.7 else "amber" if ratio >= 0.4 else "red",
                f"week {wk}: {sent} sent against about {expected} planned",
                "Behind plan: check which step is stuck (approvals, contacts, sending) and fix that one first.")
            overdue = len(lb.week_view(prog, day)["overdue"])
            add("program", "green" if overdue <= 3 else "amber" if overdue <= 8 else "red", f"{overdue} program tasks overdue",
                "Clear overdue claude tasks this run; list overdue owner and client tasks in the report.")
    else:
        add("campaign", "red", "no link-building campaign yet", "Run the SETUP link-building steps.")

    changes = load_changes(site_dir)
    recent = [c for c in changes if (day - date.fromisoformat(c["date"])).days <= 14]
    add("shipping", "green" if recent else "amber", f"{len(recent)} on-site changes shipped in the last 14 days",
        "Ship at least one change a week; if blocked, say what blocks it.")
    unindexed = [c for c in changes if c.get("indexed") is False and (day - date.fromisoformat(c["date"])).days > 14]
    add("indexing", "green" if not unindexed else "amber", f"{len(unindexed)} changed pages still not indexed after 14 days",
        "Owner: in Search Console, URL inspection, press Request indexing for: "
        + ", ".join(c["url"] for c in unindexed[:5]) + ". 1 minute each.", "owner")
    priv = _read_json(_state(site_dir, "privacy.json"), {}) or {}
    add("privacy", "green" if priv.get("verdict") == "PRIVATE" else "red", f"state folder check: {priv.get('verdict', 'never run')}",
        "Run `site_routine.py state-check --site-dir`; block /.seo/ at the host if it leaks.")
    start = date.fromisoformat(prog["start"]) if prog else None
    if start and (day - start).days >= 42:
        weeks = sorted(os.listdir(_state(site_dir, "weekly"))) if os.path.isdir(_state(site_dir, "weekly")) else []
        latest = _read_json(_state(site_dir, "weekly", weeks[-1], "summary.json"), {}) if weeks else {}
        base = None
        try:
            base = lb.Campaign(camp_dir).config.get("baseline", {}).get("gsc_impressions_28d")
        except SystemExit:
            pass
        cur = (latest.get("current_28d") or {}).get("impressions")
        if base is not None and cur is not None:
            add("trend", "green" if cur > base else "amber", f"impressions {cur} against baseline {base} after week 6",
                "Flat after six weeks: compare target pages with the top 3 competitors and close the content gap before adding links.")
    overall = "red" if any(c["status"] == "red" for c in checks) else "amber" if any(c["status"] == "amber" for c in checks) else "green"
    out = {"date": day.isoformat(), "overall": overall, "checks": checks}
    _write_json(_state(site_dir, "health.json"), out)
    return out


# ---- report -------------------------------------------------------------------------------------

def build_report(site_dir: str, day: date) -> str:
    """The owner report, assembled from files. The model adds nothing but the facts already recorded."""
    import linkbuilding as lb
    site = load_site(site_dir)
    hl = health(site_dir, day)
    summ = _read_json(_state(site_dir, "weekly", day.isoformat(), "summary.json"), {}) or {}
    cur, chg = summ.get("current_28d") or {}, summ.get("change") or {}
    shipped = [c for c in load_changes(site_dir) if (day - date.fromisoformat(c["date"])).days < 7]
    camp_dir = os.path.join(site_dir, site.get("campaign_dir", ".seo/link-building"))
    lines = [f"**{site['name']}, week of {day.isoformat()}**", ""]
    verdict = {"green": "On track.", "amber": "On track with items to watch.", "red": "Needs action."}[hl["overall"]]
    reds = [c["message"] for c in hl["checks"] if c["status"] == "red"]
    lines.append(f"Verdict: {verdict}" + (f" Main issue: {reds[0]}." if reds else ""))
    lines.append("")
    if cur:
        def sign(v):
            return "n/a" if v is None else (f"+{v:g}" if v > 0 else f"{v:g}")
        lines.append(f"Search (last 28 days vs the 28 before): clicks {cur.get('clicks')} ({sign(chg.get('clicks'))}), "
                     f"impressions {cur.get('impressions')} ({sign(chg.get('impressions'))}), average position "
                     f"{cur.get('avg_position')} ({sign(chg.get('avg_position'))}, lower is better).")
    else:
        lines.append("Search: no Search Console data this week (see Needs you).")
    lines.append("")
    lines.append("Shipped this week: " + ("; ".join(f"{c['summary']} ({c['url']})" for c in shipped) if shipped else "nothing shipped."))
    if os.path.exists(os.path.join(camp_dir, "campaign.json")):
        c = lb.Campaign(camp_dir)
        f = lb.funnel(c)
        waiting = sum(1 for p in c.prospects if p["status"] == "proposed")
        ready = sum(1 for p in c.prospects if p["status"] == "drafted")
        due = lb.due_items(c, day)
        lines += ["", f"Link building: {waiting} prospects waiting for your approval, {ready} emails ready to send "
                  f"({os.path.join(camp_dir, 'outreach-approved.csv')}), {sum(1 for d in due if d['action'].startswith('send'))} "
                  f"follow-ups due, {f['contacted']} sent so far, {f['links_still_live']} links live."]
    needs = []
    for chk in hl["checks"]:
        if chk["status"] != "green" and chk["action"] and chk.get("who") == "owner":
            needs.append(chk["action"].removeprefix("Owner: "))
    acc = _read_json(_state(site_dir, "access.json"), {}) or {}
    needs += [n.split(": ", 1)[1] if n.split(": ", 1)[0] in ("Owner", "Client or owner") else n for n in acc.get("needs_owner", [])]
    lines += ["", "Needs you:"] + ([f"- {n[:1].upper()}{n[1:]}" for n in dict.fromkeys(needs)] or ["- Nothing this week."])
    cands = _read_json(_state(site_dir, "weekly", day.isoformat(), "candidates.json"), {}) or {}
    nxt = [x["action"] for x in cands.get("candidates", []) if not x["recently_changed"]][3:5]
    lines += ["", "Next week: " + ("; ".join(nxt) if nxt else "continue the program tasks for next week.")]
    text = "\n".join(lines) + "\n"
    path = _state(site_dir, "weekly", day.isoformat(), "report.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


def monthly_due(site_dir: str, day: date) -> bool:
    """True when no weekly run has completed yet in this calendar month."""
    month = day.strftime("%Y-%m")
    return not any(r["routine"] == "weekly" and r["text"].startswith("done") and r["date"].startswith(month)
                   for r in _runs(site_dir))


# ---- pre-ship page check ------------------------------------------------------------------------

def check_page(text: str, is_html: bool = True) -> dict:
    """Deterministic gate before a changed page ships. Errors block the ship; warnings go in the report."""
    import re as _re
    errors, warnings = [], []
    body = text
    if "\u2014" in body or "\u2013" in body:
        errors.append("em or en dash found; replace with a comma, colon or full stop")
    if _re.search(r"lorem ipsum|\bTODO\b|\bTBD\b|\[insert|\{\{", body, _re.I):
        errors.append("placeholder text found (lorem ipsum, TODO, TBD, [insert, {{)")
    if is_html:
        title = _re.search(r"<title[^>]*>(.*?)</title>", body, _re.S | _re.I)
        if not title or not title.group(1).strip():
            errors.append("missing <title>")
        elif len(title.group(1).strip()) > 60:
            warnings.append(f"title is {len(title.group(1).strip())} characters; aim for 60 or fewer")
        desc = _re.search(r'<meta[^>]+name=["\']description["\'][^>]*content=["\'](.*?)["\']', body, _re.S | _re.I)
        if not desc:
            errors.append("missing meta description")
        elif not 70 <= len(desc.group(1)) <= 160:
            warnings.append(f"meta description is {len(desc.group(1))} characters; aim for 70 to 160")
        h1 = len(_re.findall(r"<h1\b", body, _re.I))
        if h1 != 1:
            errors.append(f"{h1} <h1> elements; a page needs exactly one")
        if _re.search(r'<meta[^>]+name=["\']robots["\'][^>]+noindex', body, _re.I):
            warnings.append("page is noindex; confirm that is intended")
        for i, block in enumerate(_re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', body, _re.S | _re.I), 1):
            try:
                data = json.loads(block)
            except json.JSONDecodeError as exc:
                errors.append(f"JSON-LD block {i} is not valid JSON: {exc.msg} at line {exc.lineno}")
                continue
            items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
            for it in items:
                if isinstance(it, dict) and "@type" not in it:
                    errors.append(f"JSON-LD block {i} has an item without @type")
                if isinstance(it, dict) and it.get("@type") == "FAQPage":
                    for qa in it.get("mainEntity", []):
                        if not (qa.get("name") and (qa.get("acceptedAnswer") or {}).get("text")):
                            errors.append(f"JSON-LD block {i}: FAQ entry missing a question or answer text")
    return {"pass": not errors, "errors": errors, "warnings": warnings}


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="Per-site session routines for the SEO engine.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("locate")
    sp = sub.add_parser("init")
    sp.add_argument("--site-dir", required=True); sp.add_argument("--url", required=True); sp.add_argument("--name", required=True)
    sp.add_argument("--industry", default="general"); sp.add_argument("--region", default="")
    sp.add_argument("--timezone", required=True); sp.add_argument("--topics", default="")
    sp.add_argument("--deploy-branch", default="main"); sp.add_argument("--force", action="store_true")
    sp.add_argument("--gsc-property", default=""); sp.add_argument("--ga4-property-id", default="")
    sp = sub.add_parser("set"); sp.add_argument("--site-dir", required=True); sp.add_argument("pairs", nargs="+")
    sp = sub.add_parser("schedule")
    sp.add_argument("--site-dir", required=True); sp.add_argument("--start", help="YYYY-MM-DD, default today")
    sp = sub.add_parser("state-check")
    sp.add_argument("--url", required=True); sp.add_argument("--site-dir", help="also save the verdict to .seo/privacy.json")
    for name in ("access", "pull", "analyze", "health", "report", "monthly-due"):
        sp = sub.add_parser(name); sp.add_argument("--site-dir", required=True); sp.add_argument("--date", help="YYYY-MM-DD, default today")
    sp = sub.add_parser("log-change"); sp.add_argument("--site-dir", required=True); sp.add_argument("--url", required=True)
    sp.add_argument("--kind", required=True, choices=["answer", "striking", "gap", "zero_click", "low_ctr", "audit_fix", "geo", "other"])
    sp.add_argument("--summary", required=True); sp.add_argument("--commit", default=""); sp.add_argument("--date")
    sp = sub.add_parser("mark-indexed"); sp.add_argument("--site-dir", required=True); sp.add_argument("--url", required=True)
    sp.add_argument("--indexed", choices=["yes", "no"], required=True)
    sp = sub.add_parser("check-page"); sp.add_argument("--file", required=True)
    sp = sub.add_parser("mark-run"); sp.add_argument("--site-dir", required=True)
    sp.add_argument("--routine", required=True, choices=["setup", "weekly", "midweek", "checkpoint"])
    sp.add_argument("--status", required=True, choices=["started", "done", "failed"]); sp.add_argument("--note", default="")
    sp.add_argument("--date")
    a = ap.parse_args(argv)
    day = date.fromisoformat(a.date) if getattr(a, "date", None) else datetime.now(timezone.utc).date()

    if a.cmd == "locate":
        out = locate()
    elif a.cmd == "init":
        out = init_state(a.site_dir, url=a.url, name=a.name, industry=a.industry, region=a.region, tz=a.timezone,
                         topics=[t.strip() for t in a.topics.split(",") if t.strip()], deploy_branch=a.deploy_branch,
                         force=a.force, gsc_property=a.gsc_property, ga4_property_id=a.ga4_property_id)
    elif a.cmd == "set":
        out = set_fields(a.site_dir, a.pairs)
    elif a.cmd == "schedule":
        site = load_site(a.site_dir)
        start = date.fromisoformat(a.start) if a.start else datetime.now(timezone.utc).date()
        out = {"site": site["name"], "timezone": site["timezone"], "specs": schedule_specs(site, os.path.abspath(a.site_dir), start)}
    elif a.cmd == "state-check":
        out = state_check(a.url)
        if a.site_dir:
            _write_json(_state(a.site_dir, "privacy.json"), {"checked": _now(), **out})
    elif a.cmd == "access":
        out = check_access(a.site_dir)
    elif a.cmd == "pull":
        out = pull_gsc(a.site_dir, day)
    elif a.cmd == "analyze":
        out = analyze(a.site_dir, day)
    elif a.cmd == "health":
        out = health(a.site_dir, day)
    elif a.cmd == "monthly-due":
        out = {"monthly_due": monthly_due(a.site_dir, day)}
    elif a.cmd == "report":
        print(build_report(a.site_dir, day))
        return 0
    elif a.cmd == "log-change":
        out = log_change(a.site_dir, url=a.url, kind=a.kind, summary=a.summary, commit=a.commit, day=day)
    elif a.cmd == "mark-indexed":
        mark_indexed(a.site_dir, a.url, a.indexed == "yes")
        out = {"url": a.url, "indexed": a.indexed == "yes"}
    elif a.cmd == "check-page":
        with open(a.file, encoding="utf-8", errors="replace") as fh:
            out = check_page(fh.read(), a.file.lower().endswith((".html", ".htm")))
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0 if out["pass"] else 1
    else:
        out = {"line": mark_run(a.site_dir, a.routine, a.status, a.note, day)}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
