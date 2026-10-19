# Repository Guidelines

## Project Structure & Module Organization

This repository is a Claude Code skills framework and workflow harness. The main editable sources are:

- `skills/<name>/SKILL.md` — invocable skill instructions and related prompts/scripts.
- `agents/` — sub-agent role definitions.
- `hooks/` — Bash hooks that enforce workflow and commit checks; `hooks/lib/` contains shared helpers.
- `rules/` and `templates/` — governance rules and generated-artifact templates.
- `scripts/` — deployment, installation, linting, and validation utilities.
- `runtime/` — Python run-state engine (FSM, storage primitives, CLI); synced into `.claude/runtime/` by the deploy script.
- `adapters/` — generated Codex advisory-alpha adapter inputs and runtime-entry bindings; not a Claude runtime path.
- `techstacks/` — project-owned stack profile read by `rules/architecture.md` and `rules/guidelines.md`; intentionally near-empty in this meta-repo.
- `tests/hooks/` and `tests/scripts/` — shell contract and integration tests.
- `scripts/test_*.py`, `runtime/test_*.py`, and `test_*.py` files under `skills/` — Python unit tests.
- `docs/`, `specs/`, and `evals/` — knowledge, change artifacts, and evaluation fixtures.

The root `CLAUDE.md`, `HARNESS.md`, `skills/README.md`, and `harness-manifest.json` describe the supported workflow and component inventory. Treat them as contracts when changing hooks, skills, or schemas.

## Build, Test, and Development Commands

- `bash scripts/run-tests.sh` — run the CI-equivalent suite: Bash syntax checks, documentation/manifest linting, the STE linter self-test, shell tests, and Python tests when `pytest` is available.
- `bash scripts/deploy-harness.sh` — rebuild the local derived `.claude/` installation after editing source skills, agents, hooks, rules, templates, runtime, or settings.
- `bash scripts/lint-doc-truth.sh` — verify documented paths and hook registrations independently.
- `python3 -m pytest $(find scripts runtime skills -name 'test_*.py' -not -path '*/__pycache__/*') -q` — run the Python unit tests directly. `scripts/run-tests.sh` collects the same list into `PYTESTS` with this `find`.

Before changing `hooks/` or `scripts/`, run the full test command. Keep generated `PLAN.html` artifacts local; they are rebuildable and should not be committed.

## Coding Style & Naming Conventions

Use two-space indentation in Bash and four spaces in Python. Keep shell scripts POSIX-conscious where practical, quote variables, use `set -u`/explicit error handling, and prefer clear exit statuses. Python follows standard `ruff` formatting/linting. Name skills and directories in lowercase kebab-case; use `SKILL.md`, `README.md`, and descriptive lowercase script names consistently. Preserve Markdown heading structure and fenced command examples.

## Testing Guidelines

Add or update a focused test in `tests/hooks/`, `tests/scripts/`, or the relevant Python test module when behavior changes. Shell tests should exercise the script’s stdin/environment contract in an isolated temporary Git repository. Run `bash scripts/run-tests.sh` before submitting changes.

## Commit & Pull Request Guidelines

Use concise Conventional Commit-style subjects, for example `fix(hooks): ...`, `docs(specs): ...`, or `feat(skills): ...`. Keep commits focused. Pull requests should explain the user-visible or workflow impact, identify tests run, link the related issue/spec when applicable, and include screenshots or rendered artifacts only when documentation or visual output changed. Never merge a pull request from the contributor branch without human review.

<!-- OPENWIKI:START -->

## OpenWiki

This repository has a generated `openwiki/` evidence index. It is optional just-in-time context, not required startup reading.

- Do not enumerate, preload, or search wikis at task start. Use retrieval when the user asks for it, when unfamiliar architecture or dependency behavior materially affects the task, or when source inspection leaves an important uncertainty. Stop once the question is grounded.
- When those conditions apply and OpenWiki retrieval tools are available, use `openwiki_search` for just-in-time context and `openwiki_read` for the relevant complete sections. If search returns `workspace_required`, ask which listed workspace to use and retry with its ID.
- Use `openwiki_list_workspaces` or `openwiki_list_wikis` when workspace membership itself needs to be discovered.
- If the retrieval tools are unavailable, read `openwiki/quickstart.md` and follow its links to the relevant pages.
- Treat source code and tests as authoritative. A brief's unknowns and review items are verification gaps, not automatic requirements.
- Prefer the narrowest quiet validation that proves the changed behavior. Preserve complete failure output.

The scheduled OpenWiki GitHub Actions workflow refreshes the repository wiki. Do not hand-edit generated OpenWiki pages unless explicitly asked; prefer updating source code/docs and letting OpenWiki regenerate.

<!-- OPENWIKI:END -->
