---
slug: gh-255-codex-hook-trust
status: approved
issue: 255
tracking: 257
depends_on: 253, 254
---

# Make Codex hook trust visible and actionable — Design

## Purpose

The Codex plugin registers three hooks (`adapters/codex/plugin/hooks/hooks.json`), but Codex runs a
hook only after the user trusts it. Today the installer ends without saying so, the doctor reports
`TRUST_UNKNOWN` without saying how to fix it, and nothing names a missing hook helper as such (a
deleted `verify_summary.py` shows only as `INSTALL_HASH_MISMATCH`). Users reasonably conclude
"hooks don't work with Codex". This item makes the trust state and the hooks' own dependencies
**visible and actionable, never silent**, without editing any trust choice.

## Facts this design rests on

- `codex doctor --json` carries no hook-trust field in 0.147.0 (pinned evidence) or in the latest
  stable 0.162.0 (`codex-rs/cli/src/doctor.rs` at `rust-v0.162.0`; only a "startup warning hooks"
  count and a `[features].codex_hooks` deprecation note). Read from source, not run.
- Codex's app-server protocol has `hooks/list` (`HooksListParams { cwds }` →
  `HooksListResponse`) in both 0.147.0 and 0.162.0. Each `HookMetadata` carries `trustStatus`
  (`managed | untrusted | trusted | modified`), `enabled`, `currentHash`, `pluginId`, and
  `sourcePath`. It is the per-hook, hash-pinned trust decision Codex uses to gate execution:
  approval, not an observed run. No CLI subcommand exposes it; it needs a JSON-RPC session with
  `codex app-server`.
- What an untrusted hook looks like in 0.147.0 (`codex-rs/tui` snapshots): at startup, "Hooks need
  review — N hooks are new or changed. Hooks can run outside the sandbox after you trust them",
  with options "Review hooks", "Trust all and continue", "Continue without trusting (hooks won't
  run)". `/hooks` ("view and manage lifecycle hooks") lists each hook with "Trust: New hook -
  review required" and "Press t to trust".
- The doctor already separates `unsupported` (`INSTALL_MISSING`, `MANIFEST_INVALID`,
  `DEPENDENCY_MISSING`, …) from `advisory` reasons; `TRUST_UNKNOWN`, `HOOKS_UNTRUSTED`, and
  `TRUST_CONFIG_ONLY` are advisory. Linux/WSL get `PLATFORM_UNVERIFIED`.
- The hooks probe their helpers by fixed candidate lists: `commit-gate.sh:168`
  (`scripts/verify_summary.py`, `.claude/scripts/verify_summary.py`,
  `.codex/.agent-harness/payload/scripts/verify_summary.py`) and `session-knowledge.sh:122-124`
  (`runtime/runtime_mode.py`, `.claude/runtime/runtime_mode.py`,
  `.codex/.agent-harness/payload/runtime/runtime_mode.py`).
- The Claude installer runs `bash "$SRC/scripts/init-structure.sh" --root "$TARGET_DIR"`
  (`install-harness.sh:246`); `init-structure.sh` is create-if-missing and always exits 0.

## Decisions (user-approved 2026-10-09)

1. **Visibility now, `hooks/list` later.** #255 ships the installer next step, a named doctor
   reason, evidence, and docs. Wiring `hooks/list` into the doctor is a follow-up issue that
   needs a live macOS capture before it may unlock `enforced`. The doctor stays `advisory`.
2. **A missing hook helper is `advisory`** with the new named reason `HOOK_DEPENDENCY_MISSING`
   (the adapter still works; one guarantee is gone), consistent with `INSTALL_HASH_MISMATCH`.
3. The installer's doctor run uses `--no-persist`: install writes no runtime-mode record before
   the user has reviewed trust.
4. The installer runs `init-structure.sh` (issue #255 Target, moved here from #253 at the #253
   design approval). Reason: the installed hooks and skills expect the workflow structure —
   `session-knowledge.sh` loads `docs/solutions/critical-patterns.md` and the
   `docs/solutions/INDEX.md` pointer, and the skills write `specs/<slug>/`. It is create-if-missing,
   like the Claude installer's call; the files are user-owned once created, are not recorded in
   the deployment manifest, and `--remove` leaves them (the Claude installer never removes them
   either).

## Constraints

- No step edits trust configuration (existing invariant). No `codex` call may change trust.
- Claude install output stays byte-identical; `install-harness.sh` is not edited.
- `enforced` must not become reachable by this change; an `enforced` claim stays a bug.
- Installer additions are never fatal after a successful deploy and never run under `--dry-run`
  or `--remove`.
- Bash stays macOS 3.2 compatible; Python 3 stdlib only; tests use the fake Codex and never touch
  the real `~/.codex`.

## Components

1. **Installer end step** (`scripts/install-codex-harness.sh`), after the deploy and the
   `.gitignore` step, skipped under `--dry-run`/`--remove`:
   - run `bash "$SOURCE_DIR/scripts/init-structure.sh" --root "$TARGET_DIR"`;
   - run `python3 "$SOURCE_DIR/scripts/codex_harness_doctor.py" --root "$TARGET_DIR"
     --repo-root "$SOURCE_DIR" --no-persist`, forwarding `--codex-bin`/`--codex-home` when given.
     The option parser records those two values in their own variables as well as in
     `FORWARD_ARGS`. Parse the doctor's stdout JSON with `python3` and print
     `codex-install: doctor mode: <mode> (<comma-separated reason_codes>, or none)`. A doctor
     failure is a non-zero exit or stdout that is not a JSON object with a `mode`; then print
     `codex-install: doctor could not run; run it yourself (below)` and continue. Both this call
     and the `init-structure.sh` call are guarded (`|| …`) so `set -euo pipefail` cannot end the
     install, and a missing `init-structure.sh` (older `--source` checkout) prints a skip line;
   - print the next step, two lines:
     `codex-install: next: start Codex in <target>, choose "Review hooks" (or run /hooks and press t on each Agent Harness hook); hooks do not run until trusted.`
     then the doctor command:
     - `--source` mode: `codex-install: then run: python3 <SOURCE_DIR>/scripts/codex_harness_doctor.py --root <target>`;
     - clone mode (the clone is deleted on exit, and the payload does not ship the doctor):
       `codex-install: then run: git clone --depth 1 --branch <BRANCH> <REPO_URL> <dir> && python3 <dir>/scripts/codex_harness_doctor.py --root <target>`
       (`--repo-root` defaults to the doctor's own checkout).
2. **Doctor reason** (`scripts/codex_harness_doctor.py`): a module table
   `HOOK_DEPENDENCIES = {"commit-gate.sh": (…3 verify_summary.py candidates…),
   "session-knowledge.sh": (…3 runtime_mode.py candidates…)}`. In `diagnose`, when the install
   reasons contain neither `INSTALL_MISSING` nor `MANIFEST_INVALID`, and for a hook no candidate
   is a file under `--root`, add `HOOK_DEPENDENCY_MISSING` (advisory). The hook names go in
   `diagnostic_summary["hook_dependencies_missing"]` as a sorted comma-separated string (the
   record has no detail field and reason codes must match `^[A-Z][A-Z0-9_]*$`); the key is
   present only when something is missing. Known limits, documented: `session-knowledge.sh` also
   probes `runtime/run_state.py` at the repo root only, so its active-runs section is empty in
   every Codex install — excluded here (it would fire on every install) and noted as a gap; and
   the hooks search the project directory Codex runs them in (`CLAUDE_PROJECT_DIR` or the git
   top level), which can differ from `--root` when the project is a subdirectory of a repo.
3. **Evidence.** No new fixture: `scripts/check_codex_capabilities.py` keeps a closed
   `ALLOWED_CAPTURES` vocabulary precisely so a hand-authored file cannot wear a captured label,
   and fixtures must record an observed run. Instead, `capability-matrix.json`
   `config.project_trust` keeps `status: unknown`, `source.kind: unavailable`, and
   `expires_at`; its `source.reference` states the source reading (`doctor --json` has no trust
   field at 0.147.0 or 0.162.0; app-server `hooks/list` exposes per-hook `trustStatus` at both),
   `checked_at` becomes 2026-10-09, and `exit_condition` names the `hooks/list` follow-up. The
   full citations live in `research-brief.md`.
4. **Docs** (`docs/codex-alpha-install.md`): the files the installer creates outside `.codex/`
   (`init-structure.sh` output; the "does not edit" list at `:66` updated accordingly); what a user sees when hooks are untrusted (the
   startup prompt, `/hooks`), how to trust them, that hooks do not run until trusted, what the
   installer prints, and what `TRUST_UNKNOWN`, `HOOKS_UNTRUSTED`, `TRUST_CONFIG_ONLY`, and
   `HOOK_DEPENDENCY_MISSING` mean and how to clear each.
5. **Follow-up issue**: wire `hooks/list` into the doctor (spawn `codex app-server`, map the
   Agent Harness plugin hooks' `trustStatus`), gated on a live macOS 0.147.0+ capture.

## Error behavior

| Condition | Result |
| --- | --- |
| Doctor exits non-zero or prints no parsable `mode` | message printed; install exits 0 |
| `init-structure.sh` reports a write failure | it already exits 0; install continues |
| `--dry-run` / `--remove` | neither `init-structure.sh` nor the doctor runs |
| No install manifest | `HOOK_DEPENDENCY_MISSING` not evaluated (`INSTALL_MISSING` already `unsupported`) |
| Helper present at any candidate | no reason |

## Tests

- `tests/scripts/codex-install.test.sh` (or a sibling suite): fresh install prints the doctor
  mode line and the next-step text; creates the `init-structure.sh` files without overwriting an
  existing one; `--dry-run` and `--remove` run neither; the fake Codex log contains no
  trust-changing call and `CODEX_HOME` holds no new trust config; a failing doctor still exits 0.
- `scripts/test_codex_harness_doctor.py`: the shared `installed_project()` fixture gains the
  payload helpers (`payload/scripts/verify_summary.py`, `payload/runtime/runtime_mode.py`), so
  the existing `enforced`/exact-reason assertions keep their meaning; a fixture with
  `verify_summary.py` removed yields `HOOK_DEPENDENCY_MISSING`, `advisory`, and
  `diagnostic_summary.hook_dependencies_missing == "commit-gate.sh"`; a `.claude/`-only helper
  copy satisfies the check; a drift test compares each table entry with the candidates parsed
  from the hook script, in both directions, matched by helper filename (`verify_summary.py`,
  `runtime_mode.py`) so the deliberately excluded `runtime/run_state.py` probe is not counted.
- Installer output tests assert the mode line's shape (`doctor mode: <word>`), not specific
  reasons: the fake Codex answers `doctor --json` with `{"ok":true}`.
- Evidence/matrix validator tests stay green with the new record.

## Out of scope

Bypassing or auto-granting trust; Linux/WSL runtime observation; implementing `hooks/list`
(follow-up); agent-profile paths (#268).
