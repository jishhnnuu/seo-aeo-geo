# Site setup (run once per website)

Use this when the owner opens a session with a website repo and this engine repo attached and says anything like
"set up this site", "start SEO for this client" or "onboard this website". Read `RULES.md` first. Setup is the one
routine where you ask the owner questions; ask them all in one message (step 3) and continue with what you have.

## Step 1. Find the repos and set the names

```bash
cd <engine repo> && python3 scripts/site_routine.py locate
```

| Result | Do this |
|--------|---------|
| One entry in `site_repos` | Use it as `S`. |
| Several | Ask the owner which site this session is for. Use only that one. |
| None | STOP: "Attach the website's repo to this session, then ask me again." |
| `scripts/linkbuilding.py` missing in the engine | STOP: "The engine's link-building update is not merged into main yet." |

Set `E`, `S`, `C` and `TODAY` as in `RULES.md`. `URL` and `BRANCH` come from step 4.

## Step 2. Read the site before changing anything

1. Read `$S/CLAUDE.md`, `$S/README*`, `$S/seo-config.yml` and anything in `$S/reports/` if they exist.
2. Find how it deploys and from which branch: look for `netlify.toml`, `vercel.json`, `_config.yml`, `.github/workflows/`,
   `package.json` scripts. Note the publish folder (for example the repo root, `dist`, `public`, `_site`).
3. Find the live URL: `netlify.toml`, `CNAME`, `package.json` `homepage`, the site config, or the repo description.
4. List existing scheduled tasks (`list_triggers`). For any that mention this site, show the owner the name and
   whether it is enabled, and ask whether to keep, disable or delete it. Do nothing to them without a yes.
5. List open pull requests on the site repo. Note any from other automation; never edit the files they touch.

## Step 3. Ask the owner (one message)

Ask only what you could not find in step 2:

1. Industry, and the country or city served.
2. The site's timezone (for scheduling).
3. 10 to 20 searches the business wants to be found for.
4. 3 to 5 competitors that show up in those searches.
5. Partners, suppliers, customers or associations who could link to the site.
6. One named expert at the business, with job title and credentials.
7. Sender name, job title and postal address for outreach emails.
8. The Search Console property (domain or URL prefix) and the GA4 property ID, if known.

Continue with defaults where the owner does not answer: industry `general`, timezone `UTC`, topics from the homepage.

## Step 4. Create the site's private state

```bash
python3 $E/scripts/site_routine.py init --site-dir $S --url <live url> --name "<Business name>" --industry <industry> \
  --region <2-letter country> --timezone <IANA zone, e.g. Asia/Dubai> --topics "<search 1>,<search 2>,<search 3>" \
  --deploy-branch <branch> --gsc-property <sc-domain:example.com> --ga4-property-id <digits>
```

Industry must be one of: `saas`, `ecommerce`, `local_service`, `agency`, `healthcare`, `legal`, `home_services`,
`real_estate`, `hospitality`, `nonprofit`, `publisher`, `general`. Missing values can be added later with
`python3 $E/scripts/site_routine.py set --site-dir $S key=value`.

## Step 5. Keep `.seo/` off the live site

`.seo/` will hold contacts and drafts. Block it at the host if the publish folder is the repo root:

| Host | Add this |
|------|----------|
| Netlify | A line `/.seo/*  /404.html  404!` in `_redirects` in the publish folder |
| Vercel | A line `.seo` in `.vercelignore` |
| GitHub Pages (Jekyll) | Nothing: Jekyll skips dot folders. Do not add `.seo` to `include:` |
| Cloudflare Pages, others | Exclude `.seo` from the build output, or publish a subfolder |
| Publish folder is `dist`, `public`, `_site` and `.seo` is outside it | Nothing needed |

Commit and push. After the deploy finishes:

```bash
python3 $E/scripts/site_routine.py state-check --url $URL --site-dir $S
```

| Verdict | Do this |
|---------|---------|
| `PRIVATE` | Continue. |
| `UNVERIFIED` | The site could not be reached from this session. Continue, and list it for the owner to re-check. |
| `LEAK` | Fix the host rule and re-check. Do not write any contacts until this says `PRIVATE`. |

## Step 6. Prove access

```bash
python3 $E/scripts/site_routine.py access --site-dir $S
```

Every item that is not `ok` has a `fix`. Those become the owner's first "Needs you" items. Setup continues even if
Search Console is missing; the weekly runs will use the audit list until data arrives.

## Step 7. Record the baseline (before anything ships)

```bash
python3 $E/scripts/site_routine.py pull --site-dir $S --date $TODAY       # skip if Search Console is not ok
python3 $E/scripts/linkbuilding.py init --campaign $C --site $URL --name "<Business name>" --industry <industry> \
  --region <CC> --topics "<a>,<b>" --sender-name "<Name>" --sender-title "<Title>" --sender-address "<Address>"
python3 $E/scripts/linkbuilding.py baseline --campaign $C gsc_impressions_28d=<n> gsc_clicks_28d=<n> \
  branded_owned_page1=<n> referring_domains=<n>
```

Impressions and clicks come from `$S/.seo/weekly/$TODAY/summary.json` (`current_28d`). For `branded_owned_page1`,
search the business name with WebSearch and count page-1 results that are the site or its own profiles. For
`referring_domains`, use `/seo backlinks $URL` if a backlink source is configured; otherwise leave it out. Never guess
a number: leave out what you cannot measure.

## Step 8. Audit and link-building plan

1. Run `/seo audit $URL`. Save its prioritised fix list, one item per line, as `$S/.seo/audit-$TODAY.md`.
2. Then:

```bash
python3 $E/scripts/linkbuilding.py readiness --url $URL --industry <industry> --campaign $C
python3 $E/scripts/linkbuilding.py library --campaign $C
python3 $E/scripts/linkbuilding.py screen --campaign $C
python3 $E/scripts/linkbuilding.py select --campaign $C
python3 $E/scripts/linkbuilding.py program --campaign $C --start <next Monday> [--existing-asset <url>]
```

   Use `--existing-asset` only if the site already has a page people would link to (a tool, data, a thorough guide).
3. If the region is outside the US, run the discovery steps in
   `$E/skills/seo-linkbuilding/references/prospect-discovery.md` for local directories, associations and local press,
   then `ingest`, `screen` and `select` again. The built-in library is mostly US and global.

If Ahrefs is connected in this session, run `AHREFS-HARVEST.md` now, before step 9; it fills the competitor gap
and keyword data the weekly runs use.

## Step 9. Schedule the runs

```bash
python3 $E/scripts/site_routine.py schedule --site-dir $S --start <next Monday>
```

Create each printed spec as a scheduled task with `create_trigger`, bound to this session (leave out
`persistent_session_id` and `create_new_session_on_fire`), `initiation: human_request`, using the spec's `name` and
`prompt`, and `cron_expression` or `run_once_at`. Then list them for the owner with times in the site's timezone.

## Step 10. Save and report

```bash
python3 $E/scripts/site_routine.py mark-run --site-dir $S --routine setup --status done --date $TODAY
```

Commit and push `$S/.seo/` and any host rule (see `RULES.md`). Then send the owner:

```
<Site> is set up.
Readiness: <verdict> (<score>/100). First fixes: <top 3 audit items>.
Plan: <standard or fast> start on <date>, <track> track, <n> prospects shortlisted for your approval.
Schedule: Mondays <time> (full run), Thursdays <time> for 60 days (outreach), checkpoints on <day 30> and <day 60>.
Needs you this week:
- <each access fix and approval, with minutes>
```
