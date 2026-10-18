# Owner guide: how the program runs for each website

Plain-language guide for the agency owner (and for clients who ask). The routines Claude follows are in this folder:
`SETUP.md`, `weekly.md`, `midweek.md`, `checkpoint.md`, with shared rules in `RULES.md`.

## What you provide

**Once for the whole agency**

| Item | Why | Time |
|------|-----|------|
| A Google Cloud service account, its key added to the Claude environment as `GOOGLE_APPLICATION_CREDENTIALS_JSON` | Reads Search Console and GA4 for every client | 20 minutes, once |
| Optional: `GOOGLE_API_KEY` (PageSpeed) and `BING_WEBMASTER_API_KEY` | Speed data and Bing coverage | 10 minutes each |
| A mailbox on your agency or the client's domain for outreach | Emails must come from a real person | Already have |

No Ahrefs or other paid tools are needed. Backlink data comes from free sources (Search Console's Links report,
Bing, Common Crawl, Moz free tier if added).

**For each new client site**

| Item | Where | Time |
|------|-------|------|
| The site's code in a GitHub repo the Claude GitHub app can push to | GitHub | 5 minutes |
| Service account added to Search Console (permission Full) | Search Console, Settings, Users and permissions | 3 minutes |
| Service account added to GA4 (role Viewer) and the GA4 property ID | GA4 Admin | 3 minutes |
| Answers to the 8 setup questions (industry, area, timezone, searches, competitors, partners, expert, sender) | One reply | 15 minutes |
| Local businesses: Google Business Profile access | Business Profile, add manager | 5 minutes |

If a site is not in a git repo (for example Wix or a hosted WordPress), Claude prepares every change as exact copy
and steps, and you or the client paste it in. Everything else works the same.

## What happens every week

| When | Claude does (unattended) | You do |
|------|--------------------------|--------|
| **Monday morning** | Pulls Search Console data; picks and ships 1 to 3 page improvements by fixed rules (answers to questions people search, pages close to page 1, titles that get no clicks); checks indexing; runs the link-building week (research, drafts, kits); on the first Monday of the month runs a full audit, scorecard and PDF; sends you a report | Read the report. Approve prospects and drafts, send the ready emails, do the "Needs you" items. About 45 to 60 minutes per site. |
| **Thursday morning, first 60 days** | Prepares follow-ups and the next batch, verifies new links, checks indexing, flags problems | Send follow-ups, tell Claude about replies and wins. About 20 minutes per site. |
| **Day 30 and day 60** | Checkpoint: scorecard against the starting numbers, a clear verdict and what changes | Read it and agree the changes. 10 minutes. |

Telling Claude about replies: in the site's session say, for example, "Ed from blog.example.org replied yes, the
link is at <url>". Claude logs it and verifies the link.

## How you will know early if it is not working

You do not have to wait 30 days. Every report starts with a verdict built from these checks, run every week:

| Check | Turns red when | Usually means |
|-------|----------------|---------------|
| Schedule | No completed Monday run in 8 days | The scheduled task stopped; check it is enabled |
| Access | Search Console or push access broken | A permission was removed |
| Approvals | Prospects waiting for you over 14 days | The program is waiting on you |
| Sending | 10 or more drafted emails unsent after a week | The program is waiting on you |
| Reply rate | Under 5 percent after 20 emails | The pitch or the asset is weak; Claude rewrites |
| Bounces | Over 5 percent | Bad addresses; sending pauses |
| Pace | Under 40 percent of planned emails sent | Something upstream is stuck |
| Shipping | No page change in 14 days | On-site work is blocked |
| Indexing | Changed pages unindexed after 14 days | Press "Request indexing" in Search Console |
| Privacy | The `.seo` folder is visible on the live site | Fix the host rule at once |
| Trend (from week 6) | Impressions not above the starting number | Content gap; weekly runs shift to content |

The two most common reasons programs fail are owner time (approvals and sending stall) and missing Search Console
access. Both show up red in the first or second weekly report.

## What results to expect

| By | Typical, if the weekly steps happen |
|----|-------------------------------------|
| Week 2 | First page improvements live, listings submitted, first emails sent |
| Day 30 | More of page 1 is the business on a brand search; 5 or more live links (mostly listings and partners); reply rate known |
| Day 60 | Impressions on the promoted pages above the start; first earned editorial link |
| Day 90 | More target searches in the top 10; more referring sites than at the start |
| Months 4 to 6 | More clicks; some searches in the top 3; AI answers start naming the business |

These are checks, not promises. Competitive keywords move later than brand and long-tail searches.

## Which Claude model to use

The scripts make every number-based decision (what to change, whether a check passes, what the report says), so
any model can follow the routines. Recommended: Sonnet for setup and the Monday run (it writes page copy), Haiku or
Sonnet for Thursday and the checkpoints. If a weaker model's page copy fails the quality gates twice, the routine
reverts that change and reports it rather than shipping it.
