# Re-pin an intent

Use this when the slug's SUMMARY already has an `Intent-source:` line, or when a slug started
from chat (no `Intent-source:` line) gains an approved `specs/<slug>/intent.md`.

1. If SUMMARY has an `Intent-source:` line but `specs/<slug>/intent.md` no longer exists, stop
   and escalate to a human.
2. Run the intent.md checks in Step 1 of `../SKILL.md` (approved `Status:` header line, non-empty
   pin, no uncommitted change). Stop on any failure, as Step 1 says.
3. Re-check the lane and confidence (Steps 2–4) from the new intent.md plus the chat request. If
   either differs from SUMMARY's `Lane:` or `Confidence:`, stop and escalate to a human as an
   ambiguous direction or system change. Do not edit SUMMARY.
4. Otherwise change only the `Intent-source:` line: replace it, or add it atop `### Intent` above
   the chat request. Then add one dated `### Intake notes` line with the old → new SHA (old is
   `none` when the line was added).
5. Change nothing else in SUMMARY: leave `Lane:`, `Confidence:`, `Reason:`, `Flags:`, `Route:`,
   and `Escalate:` as they are, do not rewrite SUMMARY from the template, and do not
   re-initialize run state. Then run the Step 7 `verify_summary.py --lane <slug>` check.
