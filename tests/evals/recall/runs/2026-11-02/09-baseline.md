**No, don't require review to use a different model from the implementer.** You dropped that rule on 2026-10-02, and nothing in the files I read suggests bringing it back. I recommend running both review roles on Opus 5.5 at `medium`. I changed nothing, because you didn't name target values and this branch is for #556.

## Why no diversity rule
`docs/solutions/harness/review-model-diversity-dropped-decisions.md` records the decision. Review independence comes from fresh context, read-only reviewers and plan-blindness, not from the choice of model.

Part of that record is out of date, though the decision itself still stands:
- **Age:** it is 31 days old, past the repo's 30-day staleness line.
- **Named files:** `runtime-bindings.json`, `runtime-entry-bindings.json` and `render_runtime_entry.py` no longer exist (repo-wide glob).
- **Model claim:** it says the implementer and reviewers all use Opus 5.5, but the implementer is now on Sonnet 5.5.

## Current settings

| Role | Model | Effort | Where it is set |
|---|---|---|---|
| Implementer | Sonnet 5.5 | medium | `plugins/harness/agents/implementer.md`, `ship.js:19-22` |
| Correctness review (`ship.js` runs `/code-review`) | Sonnet 5.5 | medium | `MODEL.review`, `EFFORT.review` at `ship.js:19-22` |
| Intent reviewer | Sonnet 5.5 | medium | model in `intent-reviewer.md:5`; `ship.js:1012` passes `EFFORT.review` |
| `task-reviewer` | Opus 5.5 | medium | `task-reviewer.md:5-6` |

## Recommendation
Set `MODEL.review` to `'opus'` and `intent-reviewer.md:5` to `claude-opus-5-5`, and keep effort at `medium`. You chose Opus 5.5 at `medium` for review on 2026-10-02, but the correctness review and intent reviewer are on Sonnet, and I couldn't find out why. The change would also put review on a different model from the implementer, without needing a rule.

- **Evidence gap:** the record compares Opus 5.5 with Opus 5, not with Sonnet 5.5. The quality gain is my expectation, not a measured result.
- **Cost:** it will go up, because review runs per ticket and for the final branch.

## Before you edit
- **Shared effort setting:** `EFFORT.review` drives both the correctness and intent passes in `ship.js`. To set them separately, add a new `EFFORT` key and use it at line 1012. `effort` in `intent-reviewer.md` may not apply on that path, but I didn't read `call()` to confirm it.
- **No `reviewer` agent here:** `plugins/harness/agents/` has only `task-reviewer` and `intent-reviewer`. The `reviewer` in this session's agent list comes from outside this directory, so editing it won't affect `ship.js`.
- **`task-reviewer` is pinned by a test:** `tests/scripts/task-reviewer-readonly.test.sh:14` requires `claude-opus-5-5`, so changing its model means updating that test. The only dispatch I found is in `diagnosing-bugs`.
- **`harness-models.json` is not in this repo:** PR #332 planned it, but the glob found nothing. Edit the files above directly.
- **Docs to update:** `CLAUDE.md:16` says intent review runs on Sonnet 5.5, and the record's Consequences section needs correcting.

## Not checked
The `git log` command to find when the review stage moved to Sonnet was blocked pending approval. If that move was a deliberate cost decision, it weighs against this recommendation.
