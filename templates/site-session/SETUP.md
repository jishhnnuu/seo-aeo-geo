# Site session setup (run once per website)

Use this when the owner opens a Claude session with a website's repo and this engine repo attached and says anything
like "set up this site", "start SEO for this client" or "onboard this website". It sets up the whole program for that
site: SEO, AEO, GEO and link building, plus the scheduled runs. Every later run follows `weekly.md`, `midweek.md` and
`checkpoint.md` in this folder.

Engine commands below run from the engine repo, for example `python3 scripts/site_routine.py ...`
(or `claude-seo run site_routine.py ...` where the plugin runtime is installed).

## 1. Find the repos

```bash
python3 scripts/site_routine.py locate
```

- Exactly one site repo: use it. Several: ask which one this session is for. None: ask the owner to attach it.
- The engine must be on `main` and contain `scripts/linkbuilding.py`. If it does not, stop and tell the owner the
  engine branch with link building has not been merged yet.

## 2. Read before changing anything

- The site repo's own `CLAUDE.md`, `seo-config.yml`, `reports/` and any tooling. **The site's own rules win** for
  content, brand naming and deployment.
- How it deploys (`netlify.toml`, `vercel.json`, `_config.yml`, GitHub Pages settings, CMS) and which branch goes live.
- Existing scheduled tasks for this site (`list_triggers`). List them for the owner and ask whether to delete or
  disable them. Never delete one without a yes; copy any site knowledge they contain into the site repo first.
- Open pull requests from an older automation (for example `seo/**` branches). Do not touch files they touch.

## 3. Intake (ask only what the site does not already answer)

Industry, country or region served, the site's timezone, 3 to 5 search competitors, 10 to 20 target searches,
partners, suppliers and customers who could link, one named expert with credentials, and the sender name, title and
postal address for outreach. Ask in one message.

## 4. Access check

Run `python3 scripts/google_auth.py --check --json` and prove each source with a real call: Search Console for this
property, GA4, Bing Webmaster, PageSpeed. Anything missing becomes a "needs you" item with the exact steps. Missing
access degrades the program but never blocks setup.

## 5. Create the site's private state folder

```bash
python3 scripts/site_routine.py init --site-dir <site repo> --url <live url> --name "<Name>" --industry <industry> \
  --region <CC> --timezone <IANA zone> --topics "<a>,<b>" --deploy-branch <branch>
```

This writes `.seo/` inside the **site** repo. Never write client data into the engine repo: it is public.

**Keep `.seo/` off the live site.** It holds contacts and drafts. If the host publishes the repo root, block it:

- Netlify: add `/.seo/*  /404.html  404!` to `_redirects` (or a matching `[[redirects]]` block with `force = true`).
- Vercel: add `.seo` to `.vercelignore`.
- GitHub Pages with Jekyll: dot folders are excluded by default; keep them out of `include:`.
- Anything else: exclude the folder from the build output.

After the next deploy, `python3 scripts/site_routine.py state-check --url <live url>` must say `PRIVATE`. If it says
`LEAK`, fix the host rule before any outreach data is written.

## 6. Baseline (before any change ships)

Record what exists today, with the scorecard metric names, in the campaign at `<site repo>/.seo/link-building`:

```bash
python3 scripts/linkbuilding.py init --campaign <site>/.seo/link-building --site <url> --name "<Name>" --industry <industry> \
  --region <CC> --topics "<a>,<b>" --sender-name "<Name>" --sender-title "<Title>" --sender-address "<Address>"
python3 scripts/linkbuilding.py baseline --campaign <site>/.seo/link-building gsc_impressions_28d=<n> gsc_clicks_28d=<n> \
  target_impressions_28d=<n> target_queries_top10=<n> target_queries_top3=<n> branded_owned_page1=<n> referring_domains=<n>
```

Sources: Search Console (`scripts/gsc_query.py`), a logged-out brand search for `branded_owned_page1`,
`/seo backlinks` for referring domains, `/seo maps` for map position (local), `/seo geo` for AI mentions. Record what
could not be measured; never guess a baseline.

## 7. Audit and link-building plan

1. Run `/seo audit <url>` and keep the prioritised fix list in `<site>/.seo/audit-<date>.md`.
2. Run the link-building readiness check and program:

```bash
python3 scripts/linkbuilding.py readiness --url <url> --industry <industry> --campaign <site>/.seo/link-building
python3 scripts/linkbuilding.py library --campaign <site>/.seo/link-building
python3 scripts/linkbuilding.py screen --campaign <site>/.seo/link-building
python3 scripts/linkbuilding.py select --campaign <site>/.seo/link-building
python3 scripts/linkbuilding.py program --campaign <site>/.seo/link-building --start <next Monday> [--existing-asset <url>]
```

Fast start is chosen automatically when readiness says `ready`.

## 8. Schedule the runs

```bash
python3 scripts/site_routine.py schedule --site-dir <site repo> --start <next Monday>
```

Create each spec it prints as a scheduled task bound to **this** session (no `persistent_session_id`), with
`initiation: human_request`: the two recurring ones with their `cron_expression`, the two checkpoints with
`run_once_at`. Show the owner the list with times in their timezone.

## 9. Save and report

Commit `.seo/` and any host rule on the deploy branch, push, confirm the commit is on the remote, and after deploy run
`state-check`. Then tell the owner, in plain words: what was set up, the readiness verdict, the first fixes, the
schedule, and the week-1 "needs you" list with minutes for each item.
