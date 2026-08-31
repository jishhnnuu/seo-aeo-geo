---
name: seo-screaming-frog
description: Screaming Frog SEO Spider CLI wrapper (extension). Enterprise-scale crawling — tens of thousands to millions of URLs, bulk CSV export, redirect-chain mapping — for sites past what seo-audit's ~500-page subagent crawl or seo-firecrawl's API scraping are built for. Requires a Screaming Frog SEO Spider licence you already own.
metadata:
  version: "1.7.0"
compatibility: "Requires a purchased Screaming Frog SEO Spider licence with its CLI binary (screamingfrogseospider) on $PATH. Run extensions/screaming-frog/install.sh to check and register."
---

# seo-screaming-frog

Screaming Frog is the desktop-crawler gold standard most enterprise SEO
teams already run — this skill just automates the CLI mode of a licence
you already own (or are buying), so its output feeds straight into a
claude-seo audit instead of living in a separate spreadsheet.

**This does not replace the free version's 500-URL cap for free** — the
CLI mode this wraps still enforces whatever licence tier is installed.
Buy the licence (screamingfrog.co.uk/seo-spider) if you want to actually
exceed 500 URLs; this skill has no way around that, nor would you want
it to.

## When to reach for this instead of the built-in crawlers

| Situation | Use |
|---|---|
| Up to ~500 pages, no local install wanted | `/seo audit <url>` (built-in, free, 15 parallel subagents) |
| API-driven scrape/crawl, JS-heavy site, no desktop install | `seo-firecrawl` extension |
| Tens of thousands+ URLs, redirect-chain mapping, bulk CSV, XPath extraction | This extension |

## Prerequisites

- A purchased Screaming Frog SEO Spider licence.
- Its CLI binary (`screamingfrogseospider`) on `$PATH`.
- Run `extensions/screaming-frog/install.sh` — it checks for the binary
  before installing anything and tells you exactly what's missing if not.

## Routing

| Command | Effect |
|---|---|
| `/seo screaming-frog <url>` | Headless crawl, up to 50,000 URLs, bulk CSV export to a temp dir |
| `/seo screaming-frog <url> --max-urls 200000` | Raise the cap for very large sites |
| `/seo screaming-frog <url> --output-dir ./crawls/acme` | Persist the raw CSVs instead of a temp dir |

All flags forward to `scripts/screaming_frog_run.py`, which handles
`url_safety` pre-flight, subprocess timeout management, and parses the
key bulk exports (`internal_all.csv`, `response_codes_all.csv`,
`canonicals_all.csv`, redirect chains) into one JSON summary:
`urls_crawled`, `status_code_breakdown`, `redirect_count`,
`canonical_rows`, plus `output_dir` pointing at the full raw CSVs for
anything the summary doesn't cover.

## Cross-skill delegation

- Feed `status_code_breakdown` and `redirect_count` into
  `skills/seo-technical/SKILL.md`'s crawlability/indexability findings.
- Feed `canonicals_all.csv` rows into `skills/seo-schema/SKILL.md` or
  `skills/seo-technical/SKILL.md`'s canonical-consistency checks.
- For sites this size, also consider `seo-drift` baselines on the
  highest-value URL segments rather than the whole crawl, since
  drift-comparing 100k+ URLs on every run is not the intended use case.

## Error handling

| Scenario | Action |
|---|---|
| `screamingfrogseospider` not on PATH | Report the exact install/licence steps from `docs/SCREAMING-FROG-SETUP.md`; do not attempt a workaround. |
| Crawl times out | Suggest a lower `--max-urls` or a longer `--timeout`, not a silent partial-result claim. |
| Non-zero exit code | Surface `stderr` verbatim (truncated) so the user can diagnose licence/config issues themselves. |
