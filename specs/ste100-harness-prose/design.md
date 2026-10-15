# ste100-harness-prose — Design

Written 2026-10-14. Pins: repo a5d4292; asd-ste100 0.4.0 (skills-lock hash 911447778fee); Claude Code 2.1.299

## Goal

Make the harness prose that agents execute easier for an agent to read without misreading. Adopt
the `asd-ste100` skill for new prose (B), add a warn-only linter ratchet (C), and rewrite the
existing prose (A) only after a pilot shows the rewrite is no worse than the original.

## Current state

- `asd-ste100` was installed by `npx skills add` into `.agents/skills/asd-ste100/` (untracked),
  with `skills-lock.json` (untracked) and a symlink `.claude/skills/asd-ste100`. The symlink lives
  only in this checkout. `scripts/deploy-harness.sh` syncs only root `skills/`, so consumers do not
  receive it. `.agents/skills/` is also the Codex adapter's skill location
  (`scripts/probe_codex_packaging.sh`, `scripts/deploy-codex-adapter.sh`). License: MIT.
- `specs/ste-terminology-evidence/DECISION.md` (2026-08-13) measured three STE ideas. Only
  machine-decidable acceptance criteria (§3) had an effect. One-concept-one-word (§1) had none.
  A blocking STE lint hook was rejected. `paths:` rules do not load on write, so delivery to a
  write-flow needs an explicit instruction in the consuming skill.
- `ste-lint.py` over `skills/*/*.md`, `rules/*.md`, `agents/*.md` reports 415 findings in 16,501
  words. 329 of them are hard findings (measured 2026-10-14 ste-lint 0.4.0). By rule: semicolon
  200, long-sentence 105, synonym-rotation 24 (hard), passive-voice 80 and present-perfect 6
  (advisory).
- 32 of 47 shell tests in `tests/scripts/` reference skill, rule, or agent paths (measured
  2026-10-14 `grep -lE "skills/|rules/|agents/" tests/scripts/*.sh`). Some grep exact phrases
  (for example `tests/scripts/writing-plans-contract.test.sh`).

## Approaches considered

Pilot gate method (the remaining fork after the scope answers A + B + C):

1. Comprehension probes — exact-match questions on original vs rewritten files. Cheap, easy to
   score, but measures reading, not acting.
2. Workflow-in-the-loop — run a real skill headless with old vs new prose and score its output
   against gold labels. Closer to real use, but higher cost.
3. Equivalence review only — no behavioral measurement.

Chosen: **1 + 2 together**. Probes cover all three pilot files. The workflow arm covers
`feature-intake`, which must pass both. The rollout needs every pilot file to pass. Option 3 alone does not satisfy
the user's "pilot then gate" choice. It stays as the per-file check in the rollout.

## Architecture

### Phase 1 — adopt the skill and the linter (B + C)

- **Vendor.** Copy `.agents/skills/asd-ste100/` to `skills/asd-ste100/` unchanged, keep `LICENSE`,
  and add `skills/asd-ste100/UPSTREAM.md` (source `danyuchn/asd-ste100-skill`, version, hash,
  re-vendor steps). Delete `.agents/` and `skills-lock.json`. Remove the local symlink
  `.claude/skills/asd-ste100` (it would dangle) and re-run `scripts/deploy-harness.sh` on this
  checkout so `.claude/skills/` holds the vendored copy. That re-sync rebuilds all of the
  gitignored `.claude/` tree from the sources. It is expected and changes no tracked
  `settings.json` or `hooks/` file. Add the skill to `skills/README.md`.
- **Wiring (explicit instructions, because `paths:` does not load on write):**
  - `subagent-driven-development` implementer prompt: when a task edits prose under `skills/`,
    `rules/`, `agents/`, or a dispatch prompt, apply asd-ste100 to the changed prose.
    STE-flavored mode for skills, rules, and agents. Strict mode for dispatch prompts.
  - Controller + task reviewer: the task reviewer is read-only and cannot run Bash
    (`agents/task-reviewer.md`). So the SDD controller runs `ste-lint.py --json` on each touched
    prose file at the task base and at the task head, and puts both counts in the review packet.
    The reviewer's quality verdict rejects a file whose hard count went up. A file the task
    creates has no base count. It is judged against the baseline ratchet instead (baseline 0, a
    warning, not a rejection).
  - `compound`: apply STE-flavored mode to each new `docs/solutions/` entry.
  - The implementer, the task reviewer, and `compound` exclude: fenced code, `### Intent`, `intent.md`, and literal strings that a test or
    hook matches. To find those strings before a rewrite, grep `tests/scripts/` and `hooks/` for
    the file's path and for each backticked phrase in the file.
- **Linter ratchet.** New `scripts/check_ste_baseline.py` reads `scripts/ste-baseline.json` (hard
  finding count per file under `skills/`, `rules/`, `agents/`), runs `ste-lint.py --json` on each
  file, and prints `WARN` above baseline and `NOTE` below baseline. It always exits 0. The
  baseline is generated and checked with the same `--disable` flags, which the script holds in
  one constant.
  `scripts/run-tests.sh` calls it and the `ste-lint.py --selftest`.

### Phase 2 — pilot (A)

- Pilot files: `rules/orchestration.md`, `skills/feature-intake/SKILL.md`,
  `skills/subagent-driven-development/SKILL.md`.
- Runner in `specs/ste100-harness-prose/experiment/`, modelled on
  `specs/ste-terminology-evidence/experiment/rerun.py`: a fresh temp directory per trial, headless
  Claude Code, scoring from files on disk only, `--score-only` to re-derive metrics from stored raw
  output.
  - **Probes:** 8 questions per file (budget), at least half hard (exceptions, conditions,
    break-glass paths), 10 trials per arm per file (budget).
  - **Workflow:** headless `feature-intake` classification on 8 fixture requests (budget) with
    gold `Lane` / `Confidence` / `Escalate` labels, original vs rewritten skill prose, 10 trials per
    arm (budget).
- Pass rule, per file:
  - `skills/feature-intake/SKILL.md` must pass both methods.
  - `rules/orchestration.md` and `skills/subagent-driven-development/SKILL.md` pass on probes
    alone. The workflow arm does not exercise them.
  - Unit: one scored answer. A probe arm is 8 questions × 10 trials = 80 answers per file. A
    workflow arm is 8 fixtures × 10 trials = 80 answers, where an answer is correct only when
    `Lane`, `Confidence`, and `Escalate` all match gold.
  - Aggregate rule: a method passes when the rewritten arm's correct answers are at least the
    original arm's correct answers minus 2 (budget).
  - Meaning-change rule (probes only, judged by the scorer, not a person): each probe has one
    gold answer taken from the original file. A probe that the original arm answers correctly in
    10 of 10 trials and the rewritten arm in 7 or fewer of 10 (budget) is a meaning change.
  - Both rules apply. A file fails if either fails. A single miss at ceiling fails neither rule.
- The rollout (Phase 3) needs all three pilot files to pass. Result recorded in
  `specs/ste100-harness-prose/DECISION.md`.

### Phase 3 — rollout (A), only on a pilot pass

- Phase 3 gets its own `PLAN.md` revision after `DECISION.md` exists. The first plan covers
  Phases 1–2 only, because Phase 3's task list depends on the pilot result.
- Rewrite the remaining skills, dispatch prompts, rules, and agents in waves of 4–6 files
  (budget).
- Each wave lowers the touched files' baseline entries, gets a reviewer equivalence verdict per
  file, and passes `bash scripts/run-tests.sh`.
- On a pilot fail: revert the pilot rewrites, keep Phase 1, record the reason in `DECISION.md`,
  and end A there.

## Error behavior

- `ste-lint.py` crashes or prints invalid JSON → `check_ste_baseline.py` prints
  `ste-baseline: skipped (<reason>)` and exits 0.
- A file is missing from the baseline → treated as baseline 0, plus a warning. A baseline entry
  for a deleted file → warning.
- A rewrite loses meaning → the reviewer's equivalence check rejects it. One fix round. A second
  fail leaves the file unchanged and logs it under `### Deviations`.
- A rewrite breaks a literal-grep test → fix the prose. Never loosen the test (that is the
  `weakening-validation` signal).
- Mixed result on `feature-intake` (one method passes, one fails) → that file fails. Any pilot
  file failing stops the rollout. Stop and report to the user.
- Lint counts missing from the review packet, or `ste-lint` failing at base or head → the
  reviewer's quality verdict is not a pass for that file. The controller re-runs the linter once,
  then reports the task as blocked (`docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md`).
- A pilot trial with no output file → scored as a failure, not as missing data
  (`docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md`).

## Tests

- `python3 skills/asd-ste100/scripts/ste-lint.py --selftest` in `run-tests.sh` — truth tier.
- Unit tests for `check_ste_baseline.py`: above, below, missing, deleted, crash. All exit 0 with
  the expected message — truth tier.
- `tests/scripts/context-propagation-regression.test.sh`: four assertions, each with a mutation
  case — the asd-ste100 instruction in the implementer prompt, the task reviewer prompt, and
  `compound`, and the lint-count step in the SDD controller
  (`skills/subagent-driven-development/SKILL.md`). Traceability tier: the instruction exists, not
  that agents follow it.
- Deploy smoke: `skills/asd-ste100/` appears in a consumer's `.claude/skills/` after
  `deploy-harness.sh` — truth tier.
- Pilot metrics re-derive from stored raw output with `--score-only` — provenance tier.
- Per rollout wave: `bash scripts/run-tests.sh` passes and the baseline for each rewritten file
  goes down.

## Success criteria

- `skills/asd-ste100/SKILL.md` exists, `.agents/` and `skills-lock.json` do not, and a deploy
  smoke test finds the skill in a consumer tree.
- `bash scripts/run-tests.sh` prints the `ste-baseline` report and exits 0.
- The four wiring assertions pass, and each mutation case fails as expected.
- `DECISION.md` records both pilot metrics, and `--score-only` reproduces them.
- On a pilot pass: every in-scope file's hard-finding count is at or below its pre-rollout
  baseline, and the hard-finding sum is lower than 329 (measured 2026-10-14 ste-lint 0.4.0). On a
  pilot fail: the pilot files match `a5d4292`.

## Non-goals

- Rewriting `CLAUDE.md`, `templates/`, existing `docs/solutions/` entries, or `specs/`.
- A blocking STE gate, a `PostToolUse` hook, or any change to `settings.json` or `hooks/`.
- Reproducing the ASD dictionary or enforcing the lexical rules.
- Changing any behavior that the prose describes.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | Headless Claude Code can run `feature-intake` classification on a fixture request and leave a scoreable file | none yet — Inference: `rerun.py` ran headless trials on 2.1.229 | pilot runner dry run | Score the workflow arm from a stripped classification prompt built from the skill text |
| A2 | `deploy-harness.sh` copies `skills/asd-ste100/scripts/ste-lint.py` to consumers | none yet — Inference: SYNCED includes `skills` | deploy smoke test | Add an explicit include, or keep the linter harness-only |
| A3 | Prose rewrites can keep every literal string that tests and hooks grep | provenance: Local, 2026-10-14, `tests/scripts/` (32 of 47 reference prose paths, measured 2026-10-14 grep) | `run-tests.sh` per wave | Keep the literal span unchanged and rewrite around it |
| A4 | The structural STE rules do not lower agent accuracy on harness prose | none yet | pilot (Phase 2) | Revert pilot rewrites; A ends after the pilot |
| A5 | `ste-lint.py` hard findings in harness prose are mostly real, not false positives on tables or inline code | none yet — Inference: linter skips fences only | Phase 1 baseline review | Pass `--disable` for noisy rules in `check_ste_baseline.py`, regenerate the baseline under the same flags, and record why |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| Agents follow the asd-ste100 instruction when wired in | The wiring tests prove the instruction exists (traceability), not that agents apply it |
| Rewritten prose is STE-compliant | No ASD dictionary. The lexical rules are advisory only |
| A pilot pass proves STE improves agent accuracy | The pass rule is "no worse". Ceiling effects are likely, as in the earlier trials |
| Zero lint findings after rollout | The goal is a lower count per file, not zero |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | Scope is A + B + C | All three phases are in this spec | settled |
| D2 | Pilot first, then a gated rollout for A | Phase 3 runs only after a Phase 2 pass | settled |
| D3 | Vendor into `skills/asd-ste100/`; drop `.agents/` and `skills-lock.json` | Ships to consumers; updates are a manual re-vendor | settled |
| D4 | Wire into the SDD implementer, the task reviewer, and `compound`; the controller runs the linter for the read-only reviewer | Explicit instructions with propagation tests | settled |
| D5 | Linter is a warn-only per-file baseline ratchet in `run-tests.sh` | Never blocks a build or a commit | settled |
| D6 | Pilot gate = comprehension probes for all three files + workflow-in-the-loop for `feature-intake`; a method passes at original minus 2 correct answers (budget) and no probe drops from 10/10 to 7/10 or fewer | A mixed result on `feature-intake` is a fail; the rollout needs all three files to pass | settled |
| D7 | Pilot files: `rules/orchestration.md`, `skills/feature-intake/SKILL.md`, `skills/subagent-driven-development/SKILL.md` | The rollout covers the rest | settled |
