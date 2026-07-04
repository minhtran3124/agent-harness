---
problem_type: failure
module: hooks/commit-workflow
tags: pretooluse-hook, git-commit, untracked-py, command-string-matching, workflow
severity: standard
applicable_when: Watch for this when issuing `git add` + `git commit` together in one Bash tool call while untracked `.py` files exist in the working tree.
affects:
  - hooks/check-untracked-py.sh
supersedes: null
confidence: high
confirmed_at: 2026-07-04
---
## Applicable When
Watch for this when issuing `git add` + `git commit` together in one Bash tool call while untracked `.py` files exist in the working tree.

## Symptom
A single Bash tool call that ran `git add <files>` and then `git commit -m ...` was DENIED outright, and staging stayed empty afterward — the `git add` never took effect even though it preceded the commit in the same command string. The deny message was `Untracked .py not staged (would break CI imports)` listing the very files the call intended to stage.

## Wrong Approach
Combining staging and committing in one Bash tool call, e.g. `git add a.py b.py && git commit -m "..."` (or the two as separate statements in one call), while untracked `.py` files existed in the repo.

## Why It Failed
PreToolUse hooks evaluate **before any part of the command runs**. `hooks/check-untracked-py.sh` matches on the tool's command STRING and inspects repo state as-of-call-start: it sees `git commit` in the string AND untracked `.py` files still on disk (the same-call `git add` has not executed yet), so it denies the entire tool call. The `git add` is never reached. This recurred twice in one session before the pattern was recognized.

## Correct Approach
Split staging and committing into **two separate Bash tool calls**: run `git add` first (the untracked `.py` files become staged/tracked), then run `git commit` in a second call so the hook re-evaluates against the now-clean untracked set.

## Guardrail
existing: `hooks/check-untracked-py.sh` (PreToolUse on Bash `git *`) — the gate that denies the combined call; the deny is correct behaviour, the friction is the combined-call workflow. `CLAUDE.md` Gotchas (2026-07-04) now states the "split into two Bash calls" rule explicitly, so every agent reading CLAUDE.md at session start sees it before hitting the friction.

Triaged 2026-07-04 (Wave 5 gate condition, `docs/harness-v03-plan-overview.md`): took the docs-only route over refining `hooks/check-untracked-py.sh`'s matching logic — a `hooks/*` change is high-blast under this repo's own manifest (full high-risk chain required), and the deny behavior itself is correct/desired; the friction is purely a workflow-ordering issue a one-line doc note fully resolves. Backlog entry closed: `docs/harness-experimental/improvement-backlog.md`.

## Related
- docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md
