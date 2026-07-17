# Design — deployed-manifest prune for deploy-harness

Status: proposed. Companion: `research-brief.md`, `PLAN.md`. Targets v3.

## Goal

Make `deploy-harness.sh` remove `.claude/` copies of harness entries that were **deleted from source**, without ever touching consumer additions or harness sidecar/state files. Safe by construction.

## Approach: a deploy manifest of harness-owned paths

At the end of a successful deploy, write `.claude/.harness-deployed` — a newline-delimited list of the top-level entries the harness just deployed under each synced dir, e.g.:

```
skills/xia2
skills/compound
agents/coding.md
hooks/commit-quality-gate.sh
rules/behavior.md
templates/structure
…
```

On the **next** deploy, before the copy loop (or right after it), read the *previous* `.harness-deployed`. Compute:

```
orphans = { path in previous-manifest : path's source no longer exists }
```

and `rm -rf "$OUT/$path"` for each orphan. Then overwrite `.harness-deployed` with the current set.

**Why safe:** an entry is pruned only if it appears in the *previous harness manifest* AND is gone from *current source*. A consumer's own skill never entered the manifest → never pruned. First deploy has no prior manifest → prunes nothing.

## What is eligible / never eligible

- **Eligible:** top-level entries under `skills/ agents/ hooks/ rules/ templates/` that the harness listed last deploy and source no longer has.
- **Never eligible (by construction — not in the manifest):** consumer-added skills/files, `*.harness-incoming`, `*.proposed`, `.harness-backup-*/`, `.harness-source/`, `settings.json*`, `settings.local.json`, `agent-memory/`, `worktrees/`. The manifest only ever lists what `copy_dir`/`sync_protected_*` actually deployed.

## Manifest content rule

The manifest lists exactly the paths the deploy wrote this run: every top-level entry iterated in `copy_dir` for the 5 synced dirs (both plain and protected). It is a **flat list of `<dir>/<top-level-entry>`** — not recursive; pruning a top-level orphan dir with `rm -rf` covers its contents. `skills/_archive` is already handled by `strip_archive` and is simply never added to the manifest.

## Ordering

1. Read `PREV_MANIFEST` from `$OUT/.harness-deployed` (empty if absent) — **before** any copy.
2. Run the copy loop (unchanged), accumulating `DEPLOYED[]` (each top-level entry written).
3. **Prune pass:** for each path in `PREV_MANIFEST` not in `DEPLOYED` and whose source is absent, `rm -rf "$OUT/$path"` (dry-run: report only). Guard the path shape (must start with one of the 5 synced dir names + `/`) as defense-in-depth.
4. Write `DEPLOYED[]` to `$OUT/.harness-deployed`.

Using "not in DEPLOYED this run" as the orphan test (rather than re-statting source) is both simpler and correct: DEPLOYED is exactly "what source has now", built during the copy.

## Dry-run

`--dry-run` already exits early inside `preflight_protected` before any write. The prune must therefore also be reported from the dry-run path OR the dry-run exit is left as-is and prune is simply never reached on dry-run. Decision: keep it simple — dry-run continues to write nothing and does not prune; add a one-line note to the dry-run report that stale entries would be pruned on a real run (computed from PREV_MANIFEST vs current source, read-only). This preserves "dry-run writes nothing" while still informing.

## `.harness-deployed` visibility

It is a harness state file under `.claude/` (gitignored like the rest of `.claude/`). Add it to the never-prune/never-report set trivially (it is not under a synced dir). No `.gitignore` change needed (`.claude/` is already ignored).

## Alternatives considered

- **Blind prune (orphan = no source counterpart):** rejected — deletes consumer additions; reintroduces the documented data-loss hazard.
- **Hardcode a deny-list of removed skills:** rejected — unbounded manual maintenance, misses future deletions.
- **Derive ownership from `harness-manifest.json`:** rejected — that is the *source* inventory, not a record of what a given `.claude/` received; a consumer's `.claude/` may have been deployed from an older source with different entries. The per-deploy manifest is the honest record.

## Risks

- Deletion logic in the installer — highest-care area. Mitigated: safe-by-construction (prune ⊆ previous-harness-manifest), path-shape guard, dry-run writes nothing, and the load-bearing test (consumer custom skill survives). Rollback = `git revert` (no data migration; worst case reverts to the current lingering-orphan behavior, which is non-destructive).
- Existing `.claude/` in the wild has no `.harness-deployed` yet → the first post-fix deploy prunes nothing (writes the manifest), and only *subsequent* deploys prune. Acceptable: no retroactive prune, no surprise deletion.
