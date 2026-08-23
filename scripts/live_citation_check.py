#!/usr/bin/env python3
"""
Live AI-citation checker — actually queries AI platforms instead of
inferring visibility from structural proxies (robots.txt, schema, brand
mentions elsewhere on the web).

Every other GEO signal in this plugin (geo_content_score.py,
check_ai_crawler_access.py, the seo-geo SKILL.md criteria) measures
whether a page is *citable*. None of them ask an AI platform a real
question and check whether the brand/domain actually got cited. This
script closes that gap for the one platform with a genuinely free,
ToS-compliant API: Google's Gemini API with Google Search grounding
(aistudio.google.com — free tier, no card required, rate-limited).

Other platforms (OpenAI, Anthropic, Perplexity) have no free API tier —
querying them costs money and needs a paid key. Scraping their consumer
chat UIs to avoid paying would mean impersonating a browser against
their bot detection and violating their Terms of Service; this script
does not do that. Instead it is written provider-pluggable: set
OPENAI_API_KEY / ANTHROPIC_API_KEY / PERPLEXITY_API_KEY later and this
script picks them up with no code changes. Until then it runs
Gemini-only and says so explicitly in its output.

Usage:
    python3 live_citation_check.py check "acme.com" "best crm for small business" [--json]
    python3 live_citation_check.py history "acme.com" [--limit 20] [--json]

Storage: ~/.cache/claude-seo/geo-citations/citations.db (SQLite)
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

DB_DIR = os.path.expanduser("~/.cache/claude-seo/geo-citations")
DB_PATH = os.path.join(DB_DIR, "citations.db")

GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

# Provider registry. Each entry names the env var that gates it and a
# callable that runs the query. Providers without a free tier are wired
# in but documented as such; they raise a clear "not implemented" error
# rather than silently pretending to run, so nobody mistakes a stub for
# a real (paid) result.
PROVIDERS = {
    "gemini": {
        "env": "GEMINI_API_KEY",
        "free_tier": True,
        "signup_url": "https://aistudio.google.com/app/apikey",
    },
    "openai": {
        "env": "OPENAI_API_KEY",
        "free_tier": False,
        "signup_url": "https://platform.openai.com/api-keys",
    },
    "anthropic": {
        "env": "ANTHROPIC_API_KEY",
        "free_tier": False,
        "signup_url": "https://console.anthropic.com/settings/keys",
    },
    "perplexity": {
        "env": "PERPLEXITY_API_KEY",
        "free_tier": False,
        "signup_url": "https://www.perplexity.ai/settings/api",
    },
}


def _domain_of(brand_or_domain: str) -> str:
    """Normalize a brand/domain input to a bare hostname for matching."""
    value = brand_or_domain.strip().lower()
    if "://" in value:
        value = urlparse(value).hostname or value
    value = value.removeprefix("www.")
    return value


def query_gemini(brand_or_domain: str, query: str) -> dict:
    """Query Gemini with Google Search grounding and check for brand/domain mentions."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {
            "provider": "gemini",
            "ran": False,
            "reason": f"GEMINI_API_KEY not set. Free key: {PROVIDERS['gemini']['signup_url']}",
        }

    domain = _domain_of(brand_or_domain)
    payload = {
        "contents": [{"parts": [{"text": query}]}],
        "tools": [{"google_search": {}}],
    }

    import requests

    try:
        validate_url_strict(GEMINI_URL)
        with safe_requests_session(GEMINI_URL) as session:
            response = session.post(
                GEMINI_URL,
                params={"key": api_key},
                json=payload,
                timeout=30,
            )
    except URLSafetyError as exc:
        return {"provider": "gemini", "ran": False, "reason": f"URL safety check failed: {exc}"}
    except requests.RequestException as exc:
        return {"provider": "gemini", "ran": False, "reason": f"Request failed: {exc}"}

    if response.status_code != 200:
        return {
            "provider": "gemini",
            "ran": False,
            "reason": f"HTTP {response.status_code}: {response.text[:300]}",
        }

    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return {"provider": "gemini", "ran": True, "reason": "No candidates returned", "cited": False}

    parts = candidates[0].get("content", {}).get("parts", [])
    answer_text = " ".join(p.get("text", "") for p in parts)

    grounding = candidates[0].get("groundingMetadata", {}) or {}
    grounding_chunks = grounding.get("groundingChunks", []) or []
    cited_urls = []
    for chunk in grounding_chunks:
        web = chunk.get("web", {})
        uri = web.get("uri", "")
        if uri:
            cited_urls.append(uri)

    domain_cited = any(domain in u.lower() for u in cited_urls)
    domain_mentioned_in_text = domain in answer_text.lower() or brand_or_domain.lower() in answer_text.lower()

    return {
        "provider": "gemini",
        "ran": True,
        "cited": domain_cited,
        "mentioned_in_answer_text": domain_mentioned_in_text,
        "cited_urls": cited_urls,
        "cited_urls_count": len(cited_urls),
        "answer_excerpt": answer_text[:500],
    }


def _not_implemented(provider_name: str) -> dict:
    info = PROVIDERS[provider_name]
    key = os.environ.get(info["env"])
    if not key:
        return {
            "provider": provider_name,
            "ran": False,
            "reason": (
                f"{info['env']} not set. This provider has no free tier — "
                f"get a paid key at {info['signup_url']} if you want it enabled."
            ),
        }
    return {
        "provider": provider_name,
        "ran": False,
        "reason": (
            f"{info['env']} is set but the {provider_name} query implementation "
            "is not wired up yet in this script. Contributions welcome — see "
            "PROVIDERS registry and query_gemini() as the reference implementation."
        ),
    }


def init_db() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS citation_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_or_domain TEXT NOT NULL,
            query TEXT NOT NULL,
            provider TEXT NOT NULL,
            ran INTEGER NOT NULL,
            cited INTEGER,
            mentioned_in_answer_text INTEGER,
            cited_urls_count INTEGER,
            result_json TEXT NOT NULL,
            checked_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_brand ON citation_checks(brand_or_domain, checked_at)"
    )
    conn.commit()
    return conn


def store_result(conn: sqlite3.Connection, brand_or_domain: str, query: str, result: dict) -> None:
    conn.execute(
        """
        INSERT INTO citation_checks
            (brand_or_domain, query, provider, ran, cited, mentioned_in_answer_text,
             cited_urls_count, result_json, checked_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            brand_or_domain,
            query,
            result.get("provider"),
            1 if result.get("ran") else 0,
            1 if result.get("cited") else 0 if result.get("ran") else None,
            1 if result.get("mentioned_in_answer_text") else 0 if result.get("ran") else None,
            result.get("cited_urls_count"),
            json.dumps(result),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()


def cmd_check(brand_or_domain: str, query: str, providers: list) -> dict:
    conn = init_db()
    results = []
    for provider in providers:
        if provider == "gemini":
            result = query_gemini(brand_or_domain, query)
        elif provider in PROVIDERS:
            result = _not_implemented(provider)
        else:
            result = {"provider": provider, "ran": False, "reason": "Unknown provider."}
        store_result(conn, brand_or_domain, query, result)
        results.append(result)
    conn.close()

    ran_count = sum(1 for r in results if r.get("ran"))
    return {
        "brand_or_domain": brand_or_domain,
        "query": query,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "summary": (
            f"{ran_count}/{len(results)} provider(s) actually queried "
            f"(others need a paid API key — see 'reason' fields)."
        ),
    }


def cmd_history(brand_or_domain: str, limit: int) -> dict:
    if not os.path.exists(DB_PATH):
        return {
            "brand_or_domain": brand_or_domain,
            "checks": [],
            "note": "No database found. Run `check` first.",
        }
    conn = init_db()
    rows = conn.execute(
        """
        SELECT query, provider, ran, cited, mentioned_in_answer_text,
               cited_urls_count, checked_at
        FROM citation_checks
        WHERE brand_or_domain = ?
        ORDER BY checked_at DESC
        LIMIT ?
        """,
        (brand_or_domain, limit),
    ).fetchall()
    conn.close()

    checks = [
        {
            "query": r[0],
            "provider": r[1],
            "ran": bool(r[2]),
            "cited": bool(r[3]) if r[3] is not None else None,
            "mentioned_in_answer_text": bool(r[4]) if r[4] is not None else None,
            "cited_urls_count": r[5],
            "checked_at": r[6],
        }
        for r in rows
    ]

    ran_checks = [c for c in checks if c["ran"]]
    citation_rate = (
        sum(1 for c in ran_checks if c["cited"]) / len(ran_checks) if ran_checks else None
    )

    return {
        "brand_or_domain": brand_or_domain,
        "checks": checks,
        "checks_returned": len(checks),
        "citation_rate_among_ran_checks": citation_rate,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Run a live citation check against configured providers.")
    p_check.add_argument("brand_or_domain", help="Brand name or domain to check for, e.g. acme.com")
    p_check.add_argument("query", help="The question to ask each AI platform, e.g. 'best crm for small business'")
    p_check.add_argument(
        "--providers",
        default="gemini,openai,anthropic,perplexity",
        help="Comma-separated providers to attempt (default: all registered; unconfigured ones report why they were skipped).",
    )
    p_check.add_argument("--json", action="store_true", help="Output raw JSON.")

    p_hist = sub.add_parser("history", help="Show stored citation-check history for a brand/domain.")
    p_hist.add_argument("brand_or_domain")
    p_hist.add_argument("--limit", type=int, default=20)
    p_hist.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "check":
        providers = [p.strip() for p in args.providers.split(",") if p.strip()]
        result = cmd_check(args.brand_or_domain, args.query, providers)
    else:
        result = cmd_history(args.brand_or_domain, args.limit)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
