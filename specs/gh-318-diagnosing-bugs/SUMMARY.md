# gh-318-diagnosing-bugs — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate — the change adds skills/diagnosing-bugs/SKILL.md and edits skills/feature-intake, skills/subagent-driven-development, skills/compound and skills/README.md (workflow-as-code); the user approved the intent with its three assumed defaults.
Flags: existing behavior, public contracts, audit/security, weak proof, multi-domain
Affects: workflow-engine (skills/feature-intake bug-fix routing, skills/subagent-driven-development review gate, skills/compound input, skills/README.md bug-fix path and handoff map)
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no
<!-- Optional Codex diagnosis metadata is an all-or-nothing pair:
     Runtime-mode and Runtime-evidence-id. Add it only from codex_harness_doctor.py. -->

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<!-- The user's request VERBATIM at intake — do NOT paraphrase or summarize. Either form:
     the chat request verbatim (legacy slugs), or the line
     `Intent-source: specs/<slug>/intent.md @ <sha>` followed by the request verbatim: the
     intent's `## Original request`, else the chat request, else `none — intent.md is the request`.
     This is the oracle for intent-review (the final stage of subagent-driven-development):
     the third reviewer is blind to PLAN.md and checks the finished diff against this text
     (plus the pinned intent.md, when present). If the request came over several
     conversational turns, quote the scope-deciding sentences in chronological order.
     Capturing intent here, not in the plan, is what keeps the intent oracle independent of
     the plan oracle. -->

Intent-source: specs/gh-318-diagnosing-bugs/intent.md @ a82f1ba5b7c12130a6a3d64136901e19eb6938a9

run feature-intake for https://github.com/minhtran3124/agent-harness/issues/318

### Intake notes

<!-- Agent-written intake notes (confidence reasoning, assumed defaults, re-pin lines).
     Not part of the intent oracle. `- none` when empty. -->

- Confidence high: the user replied `approve` on 2026-10-17 to the draft with its three
  `(assumed)` defaults. (1) The skill sets `disable-model-invocation: true`, and `feature-intake`
  chains it by telling the agent to Read and follow `skills/diagnosing-bugs/SKILL.md`, not
  through the Skill tool. (2) `hitl-loop.template.sh` is written new in this repo, because
  `scripts/hitl-loop*` does not exist here and copying Pocock's text is out. (3) The task
  review of the diagnosis (Phases 1–4, `diagnosis.md`) happens before the Phase 5 fix task is
  dispatched.
- Input-type is `harness improvement`, not `bug fix`: the work adds a capability (a diagnosis
  step); no existing behavior is wrong.
- Dependencies met at intake: #308 is closed (completed); #313 step 1 merged in PR #328.
  `feature-intake` SKILL.md body is 461 words (`wc -w` on the non-frontmatter lines), so there is
  headroom under the 600-word ceiling.
- Issue #313 step 2 (routing to diagnosing-bugs) waits for this issue; check it during planning.
- Branch at intake: `sdlc`. `using-git-worktrees` cuts the implementation branch from it.

## What changed

<pending — filled after implementation>

### Rationale

<pending>

### Alternatives considered

- none

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane evidence | `python3 .claude/scripts/verify_summary.py --lane gh-318-diagnosing-bugs` | 0 | intake-time check only | |

### Not auto-verified

- The lane and flags are correct for the final diff — reached traceability; commit-gate risk corroboration re-checks the lane at commit time.

### Rollback

- `git revert <sha>` for each implementation commit; the new skill directory is additive, so reverting removes it.

### Harness-Delta

- backlog: `/feature-intake` was not registered as a slash command in this cloud session, though `.claude/skills/feature-intake/SKILL.md` was loaded and invocable through the Skill tool. The cause was not found in the repo.
