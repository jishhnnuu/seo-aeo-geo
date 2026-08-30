---
name: seo-onboard
description: "Set up autonomous SEO/AEO/GEO optimization for a website so it gets audited, fixed, tested and published on a schedule forever, with no further input. Run from a session opened on the website's own repo. Configures everything, installs credentials as repo secrets, and triggers the first audit. Use this whenever someone wants a website optimized, ranked, or growing in search — however they phrase it. Triggers on: optimize this website, optimize my site, set up SEO for this, run SEO on this repo, make this site rank, get more traffic to this website, improve my search rankings, more clicks and impressions, start SEO, automate SEO, onboard this website, add this website, set up the growth loop, install the SEO agents, take over SEO for this site, I want this site optimized."
user-invocable: true
argument-hint: "<live site url>"
license: MIT
metadata:
  version: "1.4.2"
  category: seo
---

# Onboard a website onto the Growth Loop

**Invocation:** just say what you want — "optimize this website", "set up
SEO here", "I want this site ranking". No command needs to be typed or
remembered. `/seo-onboard <url>` works too if someone prefers it.

Run from a session opened on **the website's own repo**, not the engine
repo.

If no URL was given, find it yourself before asking: check `netlify.toml`,
a `CNAME` file, `package.json` homepage, the site config's
`url`/`baseURL`/`site` field, or the repo's GitHub homepage setting.

## Step 0 — Preflight: verify everything, assume nothing

**Never assume a credential or tool is present because it usually is.**
Before changing a single file, run every check below and *prove* each one
by actually exercising it — a key that exists but was never granted access
to this property will fail silently weeks later, which is far worse than
failing now.

This is the one and only place in the whole system where stopping is
correct. After preflight passes, you run to completion and never interrupt
again.

### Environment checks — a failure here is a hard blocker

| Check | How to prove it | Why it matters |
|---|---|---|
| `gh` authenticated | `gh auth status` | everything else needs it |
| `gh` has `workflow` scope | look for `workflow` in the scopes line of `gh auth status` | **without it, pushing `.github/workflows/` fails mid-run** — the single most common way this setup breaks. Fix with `gh auth refresh -h github.com -s workflow` |
| Write access to this repo | `gh repo view --json viewerPermission` shows WRITE or ADMIN | you cannot install anything otherwise |
| Working tree clean | `git status --porcelain` is empty | never mix this with the owner's uncommitted work |
| Python 3.10+ | `python3 --version` | the plugin's bundled scripts require it |
| Live site reachable | fetch the URL, expect 2xx | auditing an unreachable site produces garbage |
| `CLAUDE_CODE_OAUTH_TOKEN` | `gh secret list` on this repo, or inherited from the org | **the scheduled runs cannot start without it** — if missing, the owner must run `/install-github-app` |

### Credential checks — prove each with a live call, not a file's existence

For every one below: confirm it exists, then make a real API call and
confirm the call succeeds *for this specific site*.

| Credential | Live proof | If absent or failing |
|---|---|---|
| `GOOGLE_API_KEY` | call the PageSpeed Insights API against the live URL; expect 200 | DEGRADED: no real-user Core Web Vitals; falls back to lab-only |
| Google service account | parse the JSON, confirm `type: service_account`, `client_email`, `private_key` | DEGRADED: no Search Console, no Indexing API |
| **Search Console access for this property** | call `sites.list` with the service account and confirm this site's property is in the returned list | DEGRADED, and this is the big one: without it there is no impressions/clicks/position data, so no striking-distance keywords and no CTR work — the fastest-moving 30-day levers are gone. Fix: add the service-account `client_email` as a user on the property in Search Console. |
| GA4 property access | call the GA4 Data API for the property id; expect a valid response | DEGRADED: no organic traffic or landing-page data |
| `MOZ_API_KEY` / `BING_WEBMASTER_API_KEY` | a single cheap authenticated call each | DEGRADED: weaker backlink picture |

Do not silently treat a 403 as "not configured". A key that exists but is
not authorized is a *different* problem with a different fix, and the owner
needs to know which one they have.

### Report, then decide

Present ONE table: every check, PASS or FAIL, and for each failure exactly
what it costs and the one action that fixes it. Then:

- **Any hard blocker failed** → stop. Do not begin execution. State plainly
  what must be fixed and how, and offer to continue the moment it is.
- **Only degradations** → say exactly which capabilities will be missing
  and what that means for results, ask once whether to proceed now or wait
  until they are connected, and honour the answer. Proceeding is usually
  right — the loop genuinely works without them and they can be added later
  — but the owner must make that call knowingly, not discover it in week
  three.
- **All clear** → say so in one line and proceed without further questions.

### Anything else you could not determine

Fold these into the same single batch of questions — never a second round:

- The live URL, if you could not find it in the repo
- Whether this repo is the one that builds the live site, if ambiguous
- Anything in `seo-config.yml` you could not infer that would materially
  change strategy — business type, primary target market

Offer your best guess as the default so answering is one word. Asking
something you could have determined by reading the repo is a failure of
this step; so is stopping later to ask something that belonged here.

Nothing about this website is ever written into the engine repo. The
engine stays a generic agent team; everything site-specific lives here.

## Step 1 — Confirm the repo shape

This repo should be the one the host builds the live site from. Confirm by
finding `netlify.toml`, `vercel.json`, a static-site-generator config, or a
`package.json` build script. Say what you found.

If this repo does **not** build the site — the content lives in WordPress,
Shopify or Webflow — stop and say so. That case needs a separate control
repo and a different `site.platform`.

## Step 2 — Install the loop files

Fetch from `https://github.com/jishhnnuu/seo-aeo-geo` under
`templates/site-repo/` and write into this repo at the same relative paths:

- `seo-config.yml` → repo root
- `.github/workflows/seo-growth-loop.yml`
- `reports/HUMAN-INBOX.md`

Confirm the workflow's plugin lines read:

```
plugin_marketplaces: "https://github.com/jishhnnuu/seo-aeo-geo.git"
plugins: "claude-seo-unified@jishnu-seo-aeo-geo"
```

Fill `seo-config.yml` from the URL plus what you detect in this repo —
never guess where you can read:

- `site.url` — the live URL
- `site.platform` — `git-static`
- `site.deploy_branch` — this repo's default branch
- `site.build_command` — from `netlify.toml` / `vercel.json` / `package.json`
- `site.framework`, `site.output_dir` — detected (Astro, Next, Nuxt, Hugo,
  Jekyll, Eleventy, Gatsby, SvelteKit, plain HTML). These tell the fixer
  which source files produce which URLs, and which directory is generated
  output it must never edit.
- `site.netlify_site_name` — from `netlify.toml`'s site name or the Netlify
  API if a token is available; leave blank if unknown, it only sharpens
  pre-merge testing.

## Step 3 — Install credentials as repo secrets

Scheduled runs happen on a fresh runner with nothing on it, so credentials
must be this repo's GitHub secrets. Do this for the user — they should
never copy or paste a key by hand.

Read what is already configured on this machine:

- `~/.config/claude-seo/google-api.json` — Google API key plus a path to,
  or inline copy of, the service-account JSON
- `~/.config/claude-seo/backlinks-api.json` — Moz and Bing keys

Set each with `gh secret set`:

| Secret | Source |
|---|---|
| `GOOGLE_API_KEY` | the `api_key` field |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | the full service-account JSON, inline |
| `MOZ_API_KEY` | backlinks config, if present |
| `BING_WEBMASTER_API_KEY` | backlinks config, if present |
| `GSC_PROPERTY` | `sc-domain:<domain>`, derived from the live URL |
| `GA4_PROPERTY_ID` | this site's GA4 property, if configured |
| `INDEXNOW_KEY` | generate a fresh 32-character hex key |
| `CLAUDE_CODE_OAUTH_TOKEN` | already present if `/install-github-app` ran; if missing, say so and tell them to run it |
| `GROWTH_LOOP_PAT` | **required** — see below. Never generate this yourself; a token cannot be minted by an agent |
| `REPORT_EMAIL_TO` | optional — where to email the weekly report. Ask the user once; if they decline, the report still reaches them as a GitHub issue comment |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | optional, only with `REPORT_EMAIL_TO`. For Gmail this must be an App Password, not the account password. Never ask the user to paste it into chat — tell them to set it with `gh secret set SMTP_PASSWORD` so it is never in a transcript |

### `GROWTH_LOOP_PAT` — the one secret the loop cannot run without

GitHub does not start a workflow run from an event created with the built-in
`GITHUB_TOKEN`. The `build` job opens a pull request and `test-and-publish`
runs `on: pull_request`, so without a real token that PR is never tested and
never merged — the loop stalls every cycle while still looking healthy in the
Actions tab.

You cannot mint this token. Check whether it already exists
(`gh secret list`); if it does not, put it at the top of
`reports/HUMAN-INBOX.md` and tell the user directly, in one short paragraph:
create a fine-grained personal access token limited to this one repository,
with **Contents: read/write, Pull requests: read/write, Issues: read/write**,
then `gh secret set GROWTH_LOOP_PAT`. Give them the exact link
(`https://github.com/settings/personal-access-tokens/new`) and the exact
permission names. This is a rung-7 human atom under the resolver's ladder: it
is a physical action only the account owner can take, and everything around it
is already prepared.

Everything else on this page degrades gracefully. This one does not.

### Where the shared secrets live

The workflow's comments describe organization secrets for the credentials that
are identical across every site. Check what the account actually is before
repeating that advice — `gh api user --jq .type` returns `User` or
`Organization`:

- **Personal account** — there is no account-level Actions secret on GitHub.
  Set every secret on each site repo. That is a handful of `gh secret set`
  calls per site, which you are doing anyway; just do not tell the user they
  can set them "once".
- **Organization** — organization secrets work, and every site repo inherits
  them. On *private* repos this additionally requires a Team plan; on public
  repos it works on Free. If the org is on Free with private repos, fall back
  to per-repo secrets.

If a credential is not where you expect it, hand the problem to
`seo-resolver` before giving up on it — it will look in other locations,
check environment variables, and check whether an organization-level secret
already covers it. Only what survives that gets skipped and listed at the
end. Every one is optional and the loop degrades to weaker data rather than
failing. Never invent a value. Never print a secret's value into the chat
or into a file.

Commit the IndexNow key file: `<key>.txt` at the served site root (the
framework's `public/` or `static/` directory if it has one), containing
that key as its only content.

## Step 4 — Mark the repo as managed

```
gh repo edit --add-topic seo-growth-loop
```

This topic is how future sessions find every site running the loop, so no
central list has to exist anywhere.

## Step 5 — Ship it and run once

Commit to a branch, open a PR, merge once CI is green. These are config
and workflow files, not site content, so the loop's own test gate does not
apply to them.

Then run the first cycle now rather than waiting for Monday. The workflow
takes a `job` input, so trigger the three jobs **in order**, waiting for each
to finish before starting the next. They write to the same branch, and firing
them together makes them race:

```bash
gh workflow run seo-growth-loop.yml -f job=plan-and-audit   # roadmap + full audit
# wait for it to complete, then:
gh workflow run seo-growth-loop.yml -f job=build            # fixes + content, opens a PR
# the PR triggers test-and-publish on its own. Once it has merged:
gh workflow run seo-growth-loop.yml -f job=report           # the weekly report
```

Expect the audit to take roughly 10 to 30 minutes depending on site size.
The `build` job opens a pull request; `test-and-publish` fires from that pull
request automatically, which is the step that proves `GROWTH_LOOP_PAT` is
working. If the PR opens and nothing then tests it, that secret is missing or
wrong, and the whole loop will stall silently every cycle until it is fixed.
Check that specifically before declaring the setup done.

Watch every run. If it fails, do not report the failure and stop — invoke
`seo-resolver` with the literal error from the log and let it work the
problem. Wrong marketplace name, malformed `seo-config.yml`, a missing
checkout and an unauthenticated plugin fetch are the usual suspects, and
all are fixable. Re-run until it passes or the resolver has exhausted its
full ladder.

## Step 6 — Report

- Framework and build command detected
- Which secrets were set; which are missing and what each would unlock
- Whether the first run passed, and its SEO Health Score
- Any assumption worth confirming

Then state plainly that nothing further is needed: the loop now runs
audits weekly, fixes and content twice weekly, and indexing checks daily,
unattended.
