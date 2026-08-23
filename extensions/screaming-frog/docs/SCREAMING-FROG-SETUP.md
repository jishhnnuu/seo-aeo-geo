# Screaming Frog Extension Setup

## What this is (and isn't)

This extension automates the **CLI mode** of a Screaming Frog SEO Spider
licence you already own or are purchasing. It does not include a
licence, does not unlock paid features for free, and does not work
around the free version's 500-URL crawl cap. If you're on the free
tier, use the built-in `/seo audit` instead (also capped around 500
pages, at no cost and no local install).

## Setup

1. Buy/download Screaming Frog SEO Spider: https://www.screamingfrog.co.uk/seo-spider/
2. Install it and activate your licence.
3. Confirm the CLI binary is on `$PATH`:
   ```bash
   screamingfrogseospider --version
   ```
   - **macOS**: the CLI is typically already linked; if not, symlink the
     binary inside `Screaming Frog SEO Spider.app/Contents/MacOS/`.
   - **Linux**: the `.deb`/`.rpm` package installs the CLI on `$PATH`
     directly.
   - **Windows**: add the Screaming Frog install directory to your
     `PATH` environment variable, or run this extension from WSL with
     the Linux build installed there.
4. Run `extensions/screaming-frog/install.sh` — it re-checks the binary
   and installs the `seo-screaming-frog` skill.
5. Try: `/seo screaming-frog https://example.com`

## Licensing tiers and what they mean for this extension

| Screaming Frog tier | Crawl limit | Notes |
|---|---|---|
| Free | 500 URLs | Same order of magnitude as `/seo audit`'s built-in crawl — this extension adds little value here. |
| Paid (annual licence) | Unlimited (memory-bound) | This is the tier this extension is built for. |

## Troubleshooting

- **"screamingfrogseospider not found on PATH"**: the binary isn't
  installed or isn't linked into `$PATH`. Re-check step 3.
- **Crawl times out**: very large sites (500k+ URLs) can exceed the
  default 3600s subprocess timeout. Pass a longer `--timeout` or a
  lower `--max-urls` to `scripts/screaming_frog_run.py`.
- **Memory errors from Screaming Frog itself**: this is a Screaming
  Frog resource limit, not something this wrapper controls — see
  Screaming Frog's own docs on configuring storage mode (RAM vs
  database) for large crawls.
