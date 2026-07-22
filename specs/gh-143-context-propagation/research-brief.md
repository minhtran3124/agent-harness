# Research Brief — gh-143-context-propagation

Ground-truth findings (Explore agent + direct reads, 2026-07-22) that anchor the plan.

## 1. risk-corroboration.sh — where a path signal slots in

- Content-regex scans exclude `*.md`, `docs/`, `specs/`, `skills/`, `hooks/`, `.claude/`
  (pathspec excludes at lines 76–80) — keyword categories never see Markdown.
- **Path-based gating already exists** at lines 85–88, operating on `$STAGED_PATHS`
  (`git diff --cached --name-only`, line 67): `high-blast`, `data-loss/migration`,
  `external-provider` are added via `grep -qE ... && add_cat "<slug>"`. A new
  `workflow-engine` signal is one more line here.
- Any new slug must be mirrored in `harness-manifest.json` `hard_gates.detectable` AND in
  `category_mode()` (lines 42–57) — `scripts/check_manifest.py` Section B (lines 81–103)
  enforces hook↔manifest agreement bidirectionally in CI (regexes `add_cat "..."` and the
  case branches out of the hook source).

## 2. evals/skills/review-chain — fixture shape

- `fixtures/<name>/` = exactly 3 files: `intent.md` (verbatim request), `diff.patch`
  (self-contained, one planted defect), `truth.md` (defect class, location, expected oracle,
  FP description). 5 fixtures exist (3 correctness, 2 intent).
- Scoring is a **manual protocol** (README): apply patch in throwaway worktree, run reviews,
  score `caught / caught-wrong-reason / missed / false-positive`, hand-write
  `results/<date>-<label>.md` from `results/template.md`. No runner script (deliberate, v1).

## 3. feature-intake + manifest

- Input-type table lines 41–47; 10-flag table lines 60–70; hard gates lines 78–95 with the
  canonical-source note pointing at `harness-manifest.json` (`detectable` entry shape:
  `{slug, mode, desc}`).

## 4. Review completion state — none exists today

- `finishing-a-development-branch` steps: 1 Verify Tests (L20), 2 Base Branch (L65),
  3 Push+PR (L74), 4 Mark shipped (L89). No receipt/`reviewed_head_sha` machinery anywhere in
  skills/hooks/scripts/templates (grep-verified). `/review-diff`'s `.review/review.md` is
  visualization-only, explicitly not a gate.
- `subagent-driven-development` calls `/correctness-review` in the "Final Adversarial
  Correctness Review" prose section (~L165–191) and `/intent-review` in the prose step after it
  (~L193–205); the `digraph process` block (L56–110) has matching node labels at L76–81 —
  edit the prose sections, not the graph labels. Records only Status-Log commit shas — nothing
  machine-readable ties review passes to a HEAD sha.

## 5. PR #141 fix anchors (regression-test targets)

- P1 fix `d61e155`: `skills/subagent-driven-development/implementer-prompt.md:101` —
  "FIRST: Read `.claude/rules/auto-correct-scope.md` now…".
- P2 fix `1c0f01d`: `skills/correctness-review/correctness-reviewer-prompt.md:173-177` —
  completed 8-case inline STOP list + explicit Read before Rule-4 classification (also in
  SKILL.md fix-routing path).

## 6. Test conventions

- Hook tests: `tests/hooks/<hook>.test.sh` via `lib.sh` (`run_hook`, `assert_rc*`,
  hermetic mktemp repos). `risk-corroboration.test.sh` has 15 cases today.
- Script tests: `tests/scripts/<name>.test.sh` — auto-globbed by `run-tests.sh` L3.
- Python tests: `scripts/test_*.py`, but only run if listed in `run-tests.sh` `PYTESTS`
  (explicit list — adding a file means editing that line).
- Reusable precedent: `tests/scripts/scorer-threshold-contract.test.sh` (PR #153) parses live
  skill files + self-mutation check — the pattern Phase 0/2 lints should follow.

## 7. Reuse verdicts

| Need | Reuse | Build |
|---|---|---|
| Path-based risk signal | risk-corroboration L85–88 pattern + manifest | one grep line + entry |
| Fixture format | review-chain 3-file shape | 2 new fixtures only |
| Drift lints | scorer-threshold-contract pattern | 2 small .test.sh files |
| Receipt validation | verify_summary.py structure (argparse+pytest style) | new small script |
| Probe protocol | none exists | new evals/ subtree |
