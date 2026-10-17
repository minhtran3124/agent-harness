# Final review chain

For a diagnosed bug fix (`references/bug-fix.md`), run `diagnosing-bugs` Phase 6 first, before the audit:

1. Run the loop from `diagnosis.md` `Loop:` again. It must now pass.
2. Grep the `[DEBUG-` tag in the branch diff and in the working tree.
3. Delete each tagged log or throwaway harness that is left.
4. Name the `Confirmed:` hypothesis in the commit message and in SUMMARY `Rationale`.

If the cumulative diff touches workflow-engine paths, run `context-propagation-audit` first.
Build one explicit branch review package (`BASE..HEAD`) with `review_package.py`. Pass its path
to `correctness-review` and `intent-review`. They may share only this mechanical evidence. Their distinct
oracle inputs and blindness rules remain unchanged. Run both over the complete implementation diff.
Have each review resolve, escalate, or durably record every finding before the receipt is written.
Each invoked skill owns its detailed pipeline. Do not copy it here.
