#!/usr/bin/env python3
"""
Live AI-crawler access checker — tests whether AI bots can actually reach
a site, rather than inferring it from robots.txt text alone.

Added for this repo. Not sourced from any of the four merged upstream
projects — written after a comparison-review of the wider Claude-Code-SEO
ecosystem surfaced that robots.txt-only auditing (what this plugin, and
most SEO tools, previously did) cannot detect edge/WAF-level blocking —
notably Cloudflare's "Block AI bots" managed rule, enabled by default on
every new zone since 1 July 2025, which blocks GPTBot, ClaudeBot, and
PerplexityBot before robots.txt is even consulted. See
skills/seo-geo/SKILL.md's "Critical: robots.txt is not sufficient
evidence of AI crawler access" section for the full write-up, and
NOTICE.md section 5 for how this gap was found.

What this script actually does: sends real HTTP requests to the target
URL using each AI crawler's actual User-Agent string, and reports the
status code and any indication of a bot-challenge page (Cloudflare
challenge pages, CAPTCHA redirects) rather than a normal 200. It does
NOT parse robots.txt (skills/seo-technical already has that) — it tests
what actually happens at the HTTP layer, which is the layer robots.txt
cannot speak for.

Honesty notes, read before trusting the output:
  - A 200 response here means the crawler's specific request was not
    blocked FOR THIS SCRIPT'S REQUEST. Some WAFs use IP-reputation or
    request-pattern heuristics beyond User-Agent alone (rate, TLS
    fingerprint, ASN) — a single request from this script's IP is not
    guaranteed to reproduce what happens when the real bot's
    infrastructure requests the page. Treat a clean result as reassuring,
    not as absolute proof; treat a blocked result as a strong, actionable
    signal either way.
  - This script cannot see inside a CDN/WAF dashboard. If every UA comes
    back 200 but the site is on Cloudflare, still tell the user to check
    Security -> Bots -> AI Crawl Control directly — some challenge modes
    only trigger on repeated requests or specific paths this script
    didn't happen to hit.
  - Reuses this plugin's existing url_safety.safe_requests_get for
    DNS-rebinding protection rather than calling requests directly.

Usage:
    python3 scripts/check_ai_crawler_access.py https://example.com
    python3 scripts/check_ai_crawler_access.py https://example.com --json
    python3 scripts/check_ai_crawler_access.py https://example.com --bots GPTBot,ClaudeBot
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from url_safety import safe_requests_get, URLSafetyError
except ImportError:
    print(
        "Error: could not import url_safety.py from the same scripts/ directory. "
        "This script must be run from within the plugin's scripts/ folder or with "
        "it on the Python path.",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


# Retrieval/search bots — the ones a site normally WANTS to allow, since
# blocking these specifically costs AI-citation visibility. Distinct from
# training-only bots (GPTBot, CCBot, Bytespider) a site might legitimately
# want blocked; see references/ai-crawler-robots-presets.md in seo-fix for
# the full training-vs-retrieval-vs-user-triggered breakdown per operator.
_RETRIEVAL_BOT_USER_AGENTS: dict[str, str] = {
    "GPTBot": "Mozilla/5.0 (compatible; GPTBot/1.1; +https://openai.com/gptbot)",
    "OAI-SearchBot": "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)",
    "ClaudeBot": "Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
    "Claude-SearchBot": "Mozilla/5.0 (compatible; Claude-SearchBot/1.0; +https://www.anthropic.com/claude-searchbot)",
    "PerplexityBot": "Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
    "Google-Extended": "Mozilla/5.0 (compatible; Google-Extended)",
}

# Baseline for comparison: a normal browser UA. If this also fails, the
# problem isn't AI-crawler-specific — it's the site being unreachable,
# which the caller should report as a different, more basic finding.
_BASELINE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Substrings that suggest a challenge/block page rather than a genuine
# origin response, even on a 200 — Cloudflare and similar WAFs sometimes
# return 200 with a JS-challenge or CAPTCHA body instead of a 403.
_CHALLENGE_MARKERS: tuple[str, ...] = (
    "checking your browser",
    "cf-browser-verification",
    "cf_chl_",
    "attention required",
    "just a moment",
    "enable javascript and cookies",
    "captcha",
    "access denied",
)


def _classify(resp: requests.Response) -> str:
    # Guard against a specific false-positive trap: some sandboxed/proxied
    # execution environments (including the one this script was developed
    # and tested in) restrict outbound network access to an allowlist and
    # return a 403 for anything outside it — which looks identical to a
    # genuine bot block unless the response body is checked. Found during
    # this script's own testing: an `x-deny-reason` header and a "Host not
    # in allowlist" body came back from a completely unrelated, unblocked
    # site, purely because the execution environment's own egress proxy
    # denied it. Never report that as a finding about the target site.
    if resp.headers.get("x-deny-reason") or "not in allowlist" in (resp.text or "")[:500].lower():
        return "environment_egress_restricted"
    # Rate limiting looks identical to bot-blocking at the status-code level
    # (both commonly return 403 or 429) but means something completely
    # different for this check — found during this script's own testing
    # against a rate-limited API endpoint, where x-ratelimit-remaining: 0
    # plus a "rate limit exceeded" body came back as a plain 403. Reporting
    # that as "AI bot blocked" would be wrong: the block isn't about bot
    # identity at all, it's a request-volume ceiling any client would hit.
    if resp.headers.get("x-ratelimit-remaining") == "0" or "rate limit exceeded" in (resp.text or "")[:500].lower():
        return "rate_limited"
    if resp.status_code in (403, 429, 503):
        return "blocked"
    if resp.status_code >= 400:
        return f"error_{resp.status_code}"
    body_lower = (resp.text or "")[:5000].lower()
    if any(marker in body_lower for marker in _CHALLENGE_MARKERS):
        return "challenged"
    return "allowed"


def check(url: str, bots: dict[str, str]) -> dict:
    results: dict[str, dict] = {}

    try:
        baseline_resp = safe_requests_get(url, headers={"User-Agent": _BASELINE_USER_AGENT}, timeout=15)
        baseline_status = _classify(baseline_resp)
    except URLSafetyError as e:
        return {
            "url": url,
            "error": f"URL failed safety/DNS validation before any request was sent: {e}. "
            "This is not a bot-blocking finding — the URL itself couldn't be resolved "
            "or didn't pass this plugin's SSRF/DNS-rebinding checks. Verify the URL is "
            "correct and publicly resolvable before re-running this check.",
        }
    except requests.RequestException as e:
        return {
            "url": url,
            "error": f"Baseline request (normal browser UA) failed: {e}. "
            "Cannot distinguish AI-crawler-specific blocking from the site "
            "simply being unreachable — fix connectivity before re-running this check.",
        }

    if baseline_status == "environment_egress_restricted":
        return {
            "url": url,
            "error": (
                "This execution environment's own network egress is restricted and "
                "blocked the baseline request before it reached the target site at "
                "all (an `x-deny-reason` / 'not in allowlist' response came back, not "
                "a response from the target). This is NOT a finding about the target "
                "site's bot policy — it means this script cannot run a live check from "
                "this environment. Run it from an environment with unrestricted "
                "outbound HTTPS instead, or fall back to the manual dashboard-check "
                "instructions in skills/seo-geo/SKILL.md."
            ),
        }
    if baseline_status == "rate_limited":
        return {
            "url": url,
            "error": (
                "The baseline request was rate-limited (x-ratelimit-remaining: 0 or a "
                "'rate limit exceeded' response body), not blocked as a bot. This is "
                "common on API endpoints with strict unauthenticated rate limits and is "
                "unrelated to AI-crawler identity — re-run later once the rate limit "
                "window resets, or authenticate the request if this is an API this "
                "plugin already has credentials for (see skills/seo-google/references/"
                "rate-limits-quotas.md for this plugin's own Google API rate-limit "
                "handling as a model)."
            ),
        }

    cf_signal = bool(baseline_resp.headers.get("cf-ray") or "cloudflare" in baseline_resp.headers.get("server", "").lower())

    for bot_name, ua in bots.items():
        resp = None
        try:
            resp = safe_requests_get(url, headers={"User-Agent": ua}, timeout=15)
            status = _classify(resp)
        except URLSafetyError as e:
            status = f"safety_check_failed: {e}"
        except requests.RequestException as e:
            status = f"request_failed: {e}"
        results[bot_name] = {
            "status_code": resp.status_code if resp is not None else None,
            "classification": status,
        }

    blocked_bots = [b for b, r in results.items() if r["classification"] in ("blocked", "challenged")]
    env_restricted_bots = [b for b, r in results.items() if r["classification"] == "environment_egress_restricted"]
    rate_limited_bots = [b for b, r in results.items() if r["classification"] == "rate_limited"]

    return {
        "url": url,
        "baseline_normal_browser": baseline_status,
        "behind_cloudflare_signal": cf_signal,
        "bots": results,
        "blocked_or_challenged": blocked_bots,
        "environment_egress_restricted_bots": env_restricted_bots,
        "rate_limited_bots": rate_limited_bots,
        "summary": (
            (
                f"WARNING: {len(env_restricted_bots)} of {len(bots)} requests were blocked by "
                "this execution environment's own egress restrictions, not by the target site — "
                "those results are not usable findings. "
                if env_restricted_bots
                else ""
            )
            + (
                f"NOTE: {len(rate_limited_bots)} of {len(bots)} requests were rate-limited, "
                "not blocked as bots — not a usable bot-blocking finding either. "
                if rate_limited_bots
                else ""
            )
            + f"{len(blocked_bots)} of {len(bots)} tested AI crawlers were blocked or "
            f"challenged on this single request."
            + (
                " Site shows a Cloudflare signal (cf-ray header / Cloudflare server "
                "header) — if any bots above are blocked, check Security -> Bots -> "
                "AI Crawl Control in the Cloudflare dashboard directly; this script's "
                "single request cannot fully substitute for that."
                if cf_signal
                else ""
            )
        ),
        "caveat": (
            "A clean ('allowed') result for every bot here is reassuring but not "
            "absolute proof — some WAFs block on IP reputation, request rate, or "
            "TLS fingerprint rather than User-Agent alone. See this script's "
            "docstring before treating this as the final word."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Test whether AI crawlers can actually reach a URL.")
    parser.add_argument("url", help="URL to test")
    parser.add_argument(
        "--bots",
        type=str,
        default=None,
        help="Comma-separated subset of bot names to test (default: all of GPTBot, "
        "OAI-SearchBot, ClaudeBot, Claude-SearchBot, PerplexityBot, Google-Extended)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    bots = _RETRIEVAL_BOT_USER_AGENTS
    if args.bots:
        requested = {b.strip() for b in args.bots.split(",")}
        unknown = requested - set(_RETRIEVAL_BOT_USER_AGENTS)
        if unknown:
            print(f"Unknown bot name(s): {', '.join(sorted(unknown))}", file=sys.stderr)
            print(f"Known: {', '.join(_RETRIEVAL_BOT_USER_AGENTS)}", file=sys.stderr)
            return 1
        bots = {k: v for k, v in _RETRIEVAL_BOT_USER_AGENTS.items() if k in requested}

    result = check(args.url, bots)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0 if "error" not in result else 1

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    print(f"URL: {result['url']}")
    print(f"Baseline (normal browser UA): {result['baseline_normal_browser']}")
    print(f"Cloudflare signal detected: {result['behind_cloudflare_signal']}")
    print()
    for bot, r in result["bots"].items():
        print(f"  {bot}: {r['classification']} (status {r['status_code']})")
    print()
    print(result["summary"])
    print()
    print(f"Caveat: {result['caveat']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
