Verdict: reusable pattern. The `skill-eval-blind-run-scoring` record covers this task directly. Parts of its advice name files that are gone, so only the principles apply.

**Do first**
- Use auto-score / manual-run. Write labeled fixtures (`request.md` plus a parseable `truth.md`, with `any` for dimensions a fixture does not assert). Run each fixture blind: give the subagent only the request and the skill, never `truth.md`. Score with a deterministic, unit-tested pure-Python scorer that has no LLM and no key. `docs/solutions/harness/skill-eval-blind-run-scoring.md` (confirmed_at 2026-10-16). Its scoring command was `python3 scripts/score_intake_eval.py --run <run_dir> [--strict]`, but that script is not in this repo (see Possibly stale).
- Report the safety-critical dimension (hard-gate respect) separately and make it a hard fail under `--strict`. Run each fixture several times and keep the first scored run as the record. Do not re-run a fixture until it passes. Normalize LLM free-text in the scorer by comparing alphanumerics only, `re.sub(r"[^a-z0-9]", "", s.lower())`. Same record, confirmed_at 2026-10-16.
- If you change a reviewer or scorer prompt, add a canary and a historical replay. The canary is a fixture with each target defect planted once, clean controls beside them, and no labels. It passes when every planted defect gets the expected severity and no control gets a finding. The replay reruns a recorded case where the old review missed the defect. Treat the replay as evidence, not a gate. `docs/solutions/harness/reviewer-prompt-change-proven-by-canary-and-replay.md` (confirmed_at 2026-10-16).

**Avoid**
- Do not run the eval non-blind. The orchestrator wrote the answer key, so a run that sees `truth.md` gives a meaningless number.
- Do not trust per-task tests or reviews built on synthetic fixtures. They share the implementation's blind spot, so green means the chosen fixtures pass, not that real input behaves correctly. On gh-175, 145 tests passed and about 11 real bugs remained. `docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md`.
- Do not tune the skill to a wrong key. If several blind runs consistently disagree with a fixture, suspect `truth.md` first. Revise it and mark the earlier runs non-comparable.

**Check before done**
- Every decision the fixture text already settles is marked `settled-by-fixture`, and only open rows are scored. Without this, the simulated user asks about settled decisions and each run takes extra rounds (gh-309).
- Each reported number carries its claim limit: it covers these fixtures and this skill only, not the full chain and not the real-world rate. Also say that one canary run is one sample.
- The scorer has a unit test, and normalization is tested with spelling variants such as `Data model` versus `data-model`.

**Already decided**
None.

**Possibly stale**
- `scripts/score_intake_eval.py` and the `evals dir` named in `skill-eval-blind-run-scoring` are not in the repo. A repo-wide search for `score_*` found nothing. The `--run`/`--strict` command and the `results/<date>-<label>/` layout are out of date as written. The only evals now are `tests/evals/recall/` and `tests/evals/tickets/`, so follow their READMEs for current layout.
- `skills/subagent-driven-development/task-reviewer-prompt.md`, `task_brief.py`, `review_package.py` and `specs/gh-312-test-seams/canary.md` (from the canary record) are not in the repo. `plugins/harness/agents/task-reviewer.md` exists and may hold the reviewer prompt now. The canary check `grep -q "^Canary result: pass$" specs/<slug>/canary.md` is unverified.
- `runtime/resume_decision.py`, its test file and `skills/correctness review/SKILL.md` (from the fixture-fitted-bugs record) are not in the repo. The record also cites `hooks/risk-corroboration.sh`, which is superseded by `hooks/commit-gate.sh`. The corpus-test principle still holds.
- Age: all three records have `confirmed_at` between 2026-08-10 and 2026-10-16. Today is 2026-11-04, so two are about 19 days old and the 2026-08-10 one is about 86 days old (over 30).

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/skill-eval-blind-run-scoring.md`, `docs/solutions/harness/reviewer-prompt-change-proven-by-canary-and-replay.md`, `docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md`. I also ran a glob and a find over the repo for the `affects` paths.
