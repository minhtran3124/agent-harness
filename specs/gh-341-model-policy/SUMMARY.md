# gh-341-model-policy — Summary

Lane: high-risk
Confidence: high
Reason: hard gate — the diff edits settings.json and the agent runtime bindings and contracts (agents/), which set the model for every dispatched role.
Flags: existing behavior, multi-domain
Affects: agents/ (bindings, contracts, three new roles), settings.json (default model), CLAUDE.md, harness-manifest.json, render_agent_definitions.py (read-only role check)
Input-type: maintenance
Route: Harness v5 epic #338, issue #341 (owner-approved roadmap)
Escalate: no

### Intent

Issue #341: "[P1] Model policy: Sonnet main, Haiku tests and research, Opus advisor".

## What changed

- `coding` now runs on Sonnet 5.5. New roles: `researcher` (Haiku 5.5), `advisor` (Opus 5.5, high effort), `intent-reviewer` (Sonnet 5.5). `test-runner` stays on Haiku.
- `settings.json` sets the default session model to `sonnet`. A `## Models` section in `CLAUDE.md` states the policy and the advisor triggers.
- Models live in `agents/runtime-bindings.json`, so role files carry no model fields.

### Rationale

Cheaper models for routine work; Opus only where judgement pays for itself.

### Alternatives considered

- Rename `coding` to `implementer` — rejected; the existing role name stays to avoid churn.
- Put model fields in the role files — rejected; the renderer forbids them.

### Deviations

- `correctness_scorer` resolves through `coding`, so its model label is now Sonnet; the golden test expectation was updated.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| agent bindings | `python3 scripts/render_agent_definitions.py --check` | 0 | |
| manifest | `python3 scripts/check_manifest.py` | 0 | |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | |
| runtime bindings | `bash tests/scripts/runtime-entry-bindings.test.sh` | 0 | |
| settings merge | `bash tests/scripts/settings-merge.test.sh` | 0 | top-level model passes through |
| settings wiring | `bash tests/scripts/settings-wiring.test.sh` | 0 | |
| deploy prune | `bash tests/scripts/deploy-prune.test.sh` | 0 | |

### Rollback

`git revert <merge-sha>`.
