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

`skills/compound/SKILL.md` gains a `## Mistake twice` section: a learning matching an existing record at `high` overlap is a second occurrence, so `/compound` updates that record, then promotes it by updating (or adding) its `critical-patterns.md` entry with a `**Recurred:** <date>` line, never a near-duplicate. A path-scoped rule is only proposed in the report. The report line now names recurrence promotions.

### Rationale

Reuses the `high`-overlap level the related-docs pass already emits and the existing update-on-collision rule, so no script or subagent is added; the path-scoped rule stays a proposal because adding `paths:` to `rules/` changes what loads.

### Alternatives considered

- Detect recurrence from a user note or a counter: rejected, needs tooling or a manual step (out of scope in the intent).
- Write the path-scoped rule directly: rejected, a human decides what loads.

### Deviations

- none. No PLAN.md: one file, below the plan threshold (`rules/orchestration.md` artifact policy), so no `subagent-driven-development` waves; the independent reviews ran directly on the diff.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane evidence | `python3 scripts/verify_summary.py --lane compound-mistake-twice` | 0 | lane fields present | |
| full suite | `bash scripts/run-tests.sh` | 0 | 905 passed, ALL GREEN | |
| compound contract | `bash tests/scripts/compound-contract.test.sh` | 0 | 4 passed | |
| solution index | `python3 scripts/rebuild_solution_index.py --check` | 0 | INDEX.md is current | |

### Not auto-verified

- That a fresh `/compound` run follows the new section as intended — reached traceability (two independent prose reviews: intent and correctness, both pass at 7f801b5; the last wording fix 0c8d46f was not re-reviewed); no test runs the skill, and the optional `**Recurred:**` line was not checked against any entry parser (none found under `scripts/`, `hooks/`, `tests/` for "Full doc").

### Rollback

- `git revert <sha>`

### Review findings

- Correctness review 1: 1 Important (the guardrail sentence was spliced into the new section) and 2 Minor (record-update step unclear; recurrence marker unspecified) — fixed in 7f801b5. Re-review: pass; one Minor (precedence with the critical-context append) fixed in the next commit.
- Intent review: pass, one Minor drift (the report line now names recurrence promotions; follows from the request).

### Harness-Delta

- none

### Context-Propagation Audit

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `skills/compound/SKILL.md` `## Mistake twice` | the session running `/compound` | main | the Skill tool loads the whole SKILL.md body when `/compound` is invoked | the section is in the same file as the body it extends; `tests/scripts/compound-contract.test.sh` passes 4 of 4 |
| `high` overlap level | related-docs pass the skill runs itself | main (the skill's own text says the main thread runs the pass; a subagent only for a tree too large to screen) | the finder prompt already emits `overlap_level: high`; the new text reads that value | `skills/compound/subagents/related-docs-finder-prompt.md:45` |
| `**Recurred:**` line | readers of `critical-patterns.md` | every session start, via `hooks/session-knowledge.sh` | the file is loaded whole or by headings; the extra line is plain markdown | no parser of entry bodies under `scripts/`, `hooks/`, `tests/` (grep for "Full doc") |

Consumers searched: `grep -rln -e "skills/compound" -e "/compound" skills agents rules templates` returned `skills/README.md` and `skills/compound/README.md` (descriptions only; neither restates the overlap rule). No isolated child context receives this section. Result: PASS.
