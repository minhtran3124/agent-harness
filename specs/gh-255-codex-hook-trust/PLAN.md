---
slug: gh-255-codex-hook-trust
status: proposed
owner: Minh Tran
created: 2026-10-09
---

# Make Codex hook trust visible and actionable

## 1. Motivation

Issue #255 (tracking #257), stacked on #254 / PR #267. Codex runs a hook only after the user
trusts it, but the installer ends silently, the doctor reports `TRUST_UNKNOWN` without a fix, and a
missing hook helper is not named. Design: `specs/gh-255-codex-hook-trust/design.md` (installer
tail with `init-structure.sh`, doctor run, next step; `HOOK_DEPENDENCY_MISSING`; matrix text;
docs). Research: `specs/gh-255-codex-hook-trust/research-brief.md` (`doctor --json` has no trust
field at 0.147.0 or 0.162.0; app-server `hooks/list` has per-hook `trustStatus`).

## 2. Non-goals

- Wiring `hooks/list` into the doctor (follow-up issue, filed by the controller).
- Making `enforced` reachable; editing or auto-granting trust.
- Linux/WSL runtime observation; agent-profile paths (#268).
- Any change to `scripts/install-harness.sh` or Claude deploy output.

## Global Constraints

- Run `bash scripts/run-tests.sh` before the first `scripts/` edit and once after all tasks;
  record the result in SUMMARY prose, never as a Verify row.
- No step may edit trust configuration; no `codex` call made by the installer or doctor may
  change trust. An `enforced` result stays unreachable.
- Installer additions run only after a successful deploy, never under `--dry-run` or `--remove`,
  and can never make the installer exit non-zero (guarded under `set -euo pipefail`).
- Bash stays macOS 3.2 compatible; Python 3 stdlib only. Tests use the fake Codex and never touch
  the real `~/.codex` or the network.
- Verify commands are pipe-free, a single command, and finish in under 60 s.

## 3. Success Criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
| --- | --- | --- | --- |
| SC-1 | A Codex install whose project has no `verify_summary.py` (or no `runtime_mode.py`) at any hook candidate reports `HOOK_DEPENDENCY_MISSING`, mode `advisory`, and names the hook in `diagnostic_summary.hook_dependencies_missing`; a full install and a `.claude/`-only helper copy do not | `python3 -m pytest scripts/test_codex_harness_doctor.py -q -k hook_dependency` | exit 0 |
| SC-2 | The doctor's helper table equals the candidates parsed from `commit-gate.sh` and `session-knowledge.sh`, in both directions | `python3 -m pytest scripts/test_codex_harness_doctor.py -q -k hook_dependency_table` | exit 0 |
| SC-3 | Existing doctor behaviour is unchanged for a complete install (enforced fixture, exact reasons, persistence) | `python3 -m pytest scripts/test_codex_harness_doctor.py -q` | exit 0 |
| SC-4 | A fresh install runs `init-structure.sh` (creates the structure files, keeps an existing one), prints `doctor mode: <word>`, and prints the trust next step with the right doctor command for `--source` mode; a failing doctor still exits 0; `--dry-run` and `--remove` run neither; the fake Codex sees no trust-changing call and `CODEX_HOME` gains no config | `bash tests/scripts/codex-install-next-step.test.sh` | exit 0 |
| SC-5 | The capability matrix still validates, and `config.project_trust` records the source reading and the `hooks/list` exit condition | `python3 scripts/check_codex_capabilities.py specs/codex-support/capability-matrix.json` | exit 0 |
| SC-6 | Docs describe the untrusted-hook prompt and `/hooks`, the installer's new output, the files it creates, and each trust/dependency reason with its fix | `python3 -c "import pathlib,sys; t=pathlib.Path('docs/codex-alpha-install.md').read_text(encoding='utf-8'); sys.exit(0 if all(k in t for k in ('Hooks need review', '/hooks', 'HOOK_DEPENDENCY_MISSING', 'TRUST_UNKNOWN', 'HOOKS_UNTRUSTED', 'TRUST_CONFIG_ONLY', 'init-structure.sh', 'doctor mode:')) else 1)"` | exit 0 |
| SC-7 | The existing Codex install suite still passes | `bash tests/scripts/codex-install.test.sh` | exit 0 |

## 4. Tasks

### Task 1.1 — Doctor reason for a missing hook helper (wave 1)

- **Files:** scripts/codex_harness_doctor.py, scripts/test_codex_harness_doctor.py
- **Action:** Write the failing tests first, named so `-k hook_dependency` selects them and
  `-k hook_dependency_table` selects the drift test. Extend the shared `installed_project()`
  fixture with `.codex/.agent-harness/payload/scripts/verify_summary.py` and
  `.codex/.agent-harness/payload/runtime/runtime_mode.py` so existing assertions keep their
  meaning. Then add a module table `HOOK_DEPENDENCIES` mapping `commit-gate.sh` to its three
  `verify_summary.py` candidates and `session-knowledge.sh` to its three `runtime_mode.py`
  candidates (exact strings from `hooks/commit-gate.sh:168` and `hooks/session-knowledge.sh:122-124`,
  with the `$RUN_STATE_ROOT/` prefix removed). In `diagnose`, when the install reasons contain
  neither `INSTALL_MISSING` nor `MANIFEST_INVALID`, append `HOOK_DEPENDENCY_MISSING` to the
  advisory list for any hook with no candidate file under `root`, and set
  `diagnostic_summary["hook_dependencies_missing"]` to the sorted comma-separated hook names
  (key absent when nothing is missing). The drift test parses the hook scripts: the
  `for _vs_cand in …` list in `commit-gate.sh` and the `_RUNTIME_MODE=` assignments in
  `session-knowledge.sh`, matched by helper filename so `runtime/run_state.py` is ignored, and
  compares both directions.
- **Verify:** `python3 -m pytest scripts/test_codex_harness_doctor.py -q`
- **Done:** The file's tests pass, including the new `hook_dependency` cases and the drift test.
- **Criteria:** SC-1, SC-2, SC-3
- **Interfaces:** Consumes the hook scripts' candidate lists; produces `HOOK_DEPENDENCY_MISSING` and `diagnostic_summary.hook_dependencies_missing` in `scripts/codex_harness_doctor.py`.

### Task 1.2 — Installer tail: structure, doctor, next step (wave 1)

- **Files:** scripts/install-codex-harness.sh, tests/scripts/codex-install-next-step.test.sh
- **Action:** Write the new suite first, modelled on `tests/scripts/codex-install-gitignore.test.sh`
  (fake Codex, `--source "$ROOT"`), with cases: fresh install creates `specs/README.md` and
  `docs/solutions/critical-patterns.md` and keeps a pre-existing `techstacks/README.md`
  byte-identical; output has a line matching `codex-install: doctor mode: [a-z]+` and the two
  next-step lines, the second containing `python3 <ROOT>/scripts/codex_harness_doctor.py --root
  <target>`; a stub `--source` whose doctor exits 2 still installs with rc 0 and prints
  `doctor could not run`; a stub `--source` without `scripts/init-structure.sh` prints a skip
  line and rc 0; `--dry-run` creates no `specs/` and prints no `doctor mode`; `--remove` prints no
  `doctor mode`; the fake Codex log has no line containing `trust` and `<codex-home>` holds no
  `config.toml`. Then implement per `design.md` §Components 1: capture `--codex-bin`/
  `--codex-home` in their own variables too; after the `.gitignore` step and under the same
  `GI_RUN` condition, run `init-structure.sh` (guarded, skip line when absent), run the doctor
  with `--root "$TARGET_DIR" --repo-root "$SOURCE_DIR" --no-persist` plus forwarded codex flags
  (guarded), parse `mode` and `reason_codes` with `python3`, print the mode line, and print the
  next-step lines; the clone-mode doctor line is `git clone --depth 1 --branch <BRANCH>
  <REPO_URL> <dir> && python3 <dir>/scripts/codex_harness_doctor.py --root <target>`.
- **Verify:** `bash tests/scripts/codex-install-next-step.test.sh`
- **Done:** The new suite exits 0; `bash -n scripts/install-codex-harness.sh` exits 0;
  `bash tests/scripts/codex-install.test.sh` and `bash tests/scripts/codex-install-gitignore.test.sh`
  still exit 0.
- **Criteria:** SC-4, SC-7
- **Interfaces:** Consumes the source checkout's init-structure script and doctor; produces the installer tail in `scripts/install-codex-harness.sh` and `tests/scripts/codex-install-next-step.test.sh`.

### Task 1.3 — Record the trust-surface finding in the capability matrix (wave 1)

- **Files:** specs/codex-support/capability-matrix.json
- **Action:** In the `config.project_trust` row only: keep `status: unknown`,
  `evidence_level: unknown`, `source.kind: unavailable`, `evidence_path: null`, and
  `source.expires_at`; set `source.checked_at` to `2026-10-09`; replace `source.reference` with
  one sentence stating that `codex doctor --json` has no hook-trust field at 0.147.0 or 0.162.0,
  and that app-server `hooks/list` exposes per-hook `trustStatus` at both, read from source, not
  observed; replace `exit_condition` with: wire app-server `hooks/list` into the doctor after a
  live macOS capture of the Agent Harness hooks' `trustStatus`.
- **Verify:** `python3 scripts/check_codex_capabilities.py specs/codex-support/capability-matrix.json`
- **Done:** The validator exits 0 and `python3 -m pytest scripts/test_check_codex_capabilities.py -q` exits 0.
- **Criteria:** SC-5
- **Interfaces:** Consumes the research brief's upstream findings; produces the updated `config.project_trust` row in `specs/codex-support/capability-matrix.json`.

### Task 2.1 — Document untrusted hooks and the installer's new output (wave 2)

- **Files:** docs/codex-alpha-install.md
- **Action:** Add a section on hook trust: Codex runs a hook only after it is trusted; the startup
  prompt ("Hooks need review", its three choices, and that "Continue without trusting" means hooks
  won't run); `/hooks` and pressing `t`; that `codex doctor --json` cannot show trust yet, so the
  harness doctor reports `TRUST_UNKNOWN` (or `TRUST_CONFIG_ONLY`, `HOOKS_UNTRUSTED`) and stays
  `advisory`; and a reason table with what each of `TRUST_UNKNOWN`, `HOOKS_UNTRUSTED`,
  `TRUST_CONFIG_ONLY`, and `HOOK_DEPENDENCY_MISSING` means and how to clear it (the last: reinstall,
  and note the subdirectory-project limit and the `run_state.py` gap). Document the installer's
  new output (the `doctor mode:` line and the next step, including the clone-mode `git clone`
  command), and that it creates the `init-structure.sh` files outside `.codex/`, which are
  user-owned and left by `--remove`; update the "does not edit" list (around `:66`). Quote the
  installer lines exactly as implemented in `scripts/install-codex-harness.sh`.
- **Verify:** `python3 -c "import pathlib,sys; t=pathlib.Path('docs/codex-alpha-install.md').read_text(encoding='utf-8'); sys.exit(0 if all(k in t for k in ('Hooks need review', '/hooks', 'HOOK_DEPENDENCY_MISSING', 'TRUST_UNKNOWN', 'HOOKS_UNTRUSTED', 'TRUST_CONFIG_ONLY', 'init-structure.sh', 'doctor mode:')) else 1)"`
- **Done:** That check exits 0 and `bash scripts/lint-doc-truth.sh` exits 0.
- **Criteria:** SC-6
- **Interfaces:** Consumes the installer output from Task 1.2 and the reason from Task 1.1; produces the updated `docs/codex-alpha-install.md`.

## 5. Risks

- The installer's doctor call runs under `set -euo pipefail`; an unguarded failure would fail an
  otherwise successful install. Guarded and tested with a failing stub doctor.
- The drift test parses Bash text; a restructured hook loop needs the parser updated (the test
  fails loudly rather than passing silently).
- Trust UX is read from 0.147.0 TUI snapshots, not observed.

## 6. Status Log

- 2026-10-09 — plan written from the approved design and research brief.
