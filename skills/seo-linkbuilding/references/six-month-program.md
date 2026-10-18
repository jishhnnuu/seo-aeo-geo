# Six-Month Program

The standard engagement for every new client: a dated, 26-week program that does the work a traditional agency spreads
over 12 months. Generated per client by `linkbuilding.py program`; this file explains the design so it can be tuned.
Strategy context is in [operating-model.md](operating-model.md).

## New client: what happens when the owner names a client

1. **Intake (day 1).** Ask only what cannot be found: industry, regions served, 3 to 5 competitors, named partners,
   suppliers and customers, one named expert with credentials, sender name and address, access to Search Console and
   GA4. Look up everything else from the site.
2. **Set up (day 1).** `init`, `baseline`, `readiness`, `library`, `screen`, `select`, `program --start <monday>`.
3. **First deliverables (week 1).** The audit fixes, the readiness verdict, the foundation shortlist for approval, the
   asset brief, and `program.md` with every task dated and owned.
4. **Every week after.** Run `week` for the client: do the claude tasks, hand the owner a short list of approvals and
   sends, log what came back. Monthly, run `verify --due` and compare with the baseline.

## Why a traditional year is slow, and what removes the delay

| Traditional 12 months | Cause of the delay | What the six-month program does instead |
|-----------------------|--------------------|------------------------------------------|
| Months 1 to 3: audit, then fixes, then citations, one after the other | Work done in sequence by one person | Audit, fixes, listings and asset brief all run in weeks 1 to 4 |
| One linkable asset in month 4 or 5 | Assets treated as an extra | Asset 1 ships in week 6, asset 2 in week 15, refresh in week 22 |
| 5 to 10 pitches a week | Research and drafting take most of the hours | Research, vetting and drafting are prepared each week, so human time goes only to approving and sending |
| Expert quotes rarely used | Needs someone watching requests daily | Responses drafted 2 to 3 times a week from week 3 |
| Results reviewed quarterly | Reporting is manual | Funnel and verification every month, replan at week 12 |
| Unlinked mentions and partners left for later | Seen as small wins | Done first, because they convert best |

## What cannot be compressed (say this to every client)

- **Discovery lag.** Google takes weeks to find and count a new link, and rankings respond over months. Links won in
  month 6 show their full effect around months 8 to 10.
- **Editor response times.** People reply when they reply. More pitches in parallel helps; chasing faster does not.
- **Trust.** Age of content, consistent publishing and a real reputation build with time.

So the honest promise is: six months delivers the activity and the link volume of a traditional year. Ranking impact
lags by two to four months, so month 6 typically looks like a traditional month 8 to 10, and month 9 like month 12.
Planning estimates are ranges, never guarantees.

## Fast start for sites that are already ready

`program` checks the stored readiness verdict. If it is `ready`, the four foundation weeks compress into two (a gap
check replaces the full build-out), every later task moves three weeks earlier, and the freed weeks at the end go to a
third asset and a fourth PR wave. If the site already has a page worth linking to, pass `--existing-asset <url>`:
asset 1 is not built and pitching it starts in week 2. Calendar tasks (monthly checks, the six-month report) do not move.

A fast start is decided by the readiness check, never by impression. A site that looks finished but has no linkable
asset, no named people or no contact route will waste the first pitches, which are the best prospects.

## Tracks

`program` picks a track from the industry. Each has its own mix of tactics and asset.

| Track | Industries | First asset | Heaviest tactics |
|-------|------------|-------------|------------------|
| local | local service, home services, healthcare, legal, real estate, hospitality, retail, events | local cost guide and community resource page | citations, partners and suppliers, local press, sponsorships |
| saas_b2b | SaaS, B2B, agency, fintech, developer tools | benchmark from anonymised data, free calculator or template | directories and reviews, integration partners, data PR, podcasts |
| ecommerce | e-commerce | product test or buying guide, sales-trend data | supplier and maker pages, gift-guide editors, data PR |
| content | publisher, nonprofit, education, anything else | data story or survey with downloadable data | data PR, resource pages, partners |

YMYL industries (healthcare, legal, finance) add a credentials review in week 2 and stricter claim checking on every asset.

## The four phases

| Phase | Weeks | Goal | Exit check |
|-------|-------|------|------------|
| Foundation | 1 to 4 | Site ready, entity and listings complete, first fast-win pitches out | Readiness verdict at least mostly ready; foundation listings submitted |
| Engine | 5 to 12 | Asset 1 live and pitched; weekly outreach rhythm; cluster pages started | First earned editorial links verified; replan done at week 12 |
| Scale | 13 to 20 | Asset 2, second PR wave, guest articles and podcasts, reclaim sweep | Win rate known per tactic; weak tactics dropped |
| Compound | 21 to 26 | Refresh asset 1, third wave, double down on what wins | Six-month report against baseline; months 7 to 12 planned |

## Roles

| Owner | Does | Typical weekly time |
|-------|------|---------------------|
| claude | Research, vetting, drafts, kits, asset and content drafts, tracking, verification, reports | Unlimited preparation |
| you | Approve shortlists and drafts, send from your own mailbox, create accounts, publish pages | 1 to 3 hours per client |
| client | Facts, data, expert quotes and credentials, approval of anything published under their name | About 1 hour |

The client's expert time is the most common bottleneck. Agree it in writing at intake.

## What each month should show (and how to see it in search)

These are what a sound program typically produces, written as checks rather than promises. They are tested monthly
by `scorecard`; a failed check comes with the change to make. Results vary with competition, the asset and how fast
the client supplies what is needed.

| Month | What should be visible | How to see it yourself |
|-------|------------------------|------------------------|
| 1 | Brand search shows more of the business on page 1 (profiles, listings, maps); at least 5 live links, mostly listings and partners; reply rate at least 5 percent; local: map position starting to improve | Search the brand name logged out; `scorecard`; Search Console Links report starts to update |
| 2 | Impressions on the promoted pages above baseline; first earned editorial link | Search Console, filter to those pages, compare 28 days with the baseline |
| 3 | More target queries in the top 10; referring domains above baseline | Search Console average position for the agreed queries; `/seo backlinks` |
| 4 to 6 | Clicks above baseline; some target queries in the top 3; AI answers start citing the brand | Search Console clicks; logged-out searches for the target queries; `/seo geo` |

What month 1 will not show for most sites: big movement on competitive, non-branded keywords. That needs earned links
to be discovered and counted, which is what months 2 to 4 are for. Say this to the client at intake.

**Seeing it in search.** Personal searches are skewed by location and history, so the scorecard uses Search Console
positions as the record. For a visual check, search logged out (or in a private window) with the location set to the
client's market, for the same agreed list of queries each month, and save a screenshot.

**Recording a month.** On the same day each month:

```bash
claude-seo run linkbuilding.py snapshot --campaign <dir> --month <n> gsc_impressions_28d=<n> gsc_clicks_28d=<n> \
  target_impressions_28d=<n> target_queries_top10=<n> target_queries_top3=<n> branded_owned_page1=<n> \
  referring_domains=<n> [map_pack_rank=<n>] [ai_mentions=<n>]
claude-seo run linkbuilding.py scorecard --campaign <dir>
```

The baseline must use the same keys (`baseline gsc_impressions_28d=<n> ...`). Links, pitches and replies are added
from the campaign automatically.

## Prove it before rolling it out

Run the program on two sites first, one ready and one not, for 30 days. If both pass the month-1 checks, roll out to
the rest of the portfolio. If a check fails, apply its corrective action and re-check at day 60 before scaling.

## How a month is judged

Activity (controllable): pitches sent, listings submitted, assets shipped, expert responses. Outcomes: replies, links
won and verified, referring domains against baseline, impressions and position of the linked pages, referral traffic and
leads. Report both, and never report a pending link as a result.
