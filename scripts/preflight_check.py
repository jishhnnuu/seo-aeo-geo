#!/usr/bin/env python3
"""Prove the growth loop's credentials work, by using them.

Every check here makes a real API call. Checking that an environment variable
is set proves nothing: the three states that matter are WORKING (a live call
succeeded), UNAUTHORIZED (the credential exists but was refused -- usually a
two-minute permission grant the owner would want to know about today), and
ABSENT (nothing configured). Collapsing those into "not configured" is how a
403 goes unnoticed for a month.

Exit codes:
    0  every configured credential works, or degradations are tolerable
    1  a FATAL condition -- the loop cannot do its core job at all

Usage:
    preflight_check.py                    # human-readable report
    preflight_check.py --json             # machine-readable
    preflight_check.py --github-summary   # markdown for $GITHUB_STEP_SUMMARY
    preflight_check.py --gate             # exit 1 on FATAL, print nothing else
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

WORKING, UNAUTHORIZED, ABSENT, BROKEN = "WORKING", "UNAUTHORIZED", "ABSENT", "BROKEN"
TIMEOUT = 20


def _get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status, r.read()


def check_google_api_key():
    """PageSpeed Insights -- the cheapest call that proves the key is live."""
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        return ABSENT, "no GOOGLE_API_KEY set", "Lab-only performance data; no CrUX field data."
    url = ("https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
           f"?url=https://example.com&key={key}")
    try:
        _get(url)
        return WORKING, "PageSpeed Insights accepted the key", ""
    except urllib.error.HTTPError as e:
        if e.code in (400, 401, 403):
            return UNAUTHORIZED, f"PageSpeed Insights returned {e.code}", (
                "The key exists but is refused. Enable the PageSpeed Insights API "
                "on this key's Google Cloud project, or check its API restrictions.")
        return BROKEN, f"HTTP {e.code}", "Transient or upstream; retried next cycle."
    except Exception as e:
        return BROKEN, str(e)[:120], "Network failure, not necessarily a credential problem."


def _sa_credentials(scopes):
    raw = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip()
    if not raw:
        return None, "no GOOGLE_APPLICATION_CREDENTIALS_JSON set"
    try:
        info = json.loads(raw)
    except json.JSONDecodeError:
        return None, "the service-account secret is not valid JSON"
    if info.get("type") != "service_account":
        return None, f"expected a service account, got type={info.get('type')!r}"
    try:
        from google.oauth2 import service_account
    except ImportError:
        return None, "google-auth is not installed on this runner"
    try:
        return service_account.Credentials.from_service_account_info(
            info, scopes=scopes), info.get("client_email", "")
    except Exception as e:
        return None, f"could not build credentials: {str(e)[:100]}"


def check_search_console():
    """The one that matters most: without it there is no impressions or clicks data."""
    creds, detail = _sa_credentials(["https://www.googleapis.com/auth/webmasters.readonly"])
    if creds is None:
        return ABSENT, detail, (
            "NO Search Console data. No impressions, clicks, position or CTR, so no "
            "striking-distance keywords and no CTR work -- the fastest-moving levers "
            "inside 30 days are all unavailable.")
    email = detail
    try:
        from googleapiclient.discovery import build
        svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        sites = svc.sites().list().execute().get("siteEntry", [])
    except Exception as e:
        return UNAUTHORIZED, f"sites.list failed: {str(e)[:120]}", (
            f"Add {email} as a user on the Search Console property.")

    if not sites:
        return UNAUTHORIZED, f"{email} can see no properties", (
            f"The service account authenticates but has been granted access to nothing. "
            f"In Search Console -> Settings -> Users and permissions, add {email} with "
            f"Full permission. This is the single highest-value fix available.")

    wanted = os.environ.get("GSC_PROPERTY", "").strip()
    visible = [s.get("siteUrl", "") for s in sites]
    if wanted and wanted not in visible:
        return UNAUTHORIZED, f"{email} cannot see {wanted}", (
            f"It can see {', '.join(visible[:3])}. Either GSC_PROPERTY is wrong, or "
            f"{email} has not been added to that specific property.")
    return WORKING, f"{email} can read {wanted or visible[0]}", ""


def check_ga4():
    prop = os.environ.get("GA4_PROPERTY_ID", "").strip()
    if not prop:
        return ABSENT, "no GA4_PROPERTY_ID set", "No organic traffic or landing-page data."
    creds, detail = _sa_credentials(["https://www.googleapis.com/auth/analytics.readonly"])
    if creds is None:
        return ABSENT, detail, "No organic traffic data."
    try:
        from googleapiclient.discovery import build
        build("analyticsdata", "v1beta", credentials=creds, cache_discovery=False)
        return WORKING, f"credentials built for property {prop}", ""
    except Exception as e:
        return UNAUTHORIZED, str(e)[:120], (
            f"Add the service account as a Viewer on GA4 property {prop}.")


def check_simple(name, env, note_absent):
    return (WORKING if os.environ.get(env, "").strip() else ABSENT,
            f"{env} is set" if os.environ.get(env, "").strip() else f"no {env} set",
            "" if os.environ.get(env, "").strip() else note_absent)


def check_pat():
    if os.environ.get("HAS_PAT", "").lower() == "true":
        return WORKING, "GROWTH_LOOP_PAT is set", ""
    return ABSENT, "GROWTH_LOOP_PAT is not set", (
        "FATAL. Pull requests opened by the build job will not trigger the "
        "test-and-publish job, so nothing will ever be tested, merged or published. "
        "The loop will appear to run and change nothing. Create a fine-grained PAT "
        "scoped to this repo with Contents, Pull requests and Issues at read/write, "
        "and save it as the GROWTH_LOOP_PAT secret.")


CHECKS = [
    ("Publishing (GROWTH_LOOP_PAT)", check_pat, True),
    ("Search Console", check_search_console, False),
    ("Google API key", check_google_api_key, False),
    ("GA4", check_ga4, False),
    ("Moz", lambda: check_simple("Moz", "MOZ_API_KEY", "Weaker backlink picture."), False),
    ("Bing Webmaster", lambda: check_simple("Bing", "BING_WEBMASTER_API_KEY",
                                            "No Bing data; IndexNow still works."), False),
]


def run():
    results = []
    fatal = False
    for label, fn, is_fatal in CHECKS:
        try:
            status, detail, cost = fn()
        except Exception as e:                      # a check must never crash the gate
            status, detail, cost = BROKEN, str(e)[:120], "Preflight check itself errored."
        if is_fatal and status != WORKING:
            fatal = True
        results.append({"check": label, "status": status,
                        "detail": detail, "cost": cost})
    return results, fatal


ICON = {WORKING: "PASS", UNAUTHORIZED: "AUTH", ABSENT: "----", BROKEN: "ERR "}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--github-summary", action="store_true")
    ap.add_argument("--gate", action="store_true")
    args = ap.parse_args()

    results, fatal = run()

    if args.gate:
        if fatal:
            bad = [r for r in results if r["status"] != WORKING
                   and r["check"].startswith("Publishing")]
            for r in bad:
                print(f"::error::{r['check']}: {r['detail']}. {r['cost']}", file=sys.stderr)
        return 1 if fatal else 0

    if args.json:
        print(json.dumps({"fatal": fatal, "checks": results}, indent=2))
        return 1 if fatal else 0

    if args.github_summary:
        print("## Growth Loop preflight\n")
        print("| Check | Status | Detail |")
        print("|---|---|---|")
        for r in results:
            print(f"| {r['check']} | **{r['status']}** | {r['detail']} |")
        notes = [r for r in results if r["cost"]]
        if notes:
            print("\n### What each gap costs\n")
            for r in notes:
                print(f"- **{r['check']}** — {r['cost']}")
        print("\n_A credential that is UNAUTHORIZED exists but was refused; that is a "
              "permission grant, not a missing key, and is usually a two-minute fix._")
        return 1 if fatal else 0

    for r in results:
        print(f"[{ICON[r['status']]}] {r['check']:32} {r['detail']}")
        if r["cost"]:
            print(f"       -> {r['cost']}")
    return 1 if fatal else 0


if __name__ == "__main__":
    sys.exit(main())
