# Resume actions

`resume_decision.py` is the authority. For `rebuild`, run the named non-mutating check first, then
rebuild only when it reports projection drift. For `wait` or `stop`, report the returned reason and
do not edit. For `resume-repair` follow the named CI/review loop; do not re-run plan tasks. For
`resume-review-chain`, run `python3 scripts/check_review_receipt.py <specs/slug-dir>
--require-simplify-if <base>` first: a result with no `simplify`-related failure means the stage's
evidence already covers the current HEAD — start directly at `references/review-chain.md`, do not
re-run `references/simplify-stage.md`. A `missing` or `stale-sha` result means the stage has not
run, or its evidence no longer covers the current HEAD — start at `references/simplify-stage.md`
before the rest of final delivery/correctness/intent review. Only `execute-plan` enters the
preflight and wave loop.
