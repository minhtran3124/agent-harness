# opus-5-5-prompt-audit — Research Brief

Depth: **Deep** (intake lane high-risk: workflow-engine hard gate).

## Question

Which instructions in the harness's prompt surface (skills, dispatch prompts, agents, rules,
`CLAUDE.md`) no longer fit Claude Opus 5.5 — the model the `coding` role is now bound to
(`agents/runtime-bindings.json`, PR #230) — and what should replace them?

## Source Pack

- `Docs` — claude-api skill (bundled 2.1.284) `shared/prompt-audit.md`: dated-pattern groups,
  keep list, report/diff contract.
- `Docs` — claude-api `shared/model-migration.md` → *Migrating to Claude Opus 5 → Behavioral
  shifts* (over-verification, self-check trap, scope expansion, over-delegation, self-correction
  narration, severity filters depress recall) and *Migrating to Claude Opus 5.5* (effort default
  `medium`; progress updates as thinking blocks; "re-evaluate Opus 5-specific instructions";
  update suppressors cause under-narration).
- `Local` — three read-only audit passes (dispatch+review prompts & agents; workflow skills;
  rules + root docs), each grepping `tests/`, `scripts/`, `hooks/` for test-asserted strings.

Targets: implementer + correctness scorer → Opus 5.5; correctness finder, intent reviewer, task
reviewer → Opus 5 (Opus 5 guidance applies directly); skill bodies → main session.

## Findings (applied — user approved all four groups)

**Stale facts / contradictions (Group 2, high confidence — contradicted by the repo)**
- Scorer told `commit-quality-gate` runs ruff + pytest — the hook never runs ruff; app gates are
  opt-in (`REQUIRE_APP_GATES=1`, `hooks/commit-quality-gate.sh` early exit). Scorer also said
  "cheap model" (binding: Opus 5.5) and cited a non-existent "Fix loop" section.
- Implementer dispatched as `general-purpose`, inheriting the parent model and bypassing the
  `implementer` → `coding` binding.
- Compound extractors told to read "the session transcript", which a fresh subagent cannot see.
- `rules/orchestration.md` manifest path rendered to `.claude/harness-manifest.json` on deploy,
  contradicting the index-only rule; `REQUIRE_VERIFY` / `/compound` hint claims omitted the
  `REQUIRE_APP_GATES=1` precondition (`CLAUDE.md`, `rules/orchestration.md`, `skills/README.md`).
- `skills/README.md`, `skills/xia2/README.md`, `skills/compound/README.md`,
  `skills/visual-planner/SKILL.md`, `rules/plan-format.md`, `HARNESS.md`: stale paths,
  removed skills (`xia`, `systematic-debugging`), removed flags (`--depth=`), missing failure
  track, "writing-plans opens it" vs visual-planner's "do not auto-open".
- `rules/auto-correct-scope.md` Rule 2 carried app-stack specifics contradicting
  `rules/guidelines.md` ("ships no stack-specific guidelines").

**Review recall (Opus 5 guide: caps and severity filters depress measured recall)**
- Finder "at most 6 findings" / "six candidates per angle" and task-reviewer "limit to six"
  removed; scorer fan-out bounded at 20 parallel. Intent reviewer's "assume at least one
  mismatch… you have not looked hard enough" (re-verify trap with no downstream scorer) rewritten
  to recall-first. `## CRITICAL` headings and caps shouting de-escalated.

**Opus 5.5 guidance (added / rewritten)**
- `rules/behavior.md` §4 (scope + finish-the-whole-task) and §5 (user-facing text, corrections,
  don't take agent reports at face value) — always-on, so every role receives them.
- Implementer "self-review with fresh eyes" block → completion bar (self-check trap; the task
  reviewer is the oracle); "ask questions now" → NEEDS_CONTEXT (a subagent can't converse);
  grader vocabulary removed. SDD "one short status line" suppressor → when-to-update guidance.
  Numeric output caps (150–300 words, max 2 questions, 2–4 sentences) → outcome wording.

**Delegation calibration (Opus 5/5.5 over-delegate)**
- `rules/orchestration.md` "thin coordinator / heavy work delegated / codebase research" →
  delegate for isolation or parallelism only (implementers, isolated reviewers, wide
  investigations). Compound's 3–4 extractor subagents → in-session passes.

## Flagged, not edited (low confidence or deliberate)

Finder's adversarial "assume a bug" (scorer filters downstream); dated case notes in the scorer;
test-asserted caps (`FORBIDDEN from reading…PLAN.md`); "spec/quality reviewer" terminology;
`CLAUDE.md` "9 of the last 80 PRs", "Phase 6", code-review-graph auto-update claim (unknown —
no `settings.json` match, other hook sources unread); `terminology.md` v2.1.216 pointer;
xia2 "When in doubt, invoke"; decision-extractor style coaching; `skills/README.md` historical
note; unindented table rows in `plan-document-reviewer-prompt.md`; `using-git-worktrees`
unconditional deploy step vs a user memory preference.

Dropped from the approved set: adding the finish clause to `agents/coding.md` (duplicates
`rules/behavior.md` §4, which the coding role loads).

## Recommendation

Apply as above; verify with the contract tests that assert prompt strings, the doc-truth lint,
and the full suite; run context-propagation audit, correctness review, and intent review.
