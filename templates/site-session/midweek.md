# Midweek run (every Thursday, first 60 days)

Time budget: about 15 minutes. Read `RULES.md` first and set the names it defines, with `<routine>` = `midweek`.
No on-site page changes in this run.

1. `python3 $E/scripts/linkbuilding.py due --campaign $C`. For each "send follow-up" line, the follow-up text is
   already in the prospect's draft; run `export --campaign $C` so the owner has it in the CSV.
2. Prepare any newly `approved` prospects exactly as in `weekly.md` step 6.2 and 6.3.
3. For prospects the owner logged as `won` since Monday: `python3 $E/scripts/linkbuilding.py verify --campaign $C`.
4. Run the indexing check from `weekly.md` step 5 for pages shipped on Monday.
5. `python3 $E/scripts/site_routine.py health --site-dir $S --date $TODAY`. Note every `red` check.
6. `python3 $E/scripts/site_routine.py mark-run --site-dir $S --routine midweek --status done --date $TODAY`, then commit and push `$S/.seo/`.
7. Send the owner, in under 120 words:

```
<Site>, midweek.
Send today: <n> follow-ups and <n> new emails (file: <path to outreach-approved.csv>).
Approve: <n> prospects waiting (run `linkbuilding.py shortlist --campaign <C>` or ask me to list them).
New links verified: <n>. Pages not yet indexed: <list or "none">.
Warnings: <each red health check message, or "none">.
```
