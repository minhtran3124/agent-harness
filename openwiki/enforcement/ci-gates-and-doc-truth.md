---
type: enforcement mechanism
title: CI Gates and Doc-Truth Lint
description: How the harness-ci GitHub workflow enforces the harness in pull requests — the ci-strict-gate.sh block/warn tiers that demand machine-verified high-risk proof, the lint-doc-truth.sh docs-vs-code lint, the static conformance checkers (allowed-tools, frontmatter, skill tool conformance, runtime-neutral sources, slim surface, gate modes) run by run-tests.sh, the skill prompt-surface audit with its pinned skill count, and the report-only STE prose ratchet.
tags: [ci, enforcement, strict-gate, doc-truth, lint, conformance, github-actions, skill-audit, ste-ratchet]
verified:
  - by: openwiki/0.7.2
    at: 2026-10-19T07:24:11.736Z
sources:
  - id: openwiki-source-633423eb1b0995d2f1f891fd
    resource: repo://.agents/skills/asd-ste100/scripts/ste-lint.py
  - id: openwiki-source-29256446a21f0f4f404cc1a5
    resource: repo://.github/workflows/harness-ci.yml
  - id: openwiki-source-6d4b4e707b8d60b6ccfa3425
    resource: repo://.github/workflows/openwiki-update.yml
  - id: openwiki-source-993bde922338ac8a47aac520
    resource: repo://.github/workflows/post-merge-maintenance.yml
  - id: openwiki-source-991face7ae593d36af0365be
    resource: repo://harness-manifest.json
  - id: openwiki-source-f2a2a159a06a5f0448712dfb
    resource: repo://scripts/audit_skill_prompts.py
  - id: openwiki-source-dbd57945d6b656adf292554c
    resource: repo://scripts/check_frontmatter_contract.py
  - id: openwiki-source-14f3c12a95ccbb5234143f65
    resource: repo://scripts/check_gate_modes_smoke.py
  - id: openwiki-source-65f6fb5e062b019f24e1d6bb
    resource: repo://scripts/check_runtime_neutral_sources.py
  - id: openwiki-source-32da97a5633beec3ba10de0c
    resource: repo://scripts/check_skill_tool_conformance.py
  - id: openwiki-source-f3e583efaa2f0c2f268a0715
    resource: repo://scripts/check_slim_surface.py
  - id: openwiki-source-c1116bf9eaf7841fd5afafc3
    resource: repo://scripts/check_ste_baseline.py
  - id: openwiki-source-48c2466ba505053390e67f4a
    resource: repo://scripts/check-allowed-tools.sh
  - id: openwiki-source-f6029e8e0abe4e747763a2c8
    resource: repo://scripts/check-plugin-validate.sh
  - id: openwiki-source-2add3f15fa7a7ab248c7035a
    resource: repo://scripts/ci-strict-gate.sh
  - id: openwiki-source-e76d83a45d52c4eac45c3166
    resource: repo://scripts/lint-doc-truth.sh
  - id: openwiki-source-4cdfdef0ffef30122f434312
    resource: repo://scripts/resolve-base-ref.sh
  - id: openwiki-source-139b698785417c0b4c884c72
    resource: repo://scripts/run-tests.sh
  - id: openwiki-source-388207068993424e0e523749
    resource: repo://scripts/test_audit_skill_prompts.py
  - id: openwiki-source-df9059f5a2d63e386ca9e035
    resource: repo://scripts/verify_summary.py
  - id: openwiki-source-319e2a818c1af514747744a9
    resource: repo://tests/scripts/ci-strict-gate.test.sh
  - id: openwiki-source-2aac57b8dea798a14edabd6c
    resource: repo://tests/scripts/lint-doc-truth.test.sh
generated: { by: "openwiki/0.7.2", at: "2026-10-19T07:24:11.736Z" }
---

# CI Gates and Doc-Truth Lint

Local commit hooks warn by default. CI is where the harness enforces its rules strictly. The `harness-ci` workflow runs two kinds of checks:

1. **The strict gate** (`scripts/ci-strict-gate.sh`). It runs on pull requests only. When the PR diff touches gated paths, the PR must include a high-risk `SUMMARY.md` whose `### Verify` rows re-run clean.
2. **The test suite** (`scripts/run-tests.sh`). It runs on every push and PR, on Linux and macOS. Its L1 layer holds the static checks: doc-truth lint, `allowed-tools` presence, frontmatter contract, skill tool conformance, runtime-neutral sources, slim surface, the STE linter self-test and prose baseline, and others. Its pytest layer also runs the skill prompt-surface audit tests, which pin the registered skill count.

All of these checks share one design rule: **fail closed when the check cannot actually inspect anything.** If a check could not run, it must not report a pass. Many comments in these scripts describe earlier bugs where a check "passed" because its input was empty.

For the local counterpart see [Commit Gate](commit-gate.md). For the manifest that several checkers read see [Harness Manifest and Contracts](../concepts/harness-manifest-and-contracts.md). For the wider test layout see [Test Suite](../testing/test-suite.md).

## The `harness-ci` workflow

[`.github/workflows/harness-ci.yml`](../../.github/workflows/harness-ci.yml) runs on `push` to `main` and on every `pull_request`. It has two jobs:

| Job | When | Runner | What it runs |
| --- | --- | --- | --- |
| `test` | push + PR | matrix `ubuntu-latest`, `macos-latest` (`fail-fast: false`) | `tests/scripts/codex-alpha-contract.test.sh` as its own named step, then `bash scripts/run-tests.sh` with `HARNESS_SKIP_SUITES` set to that suite so it does not run twice |
| `strict-gate` | PR only | `ubuntu-latest` | `bash scripts/ci-strict-gate.sh "origin/${{ github.base_ref }}"` |

Details that matter when you change the workflow:

- **`fetch-depth: 0` is required in both jobs.** The verify-row lint in `run-tests.sh` and the strict gate both diff against a base ref. With a shallow checkout there is no base ref, and the lint once skipped on every run without anyone noticing.
- **The base ref is fetched explicitly** with `git fetch --no-tags origin "$BASE_REF"`. In `test` this happens on PRs only. The branch name is passed through `env`, not an inline `${{ }}`, so shell metacharacters in a branch name cannot be injected into the script.
- **The OS matrix is there to catch BSD/GNU differences** in the bash hooks. On macOS the job runs `brew install shellcheck`, so the shellcheck pass in `lint-skill-bash.sh` really runs in CI. Without shellcheck that script falls back to a syntax-only check.
- **The strict-gate job installs Python and pytest itself** (`actions/setup-python@v5`, then `pip install pytest`). `### Verify` rows it re-runs can call `python3 -m pytest`, and this job cannot rely on pytest already being on the runner.
- **The workflow sets no `REQUIRE_*` variables.** So in CI the strict gate's `scripts/` tier, open-question check, and SC-history check all run in warn mode. Only the hard-gate tier blocks.

## `ci-strict-gate.sh`: the strict-in-CI layer

The script states its own scope. It **verifies** that a PR touching a gated path includes at least one Verify row on a high-risk SUMMARY that is re-run and whose exit code matches. It **does not verify** that those rows actually cover the change. That is left to human review.

```mermaid
flowchart TD
  A["Start: base ref arg?"] -->|given| B{"base resolves to a commit?"}
  A -->|omitted| R{"resolve-base-ref.sh succeeds?"}
  R -->|no| SKIP["exit 0 with named skip reason"]
  R -->|yes| D
  B -->|no| F1["exit 1: refuse to report"]
  B -->|yes| D{"git diff BASE...HEAD ok?"}
  D -->|no| F2["exit 1: no merge base or diff error"]
  D -->|empty| P0["exit 0"]
  D -->|files| OQ["Shipping section: open questions"]
  OQ --> SC["SC-history section"]
  SC --> T{"tier selection"}
  T -->|"hard-gate path"| BLK["MODE=block"]
  T -->|"scripts/ non-test"| W{"REQUIRE_SCRIPTS_PROOF=1?"}
  W -->|yes| BLK
  W -->|no| WRN["MODE=warn"]
  T -->|neither| P1["exit 0"]
  BLK --> Q["find changed high-risk SUMMARYs with real Verify rows"]
  WRN --> Q
  Q --> V{"at least one passes verify_summary.py --check?"}
  V -->|yes| OK["exit 0 OK"]
  V -->|no| GF["gate_fail: exit 1 in block, exit 0 with WARN-ONLY in warn"]
```
*Control flow of `scripts/ci-strict-gate.sh`, from base-ref validation to the tiered proof requirement.*

### Base-ref validation (fail closed)

- **Explicit base** (the CI path): `git rev-parse --verify -q "${BASE}^{commit}"` must succeed. If it fails, the script exits 1 with "does not resolve to a commit". This also rejects a blob sha. In an earlier version, `bash scripts/ci-strict-gate.sh no/such/ref` exited 0 with no output, because only the fallback path was validated.
- **Omitted base**: the script calls [`scripts/resolve-base-ref.sh`](../../scripts/resolve-base-ref.sh). That script tries `VERIFY_ROWS_BASE`, then `origin/$GITHUB_BASE_REF`, then a non-self-tracking `@{upstream}`, then the nearest ancestor ref. If none of these resolve, the gate **skips** (exit 0) and prints the reason. It never guesses a branch name.
- **Diff failure**: `git diff --name-only "$BASE"...HEAD` must succeed. If there is no merge base (for example an orphan branch or a shallow fetch), or git fails for another reason, the script exits 1 (#277). An empty diff from a failed command must not pass as "nothing changed".

### Pre-tier sections (run even for specs-only PRs)

A PR that changes only `specs/` touches no gated path, so it would take the early exit 0. Two checks therefore run *before* tier selection. Neither one exits 0 itself, so a PR that also touches `hooks/` still needs proof.

- **Shipping / open questions.** A slug "ships" when `specs/<slug>/PLAN.md` is in the diff and its frontmatter reads `status: shipped` at HEAD but not at the merge base. The match ignores case and trailing whitespace, and accepts CRLF line endings. For each shipping slug the gate runs `python3 scripts/check_open_questions.py --slug <slug>`. Exit 1 under `REQUIRE_QUESTIONS_CLOSED=1` counts as a finding. Any other non-zero exit is an error in the check itself. If the checker script is missing, the gate prints a skip message. All three outcomes block only under `REQUIRE_QUESTIONS_CLOSED=1`. The awk frontmatter reader consumes its whole input on purpose: a large PLAN.md would otherwise cause a SIGPIPE, and under `pipefail` the plan would read as not shipped.
- **SC-history / goalposts.** For every slug whose `PLAN.md` or `SUMMARY.md` is in the diff, the gate runs `python3 scripts/verify_summary.py --sc-history <slug> --base <BASE>`. The gate also reads renames commit by commit, so it catches a spec directory created and then renamed on the branch. A renamed spec directory counts as an error, because the failure history recorded under the old slug is not followed. Findings and errors block only under `REQUIRE_SC_STABLE=1`. The gate strips whitespace around that value, the same way `verify_summary.py` reads it.

### Tiers

| Tier | Paths (regex) | Missing proof |
| --- | --- | --- |
| BLOCK | `HARD_GATE_RE='(^\|/)settings\.json$\|^hooks/\|(^\|/)\.claude/hooks/\|render_plan\.py$\|^templates/'` | exit 1 |
| WARN | `^scripts/`, excluding `^scripts/test_` | exit 0 with a report that includes `WARN-ONLY`. `REQUIRE_SCRIPTS_PROOF=1` promotes this tier to block |
| none | anything else (including `tests/hooks/`, `rules/`) | exit 0, silent |

- The hard-gate pattern reuses the precision pattern from the local `commit-gate.sh` `check_risk`. The `^hooks/` anchor deliberately excludes `tests/hooks/`, a known source of false positives. The `^templates/` branch exists only in CI: the SUMMARY template is read by machines, so changing it changes a contract.
- `scripts/` is gated because it holds the gate logic itself; for example, `verify_summary.py` decides what counts as evidence. It was rolled out in warn mode first, after measurement showed it would have blocked 9 of the last 80 PRs. The `scripts/test_*` exclusion applies **per file**: a test-only edit next to a real `scripts/` edit is still gated.
- `rules/` is deliberately not gated here. Rules are prose, and the `workflow-engine` signal and the review-receipt check already cover them.
- The tiers stay separate. If a diff touches both `hooks/` and `scripts/`, the hard-gate tier wins and the gate blocks.
- In warn mode `gate_fail` still prints what is missing. A warn tier that stays silent cannot be told apart from having no gate at all.

### Proof requirement

1. Candidates are the changed `specs/*/SUMMARY.md` files that exist at HEAD, match `^Lane:[[:space:]]*high-risk`, and contain at least one non-placeholder `### Verify` row. Rows are counted with `verify_summary.parse_verify_table`, so the placeholder rules are defined in one place.
2. The gate runs `python3 scripts/verify_summary.py --check <slug>` for each candidate. **At least one** must pass. A candidate that fails prints only a warning. The reason: the first-ever `specs/` commit makes every historic SUMMARY count as "changed", and old SUMMARYs whose fixtures are gone must not punish an honest PR.
3. If no candidate passes, `gate_fail` runs, and the result depends on the mode. A trivial row such as `true` counts as a forgery and blocks (DR-6), because `verify_summary.py` marks trivial rows and does not execute them. A row whose claimed exit code does not match the actual one also blocks.

## `lint-doc-truth.sh`: docs must match the tree

[`scripts/lint-doc-truth.sh`](../../scripts/lint-doc-truth.sh) turns the manual docs-vs-code audit into an automatic check. It exists because two PRs in a row (#9, #10) only repaired drift between docs and code. It runs first in L1 of `run-tests.sh`.

**Scope** is the set of docs an agent actually loads: `CLAUDE.md`, `README.md`, `HARNESS.md`, `skills/README.md`, `agents/*.md`, and `rules/*.md`. The globs use `nullglob`, so an empty `agents/` or `rules/` directory does not trigger "core doc missing". The `agents/` and `rules/` entries were added after stale `skills/xia2/PROJECT.md` pointers were found in `agents/` (#119/#121). The test suite guards against this scope shrinking again.

Checks:

1. **Markdown link targets** `](path)`: every one is checked. URLs and `#anchor` links are skipped.
2. **Backticked tokens containing `/`**: checked only when the first segment is a known repo root (`skills rules hooks docs templates agents scripts tests xia2 .github .claude`). The lint skips placeholders (`< > * { [ $ …`) and `specs/`, which is gitignored by design. It maps `.claude/x` back to its root source `x`. A path not found at the repo root is also tried as `skills/<path>` and `skills/*/<path>`.
3. **Hook table vs `settings.json`**: every `` | `name.sh` `` row in the `CLAUDE.md` table must exist in `hooks/`. A row marked ✅ must be registered in `settings.json`, and a row without ✅ must not be. Every `hooks/*.sh` file must appear in the table. Every `.hooks[][].hooks[].command` in `settings.json` (read with `jq`) must exist on disk, after stripping `$CLAUDE_PROJECT_DIR/` and `.claude/`.
4. **Derived-tree check (consumer side).** Unless `SKIP_DERIVED_LINT=1` is set, and when `python3` is available, the lint runs `scripts/deploy-harness.sh --target <tmpdir> --yes`. It then scans every deployed `.claude/**/*.md` for path-like tokens inside backtick spans that do not exist in the consumer repo. This catches docs that cite helpers which are never deployed. It also scans command spans such as `python3 scripts/x.py --flag`. A doc may cite a path that exists only in the harness repo if "harness repo" or "harness checkout" appears within the nearby lines. The fix the lint suggests is to ship the file via `CONSUMER_SCRIPTS`. If the deploy step fails, this check is skipped with a warning rather than failed.

Known limitations, stated in the script: bare tokens without a slash (such as `.mcp.json`) are caught only when written as links, and code blocks are scanned like prose. The script exits 0 with a single ✓ line, or 1 after listing every ✗.

## `run-tests.sh` layout

[`scripts/run-tests.sh`](../../scripts/run-tests.sh) is the single entry point the `test` job calls. It does not stop at the first failure: each failing step calls `fail`, which records the step name, and the run ends with either `ALL GREEN` or a `FAILURES:` list (with failing case names extracted from suite and pytest logs). The exit code is 1 if any step failed.

The L1 steps run serially, in this order:

1. `bash -n` over `hooks/*.sh`, `scripts/*.sh`, `tests/lib.sh`, and `tests/*/*.test.sh`.
2. Doc-truth lint (`lint-doc-truth.sh`).
3. Skill-bash lint (`lint-skill-bash.sh`): unbound variables in skill bash blocks, then `bash -n` and `shellcheck -S error` per runnable block.
4. Hook repo-root ratchet (`check-hook-root-source.sh`): no hook may derive the repo root from its own directory.
5. Plugin validate (`check-plugin-validate.sh`). It skips with a named reason when the `claude` CLI is absent, which is the case on CI runners today.
6. `check-allowed-tools.sh`.
7. Python manifest checkers, only if `python3` exists: `check_manifest.py`, `check_frontmatter_contract.py`, `check_skill_tool_conformance.py`, `check_gate_modes_smoke.py` (exactly `workflow-engine` and `weakening-validation` are warn-mode, and `hooks/lib/gate-modes.default.sh` matches the manifest), and `check_slim_surface.py`.
8. Runtime-neutral sources against the live tree.
9. Review-chain eval answer keys (`score_review_chain_eval.py --check-truth`), if the fixtures directory exists.
10. STE linter self-test (can fail the run) and STE prose baseline (report only). See [STE linter and prose ratchet](#ste-linter-and-prose-ratchet).
11. Verify-row lint on `specs/*/SUMMARY.md` and `PLAN.md` changed since the base ref (three-dot diff, intersected with files changed since the grandfather cutoff commit `af869a9`). A failed `git diff` is a failure, not an empty scope.

After L1, the script builds the shared pytest venv once (to avoid a venv-creation race), runs every `tests/hooks/*.test.sh` and `tests/scripts/*.test.sh` suite in parallel (`HARNESS_TEST_JOBS` sets the job count, `HARNESS_SKIP_SUITES` skips listed suites), and replays their logs in glob order. Finally it runs pytest over every `test_*.py` under `scripts/`, `runtime/`, and `skills/`, discovered with `find` rather than a hand list. `evals/` is excluded because its fixture repos contain tests that are meant to fail. The pytest step is skipped if no `python3` with pytest is available.

## Static conformance checkers

All of these run in the L1 block of [`scripts/run-tests.sh`](../../scripts/run-tests.sh). The Python checkers run only when `python3` is present. Each checker documents what it verifies and what it does not, and each owns one concern so that two checkers never report the same drift.

| Checker | Verifies | Deliberately does not verify |
| --- | --- | --- |
| `scripts/check-allowed-tools.sh` | every `skills/*/SKILL.md` frontmatter has a non-empty `allowed-tools:` (only the block between the first two `---` lines counts) | that the list is correct |
| `scripts/check_frontmatter_contract.py` | every skill and agent **registered in `harness-manifest.json`** has a frontmatter block with non-empty `name:` and `description:`, and `name:` equals the register key | description quality, `allowed-tools`, whether manifest entries exist on disk (that is `check_manifest.py`) |
| `scripts/check_skill_tool_conformance.py` | every runnable command in a skill's own prose is allowed by a declared `Bash(...)` pattern, and every mandated dispatch of a `*prompt*.md` file has `Agent` or `Task` | over-granting, natural-language write detection, end-to-end success |
| `scripts/check_runtime_neutral_sources.py` | the exact count of runtime-coupled references in the scan roots matches `specs/codex-support/neutralization-inventory.json` | — |
| `scripts/check_slim_surface.py` | the retired skills `executing-plans`, `review-diff`, `create-pr` are absent **both** from disk and from the manifest's `skills[]` | — |

### Frontmatter contract

The checker is driven by the manifest registers, not by globbing, so it needs no allowlist. `agents/README.md` and similar files are simply not registered. Its parser returns `None` for an unterminated frontmatter block instead of treating the whole file as frontmatter. It reads plain, quoted, and block scalar values (`>`/`|`) at column 0. If both registers are empty, it fails closed. Registered files that are missing are skipped quietly, because `check_manifest.py` reports those. The checker uses only the standard library. The docstring explains why it is used instead of `claude plugin validate --strict`: that tool treats every `agents/*.md` file as an agent, and CI runners do not ship it.

### Skill tool conformance

This check was added after five of nine skills shipped with too few permissions in the `allowed-tools` rollout. Presence checks passed, and `claude plugin validate` ignores tool names. Mechanics:

- **Which docs are scanned:** `SKILL.md` plus `references/*.md`, excluding files whose name contains `prompt`. Those are dispatch payloads that run under a subagent's grant. Frontmatter is blanked rather than cut off, so the reported line numbers stay correct.
- **Which commands are extracted:** lines from fenced `bash`/`sh`/`shell` blocks, unless the block contains `<` or `[optional]`, which marks it as illustrative. This is the same convention `lint-skill-bash.sh` uses. Inline backtick spans also count when they start with a command head (`python3`, `bash`, `git`, `grep`, …) or end in `.sh`/`.py`. For inline spans, only the command head, not the arguments, is tested for placeholders.
- **Matching:** the head of the command (up to the first pipe, chain, or redirect) is matched against the `Bash(...)` patterns with `fnmatch`. The match is tried both with and without `.claude/` (because the deploy step rewrites `scripts/x.py` to `.claude/scripts/x.py`), and with `bash `/`python3 ` prepended for bare scripts. A pattern ending in ` *` also matches the bare command. A bare `Bash` entry allows everything. A declared native tool (`Grep`, `Glob`, `Read`) covers `grep`/`rg`/`ls`/`cat`.
- **Exit codes:** 0 means clean, 1 means gaps were found, 2 means the check could not run (manifest missing, unparseable, not an object, or an empty skills register). `--json` prints a payload with `schema_version: 1`, `ok`, counts, and deduplicated `findings` on **every** exit path, so a machine consumer never sees empty stdout and reads it as clean.

### Runtime-neutral sources

This is a ratchet that keeps instruction sources independent of any single runtime. It scans `.md`/`.py`/`.sh` files under the inventory's `scan_roots` for four categories:

- `deployed-rule-path`: `.claude/rules/`
- `deployed-skill-path`: `.claude/skills/`
- `slash-skill-invocation`: `/<skill-name>` for the inventory's `skill_names`
- `vendor-agent-policy`: `model`/`effort`/`tools`/`disallowedTools` keys in `agents/*.md` frontmatter, or vendor model IDs such as `claude-opus-*`, `gpt-5*`, or `model: claude-*`

Every `(path, category)` pair must match the declared `count` **exactly**. Each inventory entry must also have a valid `classification` (`shared-source-violation`, `runtime-entry-binding`, `test-fixture`, `false-positive`), an `owner`, an `exit_condition`, and a path that still exists. A count that drifts in either direction fails and lists the offending lines. `run-tests.sh` runs it against the live tree on purpose, with `--root .`. When it ran nowhere in CI, a hook-test edit silently broke another phase's success criterion.

## Skill prompt-surface audit and the skill count pin

[`scripts/audit_skill_prompts.py`](../../scripts/audit_skill_prompts.py) measures the prompt text an agent can load: every skill registered in `harness-manifest.json` `skills[]`, plus every Markdown file under that skill's directory whose name contains `prompt` (a "companion prompt"). It counts lines, whitespace-delimited words, and characters. It measures repository files, not model output.

It reports a problem, and exits 1, when:

- a registered skill has no `skills/<name>/SKILL.md`;
- a `description:` in the frontmatter is longer than 1024 characters;
- a `SKILL.md` has more than 600 words (the progressive-disclosure ceiling). The message points to `docs/solutions/harness/deletion-test-for-word-ceiling.md`. A skill directory that contains `UPSTREAM.md` is vendored: it is exempt from the word ceiling (a note goes to stderr), but not from the description limit;
- a `*prompt*.md` file under `skills/` belongs to no registered skill ("unowned companion prompt").

Other modes: `--check-baseline` compares the inventory with a committed JSON and ignores the volatile `git_sha`; `--validate-inventory` checks the shape of a pinned inventory; `--compare BASELINE CANDIDATE` passes only when total words drop by at least 25%; `--write-json`/`--write-markdown` write baselines.

The script is not an L1 step. CI runs it through the pytest layer, in [`scripts/test_audit_skill_prompts.py`](../../scripts/test_audit_skill_prompts.py). That file has fixture tests for each failure mode above and one test against the real repository, `test_real_repository_matches_expected_surface_shape`. That test requires the audit to pass and pins `totals.skills == 16` and `totals.companion_prompts == 12`. **When you add or remove a registered skill, or add or remove a `*prompt*.md` companion, update these numbers in the same change.** Otherwise the pytest step fails. The current 16 entries are the manifest's `skills[]` list (for example `asd-ste100`, `harness-models`, `xia2`).

A new skill must also pass the other register-driven checkers: `check_manifest.py` (registered on disk), `check_frontmatter_contract.py` (`name:` equals the register key), `check-allowed-tools.sh`, and `check_skill_tool_conformance.py`.

## STE linter and prose ratchet

The `asd-ste100` skill ships a structural Simplified Technical English linter, `skills/asd-ste100/scripts/ste-lint.py`. It uses regex heuristics, not a dictionary. Its rules are `semicolon`, `phrasal-verb`, `marketing-adjective`, `nominalization`, `long-sentence`, `synonym-rotation`, and `dangling-conjunction` (all "hard", that is, `advisory-free`), plus `passive-voice` and `present-perfect` (advisory; they never fail a run). It never flags hedges such as may/might/could. It exits 1 when the hard count exceeds `--baseline` (default 0) and 2 on a usage error such as an unknown rule in `--disable`.

`run-tests.sh` uses it in two ways:

1. `ste-lint.py --selftest` runs the linter's built-in assertions. A failure fails the suite.
2. [`scripts/check_ste_baseline.py`](../../scripts/check_ste_baseline.py) is a **report-only ratchet**. It lints every `skills/*/*.md`, `skills/*/*/*.md`, `rules/*.md`, and `agents/*.md` file with `--json`, reads each file's `hard_count`, and compares it with `scripts/ste-baseline.json`. It prints `WARN` when a file's count rose (a file missing from the baseline has baseline 0) or a baseline entry names a deleted file, and `NOTE` when a count fell. If the linter crashes, returns bad JSON, or the baseline is unreadable, it prints `ste-baseline: skipped (<reason>)`.

The default run always exits 0, so the STE baseline never blocks CI. `--strict` exits 1 on any `WARN` or skip; only spec success criteria, task Done checks, and tests use it. `--against <ref>` reads the baseline from a git ref, and `--update` rewrites the baseline from the current tree (the two cannot be combined). The `synonym-rotation` rule is disabled in both the check and `--update`, because an experiment measured no effect for it, and a rule with a measured null must not count.

## Other workflows and CI coverage

Two other workflows exist; neither is a gate:

- `post-merge-maintenance.yml` runs on `pull_request_target` `closed` for merges into `main`, `loop`, or `simplify`. It checks out only the trusted base branch, marks a tracked spec run `shipped`, runs `scripts/bookkeeping.sh`, and opens a `chore/bookkeeping-<PR>` PR.
- `openwiki-update.yml` regenerates the wiki on a schedule and opens a PR. A PR opened with the default `GITHUB_TOKEN` triggers no `pull_request` workflow, so `harness-ci` runs on it only when `OPENWIKI_PR_TOKEN` is set. Otherwise the workflow prints a warning that the PR has no CI checks.

## Configuration summary

| Variable | Effect |
| --- | --- |
| `REQUIRE_SCRIPTS_PROOF=1` | strict gate: the `scripts/` tier blocks instead of warning |
| `REQUIRE_QUESTIONS_CLOSED=1` | strict gate: open-question findings, errors, or a missing checker block the PR |
| `REQUIRE_SC_STABLE=1` | strict gate: SC goalpost findings, errors, or spec renames block the PR |
| `VERIFY_ROWS_BASE` | first choice for the base ref in `resolve-base-ref.sh` |
| `SKIP_DERIVED_LINT=1` | doc-truth lint: skip the deploy-and-rescan check |
| `HARNESS_SKIP_SUITES` | `run-tests.sh`: space-separated suites to skip (CI uses it for the Codex contract) |
| `HARNESS_TEST_JOBS` | `run-tests.sh`: parallel suite jobs (default: CPU count; `1` runs suites serially) |

## Tests

- [`tests/scripts/ci-strict-gate.test.sh`](../../tests/scripts/ci-strict-gate.test.sh) builds throwaway git repos with a base commit and a diverging HEAD. It covers the tiers (hooks/templates block, scripts warn and its promotion, the per-file test exclusion, tiers staying separate), forgery (`true`) and mismatched rows, the "at least one passes" rule, bad or blob bases, orphan HEADs, every branch of the shipping and SC-history sections (CRLF, capitalised `Shipped`, a ~1 MB plan, non-ASCII slugs, renames, whitespace in `REQUIRE_SC_STABLE`).
- [`tests/scripts/lint-doc-truth.test.sh`](../../tests/scripts/lint-doc-truth.test.sh) guards the doc scope (`rules/`, `agents/`), placeholder skipping, the nullglob case, and out-of-scope unknown roots.
- The Python checkers have pytest companions in `scripts/test_check_*.py`. `run-tests.sh` discovers them automatically.
- [`scripts/test_audit_skill_prompts.py`](../../scripts/test_audit_skill_prompts.py) covers unowned prompts, the description and word ceilings, the `UPSTREAM.md` exemption, baseline drift, the 25% reduction rule, and the live skill/companion count pin.
- `scripts/test_check_ste_baseline.py` covers WARN/NOTE output, the always-exit-0 default, `--strict` on warnings and skips, `--against` refs, and `--update`.
