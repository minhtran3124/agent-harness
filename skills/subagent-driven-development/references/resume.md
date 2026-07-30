# Resume actions

`resume_decision.py` is the authority. For `rebuild`, run the named non-mutating check first, then
rebuild only when it reports projection drift. For `wait` or `stop`, report the returned reason and
do not edit. For `resume-repair` follow the named CI/review loop; do not re-run plan tasks. For
`resume-review-chain`, run `python3 scripts/check_review_receipt.py <specs/slug-dir>
--require-simplify-if <base>` first and act on its exit code, not on any specific failure message —
it fails closed on every simplify-related problem (missing entry, stale SHA, malformed shape,
failing verdict, or any other reason), so treating them uniformly is the point, not a shortcut.
Exit 0 means the stage's evidence already covers the current HEAD — start directly at
`references/review-chain.md`, do not re-run `references/simplify-stage.md`. Nonzero means the stage
has not run, or its evidence no longer covers the current HEAD for any reason the checker reports —
start at `references/simplify-stage.md` before the rest of final delivery/correctness/intent
review. Only `execute-plan` enters the preflight and wave loop.
