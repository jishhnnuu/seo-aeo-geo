# Weekly run (every Monday)

Time budget: about 45 minutes of work. Read `RULES.md` first and set the names it defines, with `<routine>` = `weekly`.

## Step 1. Read the context

1. Read `$S/CLAUDE.md` (if it exists), `$S/.seo/site.json`, and the most recent `$S/.seo/weekly/*/report.md`.
2. Note the site's rules on brand name, tone and page structure. They apply to everything you write today.

## Step 2. Check access

```bash
python3 $E/scripts/site_routine.py access --site-dir $S
```

| Result | Do this |
|--------|---------|
| `essential_ok: true` | Continue. |
| `gsc_access` or `service_account` not ok | Skip steps 3 and 4 (no data). Do steps 5 to 9. The report will list the fix. |
| `push` failed | STOP (nothing can ship). |

## Step 3. Pull this week's search data

```bash
python3 $E/scripts/site_routine.py pull --site-dir $S --date $TODAY
```

If any pull shows an `error`, run it once more. If it still fails, treat it as "no data" and skip step 4.

## Step 4. Decide and ship the on-site changes

```bash
python3 $E/scripts/site_routine.py analyze --site-dir $S --date $TODAY
```

Read `$S/.seo/weekly/$TODAY/candidates.json`.

- If `this_week` has items: do them in order, at most three, one per page.
- If `this_week` is empty or `low_data` is true: use the `fallback`. Open the newest `$S/.seo/audit-*.md` and take
  the first one to three items not already listed in `$S/.seo/changes.json`.

For each item:

1. Find the source file that renders the page. Map the URL path to the file (for example `/ac-repair` to
   `ac-repair.html`, `src/pages/ac-repair.astro` or `content/ac-repair.md`). Search with
   `grep -rl "<a phrase from the live page>" $S --include=*.html --include=*.md --include=*.astro --include=*.jsx`.
   If you cannot find it in two tries, skip the item and note it in the report.
2. Make the change the `action` describes, in the site's existing style. Rules by kind:

| Kind | Exactly what to do |
|------|--------------------|
| `answer` | Add an H2 that is the question in plain words. Directly under it, a 40 to 60 word answer that states the answer in the first sentence. Then up to 150 words of detail. Add the same question and answer to the page's FAQ section and its FAQPage JSON-LD (create both if missing). |
| `striking` | Put the query's main words in the title (under 60 characters) or an H2, answer the query in the first 100 words, and add links to this page from two related pages with descriptive anchor text. |
| `gap` | If a page already covers the topic, add a section to it like `answer`. Only create a new page if no page fits; copy the structure of the site's best existing page, add it to the sitemap, navigation or footer, and link it from two related pages. |
| `zero_click`, `low_ctr` | Rewrite only the title (under 60 characters, main query first, brand last) and the meta description (70 to 160 characters: what the visitor gets and the next step). |
| audit item | Do what the audit line says. |

3. Run the quality gates in `RULES.md` on every changed file.
4. Record each change:

```bash
python3 $E/scripts/site_routine.py log-change --site-dir $S --date $TODAY --url <page url> --kind <kind> --summary "<plain words>"
```

5. Commit and push as in `RULES.md`. Then confirm it is live: fetch the page with a cache-busting query
   (`curl -s "<url>?v=$TODAY" | grep -c "<a phrase you added>"` must be 1 or more). If the site builds slowly, wait
   five minutes and check once more; if it is still not live, report it.
6. If the site has an IndexNow key file, submit the changed URLs with `$E/scripts/indexnow_submit.py`.

## Step 5. Indexing check for earlier changes

For each entry in `$S/.seo/changes.json` that is 7 or more days old with `indexed` not `true`:

```bash
python3 $E/scripts/gsc_inspect.py <url> --site-url <gsc_property> --json
```

Record the result with `mark-indexed --site-dir $S --url <url> --indexed yes|no`. If not indexed, it goes in the
report so the owner can press "Request indexing" in Search Console.

## Step 6. Link building

```bash
python3 $E/scripts/linkbuilding.py week --campaign $C
python3 $E/scripts/linkbuilding.py due --campaign $C
```

1. Do every task in this week's list whose owner is `claude`. Use the skill instructions in
   `$E/skills/seo-linkbuilding/SKILL.md` and its references for how. Mark each finished task:
   `python3 $E/scripts/linkbuilding.py done --campaign $C --ids <task id>`.
2. Prepare outreach for prospects with status `approved`:
   - Open the prospect's site. Find a named editor or author and an email address printed on that site (contact,
     about, author or "write for us" page). Never guess an address and never use a contact form address you
     cannot see.
   - Write a `hook`: one sentence about something specific on their page that only someone who read it would know
     (at least 40 characters, no flattery such as "great article").
   - Record it with one command (never edit `prospects.json` by hand):

```bash
python3 $E/scripts/linkbuilding.py enrich --campaign $C --id <prospect id> --name "<First Last>" --email <address> \
  --source-url <page where the address is printed> --hook "<one specific sentence>" --their-page <their page url> \
  --asset-url <our page to suggest> --asset-summary "<what that page gives their readers, under 20 words>"
```

     If no public contact exists: `enrich --campaign $C --id <id> --no-contact "<where you looked>"` and move on.
3. Run `python3 $E/scripts/linkbuilding.py draft --campaign $C`, then `export --campaign $C`. Every blocked prospect
   prints what is missing; fix what you can, leave the rest.
4. If fewer than 20 prospects are `proposed` or `approved`, run discovery from
   `$E/skills/seo-linkbuilding/references/prospect-discovery.md` (unlinked mentions and resource pages first), then
   `ingest`, `screen` and `select`.

## Step 7. Monthly block (only if this is the first weekly run in this calendar month)

Check: `python3 $E/scripts/site_routine.py monthly-due --site-dir $S --date $TODAY`. If it prints
`"monthly_due": true`, do this block. If `false`, skip to step 8.

1. Run `/seo audit $URL` and save its prioritised list as `$S/.seo/audit-$TODAY.md`.
2. Month number `n` = whole months since `start` in `$C/program.json` (the first month is 1). Record:

```bash
python3 $E/scripts/linkbuilding.py snapshot --campaign $C --month <n> gsc_impressions_28d=<current_28d.impressions> \
  gsc_clicks_28d=<current_28d.clicks> branded_owned_page1=<count> referring_domains=<count>
python3 $E/scripts/linkbuilding.py verify --campaign $C --due
python3 $E/scripts/linkbuilding.py scorecard --campaign $C
```

   Take impressions and clicks from `$S/.seo/weekly/$TODAY/summary.json`. For `branded_owned_page1`, search the
   brand name with WebSearch and count the page-1 results that are the site itself or its own profiles and listings.
   Use the same method every month. Leave out any metric you could not measure; never estimate.
3. For each failed scorecard check, do its action this run if it is within these rules, otherwise list it for the owner.
4. Make the report:
   `python3 $E/scripts/linkbuilding.py report-data --campaign $C` then
   `python3 $E/scripts/google_report.py --type link-building --domain <domain> --data $C/report-data.json --output-dir $S/.seo/reports --format pdf --json`.
   The `review.status` must be `PASS`; if not, report it instead of sharing the PDF.
5. `python3 $E/scripts/site_routine.py state-check --url $URL --site-dir $S` must say `PRIVATE`. If it says `LEAK`,
   the only task left today is the host rule in `SETUP.md` step 5; report it as urgent.

## Step 8. Save

```bash
python3 $E/scripts/site_routine.py mark-run --site-dir $S --routine weekly --status done --date $TODAY --note "<n> changes shipped"
```

Commit and push `$S/.seo/` as in `RULES.md`.

## Step 9. Report to the owner

```bash
python3 $E/scripts/site_routine.py report --site-dir $S --date $TODAY
```

Send that text as the message, unchanged. Add at most two sentences at the end only for something the report cannot
know (for example a change you skipped and why). In a monthly run, add the scorecard verdict line and attach or link
the PDF.
