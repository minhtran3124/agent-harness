---
name: harness-models
description: Show, check, or apply the per-project model and effort settings in harness-models.json. Run `/harness-models show|check|apply`. The default mode is show.
allowed-tools: Bash(python3 scripts/apply_model_config.py *), Bash(git rev-parse --show-toplevel)
---

# Harness Models

This skill runs the model-config applier. It does not change any file itself.

## Steps

1. Read the mode from the argument. With no argument, use `show`.
2. If the mode is not `show`, `check`, or `apply`, stop. Tell the user the three valid modes.
3. Run `git rev-parse --show-toplevel`. Record the path that it prints.
4. Run the command for the mode from the table below.
   Write the recorded path in place of `<root>`, as a literal string.
   Do not use `$(...)` in the command. The tool grant matches only the literal form.
5. Give the output of the command to the user verbatim. Also give the exit status.

| Mode | Command |
|---|---|
| `show` (default) | `python3 scripts/apply_model_config.py --show --project-root <root>` |
| `check` | `python3 scripts/apply_model_config.py --check --project-root <root>` |
| `apply` | `python3 scripts/apply_model_config.py --apply --project-root <root>` |

## Notes

- `show` prints the settings that apply. `check` reports errors in `harness-models.json` and changes no file.
- `apply` is the only mid-session apply. The user runs it, so it is the user's own action.
- After `apply`, tell the user that agent changes can start to apply only from the next session.
- Do not edit `harness-models.json` from this skill. The user edits that file.
