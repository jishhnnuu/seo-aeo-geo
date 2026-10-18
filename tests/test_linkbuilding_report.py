"""Link-building section of google_report.py."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import google_report  # noqa: E402
import linkbuilding as lb  # noqa: E402


def _data(name: str = "Acme") -> dict:
    row = {"id": "x", "name": name, "domain": "acme-blog.example", "type": "resource_page", "cost": "free", "score": 71.2,
           "tier": "A", "rel_expected": "follow", "purpose": "link", "dr": 55, "da": 50, "traffic": 30000,
           "metrics_source": "vendor-claimed", "status": "proposed", "notes": "Resources page", "flags": ["metrics_unverified: x"]}
    paid = dict(row, id="y", name="Paper", domain="paper.example", type="sponsored_placement", cost="paid", rel_expected="sponsored", tier="B")
    return {"linkbuilding": {
        "site": "https://example.com", "name": "Example", "industry": "saas", "topics": [],
        "summary": {"candidates_reviewed": 10, "rejected_by_screening": 4, "shortlist": 2, "free": 1, "paid": 1,
                    "tier_a": 1, "tier_b": 1, "tier_c": 0, "expected_links_low": 0, "expected_links_high": 1},
        "rejection_breakdown": {"gambling": 2, "blocklisted": 2},
        "by_type": [{"type": "resource_page", "label": "Resource or curated-list page", "count": 1, "success_range": [0.05, 0.15]}],
        "free_prospects": [row], "paid_prospects": [paid],
        "readiness": {"score": 55, "verdict": "fix_first", "checks": [{"id": "a", "pass": False, "level": "fail", "label": "L", "fix": "F"}],
                      "asset_ideas": ["Idea"]},
        "baseline": {"referring_domains": 14, "captured": "x"}, "funnel": {"contacted": 0}, "profile_gaps": ["tagline"],
        "program": {"track": "saas_b2b", "week": 3, "weeks": 26, "tasks_done": 9, "tasks_total": 115, "overdue": 2,
                    "expected_links_low": 37, "expected_links_high": 105},
    }}


def _render(tmp_path: Path, rtype: str, data: dict) -> str:
    with patch.object(google_report, "HTML", None):
        res = google_report.generate_report(rtype, data, "example.com", tmp_path, "html")
    assert not res.get("error"), res
    return Path(res["files"][0]).read_text(encoding="utf-8")


def test_standalone_report_has_all_sections_and_no_dash_punctuation(tmp_path):
    html = _render(tmp_path, "link-building", _data())
    for title in ("Executive Summary", "Site Readiness", "Prospect Strategy", "Free Prospects", "Paid Prospects",
                  "Outreach Plan", "Measurement"):
        assert title in html
    assert "Shortlist is below 100" in html
    assert "week 3 of 26" in html and "2 overdue" in html
    body = html.split("</style>", 1)[1]
    assert "\u2014" not in body and "\u2013" not in body


def test_prospect_content_is_html_escaped(tmp_path):
    html = _render(tmp_path, "link-building", _data(name="<script>alert(1)</script>"))
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_full_report_embeds_link_building_after_audit_sections(tmp_path):
    data = _data()
    data["summary"] = {"health_score": 70}
    html = _render(tmp_path, "full", data)
    assert "Link Building: Executive Summary" in html and "Executive Summary" in html


def test_end_to_end_from_campaign_to_report(tmp_path):
    d = str(tmp_path / "c")
    lb.main(["init", "--campaign", d, "--site", "https://example.com", "--name", "Example", "--industry", "saas"])
    lb.main(["library", "--campaign", d])
    lb.main(["screen", "--campaign", d])
    lb.main(["select", "--campaign", d])
    lb.main(["report-data", "--campaign", d])
    import json
    data = json.loads(Path(d, "report-data.json").read_text(encoding="utf-8"))
    html = _render(tmp_path, "link-building", data)
    assert "G2" in html and "Free Prospects" in html
