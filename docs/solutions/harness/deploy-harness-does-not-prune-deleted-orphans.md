---
problem_type: bug
module: scripts/deploy-harness.sh
tags: deploy, resync, prune, orphan, deployed-manifest, safe-by-construction, data-loss, consumer-additions
severity: standard
applicable_when: You deleted a skill/agent/hook/rule/template from source, re-ran deploy-harness, and the old copy still lingers in .claude/ — or you are about to add "prune orphans" to a deploy/sync tool.
affects:
  - scripts/deploy-harness.sh
  - tests/scripts/deploy-prune.test.sh
supersedes: null
confidence: high
confirmed_at: 2026-07-17
---
## Problem

`deploy-harness.sh` never removed `.claude/` copies of harness entries **deleted from source**. After deleting a skill (e.g. `bootstrap-xia2`) and re-syncing, `.claude/skills/bootstrap-xia2/` lingered and stayed loadable — it had to be `rm -rf`'d by hand.

## Root Cause

`copy_dir()` iterates **source** entries (`for entry in "$1"/*`) and, per entry, does `rm -rf "$OUT/$1/$base"; cp -R`. It only ever touches destination paths that have a *matching source entry*. A top-level entry deleted from source has no counterpart, so the loop never visits its stale copy. (Only `strip_archive`'s hardcoded `rm -rf skills/_archive` was pruned.)

## Fix

A **per-deploy manifest** at `.claude/.harness-deployed` listing the top-level `<dir>/<entry>` paths shipped this run (under the 5 synced dirs). The next deploy prunes entries in the **previous** manifest that are gone from source — `prune = prev_manifest ∖ deployed_this_run`, shape-guarded to `skills|agents|hooks|rules|templates/<entry>`.

**Safe by construction:** only paths the harness itself recorded deploying are eligible, so consumer-added skills (never in the manifest) are never pruned — `copy_dir`'s own comment confirms the harness deliberately supports foreign `.claude/` entries. First deploy (no prior manifest) prunes nothing; `--dry-run` reports read-only. A **pre-manifest** orphan (deployed by an old version that never wrote a manifest) is never auto-pruned — remove it once by hand; every deploy after is automatic.

## Regression Test

`tests/scripts/deploy-prune.test.sh` — 6 cases. The load-bearing one: *a consumer's own skill (absent from source, never in the manifest) SURVIVES a re-sync* — a blind "orphan = no source counterpart" prune would destroy it.

## Prevention

When adding deletion to any sync tool, do not derive "ownership" from the current source inventory (indistinguishable from a consumer addition). Record what the tool itself deployed and prune only `previous_own_manifest ∖ current_source`. Never blind-prune.

## Related
- docs/solutions/harness/resync-protected-files-decisions.md
