**The eval isn't built: no files were written, because every write was blocked.** Writes under `plugins/harness/skills/recall/evals/` were refused as a sensitive path. Writes to `tests/evals/recall/` then failed because this session has no write permission there. I didn't try to get around that through Bash, and I stopped there because the session's $1 budget is nearly spent. Nothing has been run, including the scorer and any new model runs.

**What already exists**
- **Pattern:** `docs/solutions/harness/skill-eval-blind-run-scoring.md` is the playbook. It calls for labelled fixtures, blind runs, a deterministic scorer, a hard gate kept separate from judgment scores, and multiple runs.
- **Stale references:** the playbook's `scripts/score_intake_eval.py` and its `evals` dir no longer exist. The working example is `tests/evals/tickets/` (`mocks/run_case.sh` plus `mocks/score.py`).
- **Recall eval:** `plugins/harness/skills/recall/evals/evals.json` has 12 cases and a written scoring rule, but no scorer. `tests/evals/recall/runs/2026-11-02/` holds 13 unscored outputs: with-skill 01–07 and baseline 01–06.

**What I'd build**
I took "a prompt-driven skill" to mean `/harness:recall`, since that's this branch's work.
1. **`score.py`:** pure Python that applies the `evals.json` rule and reports path, action, stale-premise and format separately.
   - `--strict` fails the run if a stale record appears under Do first, Avoid or Check before done.
   - A missing output counts as "not run", and an empty output as INVALID rather than a miss.
2. **`run_blind.sh`:** runs one case from a `git archive HEAD` export with `plugins/harness/skills/recall/evals` and `tests/evals` deleted. Both arms use the same plugin and tools; only the prompt differs.
3. **`test_recall_score.py`:** unit tests for the scorer. They have to sit under `plugins/harness` or `scripts`, because `run-tests.sh` only collects `test_*.py` from those two paths.

**Problems with the current evidence**
- **Existing runs may not be blind:** `evals.json` sits in the repo that the `last_run` command ran against, so a run could have read the answer key. I tried to check the outputs for this, but that command was blocked, so it's unknown.
- **The stale gate has no data:** the only stale-premise cases are 11 and 12, and neither has a recorded run.
- **Likely skill problem:** the with-skill output for case 2 puts its matching records under Possibly stale and gives no action, so it should miss the action assertion (`CLAUDE_PROJECT_DIR`). `SKILL.md` marks any record older than 30 days as stale, and stale records can't appear in the action sections. A corpus of older records could therefore produce advice-free briefs. I've only read that one output, so how widespread this is remains unmeasured.
- **This session can't count as a run:** your request matches eval 7 word for word, and 07-baseline is the one output missing for cases 1–7. I read `evals.json`, so this session isn't blind and shouldn't be recorded as that baseline.

**To continue:** allow writes to `tests/evals/recall/` and `plugins/harness/skills/recall/evals/`, and start a new session with a larger budget. Each new blind run can cost up to $1 at the runner's limit, so check the scorer on the 13 existing outputs before paying for any.
