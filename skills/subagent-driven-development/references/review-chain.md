# Final review chain

If the cumulative diff touches workflow-engine paths, run `/context-propagation-audit` first.
Then run `/correctness-review` and `/intent-review` over the complete implementation diff. Each
must resolve, escalate, or durably record every finding before the receipt is written. The invoked
skill owns its detailed pipeline; do not copy it here.
