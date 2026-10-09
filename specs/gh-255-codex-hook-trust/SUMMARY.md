# gh-255-codex-hook-trust — Summary

Lane: high-risk
Confidence: high
Reason: the installer and the doctor decide the enforcement claim a Codex user sees (`enforced` / `advisory` / `unsupported`); the change also runs `init-structure.sh` against consumer repos from the installer (existing behavior, cross-platform).
Flags: audit/security, existing behavior, cross-platform, public contracts
Affects: `scripts/install-codex-harness.sh`, `scripts/codex_harness_doctor.py`, `specs/codex-support/capability-matrix.json` + `evidence/`, `docs/codex-alpha-install.md`
Input-type: spec slice
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> current the hook scripts are not available with codex
> and the claude code now support AGENTS.md file
> let review and checking if we can support user with codex if they want to install our harness-skill

> writing plan to the github first with seperate to each section with detail purpose and target
> after that, start for item 1 first

> approve design
> notes: - to avoid any breaking on main, let create branch call "codex" - all PRs related to it, let open to codex branch

> do for next step after this PR, continue based on it

> ok, let check sub-agent profile issue. and go to next phase 6 itme

"The next phase 6 item" after #254 is item 3, GitHub issue #255 ("Codex Phase 6.3: make hook
trust visible and actionable"). Its Target checklist is the scope of this slug. The sub-agent
profile check was done separately and filed as #268. The branch stacks on
`feat/gh-254-codex-agents-md-rules` (PR #267), because both items edit
`docs/codex-alpha-install.md` and the installer; the PR targets `codex`.

## What changed

A Codex install now ends by telling the user where trust stands and what to do. After a
successful deploy (never under `--dry-run`/`--remove`, never failing the install), the installer
runs `init-structure.sh`, runs the harness doctor once with `--no-persist` and prints
`codex-install: doctor mode: <mode> (<reasons>)`, then prints the next step: start Codex, choose
"Review hooks" (or `/hooks`, `t`), and re-run the doctor (with a paste-safe `git clone` line in
the default clone mode). The doctor names a missing hook helper as the advisory reason
`HOOK_DEPENDENCY_MISSING` and lists the hooks in `diagnostic_summary`. The capability matrix
records that `codex doctor --json` has no trust field at 0.147.0 or 0.162.0 and that app-server
`hooks/list` exposes per-hook `trustStatus` (follow-up #269). `docs/codex-alpha-install.md`
explains the untrusted-hook prompt, `/hooks`, each trust and dependency reason with its fix, and
the installer's new output.

### Rationale

The user chose visibility now and `hooks/list` later: no Codex input available to the doctor
carries observed hook trust, and `hooks/list` reports approval rather than an observed run and
could not be captured live here. Making the state visible and naming the fix removes the silent
failure without claiming enforcement. A missing helper is `advisory` (user choice) because the
adapter still works with one guarantee gone.

### Alternatives considered

- Wire app-server `hooks/list` into the doctor now — deferred by the user to #269 (needs a live
  macOS capture; trust approval is not an observed run).
- Install Codex on this host to capture `hooks/list` first — not chosen; Linux results cannot
  unlock `enforced` anyway (`PLATFORM_UNVERIFIED`).
- Missing helper as `unsupported` — rejected by the user; a damaged payload would read as an
  unusable install.
- A new evidence fixture for the source reading — rejected: the validator's closed capture
  vocabulary exists to stop hand-authored fixtures; the finding lives in the matrix row text.

### Deviations

- none

### Task review log

- Task 1.3 (`6795c61`): spec pass, quality approved, no findings.
- Task 1.1 (`d5ba42b`): spec pass, quality approved. Minor M1: the `MANIFEST_INVALID` skip of
  the helper check is untested (only `INSTALL_MISSING` is); M2: the drift test compares
  candidate tuples, so a pure reorder in a hook fails it (order decides which helper a hook
  picks, so strictness is defensible).
- Task 1.2 (`50f947f`): spec pass, quality approved. Minor M3: clone-mode next step printed a
  literal `<dir>` (not paste-safe); M4: the no-trust-call assertion ran before the later
  installs; M5: the could-not-run line hid the doctor's exit. All three fixed in `774e595`.
- Task 2.1 (`ca0a2b2`): spec pass, quality approved. Minor M6 (doc says the mode line can read
  `unsupported`, but a non-zero doctor exit prints "could not run"): refuted — the doctor exits 0
  for `unsupported` too and returns 2 only on input errors (`codex_harness_doctor.py` `main`).
  M7: the reason-table meanings were not checked by the task reviewer; forwarded to the final
  correctness review.

Full suite: `bash scripts/run-tests.sh` was ALL GREEN before the first `scripts/` edit and after
all four tasks (836 pytest passed); cited here, not as a Verify row.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 scripts/verify_summary.py --lane gh-255-codex-hook-trust` | 0 | intake |  |
| missing hook helper reason | `python3 -m pytest scripts/test_codex_harness_doctor.py -q -k hook_dependency_missing` | 0 | 5 tests: one or both helpers missing named; full and `.claude/`-only installs clean; unreadable directory counts as absent; missing install and invalid manifest not evaluated | SC-1 |
| helper table drift | `python3 -m pytest scripts/test_codex_harness_doctor.py -q -k hook_dependency_table` | 0 | drift test parses both hooks; order-sensitive | SC-2 |
| doctor suite | `python3 -m pytest scripts/test_codex_harness_doctor.py -q` | 0 | 21 doctor tests, fixture ships payload helpers | SC-3 |
| installer tail | `bash tests/scripts/codex-install-next-step.test.sh` | 0 | 14 cases incl. stub doctor exit 2 and exit-0-unparseable, missing init-structure, dry-run, remove, clone mode, exported CODEX_BIN, quoted path with flags, relative --codex-bin, no trust call | SC-4 |
| capability matrix valid | `python3 scripts/check_codex_capabilities.py specs/codex-support/capability-matrix.json` | 0 | matrix validates | SC-5 |
| docs content | `python3 -c "import pathlib,sys; t=pathlib.Path('docs/codex-alpha-install.md').read_text(encoding='utf-8'); sys.exit(0 if all(k in t for k in ('Hooks need review', '/hooks', 'HOOK_DEPENDENCY_MISSING', 'TRUST_UNKNOWN', 'HOOKS_UNTRUSTED', 'TRUST_CONFIG_ONLY', 'init-structure.sh', 'doctor mode:')) else 1)"` | 0 | required facts present | SC-6 |
| codex install suite | `bash tests/scripts/codex-install.test.sh` | 0 | 38 cases | SC-7 |
| trust row recorded | `python3 -c "import json,sys; r=[c for c in json.load(open('specs/codex-support/capability-matrix.json'))['capabilities'] if c['id']=='config.project_trust'][0]; s=r['source']; sys.exit(0 if (s['checked_at']=='2026-10-09' and 'hooks/list' in s['reference'] and 'hooks/list' in r['exit_condition'] and r['status']=='unknown' and s['kind']=='unavailable') else 1)"` | 0 | trust row content | SC-8 |
| .gitignore suite unchanged | `bash tests/scripts/codex-install-gitignore.test.sh` | 0 | 14 cases |  |

### Context-Propagation Audit

Not run: the diff touches no workflow-engine surface (`skills/*/SKILL.md`, dispatch prompts,
`agents/*.md`, `rules/*.md`; `resolve_finish_context.py` reports
`context_propagation_audit_required: false`), and #255 does not request one.

### Correctness Review

Six FIND angles over `5382f3a..22f6d78`, 8 deduplicated locations, one independent scorer each,
threshold 75.

- **H (75) — fixed in `b2d874c`.** The docs said the installer writes "only two things" outside
  `.codex/`; the root `AGENTS.md` managed section is a third.
- **Fixed anyway in `b2d874c` (scored 50; introduced by this diff, one-line fixes):**
  A — the installer's new `CODEX_BIN=""` blanked an exported `CODEX_BIN` before the deploy read
  it (reproduced; renamed `CODEX_BIN_ARG`); B — the printed doctor command was unquoted and
  dropped `--codex-bin`/`--codex-home`; C — `Path.is_file()` raised `PermissionError` on an
  unreadable directory and crashed the doctor (now `os.path.isfile`, like the hooks' `[ -f ]`);
  F — a relative `--codex-bin` broke the doctor's `cwd=<target>` call (made absolute); G — an
  exit-0 unparseable doctor output printed "could not run (exit 0)"; I — the `TRUST_UNKNOWN` doc
  row omitted the declined-to-parse case. New regression tests fail on the pre-fix code.
- Fix re-review of `b2d874c`: `fix_verdict: closed`; two P3 notes (no test for G; a doc phrase on
  bare `--codex-bin` names) fixed in the next commit.

### Advisory Findings

- C, first half (50) — the doctor probes helpers under `--root`, while the hooks resolve
  `CLAUDE_PROJECT_DIR` or the git top level; a project in a subdirectory of a repo can read clean
  while the hooks find nothing. Documented as a known limit in the design and the docs.
- J (0, unmodified line) — `runtime_mode.context_line` cuts reason codes at 6 without a marker;
  `HOOK_DEPENDENCY_MISSING` takes a slot and can push a `TRUST_*` reason off the session line.
- A persisted runtime-mode record does not notice a later deletion of a helper that lives outside
  the payload (`.claude/`), because `install_hash` covers only manifest-owned files; the cached
  mode shows until the doctor is re-run.
- An exported `CODEX_HOME` (no `--codex-home`) is not echoed into the printed command; the
  follow-up relies on the shell still exporting it (unchanged behaviour).

### Intent Findings

Plan-blind intent review over `5382f3a..8ccaa9f`: 0 gaps; #269 confirmed open.

- Drift (advisory): the "no trust field" finding is recorded in the `config.project_trust`
  reference and the research brief, not as a file under `evidence/` — the evidence validator's
  closed capture vocabulary rejects a hand-authored fixture, and the finding came from source,
  not a run. A captured `doctor --json` at 0.162.0 would need a host with Codex (see #269).
- Drift (advisory): `runtime/run_state.py` (session-knowledge active-runs, informational) is not
  in `HOOK_DEPENDENCIES`; it is root-only and so always absent under Codex; disclosed in the docs.
- Drift (equivalent): in clone mode the printed doctor command clones first, because the
  temporary clone is deleted; the issue's literal `python3 scripts/codex_harness_doctor.py`
  path would not exist.
- Excess (report-only): the printed command carries `--codex-bin`/`--codex-home` and is
  shell-quoted (correctness-review fixes B/F).

### Not auto-verified

- Codex's untrusted-hook UX (the "Hooks need review" prompt, `/hooks`, `t`) as documented —
  reached provenance (read from `codex-rs/tui` source and snapshots at `rust-v0.147.0`); not
  observed in a live session (no `codex` on this host).
- `doctor --json` has no trust field at 0.162.0, and `hooks/list` exposes `trustStatus` — reached
  provenance (source at both tags); not run.
- The installer's doctor line against a real Codex — reached traceability (the fake Codex answers
  `{"ok":true}`, so tests assert only the line's shape).

### Rollback

- Code: `git revert` the branch's commits, or close the PR unmerged; nothing reaches `codex` until merge.
- Consumers: re-run `bash scripts/install-codex-harness.sh --source <pre-#255 checkout>`; the installer's next-step text and `init-structure.sh` call disappear, and directories `init-structure.sh` created stay (it only creates, never deletes).

### Harness-Delta

- backlog — plan Verify commands use bare `python3 -m pytest`, which fails where system python3
  lacks pytest (here; the suite uses `/tmp/harness-tests-venv`). Plans should name the
  interpreter, or `run-tests.sh` should expose a targeted entry point.
- backlog — `scripts/lint-doc-truth.sh` does not scan `docs/codex-alpha-install.md`, so a stale
  path in the user-facing install doc would not fail CI.
