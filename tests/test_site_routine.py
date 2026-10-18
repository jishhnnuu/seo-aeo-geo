"""Tests for scripts/site_routine.py: per-site state, schedule specs, privacy check."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
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
        assert "—" not in p and "–" not in p
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
        assert "—" not in text and "–" not in text, f.name
        assert "send outreach" in text or f.name != "weekly.md"
