# Ahrefs harvest (one-off access window)

Use when the owner connects Ahrefs for a limited time. Goal: capture everything the weekly routines will need for
months, in priority order, so the most valuable data is saved even if access ends early. Read `RULES.md` first.

## Before the first call

1. Connectors load when a session starts. If no `mcp__Ahrefs__*` tools are listed, tell the owner to connect Ahrefs
   at claude.ai/customize/connectors and open a new session.
2. Call the Ahrefs `doc` tool for each tool before first use (its input schema is only in `doc`).
3. Call `subscription-info-limits-and-usage` (free). If it returns "Insufficient plan", STOP: the plan has no API
   access, and nothing below will work. Record the remaining units in `$S/.seo/ahrefs/<TODAY>/limits.json`.
4. Save every response as JSON under `$S/.seo/ahrefs/<TODAY>/` in the **site repo**, never in the engine repo
   (it is public, and Ahrefs data must not be republished). Commit and push after each tier, so nothing is lost if the
   session ends.

Targets: the client domain (`mode: subdomains`) and its top competitors. Use 5 competitors per site; fewer if units are short.

## Tier 1: link building (do first, highest value)

| Call | For | Settings | Save as |
|------|-----|----------|---------|
| `site-explorer-metrics` | client and each competitor | today's date | `metrics-<domain>.json` |
| `site-explorer-organic-competitors` | client | top 10 | `organic-competitors.json` (pick the 5 most relevant real competitors from it) |
| `site-explorer-referring-domains` | client | all, sort by domain rating | `refdomains-client.json` (the baseline) |
| `site-explorer-referring-domains` | each competitor | dofollow, top 1000 by domain rating | `refdomains-<domain>.json` |
| `site-explorer-broken-backlinks` | each competitor | top 200 | `broken-<domain>.json` (broken-link targets) |
| `site-explorer-pages-by-backlinks` | each competitor | top 50 | `linkmagnets-<domain>.json` (which assets earn links) |
| `site-explorer-broken-backlinks` | client | all | `broken-client.json` (links to reclaim with redirects) |

Then build the gap and load it into the campaign:

```bash
python3 $E/scripts/linkbuilding.py gap --client $S/.seo/ahrefs/<TODAY>/refdomains-client.json \
  --competitors $S/.seo/ahrefs/<TODAY>/refdomains-*.json --min-shared 2 --out $S/.seo/ahrefs/<TODAY>/gap.csv
python3 $E/scripts/linkbuilding.py ingest --campaign $C --file $S/.seo/ahrefs/<TODAY>/gap.csv --source competitor_gap --type competitor_gap
python3 $E/scripts/linkbuilding.py screen --campaign $C && python3 $E/scripts/linkbuilding.py select --campaign $C
```

(`refdomains-client.json` also matches the competitor pattern; the gap command drops domains that already link to the
client, so including it does no harm.)

## Tier 2: content and keywords

| Call | For | Settings | Save as |
|------|-----|----------|---------|
| `site-explorer-organic-keywords` | client | top 1000 by traffic, with positions | `keywords-client.json` |
| `site-explorer-organic-keywords` | each competitor | top 300 by traffic | `keywords-<domain>.json` (content gaps) |
| `site-explorer-top-pages` | each competitor | top 50 | `toppages-<domain>.json` |
| `keywords-explorer-overview` | the site's 10 to 20 target searches | the site's country | `targets-overview.json` (volumes, difficulty) |
| `serp-overview` | each target search | the site's country | `serp-<keyword>.json` (who ranks and their authority) |

## Tier 3: if units remain

| Call | For | Save as |
|------|-----|---------|
| `batch-analysis` | the top 100 gap domains, to confirm rating and traffic in one call | `gap-batch.json` |
| `brand-radar-*` mentions or impressions | the brand, if the plan includes it | `brand-radar.json` (AI answer visibility baseline) |
| `site-explorer-anchors` | client | `anchors-client.json` |

## After the harvest

1. Record the baseline from it: `referring_domains` from `metrics-<client>.json` with
   `linkbuilding.py baseline --campaign $C referring_domains=<n>`.
2. Write `$S/.seo/ahrefs/<TODAY>/SUMMARY.md`: client rating, referring domains, top 5 competitors with their ratings
   and referring domains, gap size, the 10 best gap prospects, the 10 best content gaps, and what was not pulled.
3. Commit and push `$S/.seo/`. Tell the owner what was captured, how many units were used, and what to skip next time.
4. The data is dated. Weekly runs use it as a starting list; `check-live` and `screen` still apply before outreach.
