# Repository Guidelines

This repository is a Claude Code skills framework with a thin workflow harness. Root `CLAUDE.md`,
`HARNESS.md` and `plugins/harness/skills/README.md` describe the workflow and the component inventory; treat them
as contracts when you change a hook, a skill or a script.

## Layout

- `plugins/harness/` - the plugin (name `harness`). `.claude-plugin/marketplace.json` at the repo root lists it.
- `plugins/harness/skills/<name>/SKILL.md` - the skills, with their prompts, templates and scripts.
- `plugins/harness/agents/` - the six subagent role files (model, effort and tools are in their frontmatter).
- `agents/` - this repo's own `PROJECT.md` (test command and conventions index) and a note on the agents.
- `plugins/harness/hooks/` - `hooks.json` plus four Bash hooks: rule delivery at session start, secrets scan on commit, PR-opened reminder, merged-worktree cleanup.
- `plugins/harness/rules/behavior.md` - the one behavioral rule.
- `plugins/harness/workflows/ship.js` - the autonomous Workflow script that `/harness:autopilot` launches.
- `plugins/harness/templates/structure/` - scaffold files that `plugins/harness/scripts/init-structure.sh` copies into a consumer repo.
- `plugins/harness/scripts/` - the runtime scripts (`init-structure.sh`, `write_adrs.py`, `rebuild_solution_index.py`).
- `scripts/` - lint and validation utilities for this repo, plus their `test_*.py` unit tests.
- `techstacks/` is a consumer folder that `/harness:setup` scaffolds; this repo has none.
- `tests/hooks/`, `tests/scripts/`, `tests/workflows/` - contract and integration tests.
- `docs/` - solutions, ADRs and research. `specs/` is local scratch and gitignored: one `specs/<slug>/` per ticket with `intent.md`, `design.md`, `decision.md`, `plan.md` and `summary.md`.

## Commands

- `bash scripts/run-tests.sh` - the CI-equivalent suite. Run it before you change `plugins/harness/hooks/` or `scripts/`.
- `claude --plugin-dir plugins/harness` - load the plugin from the checkout (no copy step).
- `bash scripts/lint-doc-truth.sh` and `bash scripts/check-md-links.sh` - check documented paths and links.

## Style and tests

Bash uses two-space indentation, quoted variables and `set -u`. Python uses four spaces and `ruff`.
CI runs on ubuntu and macOS, so avoid bash 4 features and GNU-only flags. Name skills and
directories in lowercase kebab-case. Add or update a focused test with every behavior change; shell
tests run in a throwaway git repo.

## Commits and pull requests

Use Conventional Commit subjects (`fix(hooks): ...`, `docs: ...`). Keep commits focused. A pull
request states the workflow impact, the tests run and the linked issue. Never merge a pull request
without human review.
