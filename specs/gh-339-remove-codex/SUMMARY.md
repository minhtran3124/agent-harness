# gh-339-remove-codex — Summary

Lane: high-risk
Confidence: high
Reason: high-blast hard gate — the diff edits hooks/* (commit-gate.sh, session-knowledge.sh, lib/normalize-tool-input.py), harness-manifest.json and the runtime bindings while removing the Codex adapter.
Flags: existing behavior, multi-domain
Affects: hooks (Codex payload branches removed), runtime/run_state.py (runtime-mode options removed), scripts/verify_summary.py (Runtime-mode header lines removed)
Input-type: maintenance
Route: Harness v5 epic #338, issue #339 (owner-approved roadmap)
Escalate: no

### Intent

Owner approved the Harness v5 roadmap on 2026-10-28 ("approve for roadmap", "bo codex adapter"); issue #339: "Tag legacy-v2.37.0 and remove the Codex adapter".

## What changed

- Deleted the Codex adapter, Codex scripts, tests, fixtures, docs and `runtime/runtime_mode.py`.
- Removed Codex branches from hooks, `run_state.py`, `verify_summary.py`, the manifest, bindings and CI. Claude behaviour unchanged.

### Rationale

Codex support was an advisory alpha, never GA; v5 targets Claude Code only (epic #338).

### Alternatives considered

- Redesign the runtime-neutral binding system now — deferred to #349, which deletes that machinery.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| commit-gate hook | `bash tests/hooks/commit-gate.test.sh` | 0 | Codex Bash-shape case removed |
| hook normalizer | `bash tests/hooks/normalize-tool-input.test.sh` | 0 | |
| session-knowledge hook | `bash tests/hooks/session-knowledge.test.sh` | 0 | runtime_mode consumer removed |
| branch-isolation hook | `bash tests/hooks/branch-isolation-guard.test.sh` | 0 | turn_id payloads switched to session_id |
| runtime bindings | `bash tests/scripts/runtime-entry-bindings.test.sh` | 0 | claude is the only runtime |
| manifest | `python3 scripts/check_manifest.py` | 0 | |

### Rollback

`git revert <merge-sha>`; the pre-v5 state is also tagged `legacy-v2.37.0`.
