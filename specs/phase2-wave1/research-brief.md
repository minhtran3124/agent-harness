# Research Brief — Phase 2 Wave 1 (zero-coupling deletes)

Source: `docs/reviews/phase-2-deep-review-2026-07-16.md` (merged PR #77) → "Wave 1" items.
All claims below **re-verified fresh on 2026-07-17** in the main session (not trusted from the review):

## W1.1 — `scripts/context-monitor.py` (298 lines)

- `grep -rn "context-monitor|context_monitor"` excluding `.git/.claude`: **only hits are docs/reviews/** (the audit docs themselves). Re-confirmed zero live refs.
- `jq keys settings.json settings.local.json` → `["hooks"]` only — **no `statusLine` key** anywhere, so the script has no invocation path.
- Not in harness-manifest.json, run-tests.sh, tests/, .github/.
- **Delete = rm the file.** No coordinated edits.

## W1.2 — `REQ.md` (22 lines)

- Zero refs in the doc-truth-lint scan set (CLAUDE.md, README.md, HARNESS.md, skills/README.md) — re-confirmed (`grep -n "REQ.md"` → no hits).
- Remaining refs are prose/historical only: `docs/research-harness-req-assessment.md` (a per-question assessment OF REQ.md), `docs/harness-v03-plan-overview.md`, `docs/research/2026-07-03-deep-review…`, `specs/harness-reliability-improvements/{PLAN,SUMMARY}` (shipped), `specs/STATE.md` (breadcrumb noise).
- Courtesy step from the review: paste REQ.md's 6 questions into `research-harness-req-assessment.md`'s preamble so that assessment doesn't orphan its subject.

## W1.3 — `templates/TEST_MATRIX.template.md` (34 lines)

- `find specs -name 'TEST_MATRIX*'` → **0** instances (re-confirmed; 33+ specs, zero uptake since the mandate).
- Exactly **3 prose mandates** + the template itself (re-confirmed by repo-wide grep, excluding historical docs):
  1. `rules/orchestration.md:62` — "Behavior-to-proof status lives in specs/<slug>/TEST_MATRIX.md…"
  2. `HARNESS.md:53` — evidence-principles bullet
  3. `README.md:64` — proof table row
- No machine consumer: not in manifest contracts, scripts, tests, SUMMARY.template.
- `specs/intent-review-stage/` explicitly *deferred* "TEST_MATRIX-from-design" — the mechanism was consciously parked, never run.
- Doc-truth lint will NOT force the prose edits (bare tokens without `/` are out of its scope) — the edits are for truth, not CI.
- **NEW (lane-deciding):** `scripts/ci-strict-gate.sh:27` `HARD_GATE_RE` includes `^templates/` — this deletion trips the CI strict gate, which requires a changed `Lane: high-risk` SUMMARY whose Verify table passes `verify_summary.py --check`. Wave 1 must therefore ship as **high-risk lane** with a machine-verifiable Verify table.

## W1.4 — `deploy-harness.sh` spinner (~20 lines)

- Re-read `scripts/deploy-harness.sh:60-83`: `SPIN` frame array + `step()` — TTY branch runs **8 frames × 0.045s of pure `sleep` BEFORE the work**, then executes, then prints `✓ label`; non-TTY branch executes and prints `- label`. The animation is decoration ahead of the task; nothing reads it.
- `grep "SPIN|spinner|0.045" tests/scripts/*.test.sh` → **no test pins the animation** (all tests run non-TTY).
- Must survive the trim: the `step()` wrapper itself (callers depend on it), the `✓/label` success print, the non-TTY `- label` branch, and the ERR trap (independent of SPIN).
- The backup-policy/interactive-prompt code is **out of scope** (Wave-3-reversed: human-approved escape hatch per `resync-protected-files-decisions.md` D3).

## Blast/lane assessment

- Files touched: 2 deletions with no wires (context-monitor, REQ), 1 deletion + 3 prose edits (TEST_MATRIX), 1 surgical trim in `scripts/deploy-harness.sh` (installer — pinned by resync-conflict/settings tests, all of which must stay green).
- `^templates/` in the diff ⇒ CI strict gate ⇒ **Lane: high-risk** (mechanical trigger, not judgment).
- `rules/orchestration.md` edit ⇒ deployed copy `.claude/rules/orchestration.md` drifts until the next `deploy-harness.sh` run (local-only, gitignored — note, not a task).
