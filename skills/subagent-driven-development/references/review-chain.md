# Final review chain

This chain starts only after `references/simplify-stage.md` has recorded its outcome and any
accepted cleanup is committed — the diff and HEAD below are already post-simplify.

If the cumulative diff touches workflow-engine paths, run `/context-propagation-audit` first.
Create one explicit branch review package (`BASE..HEAD`) using `review_package.py` and give its
path to `/correctness-review` and `/intent-review`. They may share only this mechanical evidence:
their distinct oracle inputs and blindness rules remain unchanged. Then run both over the complete
implementation diff. Each must resolve, escalate, or durably record every finding before the
receipt is written. The invoked skill owns its detailed pipeline; do not copy it here.
