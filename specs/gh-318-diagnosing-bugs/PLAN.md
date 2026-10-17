---
slug: gh-318-diagnosing-bugs
status: proposed
owner: Minh Tran
created: 2026-10-17
---

# diagnosing-bugs skill with six gated phases

## 1. Motivation

`feature-intake` classifies `Input-type: bug fix` but routes it to no diagnosis step. The bug-fix
path in `skills/README.md` names an external, optional `systematic-debugging` skill. When it is
absent, the agent reads code and guesses. Issue #318 adds an in-repo `diagnosing-bugs` skill with
six gated phases, wired into intake, the bug-fix lane, `subagent-driven-development`,
`writing-plans`, and `compound`. Design: `specs/gh-318-diagnosing-bugs/design.md` (D1–D13).
Research: `specs/gh-318-diagnosing-bugs/research-brief.md`, including the four follow-up
questions that the user confirmed on 2026-10-17 ("yes for all").

## 2. Non-goals

- No change to `scripts/verify_summary.py`, `hooks/commit-gate.sh`, `settings.json`, or any hook.
- `REQUIRE_RED_TEST=1` stays opt-in.
- No file under `templates/`. No new script under `scripts/`.
- No copy of Pocock's text. `hitl-loop.template.sh` is written new.
- No deploy into this repo's `.claude/`. Proof runs install into a scratch target.

## 3. Success Criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
|------|-------------------------|-----------------------|------------|
| SC-1 | The skill file exists and sets `disable-model-invocation: true` | `grep -qx "disable-model-invocation: true" skills/diagnosing-bugs/SKILL.md` | exit 0 |
| SC-2 | Every audited skill, the new one and `subagent-driven-development` and `feature-intake` included, is at or under the 600-word ceiling | `python3 scripts/audit_skill_prompts.py` | exit 0 |
| SC-3 | The audit surface test counts 15 skills and 12 companion prompts | `python3 -m pytest -q scripts/test_audit_skill_prompts.py` | exit 0 |
| SC-4 | The manifest lists `diagnosing-bugs` and the manifest check passes | `python3 scripts/check_manifest.py` | exit 0 |
| SC-5 | Every backticked command in a skill has a matching tool grant | `python3 scripts/check_skill_tool_conformance.py` | exit 0 |
| SC-6 | Every skill has a non-empty `allowed-tools:` line | `bash scripts/check-allowed-tools.sh` | exit 0 |
| SC-7 | No skill source names a deployed `.claude/` path or a model id | `python3 scripts/check_runtime_neutral_sources.py` | exit 0 |
| SC-8 | Every backticked repo path in the docs resolves | `bash scripts/lint-doc-truth.sh` | exit 0 |
| SC-9 | Fenced bash blocks in skills pass syntax and shellcheck | `bash scripts/lint-skill-bash.sh` | exit 0 |
| SC-10 | The HITL loop template parses as bash | `bash -n skills/diagnosing-bugs/scripts/hitl-loop.template.sh` | exit 0 |
| SC-11 | The skill carries the redaction rule with the `<REDACTED>` token | `grep -q "<REDACTED>" skills/diagnosing-bugs/SKILL.md` | exit 0 |
| SC-12 | `feature-intake` routes a bug fix to the skill file by path | `grep -q "skills/diagnosing-bugs/SKILL.md" skills/feature-intake/SKILL.md` | exit 0 |
| SC-13 | No README names `systematic-debugging` | `grep -q systematic-debugging skills/README.md skills/xia2/README.md` | exit 1 — no match |
| SC-14 | The handoff map has a `diagnosing-bugs` row | `grep -qE "^diagnosing-bugs +──►" skills/README.md` | exit 0 |
| SC-15 | `rules/plan-format.md` allows `Seams: none — <reason>` for a bug-fix task whose `diagnosis.md` says `Seam: none` | `grep -q "diagnosis.md" rules/plan-format.md` | exit 0 |
| SC-16 | The implementer takes the `Red test exempt` path when `diagnosis.md` says `Seam: none` | `grep -q "diagnosis.md" skills/subagent-driven-development/implementer-prompt.md` | exit 0 |
| SC-17 | The task reviewer accepts that `Seams: none` case | `grep -q "diagnosis.md" skills/subagent-driven-development/task-reviewer-prompt.md` | exit 0 |
| SC-18 | The task-review and implementer phrase pins still pass | `python3 scripts/check_task_review_contract.py` | exit 0 |
| SC-19 | The SDD bug-fix reference states the seam check before dispatch | `grep -q "Seam:" skills/subagent-driven-development/references/bug-fix.md` | exit 0 |
| SC-20 | SDD SKILL.md points to the bug-fix reference | `grep -q "references/bug-fix.md" skills/subagent-driven-development/SKILL.md` | exit 0 |
| SC-21 | The final review chain runs Phase 6 cleanup for a diagnosed bug | `grep -q "diagnosing-bugs" skills/subagent-driven-development/references/review-chain.md` | exit 0 |
| SC-22 | `writing-plans` copies `diagnosis.md` `Seam:` into the fix task | `grep -q "diagnosis.md" skills/writing-plans/SKILL.md` | exit 0 |
| SC-23 | `compound` takes the root cause from `diagnosis.md` | `grep -q "diagnosis.md" skills/compound/SKILL.md` | exit 0 |
| SC-24 | Changed and new prose adds no hard STE finding | `python3 scripts/check_ste_baseline.py --strict --against 09a7985` | exit 0 |
| SC-25 | This plan passes the plan contract with seams | `python3 scripts/check_plan_contract.py specs/gh-318-diagnosing-bugs/PLAN.md` | exit 0 |
| SC-26 | The quick-question run invoked `feature-intake` (the log is not empty) | `grep -qx "Skill feature-intake" specs/gh-318-diagnosing-bugs/proof/quick-question.md` | exit 0 |
| SC-27 | The quick-question run did not read the diagnosing-bugs skill | `grep -qE "^Read .*diagnosing-bugs/SKILL\.md$" specs/gh-318-diagnosing-bugs/proof/quick-question.md` | exit 1 — no match |
| SC-28 | The bug-fix run read the skill with the Read tool | `grep -qE "^Read .*diagnosing-bugs/SKILL\.md$" specs/gh-318-diagnosing-bugs/proof/bug-fix-routing.md` | exit 0 |
| SC-29 | The bug-fix run made no Skill call for diagnosing-bugs | `grep -qx "Skill diagnosing-bugs" specs/gh-318-diagnosing-bugs/proof/bug-fix-routing.md` | exit 1 — no match |
| SC-30 | In the replay transcript, the first red loop precedes the first hypothesis, and the ranked list precedes the first probe | `python3 specs/gh-318-diagnosing-bugs/proof/check_replay.py specs/gh-318-diagnosing-bugs/proof/replay.md` | exit 0 |
| SC-31 | The replay fix diff has zero `[DEBUG-` tags | `grep -qF "[DEBUG-" specs/gh-318-diagnosing-bugs/proof/replay-diff.patch` | exit 1 — no match |

## Global Constraints

- Plan-contract: 2
- Work in the task worktree root. Edit only the files your task names. Never edit `.claude/`,
  `hooks/`, `settings.json`, `templates/`, `scripts/verify_summary.py`,
  `skills/visual-planner/render_plan.py`, `scripts/ste-baseline.json`, `VERSION` or
  `CHANGELOG.md`. If a check cannot pass without one of these files, stop and report.
- Read `specs/gh-318-diagnosing-bugs/design.md` (Architecture, the six phases, Worked trace,
  Error behavior, Tests, What we do not claim, Decisions D1–D13) and
  `specs/gh-318-diagnosing-bugs/research-brief.md` (Evidence Ledger, Risks, the four confirmed
  follow-up questions) before you edit. They are the spec. Do not read or copy upstream Pocock
  text.
- The branch base for every comparison is `09a7985`. Before the first task, run
  `git merge-base --is-ancestor 09a7985 HEAD` and confirm it exits 0. If it does not, stop and
  report. The remote is `origin`.
- The system `python3` may have no pytest. If `python3 -m pytest` reports
  `No module named pytest`, run `python3 -m pip install -q pytest` once and re-run. Record the
  command you ran.
- Run shell commands as plain, separate commands. Commit only your own files: run
  `git add -- <files>`, then `git commit -- <files>` in a separate call. Never use `git add -A`,
  `git reset` or `git stash`.
- The audit counts words on the whole file, frontmatter included (`scripts/audit_skill_prompts.py`).
  The ceiling is 600 words per `SKILL.md`. `subagent-driven-development/SKILL.md` is at 600 and
  `feature-intake/SKILL.md` is at 539 (measured at `09a7985`). Meet a ceiling by deleting a
  sentence whose removal changes no behavior (the #308 deletion test), not by squeezing words.
- Prose under `skills/`, `rules/` and `agents/` follows `skills/asd-ste100/SKILL.md`: one
  instruction per sentence, at most 20 words in an instruction and 25 in a description, no
  semicolon in a new sentence, active voice. A new prose file starts at STE baseline 0, so it must
  have zero hard findings. Check with
  `python3 skills/asd-ste100/scripts/ste-lint.py --json --disable synonym-rotation <file>`.
  `ste-lint` does not read prose inside a code fence. Check fenced prompt sentences by hand.
- Name the skill path as `skills/diagnosing-bugs/...` in every skill and rule. Never write a
  `.claude/` path (`scripts/check_runtime_neutral_sources.py`).
- Every `diagnosis.md` field name is fixed by the template in Task 1.1: `Loop:`, `Repro:`,
  `Hypotheses:`, `Probes:`, `Confirmed:`, `Seam:`. The seam point is the text before
  ` — catches:` (`rules/plan-format.md`). `Seam: none — <reason>` is the only no-seam form.
- Do not use the words `correctly`, `properly`, `as expected`, `works`, `is correct`,
  `looks right`, `appropriate` or `reasonable` in a `Verify:` or `Done:` line
  (`rules/terminology.md` §3).

## 4. Tasks

### Task 1.1 — The diagnosing-bugs skill folder and its registration (wave 1)

- **Files:** skills/diagnosing-bugs/SKILL.md, skills/diagnosing-bugs/references/phases.md, skills/diagnosing-bugs/references/diagnosis-template.md, skills/diagnosing-bugs/references/diagnosis-review-prompt.md, skills/diagnosing-bugs/scripts/hitl-loop.template.sh, skills/diagnosing-bugs/tests/routing-cases.md, harness-manifest.json, scripts/test_audit_skill_prompts.py
- **Action:** Write the skill folder per design Architecture and D1–D11.
  - `SKILL.md`: frontmatter `name: diagnosing-bugs`, a description that names a bug fix routed
    by intake or `/diagnosing-bugs`, `disable-model-invocation: true`, and a non-empty
    `allowed-tools:` that grants every backticked command in the file. The first body section is
    the redaction rule: replace each secret with `<REDACTED>` before you show or write a command
    or an output. Then the isolation step (D3: tiny runs `git checkout -b fix/<slug>`; normal and
    high-risk run `using-git-worktrees`). Then the six phases, each ending in one
    `Done when:` line taken from design "The six phases". Phase 1 with no loop writes an
    `ESCALATIONS.md` block with `decision: pending` and stops (D7). Phase 3 posts three to five
    ranked hypotheses and continues without waiting (D6). Phase 4 tags each probe with a unique
    `[DEBUG-xxxx]` prefix, deletes every probe and throwaway harness before handoff, and commits
    `specs/<slug>/diagnosis.md` (D11). Between Phase 4 and Phase 5, dispatch `task-reviewer` with
    `references/diagnosis-review-prompt.md` and the `diagnosis.md` path (D5); apply the Error
    behavior budgets (two reviews, two refutation rounds). Phase 5 hands off per lane. Phase 6
    re-runs the loop, greps the tag in the fix diff and the working tree, deletes what is left,
    and names the confirmed hypothesis in the commit message and SUMMARY `Rationale`. Point to
    `references/phases.md` for long lists. Keep the whole file under 600 words.
  - `references/phases.md`: original text for loop-building techniques in preference order,
    minimisation tactics, and hypothesis and probe patterns. Do not copy upstream wording.
  - `references/diagnosis-template.md`: the shape of `specs/<slug>/diagnosis.md` with the six
    fields from Global Constraints, in that order, and one line of guidance under each.
  - `references/diagnosis-review-prompt.md`: the `task-reviewer` brief. Inputs: the
    `diagnosis.md` path and the SUMMARY path. It returns `spec_verdict` and `quality_verdict` in
    the YAML shape of `skills/subagent-driven-development/task-reviewer-prompt.md`. It fails the
    spec verdict when a field is missing, when `Loop:` has no red output, when fewer than three or
    more than five hypotheses exist, when a probe maps to no prediction, or when `Confirmed:`
    names no listed hypothesis. It states that the reviewer cannot re-run the loop.
  - `scripts/hitl-loop.template.sh`: an original bash script, mode 100644, run with `bash`. It
    defines `step "<instruction>"` (print, wait for Enter) and `capture VAR "<question>"` (read
    one answer). It ends by printing `--- Captured ---` and one `KEY=VALUE` line per capture.
  - `tests/routing-cases.md`: case table in the style of
    `skills/feature-intake/tests/lane-classification-cases.md`. Rows: a quick question does not
    fire the skill; a bug-fix input reads `skills/diagnosing-bugs/SKILL.md`; `/diagnosing-bugs`
    runs it; a tiny bug fix still runs all six phases (D4).
  - `harness-manifest.json`: add `"diagnosing-bugs"` to `skills[]` in alphabetical order.
  - `scripts/test_audit_skill_prompts.py`: change the pinned totals to 15 skills and 12
    companion prompts.
- **Verify:** `python3 scripts/audit_skill_prompts.py`
- **Done:** SC-1 to SC-11 exit 0 for this task's files; `python3 -m pytest -q scripts/test_audit_skill_prompts.py` exits 0; `python3 scripts/check_ste_baseline.py --strict --against 09a7985` prints no WARN line for a `skills/diagnosing-bugs/` file.
- **Criteria:** SC-1, SC-2, SC-3, SC-4, SC-5, SC-6, SC-7, SC-9, SC-10, SC-11, SC-24
- **Interfaces:** Consumes: design D1–D11, Error behavior, the confirmed follow-up 3. Produces: `skills/diagnosing-bugs/SKILL.md`, `skills/diagnosing-bugs/references/diagnosis-template.md`, `skills/diagnosing-bugs/references/diagnosis-review-prompt.md`, `skills/diagnosing-bugs/scripts/hitl-loop.template.sh`, `harness-manifest.json`.
- **Seams:** `scripts/audit_skill_prompts.py --json` totals and per-skill words — catches: a ceiling breach, an unlisted skill, a wrong prompt count; misses: whether the prose drives a model to follow the phases | `bash -n` on the HITL template — catches: a syntax error; misses: interactive behavior

### Task 1.2 — Seam rule accepts a diagnosed no-seam bug fix (wave 1)

- **Files:** rules/plan-format.md, skills/subagent-driven-development/implementer-prompt.md, skills/subagent-driven-development/task-reviewer-prompt.md
- **Action:** Apply confirmed follow-up 1 (D13). In `rules/plan-format.md`, change the bullet
  `A bug-fix task never writes none` so one exception holds: when `specs/<slug>/diagnosis.md`
  says `Seam: none — <reason>`, the fix task writes `Seams: none — <reason>` with the same reason.
  In `implementer-prompt.md`, in the bug-fix block, replace the rule that returns `NEEDS_CONTEXT`
  on `Seams: none`: when `diagnosis.md` says `Seam: none — <reason>`, write
  `Red test exempt: <reason>` in `### Verify` and skip the red and green rows. Otherwise keep
  `NEEDS_CONTEXT`. In `task-reviewer-prompt.md`, step 4 of the seam check (`Seams:` is `none`)
  stays an Important finding, except for a bug-fix task whose `diagnosis.md` says
  `Seam: none — <reason>` with the same reason. Each of the three files must hold the literal
  `diagnosis.md`. Keep every string pinned in `scripts/check_task_review_contract.py` word for
  word, including `Write the red test at a declared seam` and
  `cannot observe the behavior, return \`NEEDS_CONTEXT\` before any edit`.
- **Verify:** `python3 scripts/check_task_review_contract.py`
- **Done:** SC-15, SC-16, SC-17 and SC-18 exit 0; `python3 scripts/check_ste_baseline.py --strict --against 09a7985` prints no WARN line for the three files.
- **Criteria:** SC-15, SC-16, SC-17, SC-18, SC-24
- **Interfaces:** Consumes: design D13 and confirmed follow-up 1. Produces: `rules/plan-format.md`, `skills/subagent-driven-development/implementer-prompt.md`, `skills/subagent-driven-development/task-reviewer-prompt.md`.
- **Seams:** `scripts/check_task_review_contract.py` exit and stderr — catches: a removed pinned phrase; misses: the meaning of the new exception, which the task reviewer reads

### Task 1.3 — SDD controller: diagnosis context, seam check, Phase 6 (wave 1)

- **Files:** skills/subagent-driven-development/SKILL.md, skills/subagent-driven-development/references/bug-fix.md, skills/subagent-driven-development/references/review-chain.md
- **Action:** Apply D12 and confirmed follow-up 2. Write the new
  `references/bug-fix.md` (original prose, STE). It applies when SUMMARY says
  `Input-type: bug fix` and `specs/<slug>/diagnosis.md` exists. It tells the controller to:
  name the `diagnosis.md` path in the fix task's Context; before dispatch, confirm the plan has
  the `- Plan-contract: 2` marker and the fix task has a `Seams:` line (a missing marker or line
  is a mismatch); compare the first seam point of `Seams:` (text before ` — catches:`) with
  `diagnosis.md` `Seam:` for an exact match; on a mismatch, not dispatch, then correct `Seams:`
  itself on the normal lane or return the task to `writing-plans` on high-risk; on a second
  mismatch, write an `ESCALATIONS.md` block with `decision: pending` and stop. In `SKILL.md`, add
  one sentence under "Execute waves" that reads `references/bug-fix.md` for a diagnosed bug fix.
  Pay for its words with a deletion elsewhere in `SKILL.md` that passes the #308 deletion test,
  so the file stays at or under 600 words. Keep `spec then quality` and
  `spec-reviewer-prompt.md` absent. In `references/review-chain.md`, add a first step for a
  diagnosed bug fix: before the audit, run `diagnosing-bugs` Phase 6 (re-run the loop, grep the
  `[DEBUG-` tag in the branch diff and the working tree, delete what is left, name the confirmed
  hypothesis in the commit message and SUMMARY `Rationale`).
- **Verify:** `python3 scripts/audit_skill_prompts.py`
- **Done:** SC-19, SC-20, SC-21 exit 0; `python3 scripts/audit_skill_prompts.py --json` reports `subagent-driven-development` at or under 600 words; `python3 scripts/check_task_review_contract.py` exits 0.
- **Criteria:** SC-2, SC-18, SC-19, SC-20, SC-21, SC-24
- **Interfaces:** Consumes: design D5, D12, Worked trace steps 4–5, confirmed follow-up 2. Produces: `skills/subagent-driven-development/references/bug-fix.md`, `skills/subagent-driven-development/SKILL.md`, `skills/subagent-driven-development/references/review-chain.md`.
- **Seams:** `scripts/audit_skill_prompts.py --json` word count for `subagent-driven-development` — catches: a ceiling breach from the pointer; misses: whether a controller follows the seam check

### Task 2.1 — Intake routing, writing-plans seam copy, compound input (wave 2)

- **Files:** skills/feature-intake/SKILL.md, skills/writing-plans/SKILL.md, skills/compound/SKILL.md
- **Action:** In `skills/feature-intake/SKILL.md` `## Routes`, add one short line (D1, D8,
  research-brief Inference row): for `Input-type: bug fix`, use the Read tool on
  `skills/diagnosing-bugs/SKILL.md` and follow it before the lane route; do not call the Skill
  tool for it. Keep the file at or under 600 words; pay with a #308 deletion if needed. In
  `skills/writing-plans/SKILL.md`, add one sentence: when `specs/<slug>/diagnosis.md` exists,
  copy its `Seam:` into the fix task's `Seams:` and keep the `- Plan-contract: 2` marker. In
  `skills/compound/SKILL.md`, add one sentence to the bug track: when
  `specs/<slug>/diagnosis.md` exists, take the root cause from its `Confirmed:` hypothesis.
- **Verify:** `python3 scripts/audit_skill_prompts.py`
- **Done:** SC-12, SC-22, SC-23 exit 0; `python3 scripts/audit_skill_prompts.py --json` reports `feature-intake`, `writing-plans` and `compound` each at or under 600 words; SC-8 exits 0.
- **Criteria:** SC-2, SC-8, SC-12, SC-22, SC-23, SC-24
- **Interfaces:** Consumes: `skills/diagnosing-bugs/SKILL.md` from Task 1.1; design D1, D8, D12. Produces: `skills/feature-intake/SKILL.md`, `skills/writing-plans/SKILL.md`, `skills/compound/SKILL.md`.
- **Seams:** `scripts/lint-doc-truth.sh` path resolution and `scripts/audit_skill_prompts.py` word counts — catches: a dead skill path, a ceiling breach; misses: whether a model routes a bug fix (Task 3.1 proves that)

### Task 2.2 — README bug-fix path, skills reference and handoff map (wave 2)

- **Files:** skills/README.md, skills/xia2/README.md
- **Action:** In `skills/README.md`, replace the Bug Fix Path block so it reads:
  `feature-intake` → `diagnosing-bugs` (six phases, `diagnosis.md`, review) → the lane route →
  `compound`. Add a Skills Reference row for `diagnosing-bugs` marked **User- or intake-invoked**.
  Delete the `systematic-debugging` row from "External Skills". In the handoff map, replace the
  `systematic-debugging` line with `diagnosing-bugs` followed by `──►` and the lane route, and add
  `Input-type: bug fix → diagnosing-bugs` to the `feature-intake` line. In `skills/xia2/README.md`,
  change the last table row to point a bug fix at `diagnosing-bugs`. No file may still contain
  `systematic-debugging`.
- **Verify:** `bash scripts/lint-doc-truth.sh`
- **Done:** SC-8, SC-13 and SC-14 return their expected exit codes.
- **Criteria:** SC-8, SC-13, SC-14
- **Interfaces:** Consumes: `skills/diagnosing-bugs/SKILL.md` from Task 1.1 and confirmed follow-up 3. Produces: `skills/README.md`, `skills/xia2/README.md`.
- **Seams:** none — documentation-only change, checked by grep and the doc-truth lint

### Task 3.1 — Routing proof runs through a deployed harness (wave 3)

- **Files:** specs/gh-318-diagnosing-bugs/proof/extract_tool_calls.py, specs/gh-318-diagnosing-bugs/proof/quick-question.md, specs/gh-318-diagnosing-bugs/proof/bug-fix-routing.md
- **Action:** Prove A1 and confirmed follow-up 4. Write `proof/extract_tool_calls.py`: it reads
  a `claude -p --output-format stream-json --verbose` stream from a file path argument and prints
  one line per `tool_use` block, `<Tool> <first argument>` (for Read the `file_path` relative to
  the run directory, for Skill the `skill` value, for Bash the first 80 characters of
  `command`). It prints no tool results. Install the harness from this worktree into a scratch
  directory outside the repo with
  `bash scripts/install-harness.sh --source <worktree> -y -d <scratch>`, and `git init` the
  scratch directory. In the scratch directory, run `claude -p` twice with stream-json output
  saved to a file. Run 1 prompt: `Use the feature-intake skill: what does verify_summary.py --lane check for a normal lane?`.
  Run 2 prompt: `Use the feature-intake skill: scripts/x.sh exits 0 when its input file is missing; it should exit 1.`
  Stop run 2 after intake has read the diagnosis skill (budget: `--max-turns 12`). Write each
  extractor output, under a two-line header with the prompt and the CLI version, to
  `proof/quick-question.md` and `proof/bug-fix-routing.md`. If `claude -p` cannot authenticate,
  return BLOCKED with its error.
- **Verify:** `grep -qx "Skill feature-intake" specs/gh-318-diagnosing-bugs/proof/quick-question.md`
- **Done:** SC-26 and SC-28 exit 0; SC-27 and SC-29 exit 1.
- **Criteria:** SC-26, SC-27, SC-28, SC-29
- **Interfaces:** Consumes: the deployed harness built from Tasks 1.1–2.2. Produces: `specs/gh-318-diagnosing-bugs/proof/extract_tool_calls.py`, `specs/gh-318-diagnosing-bugs/proof/quick-question.md`, `specs/gh-318-diagnosing-bugs/proof/bug-fix-routing.md`.
- **Seams:** the extracted tool-call log of a real `claude -p` stream — catches: the skill firing on a quick question, a Skill-tool call instead of a Read; misses: other runtimes (Codex) and other prompts

### Task 3.2 — Replay proof on a recorded bug (wave 3)

- **Files:** specs/gh-318-diagnosing-bugs/proof/check_replay.py, specs/gh-318-diagnosing-bugs/proof/replay.md, specs/gh-318-diagnosing-bugs/proof/replay-diff.patch
- **Action:** Prove A4 and the design's replay proof. Write `proof/check_replay.py` first, from
  design "Success criteria": it reads a transcript and exits 0 only when the first line marked
  `LOOP-RED` comes before the first line marked `HYPOTHESIS`, and the first `HYPOTHESIS` comes
  before the first line marked `PROBE`. It exits 1 otherwise and names the failed order. Create
  a throwaway worktree outside the repo at `0048a16`. Copy `skills/diagnosing-bugs/` from this
  branch into it. Overlay the test file with
  `git show 8e72f7f:tests/scripts/resync-conflict.test.sh`. Run `claude -p` there with
  stream-json output and this symptom only: `A tty-less re-sync with no --yes prints the conflict menu and never prints the keeping-your-local-copy warning. Read skills/diagnosing-bugs/SKILL.md with the Read tool and follow it on the tiny lane.`
  Do not name the cause. Convert the stream to `proof/replay.md` with a script: one line per
  assistant text block or tool call, in stream order, each prefixed with a marker from the
  skill's phase headings (`LOOP-RED`, `HYPOTHESIS`, `PROBE`, `FIX`, `CLEANUP`, or `-`). Write
  `git diff 0048a16 -- . ':!specs'` from the worktree to `proof/replay-diff.patch`. Remove the
  worktree afterwards. Apply `<REDACTED>` to any secret. If the run cannot reach a fix
  (budget: `--max-turns 60`), return BLOCKED with the last phase reached.
- **Verify:** `python3 specs/gh-318-diagnosing-bugs/proof/check_replay.py specs/gh-318-diagnosing-bugs/proof/replay.md`
- **Done:** SC-30 exits 0 and SC-31 exits 1; `proof/replay-diff.patch` changes `scripts/deploy-harness.sh`.
- **Criteria:** SC-30, SC-31
- **Interfaces:** Consumes: `skills/diagnosing-bugs/SKILL.md` from Task 1.1; the pre-fix commit 0048a16 and the test commit 8e72f7f. Produces: `specs/gh-318-diagnosing-bugs/proof/check_replay.py`, `specs/gh-318-diagnosing-bugs/proof/replay.md`, `specs/gh-318-diagnosing-bugs/proof/replay-diff.patch`.
- **Seams:** `check_replay.py` exit on the marked transcript — catches: a hypothesis before a red loop, a probe before the ranked list; misses: whether the markers match the model's real phase, which is traceability tier only

## 5. Risks

- A1: on CLI 2.1.302 the Skill-tool block message for a `disable-model-invocation` skill may make
  the model refuse the steps. Task 3.1 detects it; the fallback is a model-invocable skill with a
  narrow description (design A1), which reopens D1 and needs a `DC<n>` entry.
- `subagent-driven-development/SKILL.md` has zero word headroom. Task 1.3 can fail the audit if
  no sentence passes the deletion test; then stop and report rather than squeeze words.
- Proof runs cost model calls and are not deterministic. One run per case is traceability tier;
  the SUMMARY lists these claims under `### Not auto-verified`.
- Codex handling of `disable-model-invocation` is unconfirmed (research Inference row).

### Assumption coverage

- A1 → SC-27
- A2 → Task 1.1
- A3 → SC-8
- A4 → SC-30
- A5 → SC-2

Not an SC row (Guardrail 4): `bash scripts/run-tests.sh` must exit 0 at branch finish. The
`workflow-engine` signal fires, so the final review chain starts with `context-propagation-audit`.

## 6. Status Log

- 2026-10-17 — plan written from design ff90b54, the research brief, and the user's confirmation of follow-ups 1–4 (09a7985)
