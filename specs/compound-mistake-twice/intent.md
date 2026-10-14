# Intent: Promote a learning to critical-patterns when it recurs

Author: Minh Tran
Status: approved

## Problem

`/compound` writes each learning once, into `docs/solutions/`. It has no rule for a learning that comes back: the same mistake can be recorded twice as two separate solution records, and neither is promoted to the always-read `critical-patterns.md` or to a path-scoped rule. A mistake the team already wrote down keeps happening because the second record sits in the index next to the first. (assumed)

## Proposed outcome

`skills/compound/SKILL.md` gains a "mistake twice" rule. When the session's learning matches an existing `docs/solutions/` record (the related-docs pass already finds candidates), `/compound` treats it as a second occurrence and promotes it: it appends or updates an entry in `docs/solutions/critical-patterns.md`, or, when the learning applies to one set of paths, proposes a path-scoped rule. The promotion is the compound output for that run, reported alongside tracks emitted. (assumed)

## Affected users and systems

Anyone running `/compound`, and every later session that reads `critical-patterns.md` at planning time. Touches `skills/compound/SKILL.md` only; the templates and `scripts/rebuild_solution_index.py` are not expected to change. (assumed)

## Constraints

- Wording only in the skill, in the same lean style as the rest of it; no new script and no new subagent. (assumed)
- A path-scoped rule is proposed, not written: adding `paths:` to `rules/` changes what loads (see CLAUDE.md), so a human decides. (assumed)
- `critical-patterns.md` stays short, as its own header requires; a promotion replaces or merges into an existing entry rather than adding a near-duplicate. (assumed)

## Out of scope

Automatic detection by tooling, counting recurrences across sessions, changing the record templates, and the other playbook items (E1, E2, E5).

## Open questions

- Q1. What counts as "the same learning": the related-docs pass finding a high-overlap record (the rule `compound` already uses for collisions), or an explicit recurrence note from the user? Default: high-overlap record, as the collision rule does. (assumed)
- Q2. Which promotion target wins when both fit: `critical-patterns.md` or a path-scoped rule? Default: `critical-patterns.md`, and mention the path-scoped rule as a proposal only. (assumed)

## What success looks like

A reader of `skills/compound/SKILL.md` can tell, for a learning that matches an existing record, that the run must promote it and what the promotion is; the run report names the promotion. (assumed)

## Original request

/feature-intake for E3 — from `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md` §6: "Add the 'mistake twice' rule to `/compound`: a learning that recurs a second time is promoted to `critical-patterns.md` (or a path-scoped rule), and the promotion is the compound output" (Play 4, Play 9 step 4; where: `skills/compound/SKILL.md`; expected lane: normal).
