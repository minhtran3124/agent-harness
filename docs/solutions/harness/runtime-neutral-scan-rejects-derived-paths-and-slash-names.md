---
problem_type: knowledge
module: harness
tags: [runtime-neutral, codex-alpha, skill-authoring, deployed-skill-path, slash-skill-invocation, glob-pattern, neutralization-inventory, skill-script-path]
severity: standard
applicable_when: You write or plan prose under skills/, rules/, agents/ or templates/ that names a skill's own script, the derived .claude/ tree, or a path or glob containing a registered skill name.
affects:
  - scripts/check_runtime_neutral_sources.py
  - specs/codex-support/neutralization-inventory.json
  - tests/scripts/runtime-entry-bindings.test.sh
supersedes: null
confidence: high
confirmed_at: 2026-10-16
---
## Applicable When

You write or plan prose in a scanned root (`agents`, `rules`, `skills`, `templates`, plus the
files named in the inventory's `scan_roots`). The prose names one of these:

- a skill's own script
- a path in the derived `.claude/` tree
- a path or glob that contains a registered skill name

The checker also scans the `.py` and `.sh` files under those roots.

## Pattern

`scripts/check_runtime_neutral_sources.py` records a finding for each line that does one of these
things. The inventory must declare every finding, and
`tests/scripts/runtime-entry-bindings.test.sh` requires the live `findings` list to be empty.
So each match is a CI failure, and you cannot waive it.

- **`deployed-skill-path`**: the line contains the substring `.claude/skills/`. A SKILL.md that
  names its script by the deployed path fails, even though that path resolves in consumers.
- **`deployed-rule-path`**: the line contains `.claude/rules/`.
- **`slash-skill-invocation`**: a `/` comes directly before a name in the inventory's
  `skill_names`. The character before that `/` is not a letter, digit, `_`, `.`, or `\`. So
  `skills/onboarding/...` passes, because `s` comes before the `/`. A glob such as
  `**/onboarding/...` fails, because `*` comes before the `/`.

The slash rule fires only for names in `skill_names`. A new skill becomes protected only when the
skill's registration adds it to that list. After that, any older text with `/<name>` fails.

## How to Use

- To let a skill name its own script, write the path relative to the skill's directory:
  `<skill directory>/scripts/<script>`. The skill directory is the base directory that the
  runtime reports when it loads the skill. Claude Code prints that line for each skill it loads.
  The other way is a source path such as `skills/<name>/scripts/<script>` plus a rewrite pattern in
  `scripts/deploy-harness.sh` `rewrite_derived_paths`, as the asd-ste100 linter uses. That way
  changes a deploy script.
- In a glob, put a path segment before the skill name: `**/skills/<name>/...`, never
  `**/<name>/...`.
- When a new skill registers in `skill_names`, grep the scan roots for `/<name>` first.
- Check a candidate line with the checker's own `_slash_pattern` before you put it in a plan.
  Then run `python3 scripts/check_runtime_neutral_sources.py --root .`. Exit 0 is the proof.

## Gotchas

- Research and design for the onboarding skill chose the deployed path (design D8) and the glob
  `**/onboarding/...`. Both pass the tool-conformance check and fail this scan. Only plan review
  found them (design DC3). Two independent checks read the same line under different rules, and
  passing one tells you nothing about the other.
- `specs/` is not a scanned root. A plan or design can quote a failing form as a counter-example
  without tripping the check.
- The deploy rewrite covers only named paths, `scripts/<CONSUMER_SCRIPTS>`, `render_plan.py`, and
  the asd-ste100 linter. Do not assume that a new `skills/<name>/scripts/...` mention is
  rewritten for consumers.
