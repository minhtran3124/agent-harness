# compound-mistake-twice — Summary

Lane: normal
Confidence: high
Reason: one skill's prose changes (`skills/compound/SKILL.md`); flags existing behavior and weak proof (prose has no runtime test); no block-mode hard gate fires, the warn-mode `workflow-engine` signal does.
Flags: existing behavior, weak proof
Affects: skills/compound
Input-type: harness improvement

### Intent

Intent-source: specs/compound-mistake-twice/intent.md @ de1f80611167ee8f1bb9b421cddfb712e407c11c

/feature-intake for E3 — from `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md` §6: "Add the 'mistake twice' rule to `/compound`: a learning that recurs a second time is promoted to `critical-patterns.md` (or a path-scoped rule), and the promotion is the compound output" (Play 4, Play 9 step 4; where: `skills/compound/SKILL.md`; expected lane: normal).

### Intake notes

- Intent approved by the user in chat ("approve") with the draft's defaults: Q1 same learning = a high-overlap record from the related-docs pass; Q2 `critical-patterns.md` wins and a path-scoped rule is only proposed.
- Route: normal, so `using-git-worktrees` then `subagent-driven-development`. A context-propagation audit is expected (workflow-engine path changed) when compared with `main`; against `sdlc` none is required.

## What changed

Pending.

### Rationale

Pending.

### Alternatives considered

- none

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane evidence | `python3 scripts/verify_summary.py --lane compound-mistake-twice` | 0 | lane fields present | |

### Not auto-verified

- none

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
