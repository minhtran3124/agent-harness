# remove-protected-path-guard — Summary

Lane: high-risk
Confidence: high
Reason: Removes a hook under `hooks/` and changes the manifest and documented hook inventory; CI strict-gate requires machine-verified high-risk evidence for this surface.
Flags: high-blast, existing-behavior
Affects: `hooks/protected-path-guard.sh`, its contract tests, `harness-manifest.json`, `CLAUDE.md`, and stale live references
Input-type: harness improvement

### Intent

Remove the dormant protected-path guard. It was copied and tested but not registered in
`settings.json`, and its high-blast commit-time coverage is already provided by
`risk-corroboration.sh`.

### What changed

- Deleted `hooks/protected-path-guard.sh` and `tests/hooks/protected-path-guard.test.sh`.
- Removed the `wired: false` manifest entry and dormant CLAUDE.md inventory row.
- Removed stale live comments referring to the deleted hook.

### Rationale

The hook had no runtime caller: it was absent from both source and derived settings
registrations. Keeping a dormant implementation and test contract overstated supported runtime
behavior and duplicated the active high-blast commit gate.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| removed hook and test | `bash -c 'test ! -e hooks/protected-path-guard.sh && test ! -e tests/hooks/protected-path-guard.test.sh'` | 0 | dormant implementation and contract test are absent |
| manifest consistency | `python3 scripts/check_manifest.py` | 0 | inventory, disk, settings, and risk corroboration agree |
| documentation truth | `bash scripts/lint-doc-truth.sh` | 0 | no dangling live hook inventory references |
| no live references | `bash -c 'git grep -n -I -e "protected-path-guard" -e "PROTECTED_PATH_REASON" -- . ":(exclude)docs/**" ":(exclude)specs/**" ":(exclude)CHANGELOG.md"; rc=$?; test "$rc" -eq 1'` | 0 | historical changelog references are retained; live references are absent |

### Rollback

`git revert <commit>` restores the dormant hook, its tests, and inventory entries. No runtime
consumer data or migration is involved.
