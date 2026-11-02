Verdict: reusable pattern

**Do first.**
1. Use auto-score / manual-run: labeled fixtures with a parseable `truth.md` (`any` for dimensions the fixture does not assert), blind subagent runs that get only the request and the skill, and a deterministic unit-tested scorer with no LLM. Dispatch the runs with a `--strict` hard fail on the safety-critical dimension. Run the scorer with `python3 scripts/score_intake_eval.py --run <run_dir> [--strict]`. Source: `docs/solutions/harness/skill-eval-blind-run-scoring.md` (confirmed_at 2026-10-16).
2. Run each fixture several times, because one run hides borderline flips. Make the scorer compare on alphanumerics only (`re.sub(r"[^a-z0-9]", "", s.lower())`). Before the first run, mark every decision the fixture already settles as `settled-by-fixture` and score only the open rows. Record the first scored run under `results/<date>-<label>/` and do not re-run until it passes. Source: same record (2026-10-16).
3. If you change a reviewer or scorer prompt, add a canary and a historical replay. The canary plants each target defect once, adds clean controls, and carries no pre-labels. The replay is evidence, not a gate. Build briefs and packages with the real scripts (`task_brief.py`, `review_package.py`), and set a failure budget before the run. Source: `docs/solutions/harness/reviewer-prompt-change-proven-by-canary-and-replay.md` (2026-10-16).

**Avoid.**
- A non-blind run, where the subagent sees `truth.md`. You wrote the key, so the score means nothing.
- A scorer or ratchet built from the same enumeration as the thing it checks. It shares the blind spot and reports clean over the misses (`docs/solutions/harness/ratchet-matches-spelling-not-property.md`). Match the defect's shape instead of one spelling.
- Reading a green scorer as proof before you have seen it fail. Run it against a known-bad run or the pre-fix tree.

**Check before done.**
- Run the scorer against a known-bad or pre-fix input and confirm it fails. Source: `ratchet-matches-spelling-not-property.md`.
- State on every reported number that it covers only these fixtures and this skill, not the full chain or the real-world rate. Say that one canary run is one sample. Source: `skill-eval-blind-run-scoring.md` and `reviewer-prompt-change-proven-by-canary-and-replay.md`.
- If N blind runs consistently disagree with a fixture, suspect the answer key before the skill. Revise `truth.md` and mark the prior runs non-comparable. Source: `skill-eval-blind-run-scoring.md`.

**Possibly stale.**
- `skill-eval-blind-run-scoring.md`: its `affects` path `scripts/score_intake_eval.py` is not in this repo. I found no `score_intake_eval.py` anywhere. The advice still holds, but the example command will not run here. The other `affects` entry is a garbled placeholder (`evals dir: `). The record is 17 days old.
- `reviewer-prompt-change-proven-by-canary-and-replay.md`: neither `skills/subagent-driven-development/task-reviewer-prompt.md` nor `specs/gh-312-test-seams/canary.md` exists. The reviewer prompt now appears to be `plugins/harness/agents/task-reviewer.md`. The advice still holds. The record is 17 days old.
- `ratchet-matches-spelling-not-property.md`: confirmed 2026-09-09, so it is 54 days old, more than 30. Its `scripts/check-hook-root-source.sh` still exists.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/skill-eval-blind-run-scoring.md`, `docs/solutions/harness/reviewer-prompt-change-proven-by-canary-and-replay.md`, `docs/solutions/harness/ratchet-matches-spelling-not-property.md`. I also checked the `affects` paths with `ls` and `find` under the repo root, which turned up `tests/evals` and `plugins/harness/skills/recall/evals`.
