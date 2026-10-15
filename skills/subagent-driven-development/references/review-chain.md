# Final review chain

If the cumulative diff touches workflow-engine paths, run `context-propagation-audit` first.
Build one explicit branch review package (`BASE..HEAD`) with `review_package.py`. Pass its path
to `correctness-review` and `intent-review`. They may share only this mechanical evidence. Their distinct
oracle inputs and blindness rules remain unchanged. Run both over the complete implementation diff.
Have each review resolve, escalate, or durably record every finding before the receipt is written.
Each invoked skill owns its detailed pipeline. Do not copy it here.
