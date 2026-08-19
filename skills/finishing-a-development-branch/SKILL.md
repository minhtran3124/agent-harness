---
name: finishing-a-development-branch
description: Verify a completed branch, pin required review receipts, push it, and open a pull request. Creates a PR only: never merges, force-pushes, discards work, or amends commits.
---

# Finishing a Development Branch

Announce this flow. Resolve context once and use its JSON throughout:

```bash
python3 scripts/resolve_finish_context.py
```

The helper reports branch, base, merge base, plan directory, lane, ambiguity, changed files,
receipt path, and whether a context-delivery audit is required. If it reports ambiguity, ask the
user; if no plan exists, use the tiny/no-plan path instead of guessing.

## Verify and gate

1. Run the repository’s targeted suite, or the full suite if no safe subset is known. The exact
   command comes from `agents/PROJECT.md` → *Test execution*; never assume a stack or a script
   name. Fix failures and retry at most twice; never push a failing change.
2. For non-tiny work with a resolved plan, pin reviews at the resolved base:

   ```bash
   python3 scripts/check_review_receipt.py <plan_dir> --require correctness,intent --require-audit-if <base>
   ```

   A missing, stale, failing, or blocking receipt stops the flow. Re-run the affected review; never
   edit the receipt to pass. Re-run this gate immediately before push. Tiny/no-plan work skips it.
3. Mark the resolved plan `status: shipped`, append a dated status-log entry, and commit the
   tracked `specs/` update. The helper-selected plan—not a branch-name guess—is authoritative.
   Do not manually change version/changelog/trust ledger when post-merge automation exists.

## Push and PR

Push without force. Create or update one PR against the resolved base, using a concise body with
behavioral summary, tasks, and only a useful flow diagram. After creation, best-effort transition
the run to `ready_to_merge` — run `python3 runtime/run_state.py transition --slug <slug> --to ready_to_merge --event pr.opened || true` (non-fatal; the concrete form of this checkpoint). This is the
hop the post-merge `shipped` transition depends on: `shipped` is legal only from `ready_to_merge`,
so a run left at `verifying` never terminalizes. Return the URL and stop. A human reviews and merges.

## Safety boundary

Never merge, force-push, `git add -A`, `git clean`, discard work, or amend a commit. Stage named
files only. An external reviewer is recommended for workflow-engine changes but is not a local push
gate; the receipt and deterministic checks remain mandatory.

## References

- `references/pr-body.md` — PR body shape
- `references/workflow-engine-review.md` — independent-review guidance
- `scripts/resolve_finish_context.py` — context authority
