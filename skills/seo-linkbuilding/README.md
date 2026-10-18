# Link Building Module

Everything for off-page authority lives here. It is part of every client engagement: the orchestrator
(`skills/seo/SKILL.md`, "Link Building Is Always On") and full audits run its readiness check for every site, and show
the weekly plan and scorecard for any site that already has a campaign.

## What is where

| Path | What it is |
|------|------------|
| `SKILL.md` | The `/seo linkbuilding` workflow: onboard, weekly run, approval gate, drafts, tracking, report |
| `references/six-month-program.md` | New-client process, the 26-week plan, fast start, what month 1 to 6 should show |
| `references/operating-model.md` | Portfolio strategy, free data stack, spend ladder, industry plays, multi-site rules |
| `references/site-readiness.md` | What the site needs before outreach, and the linkable assets to build |
| `references/prospect-discovery.md` | Where prospects come from and how to qualify them |
| `references/outreach-playbook.md` | First touch, follow-ups, replies, law, verification |
| `data/library.json` | Evergreen link sources by industry and the tactic success ranges used for estimates |
| `data/blocklist.json` | Screening rules: gambling, adult, piracy, fake .edu, link sellers, cloned metrics |
| `data/seller_listed_domains.txt` | Domains seen in paid guest-post sheets (paid-only, never organic) |
| `../../scripts/linkbuilding.py` | The engine. It sits in `scripts/` because `claude-seo run` only executes scripts from there |
| `../../scripts/google_report.py --type link-building` | The PDF and XLSX report section |

Campaign state for each client is written to `link-campaigns/<domain>/` in the working directory: `campaign.json`,
`prospects.json`, `program.json`, `program.md`, `suppression.txt`, drafts and exports.

## The client lifecycle in five commands

```bash
claude-seo run linkbuilding.py init --campaign link-campaigns/<domain> --site <url> --name "<Name>" --industry <industry>
claude-seo run linkbuilding.py readiness --url <url> --industry <industry> --campaign link-campaigns/<domain>
claude-seo run linkbuilding.py program --campaign link-campaigns/<domain> --start <monday>   # fast start if ready
claude-seo run linkbuilding.py week --campaign link-campaigns/<domain>                       # every week
claude-seo run linkbuilding.py scorecard --campaign link-campaigns/<domain>                  # every month
```

Tests: `tests/test_linkbuilding.py`, `tests/test_linkbuilding_report.py`.
