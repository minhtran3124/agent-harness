---
problem_type: decision
module: skills/asd-ste100/, scripts/check_ste_baseline.py, skills/subagent-driven-development/scripts/review_package.py, scripts/audit_skill_prompts.py
tags: [ste100, controlled-language, vendored-skill, warn-only-ratchet, measured-null, pilot-gate, word-ceiling, review-gate]
severity: standard
applicable_when: You add, change or extend STE (ASD-STE100) checks or rewrites in the harness, vendor a third-party skill, or change which lint rules a review step counts.
affects:
  - skills/asd-ste100/UPSTREAM.md
  - scripts/check_ste_baseline.py
  - scripts/ste-baseline.json
  - skills/subagent-driven-development/scripts/review_package.py
  - scripts/audit_skill_prompts.py
supersedes: null
confidence: high
confirmed_at: 2026-10-15
---

## Applicable When

You add, change or extend STE checks or rewrites in the harness, vendor a third-party skill, or
change which lint rules a review step counts.

## Decision 1
### Context
The user asked to apply the asd-ste100 skill to the whole harness: rewrite existing prose (A),
use the skill for new prose (B), and add the linter (C). An earlier record,
`specs/ste-terminology-evidence/DECISION.md`, measured three STE ideas. Only machine-decidable
acceptance criteria had an effect.
### Options Considered
- Rewrite all prose with no trial.
- Run a full A/B before any rewrite.
- Pilot three files, then gate the rollout on the result.
### Decision & Rationale
Pilot then gate. Three high-traffic files were rewritten and measured with comprehension probes
and real `feature-intake` runs (80 trials, $2.91). All three passed. Each method passes at
original − 2 correct answers, with no probe drop from 10/10 to 7/10 or fewer.
### Applicable When
You plan a bulk rewrite of agent-executed prose.
### Consequences
The rollout of the other files (Phase 3) is a separate plan. Its task briefs must ask the task
reviewer for a per-file meaning-equivalence review, because the task-reviewer prompt does not run
one on its own. The pilot review ran only because the Task 2.2 brief asked for it, and it caught
two dropped conditions that the tests missed
(`docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`).

## Decision 2
### Context
`npx skills add` installed the skill into `.agents/skills/` with a lock file and a symlink in
`.claude/skills/`. `deploy-harness.sh` syncs only root `skills/`, so consumers did not get it.
`.agents/skills/` is also the Codex adapter's output location.
### Options Considered
- Commit the `npx skills` install.
- Vendor into `skills/asd-ste100/`.
- Vendor only the linter under `scripts/`.
### Decision & Rationale
Vendor into `skills/asd-ste100/` from upstream `3944283c18`, with three recorded deltas in
`UPSTREAM.md`: an `allowed-tools` line, no upstream `README.md` or invalid-example fixture, and a
linter path form that the doc-truth lint accepts.
### Applicable When
You add a third-party skill to the harness.
### Consequences
Updates are a manual re-vendor. The skill is 2,659 words, over the 600-word ceiling, so
`audit_skill_prompts.py` exempts a skill directory that has `UPSTREAM.md`. The user chose this
over splitting the vendored file, which would make each re-vendor a manual merge. The exemption is
self-declared: any skill can add the marker (correctness review scored this 50, advisory).

## Decision 3
### Context
The linter runs as a per-file ratchet, and the task reviewer reads per-file BASE and HEAD hard
counts in the review package. The hard count includes `synonym-rotation`, the
one-concept-one-word rule. The earlier record measured that rule with no effect (H3).
### Options Considered
- Keep the blocking review check with every hard rule.
- Make the review check advisory.
- Keep the blocking check, but exclude `synonym-rotation`.
### Decision & Rationale
Exclude `synonym-rotation` from both the review-package count and the baseline. The approved
intent says not to turn an unmeasured rule into a blocking gate. Intent review caught the conflict
after correctness review passed. The structural rules (semicolon, long sentence, phrasal verb,
nominalization, marketing adjective) still count.
### Applicable When
You change `DISABLED_RULES` in `scripts/check_ste_baseline.py` or in
`skills/subagent-driven-development/scripts/review_package.py`, or you add a lint rule to a check
that can block.
### Consequences
A manual `ste-lint.py` run (as the vendored `SKILL.md` documents it) still counts
`synonym-rotation`, so an agent that self-checks by hand sees higher counts than the gates do.
Keep the two `DISABLED_RULES` constants equal.

## Decision 4
### Context
The linter is a style tool. A blocking CI or commit gate on it would block builds on wording.
### Options Considered
- A blocking lint in CI or in a hook.
- A warn-only per-file baseline ratchet in `run-tests.sh`.
- A manual command only.
### Decision & Rationale
A warn-only ratchet. The default `check_ste_baseline.py` run always exits 0. `--strict` exits 1
on a WARN, and only plan checks use it. The earlier record forbids a blocking gate built on a rule
with no measured effect.
### Applicable When
You change how `run-tests.sh` or CI uses the STE linter.
### Consequences
`--strict` exits 0 when the run is skipped (the linter or baseline is unusable). The plan required
this, and correctness review recorded it as advisory (score 50).

Update 2026-10-15 (`specs/ste100-prose-rollout/` design D7): `--strict` now exits 1 on a skipped
run, so a skip is never read as a pass. The default run still exits 0. `--against <git-ref>`
compares each file with its baseline entry at that ref.

## Related

- docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md
- specs/ste-terminology-evidence/DECISION.md
- specs/ste100-harness-prose/DECISION.md
- specs/ste100-harness-prose/design.md
