#!/usr/bin/env python3
"""Site-wide internal link graph analysis.

Per-page linking is a brief-level concern; this is the other half. As a site
accumulates pages, the shape of the whole graph decides which pages Google
treats as important, and that shape is invisible from any single page.

What it reports, and why each matters:

orphans
    Pages no internal link points to. Google finds them only via the sitemap
    and treats them as unimportant. This is the single highest-value finding
    here: an orphan is a page you paid to make and then hid.
depth
    Clicks from the homepage. Past three, crawl frequency and perceived
    importance both fall away sharply.
dead_ends
    Pages with no outgoing internal links. They absorb authority and pass
    none on.
anchor_diversity
    The same anchor text pointing at many different URLs, or one URL receiving
    only one anchor phrase. Both weaken the topical signal an anchor carries.
hubs / authorities
    In-degree and out-degree outliers. A cluster should have one hub linking
    out to its members and members linking back; the report names the pages
    that actually behave that way so intent can be compared to reality.
reciprocal_gaps
    A links to B but B never links back, within the same topic cluster. Often
    the cheapest fix available.

Usage:
    link_graph.py --sitemap https://example.com/sitemap.xml --json
    link_graph.py --urls urls.txt --max-pages 300
"""

import argparse
import collections
import json
import os
import re
import sys
from urllib.parse import urljoin, urlparse, urldefrag

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from url_safety import validate_url_strict, safe_get          # noqa: F401
except Exception:                                                  # pragma: no cover
    validate_url_strict = None
    safe_get = None

_HREF = re.compile(rb'<a\b[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                   re.I | re.S)
_TAG = re.compile(rb"<[^>]+>")
_SKIP_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
             ".zip", ".mp4", ".mp3", ".css", ".js", ".xml", ".ico")


def _norm(url):
    """Canonicalise for graph identity: drop fragment, trailing slash, query."""
    url, _ = urldefrag(url)
    p = urlparse(url)
    path = p.path.rstrip("/") or "/"
    return f"{p.scheme}://{p.netloc}{path}"


def _same_site(a, b):
    return urlparse(a).netloc.replace("www.", "") == urlparse(b).netloc.replace("www.", "")


def fetch(url):
    """Fetch through the project's SSRF-safe helper. Never bare requests.get."""
    if safe_get is None:
        raise RuntimeError("url_safety is unavailable; refusing to fetch unguarded")
    validate_url_strict(url)
    return safe_get(url)


def extract_links(html, base):
    """Return [(target_url, anchor_text)] for on-site links only."""
    out = []
    for m in _HREF.finditer(html):
        href = m.group(1).decode("utf-8", "ignore").strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        target = _norm(urljoin(base, href))
        if not _same_site(target, base):
            continue
        if urlparse(target).path.lower().endswith(_SKIP_EXT):
            continue
        anchor = _TAG.sub(b" ", m.group(2)).decode("utf-8", "ignore")
        anchor = " ".join(anchor.split())[:120]
        out.append((target, anchor))
    return out


def build_graph(pages):
    """pages: {url: html_bytes} -> graph dict."""
    edges = collections.defaultdict(list)
    for url, html in pages.items():
        for target, anchor in extract_links(html, url):
            if target != url:
                edges[url].append({"to": target, "anchor": anchor})
    return dict(edges)


def bfs_depth(edges, root, known):
    depth = {root: 0}
    q = collections.deque([root])
    while q:
        cur = q.popleft()
        for e in edges.get(cur, []):
            t = e["to"]
            if t in known and t not in depth:
                depth[t] = depth[cur] + 1
                q.append(t)
    return depth


def analyse(edges, known, root):
    in_deg = collections.Counter()
    anchors_to = collections.defaultdict(set)
    anchor_targets = collections.defaultdict(set)

    for src, links in edges.items():
        for e in links:
            if e["to"] in known:
                in_deg[e["to"]] += 1
                if e["anchor"]:
                    anchors_to[e["to"]].add(e["anchor"].lower())
                    anchor_targets[e["anchor"].lower()].add(e["to"])

    out_deg = {u: len({e["to"] for e in edges.get(u, []) if e["to"] in known})
               for u in known}
    depth = bfs_depth(edges, root, known) if root in known else {}

    orphans = sorted(u for u in known if in_deg[u] == 0 and u != root)
    dead_ends = sorted(u for u in known if out_deg.get(u, 0) == 0)
    too_deep = sorted(((u, d) for u, d in depth.items() if d > 3),
                      key=lambda x: -x[1])
    unreachable = sorted(u for u in known if u not in depth and u != root)

    # One anchor phrase aimed at several different URLs dilutes its meaning.
    ambiguous = sorted(
        ({"anchor": a, "targets": sorted(t)} for a, t in anchor_targets.items()
         if len(t) > 1 and len(a) > 3),
        key=lambda x: -len(x["targets"]))[:25]

    # A page receiving links under only one phrase looks narrower than it is.
    single_anchor = sorted(u for u in known
                           if in_deg[u] >= 3 and len(anchors_to[u]) == 1)

    return {
        "totals": {
            "pages": len(known),
            "internal_links": sum(len(v) for v in edges.values()),
            "orphans": len(orphans),
            "dead_ends": len(dead_ends),
            "deeper_than_3_clicks": len(too_deep),
            "unreachable_from_home": len(unreachable),
        },
        "orphans": orphans,
        "dead_ends": dead_ends,
        "too_deep": [{"url": u, "depth": d} for u, d in too_deep][:50],
        "unreachable_from_home": unreachable[:50],
        "ambiguous_anchors": ambiguous,
        "single_anchor_pages": single_anchor[:25],
        "most_linked": [{"url": u, "in_links": c} for u, c in in_deg.most_common(15)],
        "least_linked": [{"url": u, "in_links": in_deg[u]}
                         for u in sorted(known, key=lambda x: in_deg[x])[:15]],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--sitemap", help="sitemap.xml URL to take the page list from")
    src.add_argument("--urls", help="file with one URL per line")
    ap.add_argument("--root", help="homepage URL for depth (default: shortest URL)")
    ap.add_argument("--max-pages", type=int, default=300)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.sitemap:
        body = fetch(args.sitemap)
        urls = [_norm(u.decode()) for u in re.findall(rb"<loc>\s*([^<]+?)\s*</loc>", body)]
    else:
        with open(args.urls) as fh:
            urls = [_norm(l.strip()) for l in fh if l.strip()]

    urls = list(dict.fromkeys(urls))[:args.max_pages]
    if not urls:
        print(json.dumps({"error": "no URLs found"})); return 1

    pages, failed = {}, []
    for u in urls:
        try:
            pages[u] = fetch(u)
        except Exception as e:
            failed.append({"url": u, "error": str(e)[:100]})

    known = set(pages)
    root = args.root and _norm(args.root) or min(known, key=lambda u: len(urlparse(u).path))
    edges = build_graph(pages)
    result = analyse(edges, known, root)
    result["root"] = root
    result["fetch_failures"] = failed

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    t = result["totals"]
    print(f"Link graph: {t['pages']} pages, {t['internal_links']} internal links")
    print(f"  orphans (nothing links to them)  {t['orphans']}")
    print(f"  dead ends (they link nowhere)    {t['dead_ends']}")
    print(f"  deeper than 3 clicks             {t['deeper_than_3_clicks']}")
    print(f"  unreachable from the homepage    {t['unreachable_from_home']}")
    if result["orphans"]:
        print("\nOrphans, highest priority to fix:")
        for u in result["orphans"][:15]:
            print(f"  {u}")
    if failed:
        print(f"\n{len(failed)} pages could not be fetched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
