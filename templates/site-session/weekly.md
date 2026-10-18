# Weekly run (Monday)

The main run for one site: search data, the week's best on-site changes, the link-building week, and on the first run
of each calendar month the deep monthly steps. Paths: `<site>` is the site repo, `<engine>` the engine repo,
`<camp>` is `<site>/.seo/link-building`. Site config: `<site>/.seo/site.json`.

## Rules for every run

- The site repo's `CLAUDE.md` wins on content, brand naming and deploys. Then the engine's Operating Standard.
- White-hat only. Never send outreach, buy anything or create accounts. Prepare and queue for the owner.
- YMYL sites (health, legal, finance): check every factual claim against its source; hedge what cannot be verified.
- No em or en dashes in anything written; run `scripts/content_humanize.py` over new prose.
- If a step fails, say so in the report. Never report a pending change or a pending link as done.

## Steps

1. **Start.** Append `<date> weekly: started` to `<site>/.seo/runs.md`. Read `site.json`, the last weekly report in
   `<site>/.seo/weekly/`, and `<camp>/program.md`.
2. **Data.** Search Console for the last 28 days and the 28 before (`scripts/gsc_query.py --property <property>
   --days 28`, plus `--dimensions query` and page views). GA4 organic sessions and conversions if connected
   (`scripts/ga4_report.py`). Save the week's numbers to `<site>/.seo/weekly/<date>.json`.
3. **Coordinate.** Check open pull requests from other automation on the site repo; do not edit files they touch.
4. **On-site: pick the 1 to 3 highest-value changes**, in this order:
   a. a question people search that no page answers: add a 40 to 60 word answer-first section and FAQ schema;
   b. queries at positions 8 to 20: strengthen the matching page (title, heading, intro, internal links);
   c. a cluster with real impressions and no page: build a page using the site's best existing template;
   d. pages with many impressions and no clicks: rewrite the title and meta description;
   e. AEO and GEO: make key facts quotable, keep `llms.txt` and Organization schema current, check AI crawler access.
   If a page changed recently has not been recrawled, ask the owner to request indexing instead of editing it again.
5. **Test and ship.** Run the site's own checks if it has them, validate any schema you touched, commit on the deploy
   branch, push, confirm the commit is on the remote and the change is live, then announce changed URLs (IndexNow via
   `scripts/indexnow_submit.py` when the site has a key).
6. **Link building.**

```bash
python3 <engine>/scripts/linkbuilding.py week --campaign <camp>
python3 <engine>/scripts/linkbuilding.py due --campaign <camp>
```

   Do every task marked `claude` for this week (discovery, screening, asset drafts, kits, briefs), then prepare the
   week's batch: make sure approved prospects have a named public contact and a specific hook, run `draft` and
   `export`. Mark finished tasks with `done`. Never approve on the owner's behalf: list what awaits approval.
7. **Monthly block (first run in a calendar month only).**
   - `/seo audit <url>` and compare with the last audit in `<site>/.seo/`.
   - Month number = whole months since the program start. Record `snapshot --month <n>` with the scorecard metrics
     (same sources as the baseline), then run `verify --due` and `scorecard`.
   - `report-data`, then `scripts/google_report.py --type link-building` (or `--type full` with the audit data) to
     `<site>/.seo/reports/`; check the PDF review says PASS.
   - `python3 <engine>/scripts/site_routine.py state-check --url <url>` must say PRIVATE.
8. **Save.** Commit `<site>/.seo/` on the deploy branch, push, confirm on the remote. Append `<date> weekly: done`
   with one line of what shipped to `runs.md`.
9. **Report to the owner** (under 300 words, plain language):
   - One-line verdict: on track, needs action, or blocked, and why.
   - Numbers: clicks, impressions, average position, this week vs last and vs baseline; enquiries if GA4 is connected.
   - What shipped this week, with live links.
   - Link building: prospects waiting for approval, emails ready to send (file path), follow-ups due, links won.
   - Needs you: each item as one action with the minutes it takes. Say "nothing" if nothing.
   - Next week: the top 1 to 3 planned items. In a monthly run, add the scorecard verdict and any failed check.
