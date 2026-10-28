# Repository Guidelines

This repository is a Claude Code skills framework with a thin workflow harness. Root `CLAUDE.md`,
`HARNESS.md` and `skills/README.md` describe the workflow and the component inventory; treat them
as contracts when you change a hook, a skill or a script.

## Layout

- `skills/<name>/SKILL.md` - the skills, with their prompts, templates and scripts.
- `agents/` - subagent role definitions and `PROJECT.md` (test command and conventions index).
- `hooks/` - three Bash hooks: secrets scan on commit, PR-opened reminder, merged-worktree cleanup.
- `rules/behavior.md` - the one behavioral rule.
- `workflows/ship.js` - the autonomous Workflow script that `/autopilot` launches.
- `templates/structure/` - scaffold files that `scripts/init-structure.sh` copies into a consumer repo.
- `scripts/` - deploy, install, lint and validation utilities, plus their `test_*.py` unit tests.
- `adapters/` - runtime-entry bindings. `techstacks/` - project-owned stack profile, empty here.
- `tests/hooks/`, `tests/scripts/`, `tests/workflows/` - contract and integration tests.
- `docs/` - solutions, ADRs and research. `specs/` is local scratch and gitignored.

## Commands

- `bash scripts/run-tests.sh` - the CI-equivalent suite. Run it before you change `hooks/` or `scripts/`.
- `bash scripts/deploy-harness.sh` - rebuild the derived `.claude/` after editing a source file.
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
