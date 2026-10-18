"""Tests for scripts/linkbuilding.py: screening, selection, approval gate, drafts, tracking."""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import linkbuilding as lb  # noqa: E402


def run(tmp_path: Path, *argv: str) -> int:
    return lb.main([*argv])


@pytest.fixture()
def camp(tmp_path: Path) -> lb.Campaign:
    d = str(tmp_path / "c")
    lb.main(["init", "--campaign", d, "--site", "https://example.com", "--name", "Example",
             "--industry", "saas", "--topics", "invoice software,accounts payable automation",
             "--sender-name", "Alex Doe", "--sender-title", "Founder"])
    return lb.Campaign(d)


def add(camp: lb.Campaign, rows: list, source="competitor_gap", ptype="resource_page", cost="free") -> None:
    new = lb.rows_to_prospects(rows, source=source, default_type=ptype, default_cost=cost)
    lb.merge_prospects(camp.prospects, new)
    camp.save()


# ---- parsing ------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("155k", 155000), ("6.1M", 6.1e6), ("7,4k", 7400), ("1,4M", 1.4e6), ("10k+", 10000),
    ("868K (Semrush)", 868000), ("36900K", 36900000), ("85+", 85), ("483", 483), ("1.9 Million (Semrush)", 1.9e6),
    ("10$", None), ("$62.00", None), ("$500", None), ("", None), (None, None),
])
def test_parse_metric_handles_vendor_sheet_formats(raw, expected):
    got = lb.parse_metric(raw)
    assert (got is None) if expected is None else got == pytest.approx(expected)


@pytest.mark.parametrize("raw,expected", [
    ("https:/theglobeandmail.com", "theglobeandmail.com"),
    ("idiva.com 1 DF", "idiva.com"),
    ("https://www.Techimply.com/blog", "techimply.com"),
    ("  http://newskarnataka.com/ ", "newskarnataka.com"),
    ("www.decaturdaily.com", "decaturdaily.com"),
])
def test_normalize_domain(raw, expected):
    assert lb.normalize_domain(raw) == expected


# ---- screening ----------------------------------------------------------------------

def test_vendor_sheet_junk_is_rejected_and_legit_prospect_survives(camp):
    add(camp, [
        {"domain": "spankbangs.org", "dr": "54", "traffic": "45.1k", "notes": "Instant"},
        {"domain": "mit.edu.co.bz", "dr": "66", "da": "59"},
        {"domain": "kuttymoviess.com.in", "dr": "80", "da": "71"},
        {"domain": "bestcasinoreviews.example", "dr": "40", "da": "40", "notes": "online casino guest post"},
        {"domain": "cheapbacklinks.example", "dr": "50", "da": "50", "notes": "2 dofollow links, instant publish, TAT 24 hours"},
        {"domain": "trusted-accounting-blog.example", "dr": "52", "da": "50", "traffic": "40k",
         "relevance": "0.9", "email": "ed@trusted-accounting-blog.example", "contact_name": "Ed Reed"},
    ], source="vendor_sheet")
    lb.screen_all(camp)
    by = {p["domain"]: p for p in camp.prospects}
    assert by["spankbangs.org"]["excluded"]
    assert by["mit.edu.co.bz"]["excluded"] and any("fake .edu" in r for r in by["mit.edu.co.bz"]["exclude_reasons"])
    assert by["kuttymoviess.com.in"]["excluded"]
    assert by["bestcasinoreviews.example"]["excluded"]
    assert by["cheapbacklinks.example"]["excluded"]
    assert any("link-seller" in r for r in by["cheapbacklinks.example"]["exclude_reasons"])
    assert not by["trusted-accounting-blog.example"]["excluded"]


def test_seller_listed_publisher_is_demoted_to_paid_not_excluded(camp):
    add(camp, [{"domain": "ocnjdaily.com", "dr": "67", "da": "47", "traffic": "16.7k", "relevance": "0.6"}], source="vendor_sheet")
    lb.screen_all(camp)
    p = camp.prospects[0]
    assert not p["excluded"]
    assert p["cost"] == "paid"
    assert any(f.startswith("seller_listed") for f in p["flags"])
    assert any(f.startswith("metrics_unverified") for f in p["flags"])


def test_cloned_metrics_are_flagged(camp):
    add(camp, [{"domain": f"site{i}-example.com", "dr": "80", "da": "71", "relevance": "0.7"} for i in range(4)], source="vendor_sheet")
    lb.screen_all(camp)
    assert all(any(f.startswith("cloned_metrics") for f in p["flags"]) for p in camp.prospects)


def test_high_authority_without_traffic_and_mismatch_are_flagged(camp):
    add(camp, [{"domain": "ghost-authority.example", "dr": "81", "da": "7", "traffic": "50", "relevance": "0.8"}])
    lb.screen_all(camp)
    flags = " ".join(camp.prospects[0]["flags"])
    assert "authority_without_traffic" in flags and "metric_mismatch" in flags


def test_high_spam_score_excludes(camp):
    add(camp, [{"domain": "risky.example", "dr": "50", "spam_score": "34", "relevance": "0.9"}])
    lb.screen_all(camp)
    assert camp.prospects[0]["excluded"]


def test_not_live_is_excluded(camp):
    add(camp, [{"domain": "dead.example", "dr": "50", "relevance": "0.9"}])
    camp.prospects[0]["verified_live"] = False
    lb.screen_all(camp)
    assert camp.prospects[0]["excluded"]


def test_library_has_no_false_positives_for_any_industry(camp):
    for industry in ("saas", "ecommerce", "local_service", "agency", "healthcare", "legal", "home_services", "real_estate", "hospitality", "nonprofit"):
        ps = lb.library_prospects(industry, "US", ["open_source", "browser_extension"])
        c = lb.Campaign(camp.dir)
        c.config["industry"] = industry
        c.prospects = ps
        lb.screen_all(c)
        bad = [(p["domain"], p["exclude_reasons"]) for p in c.prospects if p["excluded"]]
        assert not bad, (industry, bad)


def test_library_integrity():
    lib = lb.load_library()
    ids = [s["id"] for s in lib["sources"]]
    assert len(ids) == len(set(ids))
    bl = lb.load_blocklist()
    for s in lib["sources"]:
        assert s["type"] in lib["types"], s["id"]
        assert s["cost"] in ("free", "free_tier", "paid"), s["id"]
        assert lb.normalize_domain(s["domain"]) == s["domain"], s["id"]
        assert s["domain"] not in bl["_domains"], s["id"]
        flat = json.dumps(s, ensure_ascii=False)
        assert "\u2014" not in flat and "\u2013" not in flat, s["id"]
    for t in lib["types"].values():
        lo, hi = t["success_range"]
        assert 0 <= lo <= hi <= 1


def test_region_locked_and_capability_gated_sources_are_gated():
    plain = {p["domain"] for p in lb.library_prospects("saas", None, [])}
    assert "yellowpages.com" not in plain and "chromewebstore.google.com" not in plain and "github.com" not in plain
    gated = {p["domain"] for p in lb.library_prospects("saas", "US", ["browser_extension", "open_source"])}
    assert "chromewebstore.google.com" in gated and "github.com" in gated


# ---- scoring and selection ------------------------------------------------------------

def test_nofollow_sources_score_below_equivalent_followed_ones(camp):
    add(camp, [{"domain": "followed.example", "dr": "60", "traffic": "50k", "relevance": "0.8", "email": "a@followed.example"}])
    add(camp, [{"domain": "nofollowed.example", "dr": "60", "traffic": "50k", "relevance": "0.8", "email": "a@nofollowed.example"}])
    camp.prospects[1]["rel_expected"] = "nofollow"
    lb.screen_all(camp)
    assert camp.prospects[0]["score"] > camp.prospects[1]["score"]


def test_selection_respects_mix_dedupes_and_never_pads(camp):
    rows = [{"domain": f"free{i}.example", "dr": "55", "traffic": "20k", "relevance": "0.9", "email": f"a@free{i}.example"} for i in range(8)]
    add(camp, rows, ptype="resource_page", cost="free")
    add(camp, [{"domain": f"paid{i}.example", "dr": "60", "traffic": "30k", "relevance": "0.9"} for i in range(8)],
        ptype="sponsored_placement", cost="paid")
    add(camp, [{"domain": "free0.example", "dr": "99", "relevance": "1"}], ptype="digital_pr")  # duplicate domain, other type
    add(camp, [{"domain": "weak.example", "dr": "5", "traffic": "10", "relevance": "0.05"}])
    lb.screen_all(camp)
    res = lb.select_shortlist(camp, count=20, free_ratio=0.7, max_type_ratio=1.0)
    chosen = [p for p in camp.prospects if p["status"] == "proposed"]
    assert len({p["domain"] for p in chosen}) == len(chosen), "duplicate domain selected"
    assert "weak.example" not in {p["domain"] for p in chosen}
    assert res["selected"] < 20 and res["shortfall"] == 20 - res["selected"]
    assert res["paid"] <= int(20 * 0.4)
    assert res["expected_links_low"] <= res["expected_links_high"]


def test_type_cap_prevents_one_tactic_dominating(camp):
    add(camp, [{"domain": f"dir{i}.example", "dr": "60", "traffic": "20k", "relevance": "0.9"} for i in range(30)], ptype="directory_listing")
    add(camp, [{"domain": f"res{i}.example", "dr": "55", "traffic": "20k", "relevance": "0.8", "email": f"a@res{i}.example"} for i in range(30)], ptype="resource_page")
    lb.screen_all(camp)
    res = lb.select_shortlist(camp, count=20, max_type_ratio=0.5)
    assert max(res["by_type"].values()) <= 10


# ---- approval gate, drafts, export ------------------------------------------------------

def _resource_prospect(camp, **pers):
    base = {"their_page_url": "https://blog.example.org/ap-tools", "hook": "your list of accounts payable tools skips anything for businesses under ten staff",
            "asset_url": "https://example.com/ap-benchmark", "asset_summary": "a benchmark of invoice approval times across 400 small firms"}
    base.update(pers)
    add(camp, [{"domain": "blog.example.org", "dr": "55", "traffic": "30k", "relevance": "0.9", "email": "ed@blog.example.org", "contact_name": "Ed Reed"}])
    camp.prospects[0]["personalization"] = {k: v for k, v in base.items() if v is not None}
    camp.save()
    return camp.prospects[0]


def test_unapproved_prospects_are_never_drafted(camp):
    _resource_prospect(camp)
    lb.screen_all(camp)
    lb.select_shortlist(camp, count=5)
    camp.save()
    lb.main(["draft", "--campaign", camp.dir])
    c = lb.Campaign(camp.dir)
    assert c.prospects[0]["status"] == "proposed" and not c.prospects[0].get("draft")


def test_approved_complete_prospect_gets_clean_draft_and_export(camp, tmp_path):
    _resource_prospect(camp)
    lb.screen_all(camp)
    lb.select_shortlist(camp, count=5)
    camp.save()
    lb.main(["approve", "--campaign", camp.dir, "--all-proposed"])
    lb.main(["draft", "--campaign", camp.dir])
    c = lb.Campaign(camp.dir)
    p = c.prospects[0]
    assert p["status"] == "drafted"
    d = p["draft"]
    for field in ("subject", "body", "followup_1", "followup_2"):
        assert "\u2014" not in d[field] and "\u2013" not in d[field]
    assert len(d["subject"]) <= 60 and d["word_count"] <= 130
    assert "no thanks" in d["body"]
    assert "Hi Ed," in d["body"]
    out = tmp_path / "out.csv"
    lb.main(["export", "--campaign", camp.dir, "--out", str(out)])
    rows = list(csv.DictReader(open(out, encoding="utf-8")))
    assert len(rows) == 1 and rows[0]["to_email"] == "ed@blog.example.org"


@pytest.mark.parametrize("override,needle", [
    ({"hook": "I love your content"}, "generic"),
    ({"hook": "great article, really enjoyed reading it and learning from your whole site"}, "generic"),
    ({"hook": None}, "personalization.hook"),
    ({"asset_url": None}, "personalization.asset_url"),
])
def test_generic_or_missing_personalization_blocks_the_draft(camp, override, needle):
    _resource_prospect(camp, **override)
    lb.screen_all(camp)
    lb.select_shortlist(camp, count=5)
    camp.save()
    lb.main(["approve", "--campaign", camp.dir, "--all-proposed"])
    c = lb.Campaign(camp.dir)
    assert any(needle in m for m in lb.missing_fields(c.prospects[0], c))
    lb.main(["draft", "--campaign", camp.dir])
    assert lb.Campaign(camp.dir).prospects[0]["status"] == "approved"


def test_missing_contact_or_sender_blocks_the_draft(camp):
    p = _resource_prospect(camp)
    p["contact"] = {}
    camp.config["sender_name"] = ""
    miss = lb.missing_fields(p, camp)
    assert any("contact.email" in m for m in miss) and any("sender_name" in m for m in miss)


def test_self_serve_listing_gets_kit_not_email(camp):
    lb.merge_prospects(camp.prospects, lb.library_prospects("saas", "US"))
    camp.config["profile"] = {"tagline": "Invoices, handled."}
    camp.save()
    lb.screen_all(camp)
    lb.select_shortlist(camp, count=50)
    camp.save()
    lb.main(["approve", "--campaign", camp.dir, "--ids", "lib-g2"])
    lb.main(["kit", "--campaign", camp.dir])
    kit = Path(camp.dir, "submission-kit.md").read_text(encoding="utf-8")
    assert "### G2" in kit and "MISSING" in kit
    assert lb.render_draft(lb.Campaign(camp.dir).find("lib-g2"), lb.Campaign(camp.dir)).get("error")


def test_cannot_approve_an_excluded_prospect(camp):
    add(camp, [{"domain": "spankbangs.org", "relevance": "1"}])
    lb.screen_all(camp)
    camp.prospects[0]["status"] = "proposed"
    camp.save()
    lb.main(["approve", "--campaign", camp.dir, "--ids", camp.prospects[0]["id"]])
    assert lb.Campaign(camp.dir).prospects[0]["status"] == "proposed"


# ---- tracking ------------------------------------------------------------------------

def test_followup_schedule_and_closure(camp):
    p = _resource_prospect(camp)
    day0 = date(2026, 11, 2)
    lb.log_event(p, "sent", when=day0)
    assert not lb.due_items(camp, day0 + timedelta(days=5))
    assert lb.due_items(camp, day0 + timedelta(days=6))[0]["action"].startswith("send follow-up 1")
    lb.log_event(p, "followup_1", when=day0 + timedelta(days=6))
    assert not lb.due_items(camp, day0 + timedelta(days=13))
    assert lb.due_items(camp, day0 + timedelta(days=14))[0]["action"].startswith("send follow-up 2")
    lb.log_event(p, "followup_2", when=day0 + timedelta(days=14))
    assert lb.due_items(camp, day0 + timedelta(days=21))[0]["action"].startswith("close")


def test_declining_suppresses_domain_and_contact(camp):
    p = _resource_prospect(camp)
    lb.main(["log", "--campaign", camp.dir, "--id", p["id"], "--event", "declined"])
    c = lb.Campaign(camp.dir)
    assert "blog.example.org" in c.suppressed() and "ed@blog.example.org" in c.suppressed()
    lb.screen_all(c)
    assert c.prospects[0]["excluded"]


def test_won_links_are_verified_on_schedule_and_loss_is_recorded(camp):
    p = _resource_prospect(camp)
    day0 = date(2026, 11, 2)
    lb.log_event(p, "won", when=day0, link_url="https://blog.example.org/ap-tools")
    assert not lb.due_items(camp, day0 + timedelta(days=29))
    assert lb.due_items(camp, day0 + timedelta(days=30))[0]["action"].startswith("verify")

    calls = []

    def fake(target, links):
        calls.append((target, links))
        return {"data": {"results": [{"status": "verified", "rel_attributes": ["follow"]}]}}

    out = lb.verify_won(camp, day0 + timedelta(days=30), True, verifier=fake)
    assert out[0]["status"] == "verified" and out[0]["check"] == "day30" and calls
    assert not lb.due_items(camp, day0 + timedelta(days=31))
    assert lb.due_items(camp, day0 + timedelta(days=90))[0]["action"].endswith("(day90 check)")

    lost = lb.verify_won(camp, day0 + timedelta(days=90), True,
                         verifier=lambda t, l: {"data": {"results": [{"status": "link_removed"}]}})
    assert lost[0]["status"] == "link_removed" and camp.prospects[0]["status"] == "lost"


def test_funnel_rates(camp):
    p = _resource_prospect(camp)
    lb.log_event(p, "sent", when=date(2026, 11, 2))
    lb.log_event(p, "replied", when=date(2026, 11, 3))
    lb.log_event(p, "won", when=date(2026, 11, 4), link_url="https://x.example/p")
    f = lb.funnel(camp)
    assert f["contacted"] == 1 and f["reply_rate"] == 1.0 and f["win_rate"] == 1.0


# ---- liveness, readiness, report data -----------------------------------------------------

def test_check_live_classification():
    ok_body = "<html>" + "real content " * 40 + "</html>"
    assert lb.check_live_one("https://a.example", lambda u: (200, ok_body))["live"] is True
    assert lb.check_live_one("https://a.example", lambda u: (404, ""))["live"] is False
    assert lb.check_live_one("https://a.example", lambda u: (200, "<html>This domain is for sale " + "x" * 300))["live"] is False
    assert lb.check_live_one("https://a.example", lambda u: (_ for _ in ()).throw(OSError("dns")))["live"] is False


READY_HTML = """<html><head><title>Example invoice software for small teams</title>
<link rel="canonical" href="https://example.com/"><meta name="viewport" content="width=device-width">
<script type="application/ld+json">{"@type":"Organization","name":"Example","sameAs":["https://www.linkedin.com/company/example"]}</script></head>
<body><nav><a href="/about">About us</a><a href="/contact">Contact</a><a href="/blog">Blog</a><a href="/tools/ap-calculator">Free AP calculator</a>
<a href="/privacy">Privacy</a></nav><p>By Jane Smith, reviewed by Sam Lee</p></body></html>"""

BARE_HTML = "<html><head><title>Home</title></head><body><a href='/pricing'>Pricing</a></body></html>"


def test_readiness_distinguishes_ready_from_bare_site():
    good = lb.assess_readiness(READY_HTML, "https://example.com/", "saas")
    bad = lb.assess_readiness(BARE_HTML, "http://example.com/", "saas")
    assert good["verdict"] == "ready" and good["score"] >= 80
    assert bad["verdict"] == "fix_first" and bad["score"] < 40
    assert any("asset" in p.lower() or "reason to link" in p.lower() for p in bad["priorities"])
    assert bad["asset_ideas"]


def test_local_industry_adds_nap_check():
    out = lb.assess_readiness(BARE_HTML, "https://x.com/", "local_service")
    assert any(c["id"] == "nap" for c in out["checks"])


def test_report_data_shape(camp):
    _resource_prospect(camp)
    lb.merge_prospects(camp.prospects, lb.library_prospects("saas", "US"))
    add(camp, [{"domain": "spankbangs.org"}])
    lb.screen_all(camp)
    lb.select_shortlist(camp, count=100)
    camp.save()
    data = lb.build_report_data(lb.Campaign(camp.dir))["linkbuilding"]
    s = data["summary"]
    assert s["shortlist"] == s["free"] + s["paid"] and s["rejected_by_screening"] >= 1
    assert data["free_prospects"] and data["rejection_breakdown"]
    assert s["expected_links_low"] <= s["expected_links_high"]
    json.dumps(data)


def test_overlong_draft_is_blocked(camp):
    _resource_prospect(camp, asset_summary="a benchmark " + "of invoice approval times across many small firms " * 12)
    lb.screen_all(camp)
    lb.select_shortlist(camp, count=5)
    camp.save()
    lb.main(["approve", "--campaign", camp.dir, "--all-proposed"])
    lb.main(["draft", "--campaign", camp.dir])
    p = lb.Campaign(camp.dir).prospects[0]
    assert p["status"] == "approved" and not p.get("draft")


@pytest.mark.parametrize("domain", ["canvas.ubc.ca", "canvas.hms.harvard.edu", "mycourses.usnh.edu"])
def test_learning_system_subdomains_are_flagged_as_user_content(camp, domain):
    add(camp, [{"domain": domain, "dr": "90", "da": "90", "traffic": "2M", "relevance": "0.5"}], source="vendor_sheet")
    lb.screen_all(camp)
    assert any(f.startswith("edu_user_content_subdomain") for f in camp.prospects[0]["flags"])


# ---- six-month program ------------------------------------------------------------------

@pytest.mark.parametrize("industry,track", [("saas", "saas_b2b"), ("local_service", "local"), ("ecommerce", "ecommerce"),
                                            ("nonprofit", "content"), ("unknown-thing", "content")])
def test_program_track_and_shape(camp, industry, track):
    camp.config["industry"] = industry
    prog = lb.build_program(camp, date(2026, 10, 19))
    assert prog["track"] == track and prog["weeks"] == 26
    assert prog["end"] == "2027-04-19"
    weeks = {t["week"] for t in prog["tasks"]}
    assert weeks == set(range(1, 27)), "every week has work"
    assert {t["owner"] for t in prog["tasks"]} == {"claude", "you", "client"}
    assert len({t["id"] for t in prog["tasks"]}) == len(prog["tasks"])
    assert 0 < prog["expected_links_low"] < prog["expected_links_high"]
    assert all("{" not in t["detail"] for t in prog["tasks"])
    assert any(t["title"] == "Six-month report and next plan" and t["week"] == 26 for t in prog["tasks"])
    batch = next(t for t in prog["tasks"] if t["title"] == "Weekly outreach batch")
    assert str(prog["pitches_per_week"]) in batch["detail"]


def test_program_ymyl_and_track_specific_tasks(camp):
    camp.config["industry"] = "healthcare"
    titles = {t["title"] for t in lb.build_program(camp, date(2026, 10, 19))["tasks"]}
    assert "Credentials review" in titles and "Local citations" in titles and "Software and review listings" not in titles
    camp.config["industry"] = "saas"
    titles = {t["title"] for t in lb.build_program(camp, date(2026, 10, 19))["tasks"]}
    assert "Credentials review" not in titles and "Integration and partner pages" in titles


def test_program_cli_week_and_done(camp):
    lb.main(["program", "--campaign", camp.dir, "--start", "2026-10-19"])
    prog = json.loads(Path(camp.dir, "program.json").read_text(encoding="utf-8"))
    assert Path(camp.dir, "program.md").read_text(encoding="utf-8").startswith("# Six-month link building program")
    wv = lb.week_view(prog, date(2026, 11, 3))
    assert wv["week"] == 3 and wv["tasks"] and len(wv["overdue"]) > 0
    first = [t["id"] for t in prog["tasks"] if t["week"] == 1]
    lb.main(["done", "--campaign", camp.dir, "--ids", ",".join(first)])
    prog = json.loads(Path(camp.dir, "program.json").read_text(encoding="utf-8"))
    assert all(t["done"] for t in prog["tasks"] if t["week"] == 1)
    assert lb.week_view(prog, date(2026, 10, 26))["overdue"] == []
    with pytest.raises(SystemExit):
        lb.main(["program", "--campaign", camp.dir])
    summary = lb.build_report_data(lb.Campaign(camp.dir))["linkbuilding"]["program"]
    assert summary["tasks_done"] == len(first) and summary["track"] == "saas_b2b"


# ---- fast start and scorecard ------------------------------------------------------------

def _ready(camp):
    camp.config["readiness"] = {"verdict": "ready", "score": 90}


def test_auto_mode_needs_a_passing_readiness_check(camp):
    assert lb.program_mode(camp)[0] == "standard"
    _ready(camp)
    assert lb.program_mode(camp)[0] == "fast"
    assert lb.program_mode(camp, "standard")[0] == "standard"


def test_fast_start_moves_outreach_earlier_and_keeps_calendar_tasks(camp):
    std = lb.build_program(camp, date(2026, 10, 19), "standard")
    _ready(camp)
    fast = lb.build_program(camp, date(2026, 10, 19))
    first = lambda prog, title: min(t["week"] for t in prog["tasks"] if t["title"] == title)
    assert fast["mode"] == "fast"
    assert first(fast, "Weekly outreach batch") == 2 < first(std, "Weekly outreach batch")
    assert first(fast, "Digital PR wave 1") < first(std, "Digital PR wave 1")
    assert first(fast, "Monthly results check") == first(std, "Monthly results check") == 5
    assert {t["week"] for t in fast["tasks"]} == set(range(1, 27))
    assert any(t["title"] == "Build linkable asset 3" and t["week"] >= 23 for t in fast["tasks"])
    assert any(t["title"] == "Six-month report and next plan" and t["week"] == 26 for t in fast["tasks"])
    assert len({(t["week"], t["title"]) for t in fast["tasks"]}) == len(fast["tasks"]), "no duplicate tasks in a week"


def test_existing_asset_skips_building_asset_one(camp):
    _ready(camp)
    prog = lb.build_program(camp, date(2026, 10, 19), existing_asset="https://example.com/calculator")
    titles = [t["title"] for t in prog["tasks"]]
    assert "Build linkable asset 1" not in titles and "Publish asset 1" not in titles
    wave = next(t for t in prog["tasks"] if t["title"] == "Digital PR wave 1")
    assert wave["week"] == 2 and "https://example.com/calculator" in wave["detail"]


def test_scorecard_month_on_month_and_checks(camp):
    lb.main(["baseline", "--campaign", camp.dir, "branded_owned_page1=3", "target_impressions_28d=1200",
             "referring_domains=14", "map_pack_rank=9"])
    c = lb.Campaign(camp.dir)
    p = _resource_prospect(c)
    lb.log_event(p, "sent", when=date(2026, 11, 2))
    lb.log_event(p, "replied", when=date(2026, 11, 4))
    lb.log_event(p, "won", when=date(2026, 11, 6), link_url="https://blog.example.org/ap-tools")
    c.save()
    lb.main(["snapshot", "--campaign", camp.dir, "--month", "1", "branded_owned_page1=6", "target_impressions_28d=1150", "map_pack_rank=6"])
    sc = lb.build_scorecard(lb.Campaign(camp.dir))
    rows = {r["metric"]: r for r in sc["rows"]}
    assert rows["branded_owned_page1"]["change"] == 3 and rows["branded_owned_page1"]["improved"]
    assert rows["map_pack_rank"]["improved"], "lower map rank is better"
    checks = {x["metric"]: x for x in sc["checks"]}
    assert set(checks) == {"links_live", "reply_rate", "branded_owned_page1"}, "only month-1 checks are due"
    assert checks["links_live"]["status"] == "fail" and checks["links_live"]["action"]
    assert checks["reply_rate"]["status"] == "pass" and checks["branded_owned_page1"]["status"] == "pass"
    assert sc["verdict"] == "needs_action"
    lb.main(["snapshot", "--campaign", camp.dir, "--month", "2", "target_impressions_28d=1500"])
    sc = lb.build_scorecard(lb.Campaign(camp.dir))
    assert sc["months"] == [1, 2]
    assert next(x for x in sc["checks"] if x["metric"] == "target_impressions_28d")["status"] == "pass"
    assert lb.build_report_data(lb.Campaign(camp.dir))["linkbuilding"]["scorecard"]["rows"]


def test_snapshot_rejects_unknown_metric_and_non_numbers(camp):
    with pytest.raises(SystemExit):
        lb.main(["snapshot", "--campaign", camp.dir, "--month", "1", "made_up_metric=4"])
    with pytest.raises(SystemExit):
        lb.main(["snapshot", "--campaign", camp.dir, "--month", "1", "gsc_clicks_28d=lots"])


def test_data_lives_in_the_skill_folder():
    assert Path(lb.DATA_DIR).parts[-2:] == ("seo-linkbuilding", "data")
    assert Path(lb.DATA_DIR, "library.json").is_file()
