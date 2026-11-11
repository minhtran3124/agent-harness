# Autopilot profile

The profile picks the models for one autopilot run. `${CLAUDE_SKILL_DIR}/scripts/load_profile.py` reads the plugin
default `profile.json` (next to SKILL.md), then the project override
`<checkout dir>/.claude/autopilot-profile.json` if it exists. A top-level key in the override replaces
the default one, and `stages` is merged per stage. The script prints the merged profile as JSON. On
exit 2 it names the bad file and key.

```json
{
  "orchestrator": "sonnet",
  "researcher": "haiku",
  "intake": "sonnet",
  "advisor": "opus",
  "board": true,
  "stages": {}
}
```

| Key | Allowed values | Used in |
|---|---|---|
| `orchestrator` | `sonnet`, `opus` | Check below |
| `researcher` | `haiku`, `sonnet`, `opus` | Step 2: `model` of the `researcher` call |
| `intake` | `haiku`, `sonnet`, `opus` | Step 2: `model` of the intake agent |
| `advisor` | `opus`, `fable` | Step 2 advisor call, and `advisorModel` in step 8 |
| `board` | `true`, `false` | Step 8: start the run board and open it in a browser (`false`: skip) |
| `stages` | `{ "<stage>": { "model": ..., "effort": ... } }` | Step 8: `profile: { stages }` |

## Orchestrator check

`orchestrator` is the model that should run this skill. A skill's frontmatter cannot read a file,
so the profile cannot switch the session model. Compare `orchestrator` with the model you run on.
If they differ, warn the owner once: name both models and say that `/model <orchestrator>` switches,
then go on with the current model. Do not stop the run for it.

## Stages

`stages` overrides the `workflows/ship.js` model and effort for the stages it names. A stage model is `haiku`,
`sonnet` or `opus`, and an effort is `low`, `medium`, `high`, `xhigh` or `max`. Stage names are the
keys of `MODEL` in `workflows/ship.js`, for example `review`, `intent`, `plan`, `qa` or `security`.
`workflows/ship.js` rejects an unknown stage when it starts.

Every stage can be set, `implement` and `fix` included. One rule holds whatever the profile says:
at depth L, `design` and `plan` run on Opus. Without a profile entry, `implement` runs on Opus at
depth L and on Sonnet at depth M and S (both at `medium`), and `fix` runs on Sonnet at `medium`. A
profile entry for `implement` replaces that depth rule at every depth.

## Model plan in step 7

State the orchestrator, the researcher and intake models, the advisor, and each stage the profile
overrides. Then add the defaults: Opus for design, plan and implement at depth L; implement on Sonnet
at depth M and S; fix on Sonnet at `medium`.
