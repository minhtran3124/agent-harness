# gh-318-diagnosing-bugs — Design

Written 2026-10-17. Pins: repo 07fb42e

## Goal

Add an in-repo `diagnosing-bugs` skill. It makes every `Input-type: bug fix` find and prove its
root cause in six gated phases before any fix, in every lane. Wire it into `feature-intake`, the
bug-fix lane, `subagent-driven-development`, `compound`, and `skills/README.md`.

## Current state

- `skills/feature-intake/SKILL.md` classifies `Input-type: bug fix` (Step 2) but its `## Routes`
  send a bug fix to no diagnosis step.
- `skills/README.md` "Bug Fix Path" and the handoff map name `systematic-debugging`, an external
  skill that the README's "External Skills" table calls optional.
- `skills/subagent-driven-development/implementer-prompt.md:57-68` already writes the red test at a
  declared seam, records the `red` row as `python3 scripts/run_at_commit.py <red sha> -- <test
  command>`, and allows `Red test exempt: <reason>`. `rules/auto-correct-scope.md` "Lane-aware
  autonomy" holds the matching `verify_summary.py --lane` bug-fix evidence rule.
- `specs/gh-313-prove-the-red/intent.md:53` defers #313 step 2 ("route `Input-type: bug fix` to
  `diagnosing-bugs`") to this issue.
- `scripts/audit_skill_prompts.py:22` sets `SKILL_WORD_CEILING = 600`. The `feature-intake`
  SKILL.md body is 461 words (measured 2026-10-17 `wc -w` on the non-frontmatter lines), against the 600-word ceiling (budget).
- `skills/session-retro/SKILL.md` is the one existing skill with `disable-model-invocation: true`.
- `agents/task-reviewer.md` is the reviewer that `subagent-driven-development` dispatches per
  task. Its read-only tool set (Glob, Grep, Read) comes from deployment: it is in
  `.claude/agents/task-reviewer.md:4`, not in the source frontmatter.
- `hooks/branch-isolation-guard.sh` denies implementation edits on a shared branch; only
  `specs/*` is exempt. `using-git-worktrees` detects existing isolation before it creates any.
- `scripts/hitl-loop*` does not exist (`ls scripts/hitl-loop*`, 2026-10-17). The issue's file is
  Pocock's, at commit `49dd158`.

## Approaches considered

- **A. One skill with its references, template, and reviewer brief inside it (chosen).** The
  SKILL.md stays under the ceiling, and the long lists move to `references/`. The `diagnosis.md`
  template lives in the skill, not in `templates/`. A diff that touches `templates/` enters the
  block tier of `scripts/ci-strict-gate.sh`, and this change needs no shared template.
- **B. A plus `scripts/check_diagnosis.py`.** It checks section order only (traceability). The task
  reviewer already checks that, and it adds a `scripts/` surface (warn tier). Rejected as YAGNI.
- **C. A diagnosis mode inside `feature-intake`.** It breaks the 600-word ceiling and mixes
  classification with investigation. Rejected.

## Architecture

New files under `skills/diagnosing-bugs/`:

| Path | Purpose |
|---|---|
| `SKILL.md` | Frontmatter with `disable-model-invocation: true`. Redaction rule first. Six phases, each with one completion criterion. Under 600 words (budget). |
| `references/phases.md` | Long lists: loop-building techniques, minimisation tactics, hypothesis and probe patterns. |
| `references/diagnosis-template.md` | Shape of `specs/<slug>/diagnosis.md`. |
| `references/diagnosis-review-prompt.md` | Brief for the `task-reviewer` dispatch on `diagnosis.md`. |
| `scripts/hitl-loop.template.sh` | Original script for a loop in which a human must act. Not copied from Pocock. |
| `tests/*.md` | Case files in the style of `skills/feature-intake/tests/`. |

Edited files:

- `skills/feature-intake/SKILL.md` — one routing line: for `Input-type: bug fix`, Read and follow
  `skills/diagnosing-bugs/SKILL.md` before the lane route. This closes #313 step 2.
- `skills/subagent-driven-development/SKILL.md` and `implementer-prompt.md` — the controller
  passes the `diagnosis.md` path in the task Context; the red test targets the confirmed
  hypothesis; the controller runs Phase 6 after the last wave and before the final reviews.
- `skills/compound/SKILL.md` — the bug track takes its root cause from `diagnosis.md` when it
  exists.
- `skills/README.md` — Bug Fix Path, a Skills Reference row, the handoff map; remove the
  `systematic-debugging` row from "External Skills".
- The deployed `.claude/` copies, through the repo's deploy script (see A3).

Isolation comes first. Before Phase 1, the skill cuts the lane's isolation: tiny runs
`git checkout -b fix/<slug>`; normal and high-risk run `using-git-worktrees`, which the later
route step then detects and reuses. Every probe, throwaway harness, and fix edit happens there,
never on a shared branch.

The six phases, each ending in one completion criterion:

1. **Feedback loop.** One command goes red on this bug; it is run at least once (budget: 1 run); the command and
   its redacted output are in `diagnosis.md`. The loop is fast, deterministic, and agent-runnable.
2. **Reproduce and minimise.** The loop shows the symptom the user described. Each remaining input
   element is necessary (delete one at a time).
3. **Hypothesise.** Three to five (budget) ranked hypotheses, each with a prediction, are posted to the user.
   The skill continues on its own ranking without waiting.
4. **Instrument.** Each probe maps to one prediction and changes one variable. Each debug log carries
   a unique tag such as `[DEBUG-a4f2]`. Probes stay uncommitted. One hypothesis is confirmed by
   probe evidence and recorded. Then the skill deletes every tagged probe and throwaway harness,
   so no probe stays in the working tree during planning or implementation. `diagnosis.md` is
   committed under `specs/<slug>/` with the rest of the spec.
5. **Fix.** After the diagnosis review passes, hand off to the lane: tiny writes the red test at the seam that `diagnosis.md` names in its `Seam:` line, commits
   it, then commits the fix, inside the skill; normal and high-risk follow their route with `diagnosis.md` as an
   input. No valid seam: a finding in `SUMMARY.md` plus `Red test exempt: <reason>`.
6. **Cleanup.** The session that completed the fix re-runs the Phase 1 loop (now green), greps the
   tag in the fix diff and in the working tree, deletes any tagged log or throwaway harness that
   is left, and names the confirmed hypothesis in the commit message and in SUMMARY
   `Rationale`.

## Worked trace

1. The user reports a wrong exit code from a script. Intake writes `Input-type: bug fix`, lane
   `normal`, and reads `skills/diagnosing-bugs/SKILL.md`. The skill runs `using-git-worktrees`
   first, so the work happens in a worktree on `fix/<slug>`.
2. Phase 1 runs `bash scripts/x.sh; echo $?` and gets `0` where `1` is expected (red). Phases 2–4
   write `diagnosis.md`: the minimised call, H1–H4 with predictions, probes tagged `[DEBUG-7c1e]`,
   and H2 confirmed. The skill deletes the tagged probes and commits `diagnosis.md`.
3. `task-reviewer` gets `references/diagnosis-review-prompt.md` and `diagnosis.md`. It passes.
4. Phase 5: the route continues; `using-git-worktrees` detects the existing worktree, then
   `subagent-driven-development` runs. The
   implementer's Context names `diagnosis.md`; it commits the red test for H2, then the fix.
5. Phase 6: the controller re-runs the loop (exit `1`), finds no `[DEBUG-7c1e]` in the diff or
   the working tree, and writes "H2 confirmed" into the commit message
   and `Rationale`. `compound` reads the root cause from `diagnosis.md`.

## Error behavior

| Failure | Response |
|---|---|
| No loop can be built | Write an `ESCALATIONS.md` block with `decision: pending`, listing what was tried and what is needed (environment, captured artifact, or permission to instrument). Stop. |
| Diagnosis review fails | Revise `diagnosis.md` and review again. A second failure (budget: 2 reviews) writes an `ESCALATIONS.md` block with `decision: pending` and stops. |
| Probes refute every hypothesis | Return to Phase 3 with a new list. A second full refutation (budget: 2 rounds) writes an `ESCALATIONS.md` block with `decision: pending` and stops. |
| No valid seam for the red test (any lane, tiny included) | Record the finding in `SUMMARY.md` and write `Red test exempt: <reason>`. |
| A secret appears in a command or output | Replace it with `<REDACTED>` before it is shown or written. |

## Tests

- `bash scripts/run-tests.sh`, which includes the skill-prompt word-ceiling audit — truth tier.
- Case files: a quick question through intake does not fire the skill; a bug-fix input routes to it.
  The case files are run by hand (`skills/feature-intake/tests/README.md`), so the quick-question
  case is also run once as a recorded proof: a fresh subagent gets the quick question and the
  deployed `.claude/` harness, and its transcript goes to
  `specs/gh-318-diagnosing-bugs/proof/quick-question.md`. A `### Verify` row greps that file for
  `diagnosing-bugs/SKILL.md`. This is traceability tier for one run on one runtime.
- Replay proof: one bug from `docs/solutions/` with a known cause, run in a throwaway worktree at
  its pre-fix commit. The transcript goes to `specs/gh-318-diagnosing-bugs/proof/`. Rows in
  `### Verify` record the red loop before the hypotheses, the ranked list before the probes, and
  zero `[DEBUG-` tags in the diff. Transcript-order claims are traceability tier and are also
  listed under `### Not auto-verified`.

## Success criteria

- `skills/diagnosing-bugs/SKILL.md` exists with `disable-model-invocation: true`, and
  `python3 scripts/audit_skill_prompts.py` reports no ceiling failure for it or for
  `feature-intake`.
- `skills/feature-intake/SKILL.md` contains the bug-fix routing line naming
  `skills/diagnosing-bugs/SKILL.md`.
- `grep -n systematic-debugging skills/README.md` prints nothing.
- In the replay transcript, the first red loop output appears before the first hypothesis, the
  ranked list appears before the first probe, and `git diff <base>..HEAD | grep -c '\[DEBUG-'`
  prints `0` (budget: 0 tags).
- `grep -c 'diagnosing-bugs/SKILL.md' specs/gh-318-diagnosing-bugs/proof/quick-question.md`
  prints `0` (budget: 0 matches).
- `bash scripts/run-tests.sh` exits 0.

## Non-goals

- No change to `scripts/verify_summary.py`, `hooks/commit-gate.sh`, `settings.json`, or any hook.
- `REQUIRE_RED_TEST=1` stays opt-in.
- No file under `templates/`.
- No copy of Pocock's text.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | `disable-model-invocation: true` stops the model from choosing the skill on its own, and still allows `/diagnosing-bugs` and a Read-and-follow instruction from `feature-intake`. | none yet — Inference: `skills/session-retro/SKILL.md` uses the flag as user-invoked | xia2 version-matched Docs check; SC `proof/quick-question.md` grep | The skill fires on quick questions or cannot chain. Fallback: leave it model-invocable with a narrow description. |
| A2 | `agents/task-reviewer.md` can review a non-PLAN artifact when given a brief and paths. | none yet — Inference: its deployed tools are Glob, Grep, Read only (`.claude/agents/task-reviewer.md:4`) | xia2 read of `agents/task-reviewer.md` and its dispatch prompt | The diagnosis gate has no reviewer. Fallback: dispatch `agents/reviewer.md` with the same brief. |
| A3 | The deploy script copies a new skill directory into `.claude/skills/` with no per-skill registration. | none yet | xia2 read of `scripts/deploy-harness.sh`; plan task | The deployed copy is missing. Fallback: add the registration the script needs. |
| A4 | `docs/solutions/` holds a bug with a known cause, a findable pre-fix commit, and a deterministic repro. | none yet | xia2 selection; replay task | No replay proof. Fallback: escalate for the user to pick another proof bug. |
| A5 | The `feature-intake` routing line keeps the body under the 600-word budget. | provenance: Local, 2026-10-17, `skills/feature-intake/SKILL.md` (body 461 words, measured 2026-10-17 wc -w) | SC audit row | The audit fails. Fallback: the #308 deletion test on `feature-intake`. |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| The confirmed hypothesis is the true cause. | The reviewer checks that the probe evidence supports it; that is provenance at best. The red/green pair shows the fix changes the symptom, not that the stated cause is the cause. |
| A gate enforces phase order. | No hook or script checks `diagnosis.md`; order is checked by the task reviewer only. |
| Secrets never leak. | Redaction is an instruction. The commit-time secrets scan in `hooks/commit-gate.sh` still runs, but nothing scans chat output. |
| An agent outside intake diagnoses on its own. | The skill is not model-invoked by design (D1). |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | Set `disable-model-invocation: true`; `feature-intake` chains by Read-and-follow. | The skill runs only from intake or `/diagnosing-bugs`. | settled |
| D2 | Write `hitl-loop.template.sh` new in this repo. | No third-party text to license. | settled |
| D3 | Diagnosis runs right after intake and before the rest of the lane route; the lane's branch or worktree is cut before Phase 1. | Planning starts from a confirmed cause; no probe touches a shared branch. | settled |
| D4 | Every lane with `Input-type: bug fix` runs all six phases; three to five hypotheses; no "cause known" shortcut. | Tiny bug fixes carry the diagnosis cost. | settled |
| D5 | A standalone `task-reviewer` dispatch on `diagnosis.md` gates Phase 5 in every lane. | The gate exists without a `PLAN.md`. | settled |
| D6 | Phase 3 posts the list and continues without waiting. | The user may interrupt; no wait state. | settled |
| D7 | No loop possible → `ESCALATIONS.md` block with `decision: pending`. | Commits to the slug are blocked until a decision. | settled |
| D8 | The `feature-intake` routing edit closes #313 step 2. | The PR names #313 step 2. | settled |
| D9 | Proof is a replay of one `docs/solutions/` bug at its pre-fix commit, transcript under `proof/`. | Transcript claims are listed in `### Not auto-verified`. | settled |
| D10 | Approach A: template and reviewer brief live in the skill, not in `templates/`. | The diff avoids the `ci-strict-gate.sh` block tier for `templates/`. | settled |
| D11 | Phase 4 deletes its probes before handoff; Phase 6 re-checks and deletes any left. | No probe stays in the tree during planning or implementation. | settled |
