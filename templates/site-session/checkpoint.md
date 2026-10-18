# Checkpoint (day 30 and day 60)

Read `RULES.md` first and set the names it defines, with `<routine>` = `checkpoint`. The prompt says which day.

1. Pull fresh data: `python3 $E/scripts/site_routine.py pull --site-dir $S --date $TODAY`.
2. If this month has no snapshot in `$C/campaign.json` yet, record one exactly as in `weekly.md` step 7.2.
3. Run:

```bash
python3 $E/scripts/linkbuilding.py scorecard --campaign $C --json > $S/.seo/checkpoint-scorecard-$TODAY.json
python3 $E/scripts/site_routine.py health --site-dir $S --date $TODAY
python3 $E/scripts/linkbuilding.py status --campaign $C
```

4. Decide with this table. Use the first row that matches.

| Situation | Verdict | What happens next |
|-----------|---------|-------------------|
| Any `red` health check for access, schedule, privacy or bounces | **Blocked** | Fix or escalate that item first; the results cannot be judged yet. |
| Scorecard `needs_action` and the failed checks are owner bottlenecks (approvals, sending) | **Stalled on approvals** | List the exact owner actions; nothing else changes. |
| Scorecard `needs_action` for reply rate | **Pitch problem** | Rewrite hooks, switch the lead asset, cut the weakest tactic; re-check in 30 days. |
| Scorecard `needs_action` for search metrics only | **Content gap** | Next four weekly runs prioritise `answer` and `striking` items on the promoted pages. |
| Scorecard `on_track` or only `not_measured` items | **On track** | Continue unchanged. |

5. Write `$S/.seo/checkpoint-day<d>.md` with the scorecard table, the health list, the verdict and the next steps.
6. Day 60 only: recommend to the owner whether to keep the Thursday run (keep it if at least 10 prospects are waiting
   or follow-ups are due weekly; otherwise suggest switching it off) and whether this site's results justify starting
   the same program on the next sites. Do not disable any scheduled task without the owner's yes.
7. `python3 $E/scripts/site_routine.py mark-run --site-dir $S --routine checkpoint --status done --date $TODAY --note "day <d>: <verdict>"`, commit and push `$S/.seo/`.
8. Send the owner, in under 200 words: verdict, the three most important numbers against the baseline, what changes
   now, and the "needs you" items with minutes for each.
