---
problem_type: bug
module: hooks/risk-corroboration.sh + harness-manifest.json (gate-mode contract)
tags: [commit-time-hooks, index-vs-worktree, gate-integrity, fail-closed, policy-toctou, manifest-as-authority, external-review]
severity: critical
applicable_when: A PreToolUse commit hook reads any config/policy file that influences allow/deny — it must read the INDEX-side copy (`git show :<path>`, fail-closed on absence) so unstaged edits cannot loosen the decision for the committed tree.
affects:
  - hooks/risk-corroboration.sh
  - tests/hooks/risk-corroboration.test.sh
supersedes: null
confidence: high
confirmed_at: 2026-07-23
---
## Problem

`hooks/risk-corroboration.sh` (PreToolUse gate on `git commit`) could be loosened by an
**unstaged** edit. Trigger: worktree `harness-manifest.json` edited to `"mode": "warn"` but not
staged + a staged gated change + declared `Lane: normal` → the hook exited 0 and allowed a
commit whose committed tree still ships block-mode policy. Silent policy bypass — found by
external Codex review on PR #160 **after** the local 6-angle correctness review and independent
scorer had passed the diff.

## Root Cause

Mixed evidence sides in one corroboration. Every other input is INDEX-side (staged paths via
`git diff --cached`, staged diff content, Lane via `git show :$f`), but the block-vs-warn policy
was read from the WORKTREE file (`jq ... "$REPO_DIR/harness-manifest.json"`). Policy TOCTOU: the
artifact being committed and the policy judging it came from two different trees.

The contract tests shared the blind spot: fixtures wrote the manifest to the worktree without
staging it, so the suite exercised — and locked in — the vulnerable read path. Staged-vs-unstaged
was not a dimension in any test case; only an external reviewer with a different frame flagged it.

## Fix

Commit `880eb15` — resolve `GATE_MODES` from the index, fail-closed (absent/unreadable/invalid ⇒
empty ⇒ `block`). All manifest-mode fixtures now staged.

## Regression Test

`tests/hooks/risk-corroboration.test.sh` :: "UNSTAGED worktree mode=warn does NOT loosen — index
rules (exit 2, Codex PR#160)" — commits a block-mode manifest, flips the worktree copy to warn
without staging, stages a gated change + `Lane: normal`, asserts exit 2 BLOCKED.

## Code Example

```bash
# WRONG — policy from worktree, everything else from index (TOCTOU):
GATE_MODES=$(jq -r '...' "$REPO_DIR/harness-manifest.json")
# RIGHT — same tree as the evidence being judged; fail-closed on absence:
GATE_MODES=$(git show :harness-manifest.json 2>/dev/null | jq -r \
  '.hard_gates.detectable[]? | "\(.slug)=\(.mode // "block")"' 2>/dev/null || true)
```

## Prevention

A commit-gating hook that corroborates the INDEX must read **every** input from the index — one
worktree-side read of a policy file is a bypass, because unstaged edits are agent-controllable at
commit time and never enter the commit. When reviewing any PreToolUse commit hook, audit which
tree each `[ -f ]` / `cat` / `jq <file>` reads from. Known remaining instance (backlogged in
`specs/simplify-gate-surface/SUMMARY.md` advisories): `commit-quality-gate.sh` Check 1.6 falls
back to the worktree SUMMARY/PLAN when `git show :$path` fails, including on staged deletion.

## Related

- docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md — adjacent hook-sees-wrong-state pattern, different mechanism
- docs/solutions/harness/risk-corroboration-scans-test-comments-for-auth-words.md — same hook family
