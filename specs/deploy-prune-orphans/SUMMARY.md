# deploy-prune-orphans — Summary

Lane: high-risk
Confidence: high
Reason: Adds file DELETION to scripts/deploy-harness.sh (installer, high-blast) — data-loss-adjacent. The design is safe by construction (prune ⊆ previous harness manifest, never consumer content); the load-bearing test proves a consumer's custom skill survives. Direction unambiguous (user asked to open a spec/PR for this fix).
Flags: high-blast (deploy-harness.sh), data-loss-adjacent (deletion logic)
Affects: deploy-harness.sh re-sync behavior; adds .claude/.harness-deployed manifest
Input-type: harness improvement

### Intent

"yes, open a spec/PR for the deploy prune fix" — fix the bug (surfaced this session) that deploy-harness leaves `.claude/` copies of deleted harness skills lingering (had to `rm -rf .claude/skills/bootstrap-xia2` by hand after the removal).

### What changed

deploy-harness.sh now writes a per-deploy manifest `.claude/.harness-deployed` (the top-level `<dir>/<entry>` paths it shipped this run under the 5 synced dirs), and on the next deploy prunes entries that were in the **previous** manifest but are gone from source. Safe by construction: only paths the harness itself previously deployed are eligible, so consumer additions (never in the manifest) are never pruned; shape-guarded to `skills|agents|hooks|rules|templates/<entry>`. First deploy (no prior manifest) prunes nothing. `--dry-run` reports would-be prunes read-only and writes nothing. New 6-case test suite; the load-bearing case asserts a consumer's custom skill survives.

### Rationale

The bug is real and will bite every future skill-deletion + re-sync. A naive "orphan = no source counterpart" prune would delete consumer-added skills — deploy-harness explicitly supports those (copy_dir comment: "foreign entries ... left untouched") and the harness carries a documented data-loss incident. The per-deploy manifest is the only way to distinguish a deleted-harness-skill from a consumer addition; it makes deletion safe by construction.

### Alternatives considered

- Blind prune (orphan = no source counterpart): rejected — deletes consumer additions; reintroduces the data-loss hazard.
- Hardcoded deny-list of removed skills: rejected — unbounded manual maintenance.
- Derive ownership from harness-manifest.json: rejected — that is the source inventory, not a record of what a given `.claude/` received.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| prune test suite: orphan pruned, consumer skill survives, sidecars/backups kept, dry-run no-write, idempotent | `bash tests/scripts/deploy-prune.test.sh` | 0 | 6 passed (incl. the load-bearing consumer-survives case) |
| resync-conflict suite unaffected | `bash tests/scripts/resync-conflict.test.sh` | 0 | protected-file behavior intact |
| install suite unaffected | `bash tests/scripts/install-harness.test.sh` | 0 | |
| deploy syntax valid + manifest wired | `bash -c 'bash -n scripts/deploy-harness.sh && grep -q harness-deployed scripts/deploy-harness.sh'` | 0 | |
| full suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN |

### Rollback

- `git revert <commit>` — removes the manifest write + prune pass + test; deploy returns to the current (non-destructive) lingering-orphan behavior. No data migration. Any `.claude/.harness-deployed` left behind is inert.

### Harness-Delta

- The bug itself was a Harness-Delta from the bootstrap-xia2 removal (deploy doesn't prune deleted skills) — now fixed. Reinforces that "re-sync" was silently incomplete for deletions.
