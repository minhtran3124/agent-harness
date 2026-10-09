# gh-258-open-questions-register — Summary

Lane: high-risk
Confidence: medium
Reason: workflow-engine hard gate (new spec artifact consumed by skills/rules) plus a new gate in scripts/ (CI warn tier) and a new template under templates/ (CI block tier); multi-domain across artifact, skills and gate
Flags: workflow-engine, new gate, existing behavior, multi-domain
Affects: templates/ (new QUESTIONS template), scripts/ (new register check), skills/finishing-a-development-branch and skills/brainstorming (where the register is written and checked)
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Scope-deciding sentences, in chronological order:

> check issue https://github.com/minhtran3124/agent-harness/issues/258, xem thu da implement het cac item trong table rollout chua?

> start for item #3 now

Item 3 of GitHub issue #258 (https://github.com/minhtran3124/agent-harness/issues/258), Target as written in the issue:

> - An optional `specs/<slug>/QUESTIONS.md` for multi-phase specs, next to `ESCALATIONS.md`, with the fields `OQ-n`, raised-by, closes-at (phase/task), decided-by (measurement | owner), default-until-closed, and status.
> - A traceability-tier gate: a phase cannot ship while a question with `closes-at` equal to that phase is still open. Warn-first.
> - This touches `scripts/` and the gate set, so it runs as its own high-risk-lane change. It is **not** part of the first batch.

Items 5, 6 and 7 of #258 are out of scope for this spec. The branch is cut from `spec-format`; the PR targets `--base spec-format`.

Confidence is `medium`, not `high`: the target is written in #258, but two details have a
documented default rather than a single reading, to be settled in brainstorming. (a) What a
"phase" is and when it "ships": the default is that `closes-at` names a `PLAN.md` task id or a
phase label the spec defines, and "ship" is the plan's `status: shipped` transition in
`finishing-a-development-branch`. (b) Where the gate runs: the default is a `scripts/` check
called by the finishing flow and CI, warn-first, not a new `hooks/commit-gate.sh` check
(which would add the high-blast gate).

## What changed

<filled at ship time>

### Rationale

<filled at ship time>

### Alternatives considered

- none yet (brainstorming)

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| intake lane record | `python3 .claude/scripts/verify_summary.py --lane gh-258-open-questions-register` | 0 | |

### Rollback

- `git revert -m 1 <merge-sha>` of the PR into `spec-format`.

### Not auto-verified

- none yet

### Harness-Delta

- none
