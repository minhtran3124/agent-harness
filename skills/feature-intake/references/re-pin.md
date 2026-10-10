# Re-pin an intent

Use this when the slug already has a SUMMARY and either it has an `Intent-source:` line or
`specs/<slug>/intent.md` exists. On every stop below, write nothing and tell the user why.

1. If SUMMARY has an `Intent-source:` line but intent.md no longer exists, stop. The user either
   restores intent.md or removes the `Intent-source:` line to continue from the chat request.
2. Read the files Step 1 of `../SKILL.md` names and run its intent.md checks (approved `Status:`
   header line, non-empty pin, no uncommitted change). Stop on any failure, as Step 1 says.
3. If the new pin equals the SHA already on the `Intent-source:` line, change nothing.
4. Re-classify (Steps 2–4 of `../SKILL.md`) from intent.md plus the chat request. If the lane
   differs from SUMMARY's `Lane:`, or confidence is `low`, stop and show the user the old and new
   values. The user updates SUMMARY (or the intent) and runs intake again.
5. Otherwise replace the `Intent-source:` line, or add it atop `### Intent` above the chat
   request. Add one dated `### Intake notes` line with the old → new SHA (old is `none` when the
   line was added) and any confidence or flags change; if `### Intake notes` holds only `- none`,
   replace that line.
6. Change nothing else in SUMMARY: do not rewrite it from the template or re-initialize run
   state. Run `python3 scripts/verify_summary.py --lane <slug>`.
