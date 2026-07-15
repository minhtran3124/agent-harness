---
problem_type: failure
module: harness
tags: not-observed-not-absent, false-premise, plan-blind-review, correctness-review, ground-truth, review-oracle, resync-conflict
severity: critical
applicable_when: Watch for this when a spec, design, or plan asserts that something "is never shipped" / "does not exist" / "can never conflict", and downstream code, tests, and reviews all treat that absence claim as true without one independent `ls` or `git ls-files` against ground truth.
affects:
  - scripts/deploy-harness.sh
  - tests/scripts/resync-conflict.test.sh
  - .gitignore
supersedes: null
confidence: high
confirmed_at: 2026-07-10
---
## Applicable When

A design doc makes a factual claim about **what the repository currently contains**, and every review gate downstream is anchored to that doc.

## Symptom

`sync_protected_dir` restored a consumer's `skills/xia2/PROJECT.md.proposed` unconditionally. The result: a consumer's copy was frozen forever, and source updates were silently discarded — **even under `--overwrite-conflicts`**. Reproduced: seed a stale `.proposed`, run `deploy --overwrite-conflicts`, observe the stale copy survive.

## Wrong Approach

`specs/resync-protected-files/design.md` §4.2 asserted:

> "The harness source does not ship it, so there is never a conflict: snapshot before the dir copy, restore after, always."

The premise was false. `skills/xia2/PROJECT.md.proposed` (7140 bytes) and `agents/PROJECT.md.proposed` were both tracked in git, committed in `f7d2d58` as artifacts of a `bootstrap-xia2` run against this repo itself.

Nobody ran `ls skills/xia2/`. The claim was inferred from having seen `agents/PROJECT.md.proposed` and *not having looked* at the sibling directory.

## Why It Failed

A false "what exists" premise defeats **every plan-anchored gate at once**, because they all inherit the same unverified assumption instead of checking runtime reality:

| Gate | Oracle | Result |
|---|---|---|
| per-task spec review | `PLAN.md` | ✅ passed — the code matched the plan |
| per-task code-quality review | clean code | ✅ passed — the code was clean |
| the test author | `design.md` | ✅ passed — and *enshrined* the premise in a comment: "`.proposed`, never shipped by the harness" |
| `/correctness-review` | **runtime, blind to the plan** | ❌ caught it |

The consistency is the trap. Three independent reviewers agreeing means nothing when all three read the same wrong sentence. A reviewer that can see the plan anchors on it and re-confirms its misreading — which is precisely why `/correctness-review` and `/intent-review` are dispatched blind to `PLAN.md`.

Note the test suite made it *worse*: it encoded the false premise as a comment, converting an unverified assumption into apparent documentation.

## Correct Approach

Verify "what the repo currently ships" against the filesystem and git, never against the design doc. One command would have caught this:

```bash
git ls-files skills/xia2/ | grep proposed
```

This is a direct instance of `rules/behavior.md` §1 — **`not_observed != absent`**. A missing search result, an unread file, or an unrun `ls` means *unknown*, not *absent*. Before writing "X does not exist" into a design, state where you looked; if you did not look, do not write it.

Fixed at `cfff07c`: delete both `.proposed` files, gitignore `*.proposed`, and add a repo-wide load-bearing assertion so the premise is enforced rather than assumed.

## Guardrail

`existing:` `tests/scripts/resync-conflict.test.sh` case 1 asserts `find "$T1/.claude" -name '*.proposed'` returns zero — repo-wide, not scoped to `xia2/`, so a `.proposed` added under any future protected dir fails CI. Verified non-vacuous by re-adding the file from `f7d2d58` and watching exactly that assertion turn red.

`existing:` `.gitignore` → `*.proposed`.

Together these convert the design's assumption into an invariant. Note it remains an *invariant* enforced by CI, not a runtime guard — `git add -f` bypasses the ignore, but case 1 still catches it.

## Related

- `docs/solutions/harness/gap-closure-decisions.md` — the decision-level counterpart: ground-truth on disk before acting on a doc that asserts absence.
- `docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md` — how the replacement assertion was proven to actually guard.
- `docs/solutions/harness/resync-protected-files-decisions.md` — the Rule-4 decision taken once the premise was found false.
