"""Tests for scripts/site_routine.py: per-site state, schedule specs, privacy check."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import site_routine as sr  # noqa: E402

ROUTINES = Path(sr.ENGINE_DIR, "templates", "site-session")


@pytest.fixture()
def site(tmp_path: Path) -> Path:
    d = tmp_path / "acme-site"
    d.mkdir()
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    return d


def _init(site: Path, tz="Asia/Dubai"):
    return sr.init_state(str(site), url="https://acme.example", name="Acme", industry="saas", region="ae",
                         tz=tz, topics=["invoice software"])


def test_init_writes_private_state_in_site_repo(site):
    out = _init(site)
    data = json.loads((site / ".seo" / "site.json").read_text(encoding="utf-8"))
    assert data["timezone"] == "Asia/Dubai" and data["region"] == "AE" and data["campaign_dir"] == ".seo/link-building"
    assert (site / ".seo" / "link-building").is_dir() and (site / ".seo" / "README.md").is_file()
    assert out["site"]["name"] == "Acme"
    with pytest.raises(SystemExit):
        _init(site)


def test_init_refuses_engine_repo_non_git_and_bad_timezone(tmp_path, site):
    with pytest.raises(SystemExit):
        sr.init_state(sr.ENGINE_DIR, url="https://x.example", name="X", industry="saas", region="", tz="UTC", topics=[])
    with pytest.raises(SystemExit):
        sr.init_state(str(tmp_path), url="https://x.example", name="X", industry="saas", region="", tz="UTC", topics=[])
    with pytest.raises(SystemExit):
        _init(site, tz="Mars/Olympus")


def test_schedule_specs(site):
    _init(site)
    site_cfg = sr.load_site(str(site))
    specs = sr.schedule_specs(site_cfg, str(site), date(2026, 10, 19))
    by = {s["routine"]: s for s in specs if s["routine"] != "checkpoint"}
    assert by["weekly"]["cron_expression"].startswith("CRON_TZ=Asia/Dubai ") and by["weekly"]["cron_expression"].endswith(" 8 * * 1")
    assert by["midweek"]["cron_expression"].endswith(" 8 * * 4")
    for s in by.values():
        minute = int(s["cron_expression"].split()[1])
        assert 45 <= minute <= 59, "jittered off the hour"
    cps = [s for s in specs if s["routine"] == "checkpoint"]
    # 09:00 Dubai (UTC+4) on day 30 and day 60
    assert [c["run_once_at"] for c in cps] == ["2026-11-18T05:00:00Z", "2026-12-18T05:00:00Z"]
    for s in specs:
        p = s["prompt"]
        assert str(site) in p and sr.ENGINE_DIR in p and f"templates/site-session/{s['routine']}.md" in p
        assert "git pull origin main" in p and "never send outreach" in p
        assert "\u2014" not in p and "\u2013" not in p
        assert (ROUTINES / f"{s['routine']}.md").is_file(), "prompt points at a routine file that exists"


def test_state_check_verdicts():
    leak = sr.state_check("https://a.example", lambda u: (200, '{"campaign_dir": ".seo/link-building"}'))
    assert leak["verdict"] == "LEAK" and leak["fix"]
    private = sr.state_check("https://a.example", lambda u: (404, "Not found"))
    assert private["verdict"] == "PRIVATE"
    # A site that answers every path with its homepage (SPA fallback) is not a leak.
    spa = sr.state_check("https://a.example", lambda u: (200, "<html><body>Welcome</body></html>"))
    assert spa["verdict"] == "PRIVATE"

    def boom(u):
        raise OSError("dns")
    assert sr.state_check("https://a.example", boom)["verdict"] == "UNVERIFIED"


def test_locate_finds_sibling_site_repos(tmp_path, site):
    out = sr.locate(str(site.parent))
    assert [s["dir"] for s in out["site_repos"]] == [str(site)]
    _init(site)
    assert sr.locate(str(site.parent))["site_repos"][0]["has_state"] is True


def test_routine_files_follow_writing_rules():
    for f in ROUTINES.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        assert "\u2014" not in text and "\u2013" not in text, f.name
        if f.name not in ("RULES.md", "SETUP.md", "OWNER-GUIDE.md"):
            assert "Read `RULES.md` first" in text, f.name
    rules = (ROUTINES / "RULES.md").read_text(encoding="utf-8")
    assert "Never send email" in rules and "engine repo" in rules


def test_every_command_named_in_routines_exists():
    """A routine that names a subcommand the scripts do not have would strand a smaller model."""
    import re
    import linkbuilding as lb
    lb_cmds = set(lb.build_parser()._subparsers._group_actions[0].choices)
    sr_cmds = {"locate", "init", "set", "schedule", "state-check", "access", "pull", "analyze", "health", "report",
               "monthly-due", "log-change", "mark-indexed", "check-page", "mark-run"}
    for f in ROUTINES.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        for cmd in re.findall(r"linkbuilding\.py (\w[\w-]*)", text):
            assert cmd in lb_cmds, (f.name, cmd)
        for cmd in re.findall(r"site_routine\.py (\w[\w-]*)", text):
            assert cmd in sr_cmds, (f.name, cmd)


# ---- weekly machinery ----------------------------------------------------------------------------

DAY = date(2026, 11, 2)


def _fake_runner(current_rows, page_rows, prev_page_rows):
    def run(args):
        dims = args[args.index("--dimensions") + 1]
        start = args[args.index("--start-date") + 1]
        if dims == "query,page":
            return {"rows": current_rows, "error": None}
        return {"rows": page_rows if start > "2026-10-01" else prev_page_rows, "error": None}
    return run


QUERY_ROWS = [
    {"query": "how much does ac repair cost in dubai", "page": "https://acme.example/ac-repair", "impressions": 40, "clicks": 0, "ctr": 0, "position": 14.2},
    {"query": "ac repair dubai", "page": "https://acme.example/ac-repair", "impressions": 300, "clicks": 4, "ctr": 1.3, "position": 11.0},
    {"query": "ac maintenance contract", "page": "https://acme.example/maintenance", "impressions": 90, "clicks": 1, "ctr": 1.1, "position": 9.5},
    {"query": "duct cleaning sharjah", "page": "https://acme.example/", "impressions": 60, "clicks": 0, "ctr": 0, "position": 34.0},
    {"query": "acme ac", "page": "https://acme.example/", "impressions": 20, "clicks": 12, "ctr": 60, "position": 1.0},
]
PAGE_ROWS = [
    {"page": "https://acme.example/ac-repair", "impressions": 340, "clicks": 4, "ctr": 1.2, "position": 11.4},
    {"page": "https://acme.example/pricing", "impressions": 250, "clicks": 0, "ctr": 0, "position": 6.0},
    {"page": "https://acme.example/", "impressions": 180, "clicks": 12, "ctr": 6.7, "position": 3.0},
]
PREV_ROWS = [{"page": "https://acme.example/", "impressions": 400, "clicks": 10, "ctr": 2.5, "position": 15.0}]


def test_pull_summary_and_analyze(site):
    _init(site)
    sr.set_fields(str(site), ["gsc_property=sc-domain:acme.example"])
    out = sr.pull_gsc(str(site), DAY, runner=_fake_runner(QUERY_ROWS, PAGE_ROWS, PREV_ROWS))
    s = out["summary"]
    assert s["current_28d"]["impressions"] == 770 and s["previous_28d"]["impressions"] == 400
    assert s["change"]["clicks"] == 6
    res = sr.analyze(str(site), DAY)
    assert not res["low_data"]
    kinds = [c["kind"] for c in res["this_week"]]
    assert kinds[0] == "answer", "question queries come first"
    pages = [c["page"] for c in res["this_week"]]
    assert len(pages) == len(set(pages)) <= 3, "one change per page, at most three"
    assert any(c["kind"] == "zero_click" and c["page"].endswith("/pricing") for c in res["candidates"])
    assert any(c["kind"] == "gap" for c in res["candidates"])
    for c in res["this_week"]:
        assert c["action"] and "\u2014" not in c["action"]


def test_recent_changes_are_not_picked_again_and_low_data_falls_back(site):
    _init(site)
    sr.set_fields(str(site), ["gsc_property=sc-domain:acme.example"])
    sr.pull_gsc(str(site), DAY, runner=_fake_runner(QUERY_ROWS, PAGE_ROWS, PREV_ROWS))
    sr.log_change(str(site), url="https://acme.example/ac-repair", kind="answer", summary="Added cost answer", day=DAY)
    picks = sr.analyze(str(site), DAY)["this_week"]
    assert "https://acme.example/ac-repair" not in [c["page"] for c in picks]
    thin = [{"query": "acme", "page": "https://acme.example/", "impressions": 12, "clicks": 3, "ctr": 25, "position": 1.0}]
    sr.pull_gsc(str(site), DAY, runner=_fake_runner(thin, thin, thin))
    res = sr.analyze(str(site), DAY)
    assert res["low_data"] and res["fallback"]


def test_access_with_probes(site):
    _init(site)
    out = sr.check_access(str(site), probes={"service_account": {"available": True, "client_email": "sa@x.iam"},
                                             "gsc_sites": ["sc-domain:acme.example"], "ga4_ok": False,
                                             "psi": True, "bing": False, "push": True})
    assert out["items"]["gsc_property"]["status"] == "missing" and not out["essential_ok"]
    sr.set_fields(str(site), ["gsc_property=sc-domain:acme.example"])
    out = sr.check_access(str(site), probes={"service_account": {"available": True}, "gsc_sites": ["sc-domain:acme.example"],
                                             "ga4_ok": True, "psi": True, "bing": True, "push": True})
    assert out["essential_ok"] and all(v["status"] == "ok" for k, v in out["items"].items() if k != "ga4_property")
    out = sr.check_access(str(site), probes={"service_account": {"available": True}, "gsc_sites": ["sc-domain:other.example"],
                                             "ga4_ok": True, "psi": True, "bing": True, "push": True})
    assert out["items"]["gsc_access"]["status"] == "missing"
    assert any("Users and permissions" in n for n in out["needs_owner"])


def _campaign(site):
    import linkbuilding as lb
    camp = str(site / ".seo" / "link-building")
    lb.main(["init", "--campaign", camp, "--site", "https://acme.example", "--name", "Acme", "--industry", "saas",
             "--sender-name", "Sam", "--sender-title", "Owner", "--force"])
    return lb, camp


def test_health_flags_owner_bottlenecks_and_missing_runs(site):
    _init(site)
    lb, camp = _campaign(site)
    c = lb.Campaign(camp)
    lb.merge_prospects(c.prospects, lb.library_prospects("saas", "US"))
    lb.screen_all(c)
    lb.select_shortlist(c, count=20)
    for p in c.prospects:
        if p["status"] == "proposed":
            p["proposed_at"] = "2026-10-10T00:00:00+00:00"
    c.save()
    lb.main(["program", "--campaign", camp, "--start", "2026-10-19"])
    h = sr.health(str(site), DAY)
    by = {x["id"]: x for x in h["checks"]}
    assert by["approvals"]["status"] == "red" and "approval" in by["approvals"]["action"]
    assert by["schedule"]["status"] == "amber" and by["access"]["status"] == "red" and by["privacy"]["status"] == "red"
    assert h["overall"] == "red"
    sr.mark_run(str(site), "weekly", "done", "shipped 1 change", day=DAY - timedelta(days=3))
    assert {x["id"]: x for x in sr.health(str(site), DAY)["checks"]}["schedule"]["status"] == "green"
    sr.mark_run(str(site), "weekly", "done", day=DAY - timedelta(days=20))


def test_health_reply_rate_and_bounces_after_twenty_sends(site):
    _init(site)
    lb, camp = _campaign(site)
    c = lb.Campaign(camp)
    for i in range(22):
        p = lb.make_prospect(f"site{i}.example", source="manual", ptype="resource_page")
        lb.log_event(p, "sent", when=date(2026, 10, 20))
        if i < 3:
            lb.log_event(p, "bounced", when=date(2026, 10, 21))
        c.prospects.append(p)
    c.save()
    by = {x["id"]: x for x in sr.health(str(site), DAY)["checks"]}
    assert by["reply_rate"]["status"] == "red" and by["bounces"]["status"] == "red"


def test_report_is_assembled_from_files(site):
    _init(site)
    sr.set_fields(str(site), ["gsc_property=sc-domain:acme.example"])
    sr.pull_gsc(str(site), DAY, runner=_fake_runner(QUERY_ROWS, PAGE_ROWS, PREV_ROWS))
    sr.analyze(str(site), DAY)
    sr.log_change(str(site), url="https://acme.example/ac-repair", kind="answer", summary="Added an AC repair cost answer", day=DAY)
    _campaign(site)
    text = sr.build_report(str(site), DAY)
    assert "Verdict:" in text and "clicks 16 (+6)" in text and "Added an AC repair cost answer" in text
    assert "Needs you:" in text and "Link building:" in text
    assert "\u2014" not in text and "\u2013" not in text
    assert (site / ".seo" / "weekly" / DAY.isoformat() / "report.md").is_file()


def test_cli_mark_run_and_log_change(site):
    _init(site)
    assert sr.main(["mark-run", "--site-dir", str(site), "--routine", "weekly", "--status", "started"]) == 0
    assert sr.main(["log-change", "--site-dir", str(site), "--url", "https://acme.example/x", "--kind", "geo", "--summary", "llms.txt"]) == 0
    assert sr.main(["mark-indexed", "--site-dir", str(site), "--url", "https://acme.example/x", "--indexed", "no"]) == 0
    assert sr.load_changes(str(site))[0]["indexed"] is False
    assert "weekly: started" in (site / ".seo" / "runs.md").read_text(encoding="utf-8")


GOOD_PAGE = """<html><head><title>AC Repair in Dubai | Acme</title>
<meta name="description" content="Same-day AC repair across Dubai with upfront prices, licensed technicians and a 90-day warranty.">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":"How much is AC repair?","acceptedAnswer":{"@type":"Answer","text":"Most repairs cost between AED 150 and AED 450."}}]}</script>
</head><body><h1>AC repair in Dubai</h1></body></html>"""


def test_check_page_gate(tmp_path):
    assert sr.check_page(GOOD_PAGE)["pass"]
    bad = GOOD_PAGE.replace("</h1>", "</h1><h1>Again</h1>").replace('"text":"Most', '"txt":"Most').replace("Same-day", "Same\u2014day")
    out = sr.check_page(bad)
    assert not out["pass"] and len(out["errors"]) == 3
    broken = GOOD_PAGE.replace('{"@context"', '{"@context",')
    assert any("not valid JSON" in e for e in sr.check_page(broken)["errors"])
    f = tmp_path / "p.html"
    f.write_text(GOOD_PAGE.replace("<title>AC Repair in Dubai | Acme</title>", "<title></title>"), encoding="utf-8")
    assert sr.main(["check-page", "--file", str(f)]) == 1
    md = tmp_path / "p.md"
    md.write_text("A plain answer. TODO: add price", encoding="utf-8")
    assert sr.main(["check-page", "--file", str(md)]) == 1


def test_monthly_due_follows_completed_weekly_runs(site):
    _init(site)
    assert sr.monthly_due(str(site), date(2026, 11, 2))
    sr.mark_run(str(site), "weekly", "started", day=date(2026, 11, 2))
    assert sr.monthly_due(str(site), date(2026, 11, 2)), "a started run does not count"
    sr.mark_run(str(site), "weekly", "done", day=date(2026, 11, 2))
    assert not sr.monthly_due(str(site), date(2026, 11, 9))
    assert sr.monthly_due(str(site), date(2026, 12, 7))


def test_enrich_records_contact_without_hand_editing(site):
    import linkbuilding as lb
    _init(site)
    lb_mod, camp = _campaign(site)
    c = lb.Campaign(camp)
    c.prospects.append(lb.make_prospect("blog.example.org", source="manual", ptype="resource_page"))
    c.save()
    pid = c.prospects[0]["id"]
    lb.main(["enrich", "--campaign", camp, "--id", pid, "--name", "Ed Reed", "--email", "ed@blog.example.org",
             "--source-url", "https://blog.example.org/about", "--hook", "your list of AC tools skips anything for flats under 80 square metres",
             "--their-page", "https://blog.example.org/tools", "--asset-url", "https://acme.example/guide",
             "--asset-summary", "a cost guide built from 300 real quotes"])
    p = lb.Campaign(camp).find(pid)
    assert p["contact"]["email"] == "ed@blog.example.org" and p["personalization"]["hook"].startswith("your list")
    with pytest.raises(SystemExit):
        lb.main(["enrich", "--campaign", camp, "--id", pid, "--email", "not an email"])


def test_report_needs_you_lists_only_owner_actions_and_shipped_uses_run_date(site):
    _init(site)
    lb, camp = _campaign(site)
    sr.main(["log-change", "--site-dir", str(site), "--date", DAY.isoformat(), "--url", "https://acme.example/a",
             "--kind", "answer", "--summary", "Added the cost answer"])
    sr.main(["mark-run", "--site-dir", str(site), "--routine", "weekly", "--status", "done", "--date", DAY.isoformat()])
    text = sr.build_report(str(site), DAY)
    assert "Added the cost answer" in text
    needs = text.split("Needs you:")[1].split("Next week:")[0]
    assert "Run `site_routine.py" not in needs and "Clear overdue" not in needs
    h = {c["id"]: c for c in sr.health(str(site), DAY)["checks"]}
    assert h["schedule"]["status"] == "green"
