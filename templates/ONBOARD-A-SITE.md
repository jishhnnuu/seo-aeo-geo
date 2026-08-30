# Add a website to the Growth Loop

Run this in a Claude Code session opened on **the website's own repo** —
not on the engine repo. Nothing about this website ever gets written into
the engine repo; the engine stays a generic agent team that any site can
use.

Fill in the three values below and paste the whole file.

---

## This website

- **Live URL:** `<https://example.com>`
- **Netlify site name:** `<from Netlify -> Site configuration -> Site details>` (optional — leave blank and the tester falls back to checking source instead of the rendered preview)
- **Nickname:** `<short-slug>` (optional — defaults to the repo name)

## Mission

Install the Growth Loop on this repo so it audits, fixes, tests and
publishes this website on a schedule, unattended. Work through every step
without pausing for approval on judgment calls — make the reasonable
choice, note it in your final summary, and keep going. Only stop if a step
is impossible without something only the repo owner can provide.

## Step 1 — Confirm this repo is the right shape

This repo should be the one the host (Netlify, Vercel, Cloudflare Pages,
GitHub Pages) builds the live site from. Verify by looking for a
`netlify.toml`, `vercel.json`, a static-site-generator config, or a
`package.json` with a build script. Say what you found.

If this repo does **not** build the site — i.e. the site lives in a CMS
like WordPress, Shopify or Webflow — stop and say so. That case needs a
separate control repo, which is a different setup.

## Step 2 — Copy in the loop

Fetch these from the engine repo,
`https://github.com/jishhnnuu/seo-aeo-geo`, under `templates/site-repo/`,
and write them into this repo at the same relative paths:

- `seo-config.yml` → repo root
- `.github/workflows/seo-growth-loop.yml`
- `reports/HUMAN-INBOX.md`

In the workflow, the two plugin lines should read:

```
plugin_marketplaces: "https://github.com/jishhnnuu/seo-aeo-geo.git"
plugins: "claude-seo-unified@jishnu-seo-aeo-geo"
```

In `seo-config.yml`, fill in from the values at the top of this file plus
what you can detect from the repo itself:

- `site.url` — the live URL above
- `site.platform` — `git-static`
- `site.deploy_branch` — this repo's default branch
- `site.build_command` — read it from `netlify.toml`, `vercel.json`, or
  `package.json` rather than guessing
- `site.framework` / `site.output_dir` — detect from the repo (Astro, Next,
  Hugo, Jekyll, Eleventy, plain HTML); these tell the fixer which files
  produce which URLs, and which directory is generated output it must never
  edit
- `site.netlify_site_name` — the value above, if given

## Step 3 — Install the credentials, without the owner handling any keys

The scheduled runs happen on a fresh GitHub runner with nothing on it, so
the API credentials have to be stored as this repo's GitHub secrets. Do
this for them — they should never have to copy or paste a key.

Read whatever is already configured on this machine:

- `~/.config/claude-seo/google-api.json` — contains the Google API key, and
  a path to (or inline copy of) the service-account JSON
- `~/.config/claude-seo/backlinks-api.json` — Moz and Bing keys, if present

Then set them on this repo with `gh secret set`:

| Secret | Source |
|---|---|
| `GOOGLE_API_KEY` | the `api_key` field |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | the full service-account JSON, inline |
| `MOZ_API_KEY` | backlinks config, if present |
| `BING_WEBMASTER_API_KEY` | backlinks config, if present |
| `GSC_PROPERTY` | `sc-domain:<domain>` for this site — derive it from the live URL |
| `GA4_PROPERTY_ID` | this site's GA4 property, if the owner has one configured |
| `INDEXNOW_KEY` | generate a fresh 32-character hex key for this site |
| `CLAUDE_CODE_OAUTH_TOKEN` | already set if `/install-github-app` ran here; if missing, say so |
| `GROWTH_LOOP_PAT` | **required** — a fine-grained PAT scoped to this repo, Contents + Pull requests + Issues at read/write. Only the account owner can create it |

Anything else you genuinely cannot find, skip and list at the end — the rest
are optional and the loop degrades to weaker data rather than failing. Never
invent a value, and never print a secret's value back into the chat.

`GROWTH_LOOP_PAT` is the exception: it is not optional. GitHub does not start
a workflow run from an event created with the built-in `GITHUB_TOKEN`, so a
pull request opened by the build job would never trigger the test-and-publish
job — the PR would sit open, nothing would merge, and the loop would stall
every cycle while the Actions tab still showed green. If the secret is absent,
say so plainly, link
<https://github.com/settings/personal-access-tokens/new>, and name the three
permissions exactly.

Note on shared secrets: GitHub has no account-level Actions secret. If these
repos live under a personal username, set every secret on each site repo —
do not tell the owner they only need to do it once. Organization secrets do
work for organizations (on private repos that needs a Team plan).

Then commit the IndexNow key file: a file named `<key>.txt` at the site
root (or in the public/static directory the framework serves from)
containing that same key as its only content.

## Step 4 — Mark this repo as managed

Add the GitHub topic `seo-growth-loop` to this repo:

```
gh repo edit --add-topic seo-growth-loop
```

That topic is how any future session finds every site running the loop,
without the engine repo needing to keep a list.

## Step 5 — Commit and open the first run

Commit everything to a branch, open a PR, and merge it once CI is green —
these are config and workflow files, not site content, so they don't need
the loop's own test gate. Then trigger the loop manually from the Actions
tab (`workflow_dispatch`) rather than waiting for Monday, so the first
audit lands now.

Watch the run. If it fails, read the log and fix the cause — a wrong
marketplace name, a malformed `seo-config.yml`, or a missing checkout are
the usual suspects — then re-run.

## Step 6 — Report back

In a few lines:
- Which framework and build command you detected
- Which secrets got set, and which are missing and what each would unlock
- Whether the first run passed, and the SEO Health Score it produced
- Anything you assumed that's worth confirming
