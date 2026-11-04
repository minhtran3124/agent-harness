Verdict: existing decision. The old rule that review must use a different model than the implementer was dropped on 2026-10-02. Only some of that decision's file paths still exist.

**Already decided.**
- `docs/solutions/harness/review-model-diversity-dropped-decisions.md` (confirmed_at 2026-10-02, 33 days old): the user chose `claude-opus-5-5` at `medium` for both the `reviewer` and `task-reviewer` roles. The "reviewer model differs from implementer model" rule was dropped for every runtime. Review independence now comes from three things: a fresh context per pass, reviewer bindings that are read-only by structure, and plan-blindness. The record cites Anthropic's Opus 5.5 guidance as the reason: Opus 5.5 at `medium` beats Opus 5 at `high` on code review.

**Do first.**
1. Treat "should review use a different model than the implementer?" as already answered: no, and nothing should enforce it (`docs/solutions/harness/review-model-diversity-dropped-decisions.md`, confirmed_at 2026-10-02). Reopen it only if you are deliberately reversing that decision. In that case, reintroduce the check consciously, because the record rejected a per-runtime `model_diversity` flag and downgrading the check to warnings.
2. After you change a model or effort, re-run the review evals to see whether quality held (same record, 2026-10-02): `evals dir: skills/review-chain` and `evals dir: skills/task-review`. Earlier baselines used other models, so a difference is not attributable to your change alone. I did not check whether those eval directories still exist under `plugins/harness/skills/`.

**Check before done.**
- Change the model and effort in all the places that pin a review role. Today the agent files pin these values:
  - `task-reviewer`: `claude-opus-5-5`, `medium`.
  - `intent-reviewer`: `claude-sonnet-5-5`, `medium`.
  - `implementer`: `claude-sonnet-5-5`, `medium`.
- The intent reviewer already uses the same model as the implementer, which fits the "no diversity" decision.
- Effort, not prompt wording, is the thinking control, per the record's context.

**Possibly stale.**
- The record's `affects` paths do not exist at those locations: `agents/runtime-bindings.json`, `scripts/render_runtime_entry.py`, `skills/correctness review/correctness-scorer-prompt.md` and `skills/intent-review/intent-reviewer-prompt.md`. I searched by file name and found none of them in the repo. The related `adapters/runtime-entry-bindings.json` is also absent, and a grep for "diversity" or "distinct" in `*.py` and `*.json` found no enforcement code.
- Model and effort now live in the frontmatter of `plugins/harness/agents/*.md`. The record's advice about editing the bindings file and the render script is out of date.
- The principle itself still holds: nothing enforces diversity, and independence rests on context and blindness.
- The record's Consequences describe the old state: scorer, finders, intent reviewer and implementer all on `claude-opus-5-5`. That is no longer true, because the implementer and intent reviewer are now `claude-sonnet-5-5`. The record's rationale for the Opus 5.5 `medium` choice may need checking against the current setup before you rely on it.
- The record is 33 days old, which is over the 30-day threshold.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/review-model-diversity-dropped-decisions.md`. I also ran a Grep over `*.py` and `*.json` for "diversity|distinct", a Grep of `plugins/harness/agents` for `^(model|effort):`, and file-existence checks with ls and find.
