#!/usr/bin/env python3
"""
Live voice-search-eligibility checker.

Honesty note up front: there is no public API — free or paid — that lets
a third-party script ask "Hey Google" or "Alexa" a question and read back
what the assistant actually said. Amazon and Google do not expose that
surface to developers; the only way to observe it is a physical device or
an emulator, which cannot be scripted into an SEO audit. This script does
NOT claim to solve that. What it does instead: voice assistants overwhelmingly
answer factual questions by reading Google's featured snippet / answer box
for that query, so live-checking featured-snippet eligibility is the closest
honest, scriptable proxy for voice-answer eligibility that exists.

Uses Google's Programmable Search Engine JSON API (a genuinely free tier —
100 queries/day, no card required: programmablesearchengine.google.com then
enable the JSON API at console.cloud.google.com/apis/library/customsearch.googleapis.com).

This is a live, real-time web check — not a static heuristic — but it is a
proxy, not ground truth. Pair it with skills/seo-geo/references
voice-search-optimization.md for the structural checklist (question-based
headings, concise direct answers, schema) that makes a page eligible in the
first place.

Usage:
    python3 voice_search_live_check.py check "acme.com" "how do I reset a crm password" [--json]
    python3 voice_search_live_check.py history "acme.com" [--limit 20] [--json]

Storage: ~/.cache/claude-seo/voice-search/checks.db (SQLite)
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

try:
    from url_safety import validate_url_strict, safe_requests_session, URLSafetyError  # noqa: E402
except ImportError as _import_exc:
    raise RuntimeError(
        "scripts/url_safety.py is required for SSRF protection. "
        "Install with: pip install -r requirements.txt"
    ) from _import_exc

DB_DIR = os.path.expanduser("~/.cache/claude-seo/voice-search")
DB_PATH = os.path.join(DB_DIR, "checks.db")

CSE_URL = "https://www.googleapis.com/customsearch/v1"


def _domain_of(brand_or_domain: str) -> str:
    value = brand_or_domain.strip().lower()
    if "://" in value:
        value = urlparse(value).hostname or value
    return value.removeprefix("www.")


def query_featured_snippet(brand_or_domain: str, query: str) -> dict:
    """
    Query Google's Programmable Search Engine for `query` and check whether
    the target domain holds position 1 (the slot voice assistants read from
    most often) or appears in the top 3.
    """
    api_key = os.environ.get("GOOGLE_CSE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        return {
            "provider": "google_cse",
            "ran": False,
            "reason": (
                "GOOGLE_CSE_API_KEY and/or GOOGLE_CSE_ID not set. Free setup: "
                "create a search engine at programmablesearchengine.google.com "
                "(set it to search the whole web), then enable the JSON API and "
                "get a key at console.cloud.google.com/apis/library/customsearch.googleapis.com "
                "(100 free queries/day)."
            ),
        }

    domain = _domain_of(brand_or_domain)

    try:
        validate_url_strict(CSE_URL)
        with safe_requests_session(CSE_URL) as session:
            response = session.get(
                CSE_URL,
                params={"key": api_key, "cx": cse_id, "q": query, "num": 10},
                timeout=30,
            )
    except URLSafetyError as exc:
        return {"provider": "google_cse", "ran": False, "reason": f"URL safety check failed: {exc}"}
    except Exception as exc:  # requests.RequestException, but avoid importing requests just for the type
        return {"provider": "google_cse", "ran": False, "reason": f"Request failed: {exc}"}

    if response.status_code != 200:
        return {
            "provider": "google_cse",
            "ran": False,
            "reason": f"HTTP {response.status_code}: {response.text[:300]}",
        }

    data = response.json()
    items = data.get("items", []) or []
    ranked_domains = [_domain_of(item.get("link", "")) for item in items]

    position = None
    for idx, d in enumerate(ranked_domains, start=1):
        if d == domain:
            position = idx
            break

    return {
        "provider": "google_cse",
        "ran": True,
        "position": position,
        "holds_position_1": position == 1,
        "in_top_3": position is not None and position <= 3,
        "top_3_domains": ranked_domains[:3],
        "voice_eligibility_note": (
            "Voice assistants read from position 1 / the answer box far more often "
            "than lower ranks; this is a live rank check as a proxy, not a guarantee "
            "the assistant reads this exact result aloud."
        ),
    }


def init_db() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS voice_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_or_domain TEXT NOT NULL,
            query TEXT NOT NULL,
            ran INTEGER NOT NULL,
            position INTEGER,
            holds_position_1 INTEGER,
            in_top_3 INTEGER,
            result_json TEXT NOT NULL,
            checked_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_voice_brand ON voice_checks(brand_or_domain, checked_at)")
    conn.commit()
    return conn


def store_result(conn: sqlite3.Connection, brand_or_domain: str, query: str, result: dict) -> None:
    conn.execute(
        """
        INSERT INTO voice_checks
            (brand_or_domain, query, ran, position, holds_position_1, in_top_3, result_json, checked_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            brand_or_domain,
            query,
            1 if result.get("ran") else 0,
            result.get("position"),
            1 if result.get("holds_position_1") else 0 if result.get("ran") else None,
            1 if result.get("in_top_3") else 0 if result.get("ran") else None,
            json.dumps(result),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()


def cmd_check(brand_or_domain: str, query: str) -> dict:
    conn = init_db()
    result = query_featured_snippet(brand_or_domain, query)
    store_result(conn, brand_or_domain, query, result)
    conn.close()
    return {
        "brand_or_domain": brand_or_domain,
        "query": query,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }


def cmd_history(brand_or_domain: str, limit: int) -> dict:
    if not os.path.exists(DB_PATH):
        return {"brand_or_domain": brand_or_domain, "checks": [], "note": "No database found. Run `check` first."}
    conn = init_db()
    rows = conn.execute(
        """
        SELECT query, ran, position, holds_position_1, in_top_3, checked_at
        FROM voice_checks WHERE brand_or_domain = ? ORDER BY checked_at DESC LIMIT ?
        """,
        (brand_or_domain, limit),
    ).fetchall()
    conn.close()
    checks = [
        {
            "query": r[0],
            "ran": bool(r[1]),
            "position": r[2],
            "holds_position_1": bool(r[3]) if r[3] is not None else None,
            "in_top_3": bool(r[4]) if r[4] is not None else None,
            "checked_at": r[5],
        }
        for r in rows
    ]
    return {"brand_or_domain": brand_or_domain, "checks": checks, "checks_returned": len(checks)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Live-check featured-snippet position as a voice-answer proxy.")
    p_check.add_argument("brand_or_domain")
    p_check.add_argument("query")
    p_check.add_argument("--json", action="store_true")

    p_hist = sub.add_parser("history", help="Show stored voice-eligibility check history.")
    p_hist.add_argument("brand_or_domain")
    p_hist.add_argument("--limit", type=int, default=20)
    p_hist.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.command == "check":
        result = cmd_check(args.brand_or_domain, args.query)
    else:
        result = cmd_history(args.brand_or_domain, args.limit)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
