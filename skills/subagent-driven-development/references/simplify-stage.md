# Simplify stage

One required cleanup pass over the branch diff, run once per final review cycle, after every wave
task has passed and before the branch review package, `/context-propagation-audit`,
`/correctness-review`, `/intent-review`, and `.review-receipt.json` (Global Constraint: "All final
review packages, oracles, and receipts are created after accepted simplify mutations"). Uses only
Claude Code's bundled `/simplify`; never create or call a repository skill of that name.

## Sequence

1. **Resolve policy.** Run `python3 scripts/check_claude_simplify.py` with the intake lane, the
   explicitly resolved `<base>..<head>` (the same base the branch review package will use — never
   an implicit default branch), the changed reviewable paths, `git diff --numstat` for that exact
   range, and the installed Claude Code version. Its JSON `required`/`reason`/`capability`/`ok`/
   `reviewable_paths` is the only source of that decision; do not re-derive any of it from the diff
   yourself.
2. **No reviewable paths.** `reviewable_paths` is empty (`reason` is one of `no_changes`,
   `documentation_only`, `specs_bookkeeping_only`, `evaluation_only`, `vendor_only`,
   `generated_only`, `excluded_only`). `check_review_receipt.py --require-simplify-if`'s own
   push-time check independently agrees no entry is needed for a diff with no reviewable path — do
   not call `simplify_record.py` at all. Skip straight to `references/review-chain.md`.
3. **Reviewable paths exist — begin.** On a clean, fully committed worktree, run
   `simplify_record.py begin --base <base> --target HEAD --claude-code-version <version>` and keep
   its JSON output — it is the only place the dirty-worktree refusal and base/pre-checkpoint
   resolution happen; do not reimplement either check here. Do this regardless of `required`:
   `check_review_receipt.py`'s push-time gate only knows whether the diff touches a reviewable
   path, not the lane/tiny-size threshold that decides `required` — so an entry must exist whenever
   any reviewable path changed, even a `tiny_source_change` that step 1 marked advisory-only.
4. **`required: true` and `ok: false`.** The client capability is missing, malformed, or too old:
   stop and report the capability error from step 1's JSON; do not invoke `/simplify` and do not
   continue silently to `references/review-chain.md`.
5. **Decide whether to invoke.** `required: false` (the tiny/advisory case) — skip the invocation;
   the outcome is `outcome: no_op` with step 1's bounded `reason`; go to step 7. `required: true`
   and `ok: true` — invoke Claude Code's bundled `Skill(simplify)` over this range exactly once: one
   tool call, one matching result. If the tool call itself errors before producing a result, that
   is `cannot_verify` in step 6 — not license to invoke it again.
6. **Handle the invocation's result.** An unchanged worktree is `outcome: no_op`. A mutation is
   `outcome: changed`: build a delta review package for exactly `pre_sha..post_sha` with
   `review_package.py`, run the task's own targeted `Verify` command over that delta, and dispatch
   the same combined `task-reviewer` used for wave tasks (`task-reviewer-prompt.md`, one dispatch,
   `spec_verdict` + `quality_verdict`) with the plan's Global Constraints as context. A
   `cannot_verify` or failing `spec_verdict`, a `needs_fixes` `quality_verdict`, a failing targeted
   verification run, and any Critical/Important finding are all rejections. Resolve a rejection by
   either discarding the mutation (worktree returns to `pre_sha`, so the outcome recorded in step 7
   becomes `no_op`) or fixing the flagged issues directly and re-running only the targeted
   verification and the delta review — never the `/simplify` invocation — until both pass.
7. **Record the outcome.** Run `simplify_record.py finish --begin-state <step-3 output> --outcome
   changed|no_op --changed-files ... --reason <the step-1 bounded reason> --verification-result
   pass|fail --delta-verdict '{"spec_verdict":...,"quality_verdict":...}'`. Step 3 always ran before
   this point whenever reviewable paths exist, so `--begin-state` always has a valid file to read —
   including the not-required/`tiny_source_change` skip in step 5. It resolves the post-simplify
   SHA, checks ancestry, and recomputes `result` from that evidence itself — never hand-set
   `result: pass`. A `no_op` outcome carries no verification/delta evidence, matching the receipt's
   no-op shape.
8. **Commit accepted cleanup.** A `changed` outcome whose recorded `result` is `pass` must be
   committed before the branch review package is created in `references/review-chain.md` — that
   commit is itself part of the ordering constraint, not optional bookkeeping. A `no_op` outcome has
   nothing to commit.
9. **Hand off.** Create or update `.review-receipt.json`: set `reviewed_head_sha` to the current
   (post-simplify) HEAD and append the `finish` entry to `reviews` with `type: simplify`. Then read
   `references/review-chain.md` for the remaining final sequence — its branch package and oracles
   run at this post-simplify HEAD. A later post-review code commit still invalidates the receipt
   per the existing rule in "Receipt and ship gate"; never hand-edit `reviewed_head_sha` or a
   recorded entry.

For a resumed session, see `references/resume.md`: it uses
`check_review_receipt.py --require-simplify-if <base>`'s exit code as the authority for whether
this stage's evidence is still valid for the current HEAD or must be resumed from step 1.
