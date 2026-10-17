#!/usr/bin/env python3
"""Link-building campaign engine: prospect screening, selection, approval-gated outreach, tracking.

Turns a pile of candidate link sources into a short, defensible, human-approved
outreach list, then tracks each prospect until the link is live and verified.
It never sends email and never buys anything. Its job is to make the decision
auditable.

Pipeline (each step is one subcommand, state lives in a campaign directory):

    init        create campaign.json (site profile, sender, settings)
    library     add the industry-matched evergreen sources from data/linkbuilding/library.json
    ingest      add prospects from a CSV/JSON export (competitor gap, SERP research, a vendor sheet)
    check-live  confirm each prospect domain resolves to a real, unparked site (network)
    screen      apply hard disqualifiers, soft flags and a 0-100 score
    select      choose the shortlist (default 100, mostly free, no padding with weak prospects)
    shortlist   print the shortlist for human review
    approve     the human gate: only approved prospects are drafted or exported
    reject      record a rejection with a reason
    draft       write first-touch and follow-up emails for approved pitch prospects (complete only)
    kit         write the submission kit for approved self-serve listings
    export      write a mail-merge CSV of complete drafts
    log         record an event (sent, replied, won, declined, bounced, unsubscribed, lost)
    due         list follow-ups and verification checks that are due
    verify      re-check won links are still live, followed or not (network)
    status      funnel counts
    baseline    store before-metrics so results can be judged against them
    report-data write the JSON consumed by `google_report.py --type link-building`
    readiness   audit whether the site is ready to earn links, with what to change

Usage:
    python scripts/linkbuilding.py init --campaign link-campaigns/example.com --site https://example.com \\
        --name "Example" --industry saas --topics "invoice software,accounts payable"
    python scripts/linkbuilding.py library --campaign link-campaigns/example.com
    python scripts/linkbuilding.py screen --campaign link-campaigns/example.com
    python scripts/linkbuilding.py select --campaign link-campaigns/example.com --count 100
    python scripts/linkbuilding.py shortlist --campaign link-campaigns/example.com

All commands print JSON when --json is passed.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
DATA_DIR = os.path.join(REPO_ROOT, "data", "linkbuilding")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

STATUS_ORDER = [
    "candidate", "proposed", "approved", "rejected", "drafted", "sent",
    "followup_1", "followup_2", "replied", "won", "declined", "no_response",
    "bounced", "unsubscribed", "lost",
]
SELF_SERVE_MODES = {"self_serve", "purchase", "manual"}
FOLLOWUP_1_DAYS = 6
FOLLOWUP_2_DAYS = 14
CLOSE_AFTER_DAYS = 21
MAX_DRAFT_WORDS = 130
VERIFY_CHECKPOINTS = (30, 90, 180)
MIN_SCORE_DEFAULT = 40

# Weights sum to 1.0. Relevance dominates on purpose: an irrelevant high-DR link is the
# most common way link building wastes money and, at scale, draws a spam classification.
WEIGHTS = {"relevance": 0.35, "authority": 0.20, "attainability": 0.25, "audience": 0.12, "integrity": 0.08}
SOFT_FLAG_PENALTY = 6
SOFT_FLAG_PENALTY_CAP = 24

AUTHORITY_HINT = {"high": 0.85, "medium": 0.60, "low": 0.35}
AUDIENCE_HINT = {"high": 0.80, "medium": 0.50, "low": 0.25}

STOPWORDS = set(
    "a an and are as at be by for from has have how in is it its of on or that the this to was "
    "what when where which who why will with your you our we best top guide tips free online new "
    "services service company business site website page pages blog".split()
)

GENERIC_HOOKS = (
    "love your content", "great article", "great post", "i came across your", "hope this finds you",
    "i was browsing", "big fan", "amazing content", "i recently stumbled", "i noticed your website",
)

REQUIRED_PERSONALIZATION = {
    "unlinked_mention": ["their_page_url"],
    "broken_link": ["their_page_url", "broken_url", "asset_url", "asset_summary"],
    "resource_page": ["their_page_url", "hook", "asset_url", "asset_summary"],
    "competitor_gap": ["hook", "asset_url", "asset_summary"],
    "guest_contribution": ["hook", "topics"],
    "digital_pr": ["hook", "asset_url", "asset_summary"],
    "partner_page": ["their_page_url", "relationship", "asset_url"],
    "podcast_guest": ["hook", "topics"],
}
EMAIL_TYPES = set(REQUIRED_PERSONALIZATION)

ASSET_IDEAS = {
    "saas": [
        "An original benchmark report built from your anonymised product data",
        "A free calculator or template tied to the problem the product solves",
        "A public glossary or 'how it works' hub that other writers can cite",
        "A comparison or alternatives page with honest trade-offs",
        "A free tool or grader that gives a score people want to share",
    ],
    "ecommerce": [
        "A buying guide with real test results and photos you took yourself",
        "A size, fit or compatibility tool people bookmark",
        "A price or trend study from your own sales data",
        "A supplier or maker story with real people and places",
        "A sustainability or sourcing page with verifiable specifics",
    ],
    "local_service": [
        "A local cost guide with real quoted prices from your jobs",
        "A neighbourhood or city resource page (permits, schedules, local rules)",
        "A sponsorship or community-event page naming local partners",
        "Before and after case studies with the customer's permission",
        "A seasonal checklist that local newsletters and councils can share",
    ],
    "agency": [
        "A named case study with before and after numbers the client has approved",
        "An annual survey of your clients' industry with the dataset published",
        "A free audit template or checklist",
        "A teardown series of public campaigns with your analysis",
    ],
    "healthcare": [
        "Patient-education pages written or reviewed by named clinicians with credentials",
        "A local health resource guide (clinics, services, helplines)",
        "A plain-language explainer for a condition your practice treats, with sources",
    ],
    "legal": [
        "A state-specific guide to a common legal question, reviewed by a named attorney",
        "A plain-language checklist or form guide",
        "A local court or process explainer that journalists can cite",
    ],
    "home_services": [
        "A cost guide by job type with real local price ranges",
        "A maintenance calendar by season",
        "A project gallery with permits and materials listed",
    ],
    "real_estate": [
        "A neighbourhood market report using public sales data you re-cut",
        "A buyer or seller checklist for your market",
        "A local schools, transport and amenities guide",
    ],
    "hospitality": [
        "A local guide written by staff who live there",
        "A sourcing page naming local suppliers (they will often link back)",
        "A seasonal events calendar for the area",
    ],
    "publisher": [
        "A data-led story with the dataset downloadable",
        "A reference explainer on a recurring news topic, kept updated",
        "An expert directory or source list other writers use",
    ],
    "nonprofit": [
        "An impact report with figures and methodology",
        "A resource hub for the community you serve",
        "A partner and funder page that those partners will link back to",
    ],
    "general": [
        "One original data point or survey your niche does not have yet",
        "A genuinely useful free tool, template or checklist",
        "A definitive guide that is clearly better than the current top results",
        "A named expert profile with credentials and published quotes",
    ],
}

SITE_SIGNALS = {
    "contact": re.compile(r"contact|get in touch|reach us", re.I),
    "about": re.compile(r"\babout\b|our story|who we are|our team", re.I),
    "blog": re.compile(r"\bblog\b|\barticles?\b|\bnews\b|\binsights?\b|\bresources?\b|\bguides?\b", re.I),
    "asset": re.compile(
        r"calculator|\btools?\b|research|\bstud(y|ies)\b|statistics|\breport\b|benchmark|survey|template|"
        r"checklist|\bdata\b|\bgrader\b|\bgenerator\b|\bindex\b", re.I),
    "author": re.compile(r"\bBy\s+[A-Z][a-z]+|[Aa]uthor|[Ww]ritten by|[Rr]eviewed by|[Mm]edically reviewed"),
    "legal": re.compile(r"privacy|terms", re.I),
}
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{8,}\d)")


# --------------------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------------------

def now_iso(today: Optional[date] = None) -> str:
    if today:
        return datetime(today.year, today.month, today.day, tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_day(value: Optional[str]) -> date:
    return date.fromisoformat(value) if value else datetime.now(timezone.utc).date()


def normalize_domain(value: str) -> str:
    """Return a bare lowercase registrable-looking host: no scheme, www, port, path."""
    if not value:
        return ""
    v = (value.strip().lower().split() or [""])[0]
    v = re.sub(r"^[a-z]+:/*", "", v) if "://" in v or v.startswith("http") else v
    v = v.split("/")[0].split("?")[0].split("#")[0].split(":")[0]
    v = v.strip(". ")
    return v[4:] if v.startswith("www.") else v


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def parse_metric(value) -> Optional[float]:
    """Parse '155k', '1.4M', '7,4k', '10k+', '868K (Semrush)', '85+'. Junk like '10$' or '$62.00' returns None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower()
    if not s or "$" in s:
        return None
    s = re.sub(r"\(.*?\)", "", s).replace("million", "m").replace("+", "").strip()
    s = re.sub(r"(?<=\d),(?=\d{1,2}[kmb]\b)", ".", s)
    s = s.replace(",", "").replace(" ", "")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([kmb])?", s)
    if not m:
        return None
    mult = {"k": 1e3, "m": 1e6, "b": 1e9}.get(m.group(2) or "", 1)
    return float(m.group(1)) * mult


def tokens(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2 and t not in STOPWORDS}


def load_json(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def save_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


class Campaign:
    """A campaign directory: campaign.json, prospects.json, suppression.txt."""

    def __init__(self, directory: str):
        self.dir = directory
        self.config_path = os.path.join(directory, "campaign.json")
        self.prospects_path = os.path.join(directory, "prospects.json")
        self.suppression_path = os.path.join(directory, "suppression.txt")
        self.config = load_json(self.config_path)
        if self.config is None:
            raise SystemExit(f"No campaign at {directory}. Run `init` first.")
        self.prospects = (load_json(self.prospects_path, {}) or {}).get("prospects", [])

    def save(self) -> None:
        save_json(self.config_path, self.config)
        save_json(self.prospects_path, {"prospects": self.prospects})

    def find(self, pid: str) -> dict:
        for p in self.prospects:
            if p["id"] == pid:
                return p
        raise SystemExit(f"No prospect with id {pid!r}")

    def suppressed(self) -> set:
        try:
            with open(self.suppression_path, encoding="utf-8") as fh:
                return {l.strip().lower() for l in fh if l.strip() and not l.startswith("#")}
        except FileNotFoundError:
            return set()

    def suppress(self, *items: str) -> None:
        current = self.suppressed()
        new = {i.strip().lower() for i in items if i and i.strip()} - current
        if new:
            with open(self.suppression_path, "a", encoding="utf-8") as fh:
                for item in sorted(new):
                    fh.write(item + "\n")


def load_library() -> dict:
    return load_json(os.path.join(DATA_DIR, "library.json"), {"types": {}, "sources": []})


def load_blocklist() -> dict:
    data = load_json(os.path.join(DATA_DIR, "blocklist.json"), {}) or {}
    data["_compiled_hard"] = [(r["id"], re.compile(r["pattern"], re.I), r["reason"]) for r in data.get("hard_keyword_patterns", [])]
    data["_compiled_soft"] = [(r["id"], re.compile(r["pattern"], re.I), r["reason"]) for r in data.get("soft_keyword_patterns", [])]
    data["_seller_re"] = re.compile(data.get("seller_signal_pattern", r"$^"), re.I)
    data["_domains"] = {d["domain"].lower(): d for d in data.get("domains", [])}
    return data


def load_seller_listed() -> set:
    path = os.path.join(DATA_DIR, "seller_listed_domains.txt")
    out = set()
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#"):
                    continue
                out.update(normalize_domain(w) for w in line.split())
    except FileNotFoundError:
        pass
    return out


# --------------------------------------------------------------------------------------
# Prospect construction
# --------------------------------------------------------------------------------------

def make_prospect(domain: str, *, source: str, ptype: str, cost: str = "free", **kw) -> dict:
    d = normalize_domain(domain)
    return {
        "id": kw.pop("id", None) or f"{slug(d)}-{slug(ptype)}",
        "domain": d,
        "url": kw.pop("url", None) or f"https://{d}",
        "name": kw.pop("name", None) or d,
        "source": source,
        "type": ptype,
        "cost": cost,
        "rel_expected": kw.pop("rel_expected", "unknown"),
        "industries": kw.pop("industries", ["all"]),
        "regions": kw.pop("regions", []),
        "authority_hint": kw.pop("authority_hint", None),
        "metrics": kw.pop("metrics", {}),
        "relevance": kw.pop("relevance", None),
        "effort": kw.pop("effort", 3),
        "purpose": kw.pop("purpose", "link"),
        "contact": kw.pop("contact", {}),
        "personalization": kw.pop("personalization", {}),
        "notes": kw.pop("notes", ""),
        "verified_live": kw.pop("verified_live", None),
        "status": "candidate",
        "excluded": False,
        "exclude_reasons": [],
        "flags": [],
        "score": None,
        "tier": None,
        "events": [],
        **kw,
    }


def library_prospects(industry: str, region: Optional[str] = None, capabilities: Optional[list] = None) -> list:
    lib = load_library()
    out = []
    for s in lib["sources"]:
        inds = s.get("industries", ["all"])
        if "all" not in inds and industry not in inds:
            continue
        regs = s.get("regions", [])
        if regs and (not region or region.upper() not in regs):
            continue
        if s.get("requires") and s["requires"] not in (capabilities or []):
            continue
        cost = "paid" if s["cost"] == "paid" else "free"
        out.append(make_prospect(
            s["domain"], source="library", ptype=s["type"], cost=cost, id=f"lib-{s['id']}",
            url=s["url"], name=s["name"], rel_expected=s.get("rel_expected", "unknown"),
            industries=inds, regions=regs, authority_hint=s.get("authority_hint"),
            effort=s.get("effort", 3), purpose=s.get("purpose", "link"),
            notes=(s.get("notes", "") + (" " + s["price_note"] if s.get("price_note") else "")).strip(),
            cost_detail=s["cost"], industry_match=("all" not in inds),
        ))
    return out


def _first(row: dict, *names):
    for n in names:
        for k, v in row.items():
            if k and k.strip().lower() == n and v not in (None, ""):
                return v
    return None


def rows_to_prospects(rows: list, *, source: str, default_type: str, default_cost: str) -> list:
    out = []
    for row in rows:
        dom = _first(row, "domain", "website", "websites", "site", "url", "referring domain", "source domain")
        if not dom:
            continue
        metrics = {
            "dr": parse_metric(_first(row, "dr", "domain rating")),
            "da": parse_metric(_first(row, "da", "domain authority")),
            "traffic": parse_metric(_first(row, "traffic", "organic traffic")),
            "spam_score": parse_metric(_first(row, "spam_score", "spam score")),
            "metrics_source": _first(row, "metrics_source") or ("vendor-claimed" if source == "vendor_sheet" else "unverified"),
        }
        rel = _first(row, "relevance")
        email = _first(row, "email", "contact_email")
        p = make_prospect(
            dom, source=source, ptype=_first(row, "type", "opportunity_type") or default_type,
            cost=_first(row, "cost") or default_cost, name=_first(row, "name", "title"),
            url=_first(row, "page_url", "url") if "://" in str(_first(row, "page_url", "url") or "") else None,
            metrics={k: v for k, v in metrics.items() if v is not None},
            relevance=float(rel) if rel not in (None, "") else None,
            notes=" ".join(str(_first(row, "notes", "note", "comment") or "").split()),
            contact={k: v for k, v in {"name": _first(row, "contact_name"), "email": email,
                                       "source_url": _first(row, "contact_source")}.items() if v},
            personalization={k: v for k, v in {
                "hook": _first(row, "hook"), "their_page_url": _first(row, "their_page_url"),
                "broken_url": _first(row, "broken_url"), "asset_url": _first(row, "asset_url"),
                "asset_summary": _first(row, "asset_summary"), "relationship": _first(row, "relationship"),
                "topics": [t.strip() for t in str(_first(row, "topics") or "").split("|") if t.strip()] or None,
            }.items() if v},
        )
        out.append(p)
    return out


def merge_prospects(existing: list, new: list) -> tuple:
    """Add new prospects. A domain+type pair is unique; existing state is preserved."""
    keys = {(p["domain"], p["type"]) for p in existing}
    added = 0
    for p in new:
        k = (p["domain"], p["type"])
        if k in keys:
            continue
        existing.append(p)
        keys.add(k)
        added += 1
    return added, len(new) - added


# --------------------------------------------------------------------------------------
# Screening and scoring
# --------------------------------------------------------------------------------------

def _host_text(p: dict) -> str:
    return " ".join([p["domain"].replace(".", " ").replace("-", " "), p.get("name", ""), p.get("notes", ""),
                     " ".join(str(v) for v in p.get("personalization", {}).values() if isinstance(v, str))])


def screen_prospect(p: dict, ctx: dict) -> None:
    """Fill excluded/exclude_reasons/flags on a prospect. Hard reasons exclude; soft flags only cost points."""
    bl, seller = ctx["blocklist"], ctx["seller_listed"]
    reasons, flags = [], []
    dom = p["domain"]
    text = _host_text(p)
    is_library = p["source"] == "library"

    if dom in bl["_domains"]:
        reasons.append(f"blocklisted: {bl['_domains'][dom]['reason']}")
    for sfx in bl.get("fake_edu_suffixes", []):
        if dom.endswith("." + sfx) or dom == sfx:
            reasons.append("fake .edu lookalike (commercial domain dressed as a university)")
    if dom in bl.get("fake_edu_domains", []):
        reasons.append("fake .edu lookalike (commercial domain dressed as a university)")
    first_label = dom.split(".")[0]
    if dom.count(".") >= 2 and (first_label in bl.get("ugc_lms_prefixes", [])
                                or (dom.endswith(".edu") and first_label in bl.get("ugc_subdomain_prefixes_on_edu", []))):
        flags.append("edu_user_content_subdomain: learning-system page anyone can create; little value")
    for pid, rx, why in bl["_compiled_hard"]:
        if rx.search(text):
            reasons.append(f"{pid}: {why}")
    for pid, rx, why in bl["_compiled_soft"]:
        if rx.search(text):
            flags.append(f"{pid}: {why}")

    if not is_library:
        if bl["_seller_re"].search(text) and p["type"] != "sponsored_placement":
            reasons.append("link-seller language in the listing (paid dofollow placement, breaks Google link-spam policy)")
        if dom in seller and p["type"] != "sponsored_placement":
            flags.append("seller_listed: appeared in a paid guest-post inventory sheet; paid-only, never organic")
            p["cost"] = "paid"
        if re.search(r"(^|\.)(info|xyz|top|click|icu|buzz)$", dom):
            flags.append("low_trust_tld")
        label = dom.split(".")[0]
        if len(label) >= 22 or sum(w in label for w in ("auto", "cheap", "insurance", "loan", "best", "online", "buy")) >= 3:
            flags.append("exact_match_keyword_domain")

    m = p.get("metrics", {})
    dr, da, traffic, spam = m.get("dr"), m.get("da"), m.get("traffic"), m.get("spam_score")
    if dr is not None and da is not None and abs(dr - da) >= 35 and not is_library:
        flags.append(f"metric_mismatch: DR {dr:g} vs DA {da:g}; at least one number is unreliable")
    if (dr or da or 0) >= 50 and traffic is not None and traffic < 200:
        flags.append("authority_without_traffic: high rating, almost no organic visitors (typical of expired or network domains)")
    if spam is not None and spam >= 30:
        reasons.append(f"spam score {spam:g}% (provider scale; treat 30%+ as unsafe)")
    elif spam is not None and spam >= 15:
        flags.append(f"spam_score_elevated: {spam:g}%")
    if m.get("metrics_source") in ("vendor-claimed", "unverified") and (dr or da):
        flags.append("metrics_unverified: authority numbers came from a seller or an unverified source")
    if p.get("verified_live") is False:
        reasons.append("domain did not resolve to a live, unparked site")

    key = (dr, da)
    if None not in key and key in ctx["cloned_metrics"] and not is_library:
        flags.append("cloned_metrics: identical DA/DR pair shared with several unrelated sites")

    if p["domain"] in ctx["suppressed"]:
        reasons.append("on the suppression list (asked not to be contacted)")

    p["excluded"] = bool(reasons)
    p["exclude_reasons"] = sorted(set(reasons))
    p["flags"] = sorted(set(flags))


def relevance_of(p: dict, ctx: dict) -> tuple:
    """Return (value 0-1, basis). A supplied value wins; otherwise estimate from the library or token overlap."""
    if p.get("relevance") is not None:
        return max(0.0, min(1.0, float(p["relevance"]))), "supplied"
    if p["source"] == "library":
        return (0.95 if p.get("industry_match") else 0.60), "library industry match"
    overlap = len(ctx["site_tokens"] & tokens(_host_text(p)))
    return min(0.8, 0.25 + 0.2 * overlap), "estimated from topic overlap; confirm by reading the page"


def score_prospect(p: dict, ctx: dict) -> None:
    types = ctx["types"]
    t = types.get(p["type"], {"attain": 0.2})
    m = p.get("metrics", {})
    rel, basis = relevance_of(p, ctx)

    rating = m.get("dr") if m.get("dr") is not None else (m.get("da") * 0.9 if m.get("da") is not None else None)
    if rating is not None:
        authority = min(rating, 80) / 80
    elif p.get("authority_hint") in AUTHORITY_HINT:
        authority = AUTHORITY_HINT[p["authority_hint"]]
    else:
        authority = 0.40
    # A nofollow or sponsored link passes little ranking authority; its value is entity, brand and referral traffic.
    if p.get("rel_expected") in ("nofollow", "sponsored", "ugc"):
        authority *= 0.5
    traffic = m.get("traffic")
    if traffic is not None:
        audience = min(1.0, math.log10(max(traffic, 1)) / 6)
    else:
        audience = AUDIENCE_HINT.get(p.get("authority_hint"), 0.30)
    integrity = 1.0 if p.get("verified_live") else 0.6
    if p["source"] != "library" and not p.get("contact") and t.get("mode") == "email":
        integrity -= 0.2
    attain = t["attain"]

    parts = {"relevance": rel, "authority": authority, "attainability": attain, "audience": audience, "integrity": max(0.0, integrity)}
    raw = 100 * sum(WEIGHTS[k] * v for k, v in parts.items())
    penalty = min(SOFT_FLAG_PENALTY_CAP, SOFT_FLAG_PENALTY * len(p["flags"]))
    p["score"] = round(max(0.0, raw - penalty), 1)
    p["score_parts"] = {k: round(v, 2) for k, v in parts.items()}
    p["score_parts"]["penalty"] = penalty
    p["relevance_basis"] = basis
    p["tier"] = "A" if p["score"] >= 70 else "B" if p["score"] >= 55 else "C" if p["score"] >= MIN_SCORE_DEFAULT else "X"


def build_context(campaign: Campaign) -> dict:
    metric_pairs = {}
    for p in campaign.prospects:
        m = p.get("metrics", {})
        if m.get("dr") is not None and m.get("da") is not None and p["source"] != "library":
            metric_pairs.setdefault((m["dr"], m["da"]), set()).add(p["domain"])
    cloned = {k for k, v in metric_pairs.items() if len(v) >= 4}
    topics = campaign.config.get("topics", []) + [campaign.config.get("industry", ""), campaign.config.get("name", "")]
    return {
        "blocklist": load_blocklist(),
        "seller_listed": load_seller_listed(),
        "types": load_library()["types"],
        "cloned_metrics": cloned,
        "site_tokens": tokens(" ".join(topics)),
        "suppressed": {normalize_domain(s) for s in campaign.suppressed() if "@" not in s},
    }


def screen_all(campaign: Campaign) -> dict:
    ctx = build_context(campaign)
    for p in campaign.prospects:
        if p["status"] in ("rejected",):
            continue
        screen_prospect(p, ctx)
        score_prospect(p, ctx)
    excluded = [p for p in campaign.prospects if p["excluded"]]
    reasons: dict = {}
    for p in excluded:
        for r in p["exclude_reasons"]:
            reasons[r.split(":")[0]] = reasons.get(r.split(":")[0], 0) + 1
    return {"screened": len(campaign.prospects), "excluded": len(excluded), "exclusion_breakdown": reasons,
            "eligible": sum(1 for p in campaign.prospects if not p["excluded"] and p["tier"] != "X")}


# --------------------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------------------

def select_shortlist(campaign: Campaign, count: int = 100, free_ratio: float = 0.7,
                     max_paid_ratio: float = 0.4, max_type_ratio: float = 0.3,
                     min_score: float = MIN_SCORE_DEFAULT) -> dict:
    """Pick the best prospects under free/paid and diversity limits. Never pads below min_score."""
    for p in campaign.prospects:
        if p["status"] == "proposed":
            p["status"] = "candidate"
    pool = [p for p in campaign.prospects
            if not p["excluded"] and p["score"] is not None and p["score"] >= min_score
            and p["status"] == "candidate"]
    pool.sort(key=lambda p: (-p["score"], p.get("effort", 3), p["domain"]))
    seen, uniq = set(), []
    for p in pool:
        if p["domain"] in seen:
            continue
        seen.add(p["domain"])
        uniq.append(p)

    free_slots = round(count * free_ratio)
    paid_cap = min(count - free_slots, int(count * max_paid_ratio)) if free_ratio < 1 else 0
    type_cap = max(1, int(count * max_type_ratio))
    chosen, per_type = [], {}

    def take(candidates, limit):
        got = 0
        for p in candidates:
            if got >= limit or len(chosen) >= count:
                break
            if per_type.get(p["type"], 0) >= type_cap:
                continue
            chosen.append(p)
            per_type[p["type"]] = per_type.get(p["type"], 0) + 1
            got += 1
        return got

    free = [p for p in uniq if p["cost"] == "free"]
    paid = [p for p in uniq if p["cost"] != "free"]
    got_free = take(free, free_slots)
    # Unfilled free slots may go to paid, but only up to the paid ceiling.
    take(paid, min(paid_cap + (free_slots - got_free), int(count * max_paid_ratio)))
    if len(chosen) < count:
        take([p for p in free if p not in chosen], count - len(chosen))
    for p in chosen:
        p["status"] = "proposed"
    chosen.sort(key=lambda p: -p["score"])
    lo = sum(campaign_type_range(p, campaign)[0] for p in chosen)
    hi = sum(campaign_type_range(p, campaign)[1] for p in chosen)
    return {
        "requested": count, "selected": len(chosen), "shortfall": max(0, count - len(chosen)),
        "free": sum(1 for p in chosen if p["cost"] == "free"), "paid": sum(1 for p in chosen if p["cost"] != "free"),
        "by_tier": {t: sum(1 for p in chosen if p["tier"] == t) for t in "ABC"},
        "by_type": per_type,
        "expected_links_low": round(lo), "expected_links_high": round(hi),
        "note": ("Shortfall means fewer prospects cleared the quality bar. Run more discovery (competitor gap, "
                 "SERP resource pages, unlinked mentions) instead of lowering the bar." if len(chosen) < count else ""),
    }


def campaign_type_range(p: dict, campaign: Campaign) -> tuple:
    r = load_library()["types"].get(p["type"], {}).get("success_range", [0.02, 0.1])
    return r[0], r[1]


# --------------------------------------------------------------------------------------
# Liveness
# --------------------------------------------------------------------------------------

PARKED_RE = re.compile(r"domain (is )?(for sale|may be for sale)|buy this domain|this domain has expired|account suspended|"
                       r"parked (free|domain)|sedo\.com|dan\.com/buy", re.I)


def check_live_one(url: str, fetch: Optional[Callable] = None) -> dict:
    """Return {live, status_code, reason}. `fetch` is injectable for tests; the default is SSRF-safe."""
    if fetch is None:
        try:
            from url_safety import safe_requests_get

            def fetch(u):  # type: ignore[no-redef]
                r = safe_requests_get(u, timeout=15, headers={"User-Agent": "claude-seo-linkcheck/1.0"}, allow_redirects=True)
                return r.status_code, r.text[:20000]
        except ImportError:
            return {"live": None, "status_code": None, "reason": "url_safety unavailable"}
    try:
        code, body = fetch(url)
    except Exception as exc:  # noqa: BLE001 - any network failure is simply "not confirmed live"
        return {"live": False, "status_code": None, "reason": f"{type(exc).__name__}: {exc}"[:160]}
    if code >= 400:
        return {"live": False, "status_code": code, "reason": f"HTTP {code}"}
    if PARKED_RE.search(body or "") or len((body or "").strip()) < 200:
        return {"live": False, "status_code": code, "reason": "parked, suspended or empty page"}
    return {"live": True, "status_code": code, "reason": "ok"}


# --------------------------------------------------------------------------------------
# Drafting
# --------------------------------------------------------------------------------------

def _first_name(contact: dict) -> str:
    name = (contact or {}).get("name", "").strip()
    return name.split()[0] if name else ""


def missing_fields(p: dict, campaign: Campaign) -> list:
    """What blocks this prospect from a send-ready draft."""
    miss = []
    c = campaign.config
    for f in ("sender_name", "sender_title"):
        if not c.get(f):
            miss.append(f"campaign.{f}")
    contact = p.get("contact", {})
    if not contact.get("email"):
        miss.append("contact.email (a publicly listed address, never a guessed one)")
    if not contact.get("name"):
        miss.append("contact.name")
    pers = p.get("personalization", {})
    for f in REQUIRED_PERSONALIZATION.get(p["type"], []):
        if not pers.get(f):
            miss.append(f"personalization.{f}")
    hook = (pers.get("hook") or "").strip()
    if hook and (len(hook) < 40 or any(g in hook.lower() for g in GENERIC_HOOKS)):
        miss.append("personalization.hook is generic; it must reference something specific on their page")
    if contact.get("email") and contact["email"].lower() in campaign.suppressed():
        miss.append("contact is on the suppression list")
    return miss


def _sign_off(c: dict) -> str:
    lines = [c.get("sender_name", ""), f"{c.get('sender_title', '')}, {c.get('name', '')}".strip(", ")]
    if c.get("sender_address"):
        lines.append(c["sender_address"])
    lines.append('If you would rather not hear from me about this, reply "no thanks" and I will not write again.')
    return "\n".join(l for l in lines if l)


def render_draft(p: dict, campaign: Campaign) -> dict:
    c, pers = campaign.config, p.get("personalization", {})
    first = _first_name(p.get("contact", {}))
    greet = f"Hi {first}," if first else "Hello,"
    asset = pers.get("asset_url") or c.get("site", "")
    topic = (c.get("topics") or ["this topic"])[0]
    page = pers.get("their_page_url", "")
    summary = pers.get("asset_summary", "")
    t = p["type"]
    if t == "unlinked_mention":
        subject = f"Thanks for mentioning {c.get('name', 'us')}"
        body = (f"{greet}\n\nThanks for mentioning {c.get('name', 'us')} on {page}. I noticed the mention does not link "
                f"to us, and readers who want to find us have to search. If you are happy to add a link to {asset}, "
                f"it would help them get there.\n\nEither way, thank you for the coverage.")
    elif t == "broken_link":
        subject = "A broken link on your page"
        body = (f"{greet}\n\nWhile reading {page} I found a link that now returns an error: {pers.get('broken_url', '')}. "
                f"In case it is useful, {summary} lives at {asset} and covers the same ground.\n\n"
                f"No pressure at all. I thought you would want to know about the dead link.")
    elif t == "resource_page":
        subject = f"Suggestion for your {topic} resources"
        body = (f"{greet}\n\nI was reading {page} and {pers.get('hook', '')}\n\nWe published {summary} at {asset}. It may "
                f"suit the people who use your list, though it is entirely your call.\n\nThanks for keeping that page useful.")
    elif t in ("competitor_gap", "digital_pr"):
        subject = f"Data your readers may find useful: {topic}"
        body = (f"{greet}\n\n{pers.get('hook', '')}\n\nWe just published {summary}: {asset}. If it is useful for something "
                f"you are working on, you are welcome to use it, and I can share the underlying numbers.\n\nThanks for your time.")
    elif t == "guest_contribution":
        topics = pers.get("topics") or []
        subject = "Two article ideas for your readers"
        body = (f"{greet}\n\n{pers.get('hook', '')}\n\nI could write either of these for you, original and unpublished "
                f"elsewhere:\n- {topics[0] if topics else ''}\n- {topics[1] if len(topics) > 1 else ''}\n\n"
                f"Happy to send an outline first if one looks right. Samples of my writing: {asset}")
    elif t == "partner_page":
        subject = f"Our work with {p.get('name', 'you')}"
        body = (f"{greet}\n\nWe {pers.get('relationship', 'work together')}, and I saw your page at {page}. "
                f"If it makes sense to mention us there, our page is {asset}. Happy to return the favour on ours.\n\nThank you.")
    elif t == "podcast_guest":
        topics = pers.get("topics") or []
        subject = f"Guest idea for your show: {topics[0] if topics else topic}"[:60]
        body = (f"{greet}\n\n{pers.get('hook', '')}\n\nI could speak about {', '.join(topics[:2])}. "
                f"If either suits an upcoming episode I would be glad to share details.\n\nThank you for considering it.")
    else:
        return {"error": f"{t} is a self-serve listing; use `kit` instead of an email draft"}
    sign = _sign_off(c)
    follow1 = (f"{greet}\n\nA short follow-up on my note about {asset}. If it is not a fit, that is completely fine.\n\n"
               f"{c.get('sender_name', '')}\n{c.get('name', '')}")
    follow2 = (f"{greet}\n\nLast note from me. If it becomes useful later, it is here: {asset}. Thank you for your time.\n\n"
               f"{c.get('sender_name', '')}\n{c.get('name', '')}")
    out = {"subject": subject[:60], "body": f"{body}\n\n{sign}", "followup_1": follow1, "followup_2": follow2}
    try:
        from content_humanize import humanize
        for k in ("subject", "body", "followup_1", "followup_2"):
            out[k] = humanize(out[k])["cleaned"]
    except ImportError:
        for k in ("subject", "body", "followup_1", "followup_2"):
            out[k] = out[k].replace("\u2014", ", ").replace("\u2013", "-")
    out["word_count"] = len(out["body"].split())
    return out


def kit_markdown(campaign: Campaign) -> str:
    c = campaign.config
    prof = c.get("profile", {})
    lines = [f"# Submission kit: {c.get('name', '')}", "",
             "Paste these fields exactly. Keep the name, address and phone identical on every listing.", "",
             "## Profile", ""]
    fields = [("Name", c.get("name")), ("Website", c.get("site")), ("Tagline (60 chars)", prof.get("tagline")),
              ("Short description (160 chars)", prof.get("short_description")),
              ("Long description (about 150 words)", prof.get("long_description")),
              ("Categories", ", ".join(prof.get("categories", [])) or None), ("Address", prof.get("address")),
              ("Phone", prof.get("phone")), ("Email", prof.get("email")), ("Logo URL", prof.get("logo_url")),
              ("Social profiles", ", ".join(prof.get("social", [])) or None), ("Founded", prof.get("founded"))]
    missing = []
    for label, val in fields:
        if val:
            lines.append(f"- **{label}:** {val}")
        else:
            lines.append(f"- **{label}:** MISSING, add `profile.{label.split(' (')[0].lower().replace(' ', '_')}` to campaign.json")
            missing.append(label)
    lines += ["", "## Approved self-serve submissions", ""]
    types = load_library()["types"]
    items = [p for p in campaign.prospects if p["status"] == "approved" and types.get(p["type"], {}).get("mode") in SELF_SERVE_MODES]
    if not items:
        lines.append("None approved yet.")
    for p in sorted(items, key=lambda x: -x["score"]):
        lines += [f"### {p['name']} ({p['cost']})", f"- Where: {p['url']}", f"- Why: {p['purpose']}; expected link attribute: {p['rel_expected']}",
                  f"- Notes: {p['notes'] or 'none'}", "- [ ] Submitted   - [ ] Live link URL recorded", ""]
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------------------
# Events, follow-ups, verification
# --------------------------------------------------------------------------------------

def log_event(p: dict, event: str, *, when: Optional[date] = None, link_url: str = "", note: str = "") -> None:
    p["events"].append({"event": event, "at": now_iso(when), "link_url": link_url, "note": note})
    status_map = {"sent": "sent", "followup_1": "followup_1", "followup_2": "followup_2", "replied": "replied",
                  "won": "won", "declined": "declined", "bounced": "bounced", "unsubscribed": "unsubscribed",
                  "lost": "lost", "no_response": "no_response"}
    if event in status_map:
        p["status"] = status_map[event]
    if event == "won" and link_url:
        p["link_url"] = link_url


def _event_date(p: dict, event: str) -> Optional[date]:
    for e in reversed(p["events"]):
        if e["event"] == event:
            return datetime.fromisoformat(e["at"]).date()
    return None


def due_items(campaign: Campaign, today: date) -> list:
    out = []
    for p in campaign.prospects:
        sent = _event_date(p, "sent")
        if p["status"] == "sent" and sent and (today - sent).days >= FOLLOWUP_1_DAYS:
            out.append({"id": p["id"], "action": "send follow-up 1", "overdue_days": (today - sent).days - FOLLOWUP_1_DAYS})
        elif p["status"] == "followup_1" and sent and (today - sent).days >= FOLLOWUP_2_DAYS:
            out.append({"id": p["id"], "action": "send follow-up 2 (last)", "overdue_days": (today - sent).days - FOLLOWUP_2_DAYS})
        elif p["status"] == "followup_2" and sent and (today - sent).days >= CLOSE_AFTER_DAYS:
            out.append({"id": p["id"], "action": "close as no_response", "overdue_days": (today - sent).days - CLOSE_AFTER_DAYS})
        if p["status"] == "won" and p.get("link_url"):
            won = _event_date(p, "won")
            done = {e["note"] for e in p["events"] if e["event"] == "verified"}
            for d in VERIFY_CHECKPOINTS:
                tag = f"day{d}"
                if won and (today - won).days >= d and tag not in done:
                    out.append({"id": p["id"], "action": f"verify link ({tag} check)", "overdue_days": (today - won).days - d})
                    break
    return out


def verify_won(campaign: Campaign, today: date, only_due: bool, verifier: Optional[Callable] = None) -> list:
    if verifier is None:
        from verify_backlinks import verify_backlinks as verifier  # network
    due_ids = {d["id"] for d in due_items(campaign, today) if d["action"].startswith("verify")}
    results = []
    for p in campaign.prospects:
        if p["status"] != "won" or not p.get("link_url"):
            continue
        if only_due and p["id"] not in due_ids:
            continue
        res = verifier(campaign.config["site"], [{"source_url": p["link_url"]}])
        r = (res.get("data", {}).get("results") or [{}])[0]
        won = _event_date(p, "won")
        tag = next((f"day{d}" for d in VERIFY_CHECKPOINTS if won and (today - won).days >= d and f"day{d}" not in
                    {e["note"] for e in p["events"] if e["event"] == "verified"}), "adhoc")
        p["events"].append({"event": "verified", "at": now_iso(today), "link_url": p["link_url"], "note": tag,
                            "status": r.get("status"), "rel": r.get("rel_attributes")})
        if r.get("status") in ("link_removed", "lost"):
            p["status"] = "lost"
        results.append({"id": p["id"], "link_url": p["link_url"], "status": r.get("status"), "rel": r.get("rel_attributes"), "check": tag})
    return results


# --------------------------------------------------------------------------------------
# Site readiness
# --------------------------------------------------------------------------------------

def assess_readiness(html: str, url: str, industry: str = "general") -> dict:
    """Pure function: score whether a homepage gives link builders something to work with."""
    low = html.lower()
    checks = []

    def add(cid, ok, label, fix, weight, level="fail"):
        checks.append({"id": cid, "pass": bool(ok), "label": label, "fix": "" if ok else fix, "weight": weight,
                       "level": "pass" if ok else level})

    add("https", url.lower().startswith("https://"), "Site is served over HTTPS", "Move the site to HTTPS and redirect HTTP; sites without it are skipped by most editors.", 8)
    robots_noindex = bool(re.search(r'<meta[^>]+name=["\']robots["\'][^>]+noindex', low))
    add("indexable", not robots_noindex, "Homepage is indexable", "Remove the noindex directive; prospects and Google both check this.", 10)
    add("canonical", "rel=\"canonical\"" in low or "rel='canonical'" in low, "Canonical URL declared", "Add a canonical tag so links consolidate on one URL.", 4, "warn")
    add("title", bool(re.search(r"<title>[^<]{10,}", low)), "Descriptive title tag", "Write a clear title; it is what appears when someone links with the page title.", 4, "warn")
    add("viewport", "name=\"viewport\"" in low or "name='viewport'" in low, "Mobile viewport set", "Make the site mobile-friendly; most editors check on a phone.", 4, "warn")
    ld = re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I)
    ld_text = " ".join(ld).lower()
    has_org = any(k in ld_text for k in ('"organization"', '"localbusiness"', '"person"', '"onlinestore"', '"professionalservice"'))
    add("org_schema", has_org, "Organization or LocalBusiness schema present", "Add Organization schema with name, logo and sameAs links so profiles and mentions resolve to one entity.", 7)
    add("sameas", "sameas" in ld_text, "sameAs links to official profiles", "List LinkedIn, Crunchbase, GitHub and other official profiles in sameAs.", 5, "warn")
    anchors = " ".join(re.findall(r"<a\b[^>]*>(.*?)</a>", html, re.S | re.I))
    anchors_text = re.sub(r"<[^>]+>", " ", anchors)
    add("contact", SITE_SIGNALS["contact"].search(anchors_text) or "mailto:" in low, "Contact route visible", "Add a contact page or address so editors can verify who you are.", 8)
    add("about", SITE_SIGNALS["about"].search(anchors_text), "About or team page linked", "Add an About page naming real people and credentials; editors will not link to anonymous sites.", 8)
    add("content_hub", SITE_SIGNALS["blog"].search(anchors_text), "Blog or resources hub linked", "Create a resources hub so there is a place for linkable pages to live.", 8)
    has_asset = SITE_SIGNALS["asset"].search(anchors_text)
    add("linkable_asset", has_asset, "Linkable asset visible (tool, data, research, template)", "Nothing here gives a site a reason to link. Build at least one asset from the ideas below before outreach.", 18)
    add("authors", SITE_SIGNALS["author"].search(html), "Named authors or reviewers on content", "Add bylines with short bios and credentials; this is also an E-E-A-T signal.", 6, "warn")
    add("legal", SITE_SIGNALS["legal"].search(anchors_text), "Privacy and terms pages linked", "Add privacy and terms pages; they signal a real business to reviewers.", 4, "warn")
    if industry in ("local_service", "healthcare", "legal", "home_services", "real_estate", "hospitality", "retail"):
        add("nap", bool(PHONE_RE.search(re.sub(r"<[^>]+>", " ", html))), "Phone number visible (local NAP)", "Show name, address and phone in the footer; citations must match it exactly.", 6)
    total = sum(c["weight"] for c in checks)
    got = sum(c["weight"] for c in checks if c["pass"])
    score = round(100 * got / total) if total else 0
    fails = sorted([c for c in checks if not c["pass"]], key=lambda c: -c["weight"])
    verdict = ("ready" if score >= 80 and has_asset else "fix_first" if score < 60 or not has_asset else "mostly_ready")
    return {"url": url, "score": score, "verdict": verdict, "checks": checks, "priorities": [c["fix"] for c in fails],
            "asset_ideas": ASSET_IDEAS.get(industry, ASSET_IDEAS["general"]) + ([] if industry == "general" else ASSET_IDEAS["general"][:1])}


# --------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------

def funnel(campaign: Campaign) -> dict:
    counts = {s: 0 for s in STATUS_ORDER}
    for p in campaign.prospects:
        counts[p["status"]] = counts.get(p["status"], 0) + 1
    sent = sum(1 for p in campaign.prospects if _event_date(p, "sent"))
    replied = sum(1 for p in campaign.prospects if any(e["event"] == "replied" for e in p["events"]))
    won = counts.get("won", 0) + counts.get("lost", 0)
    return {"counts": counts, "contacted": sent, "reply_rate": round(replied / sent, 3) if sent else None,
            "win_rate": round(won / sent, 3) if sent else None, "links_won": won, "links_still_live": counts.get("won", 0)}


def row_for_report(p: dict) -> dict:
    m = p.get("metrics", {})
    return {"id": p["id"], "name": p["name"], "domain": p["domain"], "type": p["type"], "cost": p["cost"],
            "score": p["score"], "tier": p["tier"], "rel_expected": p["rel_expected"], "purpose": p["purpose"],
            "dr": m.get("dr"), "da": m.get("da"), "traffic": m.get("traffic"), "metrics_source": m.get("metrics_source", ""),
            "status": p["status"], "notes": p["notes"], "flags": p["flags"], "effort": p.get("effort")}


def build_report_data(campaign: Campaign) -> dict:
    types = load_library()["types"]
    short = [p for p in campaign.prospects if p["status"] in ("proposed", "approved", "drafted", "sent", "followup_1",
                                                               "followup_2", "replied", "won", "declined", "no_response", "lost")]
    short.sort(key=lambda p: -(p["score"] or 0))
    lo = sum(types.get(p["type"], {}).get("success_range", [0.02, 0.1])[0] for p in short)
    hi = sum(types.get(p["type"], {}).get("success_range", [0.02, 0.1])[1] for p in short)
    excluded = [p for p in campaign.prospects if p["excluded"]]
    breakdown: dict = {}
    for p in excluded:
        for r in p["exclude_reasons"]:
            key = r.split(":")[0]
            breakdown[key] = breakdown.get(key, 0) + 1
    by_type: dict = {}
    for p in short:
        by_type[p["type"]] = by_type.get(p["type"], 0) + 1
    cfg = campaign.config
    return {"linkbuilding": {
        "site": cfg.get("site"), "name": cfg.get("name"), "industry": cfg.get("industry"), "topics": cfg.get("topics", []),
        "generated": now_iso(),
        "summary": {"candidates_reviewed": len(campaign.prospects), "rejected_by_screening": len(excluded),
                    "shortlist": len(short), "free": sum(1 for p in short if p["cost"] == "free"),
                    "paid": sum(1 for p in short if p["cost"] != "free"),
                    "tier_a": sum(1 for p in short if p["tier"] == "A"), "tier_b": sum(1 for p in short if p["tier"] == "B"),
                    "tier_c": sum(1 for p in short if p["tier"] == "C"),
                    "expected_links_low": round(lo), "expected_links_high": round(hi)},
        "rejection_breakdown": breakdown,
        "by_type": [{"type": t, "label": types.get(t, {}).get("label", t), "count": n,
                     "success_range": types.get(t, {}).get("success_range")} for t, n in sorted(by_type.items(), key=lambda kv: -kv[1])],
        "free_prospects": [row_for_report(p) for p in short if p["cost"] == "free"],
        "paid_prospects": [row_for_report(p) for p in short if p["cost"] != "free"],
        "readiness": cfg.get("readiness"), "baseline": cfg.get("baseline"), "funnel": funnel(campaign),
        "profile_gaps": [k for k in ("tagline", "short_description", "long_description", "address", "phone") if not cfg.get("profile", {}).get(k)],
    }}


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def emit(args, payload, text: str = "") -> None:
    if getattr(args, "json", False) or not text:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(text)


def table(rows: list, cols: list) -> str:
    widths = [max(len(str(c)), *(len(str(r.get(c, ""))) for r in rows)) if rows else len(c) for c in cols]
    line = lambda r: "  ".join(str(r.get(c, ""))[:w].ljust(w) for c, w in zip(cols, widths))
    return "\n".join([line({c: c for c in cols}), line({c: "-" * w for c, w in zip(cols, widths)})] + [line(r) for r in rows])


def cmd_init(a):
    os.makedirs(a.campaign, exist_ok=True)
    if os.path.exists(os.path.join(a.campaign, "campaign.json")) and not a.force:
        raise SystemExit("Campaign exists. Use --force to overwrite.")
    cfg = {"site": a.site, "name": a.name, "industry": a.industry, "region": a.region,
           "topics": [t.strip() for t in (a.topics or "").split(",") if t.strip()],
           "capabilities": [t.strip() for t in (a.capabilities or "").split(",") if t.strip()],
           "sender_name": a.sender_name, "sender_title": a.sender_title, "sender_address": a.sender_address,
           "profile": {}, "created": now_iso()}
    save_json(os.path.join(a.campaign, "campaign.json"), cfg)
    save_json(os.path.join(a.campaign, "prospects.json"), {"prospects": []})
    emit(a, {"campaign": a.campaign, "config": cfg}, f"Created campaign at {a.campaign}")


def cmd_library(a):
    c = Campaign(a.campaign)
    added, skipped = merge_prospects(c.prospects, library_prospects(c.config["industry"], c.config.get("region"), c.config.get("capabilities")))
    c.save()
    emit(a, {"added": added, "already_present": skipped}, f"Library: added {added}, skipped {skipped} already present.")


def cmd_ingest(a):
    c = Campaign(a.campaign)
    path = a.file
    if path.lower().endswith(".json"):
        data = load_json(path)
        rows = data.get("prospects", data) if isinstance(data, dict) else data
    else:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
    new = rows_to_prospects(rows, source=a.source, default_type=a.type, default_cost=a.cost)
    added, skipped = merge_prospects(c.prospects, new)
    c.save()
    emit(a, {"added": added, "duplicates": skipped, "source": a.source}, f"Ingested {added} prospects ({skipped} duplicates).")


def cmd_check_live(a):
    c = Campaign(a.campaign)
    n = 0
    for p in c.prospects:
        if p["verified_live"] is not None and not a.recheck:
            continue
        if a.limit and n >= a.limit:
            break
        res = check_live_one(p["url"])
        p["verified_live"] = res["live"]
        if res["live"] is False:
            p["live_reason"] = res["reason"]
        n += 1
    c.save()
    emit(a, {"checked": n, "live": sum(1 for p in c.prospects if p["verified_live"]),
             "dead": sum(1 for p in c.prospects if p["verified_live"] is False)}, f"Checked {n} domains.")


def cmd_screen(a):
    c = Campaign(a.campaign)
    res = screen_all(c)
    c.save()
    emit(a, res, f"Screened {res['screened']}: {res['excluded']} excluded, {res['eligible']} eligible. {res['exclusion_breakdown']}")


def cmd_select(a):
    c = Campaign(a.campaign)
    res = select_shortlist(c, a.count, a.free_ratio, a.max_paid_ratio, a.max_type_ratio, a.min_score)
    c.save()
    emit(a, res, (f"Selected {res['selected']} of {a.count} ({res['free']} free, {res['paid']} paid). "
                  f"Planning estimate: {res['expected_links_low']} to {res['expected_links_high']} links if all are pursued. {res['note']}"))


def cmd_shortlist(a):
    c = Campaign(a.campaign)
    rows = [row_for_report(p) for p in c.prospects if p["status"] in ("proposed", "approved") ]
    rows.sort(key=lambda r: -(r["score"] or 0))
    if a.cost:
        rows = [r for r in rows if (r["cost"] == "free") == (a.cost == "free")]
    emit(a, {"shortlist": rows}, table(rows, ["id", "tier", "score", "cost", "type", "rel_expected", "status", "name"]))


def cmd_approve(a):
    c = Campaign(a.campaign)
    if a.ids:
        targets = [c.find(i) for i in a.ids.split(",")]
    elif a.tier:
        targets = [p for p in c.prospects if p["status"] == "proposed" and p["tier"] in a.tier.split(",")]
    elif a.all_proposed:
        targets = [p for p in c.prospects if p["status"] == "proposed"]
    else:
        raise SystemExit("Specify --ids, --tier or --all-proposed.")
    done = []
    for p in targets:
        if p["status"] not in ("proposed", "candidate"):
            continue
        if p["excluded"]:
            continue
        p["status"] = "approved"
        p["approval"] = {"by": a.by, "at": now_iso()}
        done.append(p["id"])
    c.save()
    emit(a, {"approved": done}, f"Approved {len(done)} prospects.")


def cmd_reject(a):
    c = Campaign(a.campaign)
    for i in a.ids.split(","):
        p = c.find(i)
        p["status"] = "rejected"
        p["events"].append({"event": "rejected", "at": now_iso(), "note": a.reason})
    c.save()
    emit(a, {"rejected": a.ids.split(",")}, f"Rejected {len(a.ids.split(','))}.")


def cmd_draft(a):
    c = Campaign(a.campaign)
    out = []
    for p in c.prospects:
        if p["status"] != "approved" or p["type"] not in EMAIL_TYPES:
            continue
        miss = missing_fields(p, c)
        if miss:
            p["draft"] = None
            out.append({"id": p["id"], "ready": False, "missing": miss})
            continue
        draft = render_draft(p, c)
        if draft["word_count"] > MAX_DRAFT_WORDS:
            p["draft"] = None
            out.append({"id": p["id"], "ready": False,
                        "missing": [f"draft is {draft['word_count']} words (limit {MAX_DRAFT_WORDS}); shorten the hook or asset_summary"]})
            continue
        p["draft"] = draft
        p["status"] = "drafted"
        out.append({"id": p["id"], "ready": True, "subject": draft["subject"], "words": draft["word_count"]})
    c.save()
    ready = sum(1 for o in out if o["ready"])
    emit(a, {"drafts": out}, f"{ready} drafted, {len(out) - ready} blocked (see missing fields).")


def cmd_kit(a):
    c = Campaign(a.campaign)
    path = os.path.join(a.campaign, "submission-kit.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(kit_markdown(c))
    emit(a, {"written": path}, f"Wrote {path}")


def cmd_export(a):
    c = Campaign(a.campaign)
    rows = []
    for p in c.prospects:
        if p["status"] != "drafted" or not p.get("draft"):
            continue
        d = p["draft"]
        rows.append({"id": p["id"], "domain": p["domain"], "to_name": p["contact"].get("name", ""),
                     "to_email": p["contact"]["email"], "subject": d["subject"], "body": d["body"],
                     "followup_1": d["followup_1"], "followup_2": d["followup_2"]})
    path = a.out or os.path.join(a.campaign, "outreach-approved.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "domain", "to_name", "to_email", "subject", "body", "followup_1", "followup_2"])
        w.writeheader()
        w.writerows(rows)
    emit(a, {"written": path, "rows": len(rows)}, f"Wrote {len(rows)} send-ready rows to {path}. Nothing has been sent.")


def cmd_log(a):
    c = Campaign(a.campaign)
    p = c.find(a.id)
    log_event(p, a.event, when=parse_day(a.date) if a.date else None, link_url=a.link_url or "", note=a.note or "")
    if a.event in ("declined", "unsubscribed", "bounced") and p.get("contact", {}).get("email"):
        c.suppress(p["contact"]["email"])
    if a.event in ("declined", "unsubscribed"):
        c.suppress(p["domain"])
    c.save()
    emit(a, {"id": p["id"], "status": p["status"]}, f"{p['id']}: {p['status']}")


def cmd_due(a):
    c = Campaign(a.campaign)
    items = due_items(c, parse_day(a.today))
    emit(a, {"due": items}, table(items, ["id", "action", "overdue_days"]) if items else "Nothing due.")


def cmd_verify(a):
    c = Campaign(a.campaign)
    res = verify_won(c, parse_day(a.today), a.due)
    c.save()
    emit(a, {"checked": res}, f"Verified {len(res)} links.")


def cmd_status(a):
    c = Campaign(a.campaign)
    f = funnel(c)
    emit(a, f, "\n".join(f"{k}: {v}" for k, v in f["counts"].items() if v) + f"\nreply rate: {f['reply_rate']}  win rate: {f['win_rate']}")


def cmd_baseline(a):
    c = Campaign(a.campaign)
    base = c.config.get("baseline", {})
    for kv in a.values:
        k, _, v = kv.partition("=")
        base[k.strip()] = parse_metric(v) if parse_metric(v) is not None else v
    base["captured"] = now_iso()
    c.config["baseline"] = base
    c.save()
    emit(a, base, f"Baseline stored: {base}")


def cmd_report_data(a):
    c = Campaign(a.campaign)
    data = build_report_data(c)
    out = a.out or os.path.join(a.campaign, "report-data.json")
    save_json(out, data)
    emit(a, {"written": out, "summary": data["linkbuilding"]["summary"]}, f"Wrote {out}")


def cmd_readiness(a):
    if a.html_file:
        html = Path(a.html_file).read_text(encoding="utf-8", errors="replace")
    else:
        from fetch_page import fetch_page
        res = fetch_page(a.url)
        if res.get("error") or not res.get("content"):
            raise SystemExit(f"Could not fetch {a.url}: {res.get('error')}")
        html = res["content"]
    out = assess_readiness(html, a.url, a.industry)
    if a.campaign:
        c = Campaign(a.campaign)
        c.config["readiness"] = out
        c.save()
    text = f"Readiness {out['score']}/100 ({out['verdict']})\n" + "\n".join(f"- {p}" for p in out["priorities"])
    emit(a, out, text)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Link-building campaign engine (screen, select, approve, draft, track, verify).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("--json", action="store_true")
        sp.set_defaults(fn=fn)
        return sp

    def camp(sp):
        sp.add_argument("--campaign", required=True, help="Campaign directory")

    sp = add("init", cmd_init, "Create a campaign"); camp(sp)
    sp.add_argument("--site", required=True); sp.add_argument("--name", required=True)
    sp.add_argument("--industry", default="general"); sp.add_argument("--region", default=None)
    sp.add_argument("--topics", default=""); sp.add_argument("--capabilities", default="", help="comma list: browser_extension, wordpress_plugin, shopify_app, atlassian_app, public_api, open_source")
    sp.add_argument("--sender-name", default="")
    sp.add_argument("--sender-title", default=""); sp.add_argument("--sender-address", default="")
    sp.add_argument("--force", action="store_true")
    sp = add("library", cmd_library, "Add evergreen sources for the industry"); camp(sp)
    sp = add("ingest", cmd_ingest, "Add prospects from CSV/JSON"); camp(sp)
    sp.add_argument("--file", required=True)
    sp.add_argument("--source", default="manual", choices=["manual", "competitor_gap", "serp", "mention", "broken", "vendor_sheet"])
    sp.add_argument("--type", default="competitor_gap"); sp.add_argument("--cost", default="free", choices=["free", "paid"])
    sp = add("check-live", cmd_check_live, "Confirm domains are live and unparked"); camp(sp)
    sp.add_argument("--limit", type=int, default=0); sp.add_argument("--recheck", action="store_true")
    sp = add("screen", cmd_screen, "Apply disqualifiers and scoring"); camp(sp)
    sp = add("select", cmd_select, "Pick the shortlist"); camp(sp)
    sp.add_argument("--count", type=int, default=100); sp.add_argument("--free-ratio", type=float, default=0.7)
    sp.add_argument("--max-paid-ratio", type=float, default=0.4); sp.add_argument("--max-type-ratio", type=float, default=0.3)
    sp.add_argument("--min-score", type=float, default=MIN_SCORE_DEFAULT)
    sp = add("shortlist", cmd_shortlist, "Show the shortlist"); camp(sp)
    sp.add_argument("--cost", choices=["free", "paid"])
    sp = add("approve", cmd_approve, "Human gate: approve prospects"); camp(sp)
    sp.add_argument("--ids"); sp.add_argument("--tier"); sp.add_argument("--all-proposed", action="store_true")
    sp.add_argument("--by", default="owner")
    sp = add("reject", cmd_reject, "Reject prospects"); camp(sp)
    sp.add_argument("--ids", required=True); sp.add_argument("--reason", default="")
    sp = add("draft", cmd_draft, "Draft emails for approved prospects"); camp(sp)
    sp = add("kit", cmd_kit, "Write the self-serve submission kit"); camp(sp)
    sp = add("export", cmd_export, "Write the mail-merge CSV"); camp(sp)
    sp.add_argument("--out")
    sp = add("log", cmd_log, "Record an event"); camp(sp)
    sp.add_argument("--id", required=True)
    sp.add_argument("--event", required=True, choices=["sent", "followup_1", "followup_2", "replied", "won", "declined", "bounced", "unsubscribed", "lost", "no_response"])
    sp.add_argument("--link-url"); sp.add_argument("--note"); sp.add_argument("--date")
    sp = add("due", cmd_due, "Follow-ups and verifications due"); camp(sp)
    sp.add_argument("--today")
    sp = add("verify", cmd_verify, "Re-check won links"); camp(sp)
    sp.add_argument("--due", action="store_true"); sp.add_argument("--today")
    sp = add("status", cmd_status, "Funnel counts"); camp(sp)
    sp = add("baseline", cmd_baseline, "Store before-metrics (key=value ...)"); camp(sp)
    sp.add_argument("values", nargs="+")
    sp = add("report-data", cmd_report_data, "Write report JSON"); camp(sp)
    sp.add_argument("--out")
    sp = add("readiness", cmd_readiness, "Audit whether the site can earn links")
    sp.add_argument("--url", required=True); sp.add_argument("--industry", default="general")
    sp.add_argument("--html-file"); sp.add_argument("--campaign")
    return ap


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    args.fn(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
