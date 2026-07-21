# remove-agent-memory — Summary

Lane: high-risk
Confidence: high
Reason: Removes a distributed agent contract and installer/template behavior; the acceptance proof must cover fresh installs, upgrades, and consumer-owned data preservation.
Flags: existing-behavior, high-blast, weak-proof
Affects: agents/{coding,reviewer,test-runner}.md, scripts/{init-structure,install-harness,lint-doc-truth}.sh, structural templates, current installation documentation
Input-type: harness improvement

### Intent

Remove the unused tracked per-agent memory convention end to end. Keep `/compound` and
`docs/solutions/` as the sole committed harness-managed knowledge path. Do not migrate or delete
consumer-owned data during installation.

### What changed

- Removed persistent-memory frontmatter from the three bundled agents.
- Deleted the tracked store and structural template, and reduced initialization to six files.
- Updated installer behavior, integration contracts, current documentation, and doc-truth roots.
- Added regression coverage for dry-run emptiness, fresh install, reinstall, memory-free agents,
  and preservation of a pre-existing consumer directory.

### Rationale

The feature had no runtime consumer and its documented decay protocol was dead prose. Removing
the scaffold and distributed configuration eliminates a misleading supported path while retaining
the existing non-destructive installer guarantee.

### Deviations

- Historical research and decision records under `docs/` and this spec remain unchanged.
- The live-surface assertion constructs the consumer-owned directory name in shell tests so the
  tests can verify its absence without making the removed feature appear as a live reference.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| initializer contracts | `bash tests/scripts/init-structure.test.sh` | 0 | 3 passed; six files, idempotency, and no removed directory |
| installer contracts | `bash tests/scripts/install-harness.test.sh` | 0 | 10 passed; dry-run, fresh install, reinstall, memory-free agents, and preservation |
| documentation truth | `bash scripts/lint-doc-truth.sh` | 0 | referenced paths and hook registrations agree |
| live-surface removal | `bash -c 'rg -n --hidden --glob "!.git/**" --glob "!.claude/**" --glob "!docs/**" --glob "!specs/**" -e "agent-memory" -e "^memory: project$" -e "^memory: local$" -e "^memory: user$" .; rc=$?; test "$rc" -eq 1'` | 0 | no removed feature or persistent-memory frontmatter outside history and this spec |

### Rollback

`git revert <commit>` restores the source definitions and scaffolding behavior. No migration or
consumer-data cleanup was performed, so rollback does not require data recovery.

### Harness-Delta

- none
