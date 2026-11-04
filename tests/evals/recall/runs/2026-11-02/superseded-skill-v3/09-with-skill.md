Verdict: existing decision

**Already decided.**
- `docs/solutions/harness/review-model-diversity-dropped-decisions.md` (confirmed_at 2026-10-02): the user chose `claude-opus-5-5` at `medium` effort for the reviewer and task-reviewer roles. The user also dropped the rule that review must use a different model than the implementer, for every runtime. Review independence now comes from fresh context per pass, read-only reviewer bindings and plan-blindness. If you want to bring the diversity rule back, you are reversing this decision. Options already rejected: Sonnet 5.5 reviewers, moving `coding` off Opus 5.5, a per-runtime `model_diversity` flag, and downgrading the checks to warnings.

**Check before done.**
- After you change the pins, re-run the evals in `skills/review-chain` and `skills/task-review`. The record says this is how you measure whether review quality held. Earlier baselines used other models, so a difference is not attributable to your change alone.

**Possibly stale.**
- `docs/solutions/harness/review-model-diversity-dropped-decisions.md` is 33 days old (confirmed 2026-10-02, today 2026-11-04). None of its `affects` paths exist under `plugins/harness/`: `agents/runtime-bindings.json`, `scripts/render_runtime_entry.py`, `correctness-scorer-prompt.md` and `intent-reviewer-prompt.md`. A name search also found no `runtime-entry-bindings.json` and no `harness-models.json`. The decision itself still holds. `plugins/harness/agents/task-reviewer.md` still pins `model: claude-opus-5-5` and `effort: medium`. The pins seem to live in agent frontmatter now, so find where the reviewer and intent-reviewer pins live before you edit. I did not find the intent-reviewer pin.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/review-model-diversity-dropped-decisions.md`, `plugins/harness/agents/task-reviewer.md`. I also searched the repo by name and content for the `affects` paths and for `diversity`, `opus-5-5` and `harness-models`.
