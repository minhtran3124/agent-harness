# Resume actions

`resume_decision.py` is the authority. For `rebuild`, run the named non-mutating check first, then
rebuild only when it reports projection drift. For `wait` or `stop`, report the returned reason and
do not edit. For `resume-repair` follow the named CI/review loop; do not re-run plan tasks. For
`resume-review-chain`, start final delivery/correctness/intent review. Only `execute-plan` enters
the preflight and wave loop.
