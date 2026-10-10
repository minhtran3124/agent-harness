# Re-pin an intent

Use this when the slug's SUMMARY already has an `Intent-source:` line, or when a slug started
from chat (no `Intent-source:` line) gains an approved `specs/<slug>/intent.md`.

1. If SUMMARY has an `Intent-source:` line but `specs/<slug>/intent.md` no longer exists,
   escalate (below).
2. Read the files Step 1 of `../SKILL.md` names and run its intent.md checks (approved `Status:`
   header line, non-empty pin, no uncommitted change). Stop on any failure, as Step 1 says.
3. If the new pin equals the SHA already on the `Intent-source:` line, change nothing and stop
   the re-pin; still run the `verify_summary.py --lane <slug>` check from step 7.
4. If `specs/<slug>/ESCALATIONS.md` has a block an earlier re-pin raised for this slug: while its
   `decision:` is `pending`, stop. Once a decision is recorded, apply it: set `Lane:`,
   `Confidence:`, `Reason:`, `Flags:`, `Route:`, and `Escalate:` as decided, skip step 5, and do
   step 6, whose Intake notes line also names the decision's E-id.
5. Re-check the lane, confidence, and flags (Steps 2–4 of `../SKILL.md`) from the new intent.md
   plus the chat request. If `Lane:`, `Confidence:`, or `Flags:` differs from SUMMARY, escalate
   (below).
6. Change the `Intent-source:` line: replace it, or add it atop `### Intent` above the chat
   request. Then add one dated `### Intake notes` line with the old → new SHA (old is `none`
   when the line was added). If `### Intake notes` holds only `- none`, replace that line with
   the note.
7. Change nothing else in SUMMARY: apart from lines a decision set in step 4, leave `Lane:`,
   `Confidence:`, `Reason:`, `Flags:`, `Route:`, and `Escalate:` as they are, do not rewrite
   SUMMARY from the template, and do not re-initialize run state. Then run the Step 7
   `verify_summary.py --lane <slug>` check of `../SKILL.md`.

## Escalate

Append a block to `specs/<slug>/ESCALATIONS.md` (shape: `templates/ESCALATIONS.template.md`,
trigger `ambiguous-direction`, `decision: pending`) and stop. Do not edit SUMMARY. A human may
record a decision (applied by step 4 on the next intake run) or edit SUMMARY directly, in which
case the next re-check simply matches.
