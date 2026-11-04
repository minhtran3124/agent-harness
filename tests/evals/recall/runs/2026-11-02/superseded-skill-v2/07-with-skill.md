Verdict: reusable pattern

**Do first**
- Follow the auto-score / manual-run pattern in `docs/solutions/harness/skill-eval-blind-run-scoring.md` (confirmed_at 2026-10-16). The steps are:
  1. Write labeled fixtures, each with a `request.md` and a parseable `truth.md`. Use `any` for dimensions a fixture does not assert.
  2. Dispatch blind subagents. Each gets only `request.md` and the skill, never `truth.md`.
  3. Score with a pure-Python, unit-tested scorer that uses no LLM and no key.
  4. Make the safety-critical dimension a hard fail with `--strict`.
  5. Run several times, and record the first scored run as the record.
  - The record's example command is `python3 scripts/score_intake_eval.py --run <run_dir> [--strict]`.
- In that scorer, normalize LLM free-text before comparing. Use `re.sub(r"[^a-z0-9]", "", s.lower())`. Before the first run, mark each decision the fixture already states as `settled-by-fixture`, and score only the open rows (same record, confirmed_at 2026-10-16).
- If the eval targets a reviewer or scorer prompt, add a canary and a historical replay (`docs/solutions/harness/reviewer-prompt-change-proven-by-canary-and-replay.md`, confirmed_at 2026-10-16).
  - Canary: plant each defect once, add clean controls, and do not pre-label the defects. The gate passes when every planted defect gets the expected severity and no control gets a finding.
  - Replay: re-run the reviewer on a recorded case where the old review approved and a later review found the defect. This is evidence, not a gate.
  - Set a failure budget before the run.
  - The plan check can be `grep -q "^Canary result: pass$" specs/<slug>/canary.md`.

**Avoid**
- Do not treat green per-task tests on synthetic fixtures as proof of correctness. The record is `docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md`. On gh-175, 145 tests were green and about 11 real bugs were still found, because the tests shared the code's blind spots. For this eval, run the scorer over real inputs, not only tidy fixtures.

**Check before done**
- Blind-run integrity. No run saw `truth.md`, and the eval states that the number is a claim about these fixtures and this skill only.
- Multi-run. Show that hard-gate respect is stable across runs, and check borderline fixtures for flips.
- Answer key. If N blind runs consistently disagree with a fixture, revise `truth.md` and mark the earlier runs non-comparable. Do not tune the skill to a wrong key.
- Scorer red-check. For a canary or replay eval, state in `### Not auto-verified` that one run is one sample.

**Possibly stale**
- `docs/solutions/harness/skill-eval-blind-run-scoring.md`: `scripts/score_intake_eval.py` is not in the repo, and the `evals dir:` entries in `affects` look like a broken placeholder. Under `plugins/harness/` I found only `skills/recall/evals/evals.json`, plus `tests/evals/`. The pattern still holds, but treat the paths as unconfirmed.
- `docs/solutions/harness/reviewer-prompt-change-proven-by-canary-and-replay.md`: both `affects` paths are missing. `skills/subagent-driven-development/task-reviewer-prompt.md` does not exist. `plugins/harness/agents/task-reviewer.md` may be its replacement. `specs/gh-312-test-seams/canary.md` was not found.
- `docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md`: the `affects` paths `runtime/resume_decision.py` and `runtime/test_resume_decision.py` are missing. The record also cites `hooks/risk-corroboration.sh`, which its own footer says was superseded. The lesson still holds.
- All three records were confirmed on 2026-08-10 or 2026-10-16, so none is more than 30 days old as of today (2026-11-02), except the gh-175 record, which is 84 days old.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/skill-eval-blind-run-scoring.md`, `docs/solutions/harness/reviewer-prompt-change-proven-by-canary-and-replay.md`, `docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md`. I also ran a find under the repo for the `affects` paths and found `plugins/harness/skills/recall/evals/evals.json`, `tests/evals/` and `plugins/harness/agents/task-reviewer.md`.
