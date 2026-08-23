#!/usr/bin/env python3
"""
Server log analysis for crawl budget and AI-crawler ground truth.

Added for this repo. Not sourced from any of the four merged upstream
projects — added after a second deep-research pass surfaced
lionkiii/claude-seo-skills' server-log-analysis skill as a genuinely
distinct capability nothing else in this plugin had. See NOTICE.md
section 5 for how this gap was found.

Why this is different from scripts/check_ai_crawler_access.py: that
script tests current-moment access with a handful of live requests from
wherever it's run. This script reads the site's own access logs — the
actual historical record of what Googlebot, GPTBot, ClaudeBot, and every
other crawler really did, from the origin server's own point of view.
Neither replaces the other:
  - check_ai_crawler_access.py answers "can AI bots reach this page
    right now, from here?"
  - This script answers "what have real crawlers actually been doing
    over the period covered by these logs?" — including patterns a
    single live test can't show: crawl frequency, whether a bot is
    burning its budget on 404s or redirect chains, whether AI bots are
    visiting at all despite a permissive robots.txt (permission isn't
    the same as uptake).

Supports the Combined Log Format used by Apache and Nginx by default:
    IP - - [timestamp] "METHOD /path HTTP/1.1" status bytes "referer" "user-agent"

Does not require an MCP, API key, or network access — the log file is
supplied locally. This plugin cannot fetch logs itself; the user must
export them from their hosting/CDN dashboard (e.g. Cloudflare Logpush,
Nginx access.log, Apache access_log) and point this script at the file.

Usage:
    python3 scripts/analyze_crawl_logs.py --file access.log
    python3 scripts/analyze_crawl_logs.py --file access.log --json
    python3 scripts/analyze_crawl_logs.py --file access.log --days 7
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


# Reuses the same bot identifiers as skills/seo-fix/references/
# ai-crawler-robots-presets.md so a "GPTBot" here means the same thing
# it means there — keep these two lists in sync if either changes.
_BOT_SIGNATURES: dict[str, str] = {
    "Googlebot": "search_index",
    "Bingbot": "search_index",
    "GPTBot": "ai_training",
    "OAI-SearchBot": "ai_retrieval",
    "ChatGPT-User": "ai_user_triggered",
    "ClaudeBot": "ai_training",
    "Claude-SearchBot": "ai_retrieval",
    "Claude-User": "ai_user_triggered",
    "Claude-Web": "ai_user_triggered",
    "PerplexityBot": "ai_retrieval",
    "Perplexity-User": "ai_user_triggered",
    "Applebot-Extended": "ai_training",
    "Applebot": "search_index",
    "Meta-ExternalAgent": "ai_training",
    "Amazonbot": "search_index",
    "CCBot": "ai_training",
    "Bytespider": "ai_training",
    "Google-Extended": "ai_training",
    "AhrefsBot": "seo_tool",
    "SemrushBot": "seo_tool",
    "MJ12bot": "seo_tool",
    "DotBot": "seo_tool",
}

# Combined Log Format (Apache/Nginx default)
_LOG_LINE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" '
    r'(?P<status>\d{3}) (?P<bytes>\S+) '
    r'"(?P<referer>[^"]*)" "(?P<ua>[^"]*)"'
)

_TIME_FORMAT = "%d/%b/%Y:%H:%M:%S"


def _identify_bot(user_agent: str) -> str | None:
    for signature in _BOT_SIGNATURES:
        if signature.lower() in user_agent.lower():
            return signature
    return None


def _parse_line(line: str) -> dict | None:
    m = _LOG_LINE.match(line)
    if not m:
        return None
    d = m.groupdict()
    try:
        # strip timezone offset (e.g. " +0000") before parsing
        ts_str = d["time"].rsplit(" ", 1)[0]
        d["parsed_time"] = datetime.strptime(ts_str, _TIME_FORMAT)
    except ValueError:
        d["parsed_time"] = None
    d["status"] = int(d["status"])
    d["bot"] = _identify_bot(d["ua"])
    return d


def analyze(lines: list[str], days: int | None = None) -> dict:
    parsed = []
    unparsed_count = 0
    for line in lines:
        entry = _parse_line(line.strip())
        if entry is None:
            unparsed_count += 1
            continue
        parsed.append(entry)

    if days is not None:
        timestamps = [e["parsed_time"] for e in parsed if e["parsed_time"]]
        if timestamps:
            cutoff = max(timestamps) - timedelta(days=days)
            parsed = [e for e in parsed if e["parsed_time"] and e["parsed_time"] >= cutoff]

    total_requests = len(parsed)
    bot_requests = [e for e in parsed if e["bot"]]
    human_requests = total_requests - len(bot_requests)

    per_bot: dict[str, dict] = {}
    for bot_name in set(e["bot"] for e in bot_requests):
        bot_entries = [e for e in bot_requests if e["bot"] == bot_name]
        status_counts = Counter(e["status"] for e in bot_entries)
        path_counts = Counter(e["path"] for e in bot_entries)
        wasted = sum(c for status, c in status_counts.items() if status >= 400 or 300 <= status < 400)
        per_bot[bot_name] = {
            "category": _BOT_SIGNATURES.get(bot_name, "unknown"),
            "total_requests": len(bot_entries),
            "status_breakdown": dict(status_counts),
            "wasted_requests_4xx_5xx_3xx": wasted,
            "wasted_pct": round((wasted / len(bot_entries)) * 100, 1) if bot_entries else 0.0,
            "top_paths": path_counts.most_common(5),
        }

    ai_retrieval_bots_seen = [b for b, meta in per_bot.items() if meta["category"] == "ai_retrieval"]
    ai_retrieval_absent = [
        b for b, cat in _BOT_SIGNATURES.items() if cat == "ai_retrieval" and b not in per_bot
    ]

    notes = []
    if not bot_requests:
        notes.append(
            "No recognized bot traffic found in this log sample. Either the log period is "
            "too short/old, the site isn't being crawled by any recognized bot yet, or the "
            "log format doesn't match Combined Log Format (check --file is genuinely an "
            "access log, not an error log)."
        )
    if ai_retrieval_absent and bot_requests:
        notes.append(
            f"No visits found from: {', '.join(ai_retrieval_absent)}. A permissive robots.txt "
            "and a clean live-access check (scripts/check_ai_crawler_access.py) only prove a "
            "bot COULD reach the site — this log shows whether it actually HAS. Absence here "
            "over a real time window is worth investigating on its own, separately from the "
            "access checks."
        )
    for bot_name, meta in per_bot.items():
        if meta["wasted_pct"] > 20:
            notes.append(
                f"{bot_name}: {meta['wasted_pct']}% of its requests hit a 3xx/4xx/5xx status — "
                "that's crawl budget spent on redirects or errors instead of indexable content. "
                "Check the top_paths for this bot to find what's being repeatedly hit."
            )

    return {
        "total_requests_parsed": total_requests,
        "unparsed_lines": unparsed_count,
        "human_requests": human_requests,
        "bot_requests": len(bot_requests),
        "bot_traffic_pct": round((len(bot_requests) / total_requests) * 100, 1) if total_requests else 0.0,
        "per_bot": per_bot,
        "ai_retrieval_bots_seen": ai_retrieval_bots_seen,
        "ai_retrieval_bots_absent": ai_retrieval_absent,
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze server access logs for crawl budget and AI-crawler ground truth.")
    parser.add_argument("--file", type=Path, required=True, help="Path to an access log file (Combined Log Format)")
    parser.add_argument("--days", type=int, default=None, help="Only analyze the most recent N days in the log")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        return 1

    try:
        lines = args.file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        print(f"Error reading {args.file}: {e}", file=sys.stderr)
        return 1

    if not lines:
        print(f"Error: {args.file} is empty.", file=sys.stderr)
        return 1

    result = analyze(lines, days=args.days)

    if result["total_requests_parsed"] == 0:
        print(
            f"Warning: 0 of {len(lines)} lines matched Combined Log Format. "
            "This script only supports Combined Log Format (Apache/Nginx default). "
            "If this is a different format (JSON logs, W3C Extended, Cloudflare Logpush), "
            "it needs a different parser than this one — do not report crawl-budget "
            "findings from an unparsed log.",
            file=sys.stderr,
        )
        return 1

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Total requests parsed: {result['total_requests_parsed']} (unparsed lines: {result['unparsed_lines']})")
        print(f"Human traffic: {result['human_requests']}  |  Bot traffic: {result['bot_requests']} ({result['bot_traffic_pct']}%)")
        print()
        for bot_name, meta in sorted(result["per_bot"].items(), key=lambda kv: -kv[1]["total_requests"]):
            print(f"  {bot_name} ({meta['category']}): {meta['total_requests']} requests, {meta['wasted_pct']}% wasted (3xx/4xx/5xx)")
            for path, count in meta["top_paths"]:
                print(f"      {count:>5}  {path}")
        if result["notes"]:
            print("\nNotes:")
            for note in result["notes"]:
                print(f"  - {note}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
