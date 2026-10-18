---
name: seo-linkbuilding
description: "Link building campaign for a website: checks site readiness, builds a screened shortlist of about 100 legitimate link opportunities (mostly free, some disclosed paid), waits for owner approval, drafts personalised outreach, tracks replies and wins, verifies links stay live, and adds a Link Building section to the SEO report. Refuses spam, link sellers, PBNs and fake .edu domains. Use when user says link building, build backlinks, outreach, guest post, get links, link prospects, digital PR, citations, or link campaign."
user-invocable: true
argument-hint: "<url> [plan|prospects|approve|draft|track|verify|report]"
license: MIT
compatibility: "Core workflow needs only the bundled scripts. Better prospect data with Moz, Bing Webmaster, DataForSEO or the Ahrefs MCP; all optional."
metadata:
  author: jishhnnuu
  version: "1.8.1"
  category: seo
---

# Link Building

Acts as the off-page owner for a site: finds where legitimate links can be earned, tells the
owner what to change on the site so outreach works, prepares everything, and measures results.
It proposes and prepares. The owner decides and sends.

## Hard rules (never relax these)

1. **Approval gate.** Nothing is drafted or exported for a prospect the owner has not approved.
   Present the shortlist, stop, and wait. Approval in one run does not carry over to new prospects.
2. **Never send.** Produce drafts and a mail-merge CSV. Do not email anyone from this skill.
3. **No bought links.** Never recommend undisclosed dofollow purchases, link exchanges, PBNs, link-seller
   sheets, scholarship or `.edu` hunting, or comment/forum spam. Paid means disclosed sponsored content and
   fee-based listings, expected to carry `rel="sponsored"` or `nofollow`.
4. **No padding.** If fewer than 100 prospects clear the bar, say so and run more discovery.
5. **Label the evidence.** Every DR, DA and traffic figure carries its source. Seller numbers are claims.
6. **No invented contacts.** Only publicly listed business addresses, never pattern-guessed ones.
7. **Honest forecasts.** Success rates are planning ranges, not promises. Say so wherever they appear.

Follow the writing rules in `CLAUDE.md`: no em or en dashes as punctuation, no stock AI phrasing.

## Commands

| Command | Does |
|---------|------|
| `/seo linkbuilding <url>` | Full flow: readiness, shortlist, then stop for approval |
| `/seo linkbuilding plan <url>` | Readiness and asset plan only |
| `/seo linkbuilding prospects <url>` | Discovery, screening, shortlist (no drafting) |
| `/seo linkbuilding approve` | Walk the owner through the shortlist and record decisions |
| `/seo linkbuilding draft` | Drafts and submission kit for approved prospects |
| `/seo linkbuilding track` | Log events, show what is due, funnel counts |
| `/seo linkbuilding verify` | Re-check won links (30, 90, 180 days) |
| `/seo linkbuilding report` | Link Building PDF/XLSX via `google_report.py --type link-building` |

All scripts run through `claude-seo run linkbuilding.py <subcommand> --campaign link-campaigns/<domain>`.

## Workflow

### 1. Intake

Collect: site URL, business name, industry (one of `saas`, `ecommerce`, `local_service`, `agency`, `healthcare`,
`legal`, `home_services`, `real_estate`, `hospitality`, `nonprofit`, `publisher`, `general`), region (ISO country,
needed for local listings), 3 to 6 topics the site wants to rank for, capabilities (`open_source`,
`browser_extension`, `wordpress_plugin`, `shopify_app`, `atlassian_app`, `public_api`), and sender name, title and
postal address. Then:

```bash
claude-seo run linkbuilding.py init --campaign link-campaigns/<domain> --site <url> --name "<Name>" \
  --industry <industry> --region <CC> --topics "<a>,<b>" --capabilities "<list>" \
  --sender-name "<Name>" --sender-title "<Title>" --sender-address "<Address>"
```

### 2. Baseline and readiness

Record the before-state so results can be judged:

```bash
claude-seo run linkbuilding.py baseline --campaign <dir> referring_domains=<n> gsc_clicks_28d=<n> gsc_impressions_28d=<n>
claude-seo run linkbuilding.py readiness --url <url> --industry <industry> --campaign <dir>
```

Get referring domains from `/seo backlinks` (Moz, Bing, DataForSEO) and clicks from `/seo google gsc` if connected.
If the verdict is `fix_first`, tell the owner plainly that outreach will convert poorly until the failing items
and the missing linkable asset are fixed. Offer to continue with the free self-serve listings in the meantime, which
do not depend on the asset. Load `references/site-readiness.md` for the fixes and asset ideas.

### 3. Evergreen sources

```bash
claude-seo run linkbuilding.py library --campaign <dir>
```

### 4. Live discovery

Load `references/prospect-discovery.md` and follow it. Use WebSearch for unlinked mentions, resource pages and
partner pages; use the best available backlink source for competitor gap (see `seo-backlinks`); optionally the
Ahrefs or DataForSEO extensions. Write findings to CSV and ingest:

```bash
claude-seo run linkbuilding.py ingest --campaign <dir> --file <csv> --source competitor_gap --type competitor_gap
```

CSV columns: `domain, name, dr, da, traffic, notes, relevance, contact_name, email, contact_source, hook,
their_page_url, broken_url, asset_url, asset_summary, relationship, topics, metrics_source`. Fill `relevance`
(0 to 1) only after reading the page. Put the topics for a guest pitch in `topics`, separated by `|`.
If the owner supplies a vendor or agency sheet, ingest it with `--source vendor_sheet`; the screen will separate
what is usable (rarely much) and explain the rest.

### 5. Verify, screen, select

```bash
claude-seo run linkbuilding.py check-live --campaign <dir>
claude-seo run linkbuilding.py screen --campaign <dir>
claude-seo run linkbuilding.py select --campaign <dir> --count 100 --free-ratio 0.7
claude-seo run linkbuilding.py shortlist --campaign <dir>
```

For the top 20 prospects, run the qualification checklist in `references/prospect-discovery.md` by hand (read
three pages, check authors, outbound links, indexing, `domain_history.py`). Lower `relevance` or reject any that
fail. Re-run `screen` and `select` after changes.

### 6. Present and stop

Show the shortlist grouped by Free and Paid, with tier, tactic, expected link attribute, metric source and flags.
State the shortfall if any. State the planning estimate and that it is a range from typical acceptance rates.
**Stop and ask the owner which to approve.** Do not continue to drafting in the same turn unless they have already
told you which prospects to approve.

```bash
claude-seo run linkbuilding.py approve --campaign <dir> --ids <id1>,<id2>   # or --tier A,B or --all-proposed
claude-seo run linkbuilding.py reject --campaign <dir> --ids <id> --reason "<why>"
```

### 7. Prepare the first touch

For approved email-type prospects, make sure each has a named contact with a public address and a specific hook
(see `references/outreach-playbook.md`). Then:

```bash
claude-seo run linkbuilding.py draft --campaign <dir>     # complete prospects only; reports what is missing
claude-seo run linkbuilding.py kit --campaign <dir>       # profile copy and checklists for self-serve listings
claude-seo run linkbuilding.py export --campaign <dir>    # mail-merge CSV; nothing is sent
```

Show the drafts. Fix anything generic. Run `content_humanize.py` over any text you rewrite by hand. Recommend a
first batch of 20 to 30 sends, not the whole list.

### 8. Track

Ask the owner to tell you when emails go out and what comes back, and log each event:

```bash
claude-seo run linkbuilding.py log --campaign <dir> --id <id> --event sent|replied|won|declined|bounced|unsubscribed --link-url <url>
claude-seo run linkbuilding.py due --campaign <dir>        # follow-ups at day 6 and 14, closure at 21, verifications
claude-seo run linkbuilding.py status --campaign <dir>
```

Declines and unsubscribes are suppressed automatically. After the first 20 sends, compare the real reply and
win rates with the planning estimate and adjust hooks, assets or tactics before the next batch.

### 9. Verify

```bash
claude-seo run linkbuilding.py verify --campaign <dir> --due
```

Report which links exist, which `rel` they carry, and which were lost. A link is a result only once verified.

### 10. Report

```bash
claude-seo run linkbuilding.py report-data --campaign <dir>
claude-seo run google_report.py --type link-building --domain <domain> --data <dir>/report-data.json --output-dir <dir> --format all
```

The `full` report type includes the same section when `linkbuilding` data is present. Check the PDF review reports
`"status": "PASS"` before presenting it. Offer the report after any completed analysis.

## Output to the owner

Lead with the decision they need: what you recommend approving, what you rejected and why, what the site must
change first. Then the numbers. Keep jargon out of the summary; define DR and rel attributes once in plain words.

## References

- `references/operating-model.md`: portfolio strategy, free data stack, spend ladder, industry plays, multi-site rules
- `references/site-readiness.md`: checks, linkable assets, how to make assets citable, timeline
- `references/prospect-discovery.md`: where candidates come from, qualification checklist, how to treat vendor sheets
- `references/outreach-playbook.md`: first-touch principles, cadence, replies, law, verification
- `../seo/references/backlink-quality.md`: toxic patterns and disavow criteria
- `../seo/references/free-backlink-sources.md`: what each data source can and cannot tell you

## Related skills and agents

`seo-backlinks` (profile analysis, gap data, verification), `seo-local` (citations and GBP), `seo-content-brief`
and `seo-cluster` (building the linkable asset), `seo-geo` (AI citation value), and the `seo-outreach` agent for
unattended Growth Loop runs, which follows the same rules and queues drafts for a human.
