Verdict: existing decision

**Already decided.**
- `docs/solutions/harness/review-model-diversity-dropped-decisions.md` (confirmed_at 2026-10-02): The user chose `claude-opus-5-5` at `medium` effort for the reviewer and task-reviewer roles. The rule that review must use a different model than the implementer was dropped for every runtime. Review independence now rests on fresh context per pass, read-only reviewer bindings and plan-blindness. Do not reintroduce a model-diversity check without a new decision.

**Do first.**
- `docs/solutions/harness/reviewer-prompt-change-proven-by-canary-and-replay.md` (confirmed_at 2026-10-16): This applies only if your change also edits a reviewer prompt. A phrase pin does not show that the reviewer behaves the same. Run a canary with planted defects and clean controls, then a historical replay. The record's `rules` for the canary pass check are `grep -q "^Canary result: pass$" specs/<slug>/canary.md`.
- `docs/solutions/harness/review-model-diversity-dropped-decisions.md` (confirmed_at 2026-10-02): The decision's Consequences section says to measure whether quality held by re-running the evals for `skills/review-chain` and `skills/task-review` after redeploy.

**Check before done.**
- The decision record lists three open consequences. Codex bindings still differ by mapping only, and the Codex reviewer `model_class` still says "distinct". `correctness_scorer → coding` has no stated rationale. Old eval baselines used other models, so a score change cannot be attributed to your change alone.
- If you change a reviewer prompt, state in `### Not auto-verified` that one canary run is one sample.

**Possibly stale.**
- `docs/solutions/harness/review-model-diversity-dropped-decisions.md` is 31 days old (2026-10-02, today is 2026-11-02). All four of its `affects` paths are missing. They are `agents/runtime-bindings.json`, `scripts/render_runtime_entry.py`, `skills/correctness review/correctness-scorer-prompt.md` and `skills/intent-review/intent-reviewer-prompt.md`. A Glob for those file names under the repo, which includes `plugins/harness/`, found nothing. A name search for `runtime-bindings`, `opus-5-5` and `harness-models` outside `docs/` found only `plugins/harness/agents/task-reviewer.md`, `plugins/harness/agents/advisor.md`, `tests/scripts/task-reviewer-readonly.test.sh` and `CHANGELOG.md`. The bindings now seem to live in agent files, not in the JSON file the record names. Check `plugins/harness/agents/` for where the model and effort are set before you trust the record's file list. I did not open those agent files, so I cannot say what they pin now. I also did not check `CHANGELOG.md` for a later change to the decision.
- `docs/solutions/harness/reviewer-prompt-change-proven-by-canary-and-replay.md` has one missing `affects` path: `specs/gh-312-test-seams/canary.md`. Its other path, `skills/subagent-driven-development/task-reviewer-prompt.md`, was not found either. The record is 17 days old, and its method still applies.

**Search surface:** docs/solutions/INDEX.md, docs/solutions/critical-patterns.md, docs/solutions/harness/review-model-diversity-dropped-decisions.md, docs/solutions/harness/reviewer-prompt-change-proven-by-canary-and-replay.md. I also ran Glob and Grep over the repo for the `affects` file names and the terms `diversity`, `opus-5-5`, `runtime-bindings` and `harness-models`.
