# gh-308-deletion-test-ceiling — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: orchestrator (intent-review routing)
- date: 2026-10-16
- trigger: ambiguous-direction
- question: The approved `intent.md` (pinned at `03e3555`) and the decisions the user made later in brainstorming disagree on three points; which one is the intent the branch must meet?
- context: Intent review (plan-blind, oracle = pinned intent.md) reports these as gaps or drift. Shipping is blocked until the oracle and the diff agree.
  - (a) intent.md: "The STE-flavored mode of `skills/asd-ste100/SKILL.md` states the same procedure as the way to meet a length cap." The user chose option A in brainstorming instead: a harness-owned KB entry, because `asd-ste100` is a vendored copy whose `UPSTREAM.md` allows no further differences (design D1). The diff follows D1.
  - (b) intent.md: "A blind task-review run on those diffs reports zero lost conditions, recorded beside the existing A/B in `rules/terminology.md`." The user chose proof option A instead: the existing qualifier check plus the reviewer's meaning verdict, with no new eval and no `terminology.md` entry (design D2). The diff follows D2.
  - (c) intent.md Constraints: "Edits to the three skills delete whole sentences only." The approved design adds whole-block moves behind a one-line pointer (design Architecture §2, D4). The diff has two such pointers in `finishing-a-development-branch` and one in `feature-intake`, plus one reworded antecedent ("Then stage exactly `RUN.json` and `events.jsonl`").
  - Related, smaller: intent.md says "freeing at least 60 words in each"; `feature-intake` freed 59 (598 → 539). Its success line "each at least 60 words under 600" holds (539 is 61 under).
- options:
  - A) Amend `intent.md` to match the approved design (D1, D2, the block-move rule, and "at least 60 words under 600" as the measure), commit it, and re-pin the slug through feature-intake's re-pin procedure. Then re-run intent review against the new pin. No code change. Recommended: the design decisions were the user's own choices, recorded in this conversation, and they avoid a vendored-file edit and an out-of-place experiment record.
  - B) Keep `intent.md` as written and do the missing work: add the procedure to `skills/asd-ste100/SKILL.md` and record a fourth difference in its `UPSTREAM.md`; add a blind task-review eval fixture and run, recorded in `rules/terminology.md`; delete one more whole sentence in `feature-intake`; and replace the three pointers with plain deletions where possible. This reverses design D1 and D2 (each needs a `DC<n>` entry) and adds two more workflow-engine files.
  - C) Mixed: say which of (a), (b), (c) to keep as written and which to amend.
- default_if_no_response: BLOCK
- decision: A — amend `intent.md` to match the approved design (D1, D2, the block-move rule, "at least 60 words under 600"), re-approve it, re-pin the slug, and re-run intent review. No code change.
- decided_by: Minh Tran (chat reply "A")
- decided_at: 2026-10-16
