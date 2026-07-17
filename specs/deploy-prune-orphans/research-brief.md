# Research — deploy-harness leaves deleted-skill orphans in .claude/

Verified 2026-07-17 (surfaced when re-syncing `.claude/` after the bootstrap-xia2 removal: `.claude/skills/bootstrap-xia2/` lingered and had to be removed by hand).

## The bug

`scripts/deploy-harness.sh` `copy_dir()` iterates **source** entries (`for entry in "$1"/*`) and, per entry, does `rm -rf "$OUT/$1/$base"; cp -R`. It only ever touches destination paths that have a matching source entry. A top-level entry that was **deleted from source** (e.g. `skills/bootstrap-xia2/`) has no source counterpart, so the loop never visits its stale `.claude/` copy → it lingers indefinitely. For a skill, that means `/bootstrap-xia2` stays loadable in a re-synced repo even though the source deleted it.

Scope: the 5 wholesale-synced dirs — `skills agents hooks rules templates` (the `for d in …` loop). `agent-memory`, `settings.local.json`, `worktrees`, `.harness-backup-*`, `.harness-source` are NOT in that loop and are never touched.

## Why the naive fix is unsafe

"Prune any `$OUT` entry with no source counterpart" would delete **consumer additions**, not just harness orphans. A consuming repo's `.claude/` can legitimately hold:
- a consumer's own custom skill under `.claude/skills/<their-skill>/` (no source counterpart, but must survive);
- protected-file sidecars: `*.harness-incoming`, `*.proposed`;
- `.harness-backup-*/`, `settings.local.json` (already outside the synced dirs, but a blind recursive prune could reach them);
- backup/invalid files `settings.json.invalid-bak-*`.

The harness is deliberately paranoid here — `install-harness.sh`'s head comment records a **real data-loss incident** (a prior installer pruned root-staged payload and destroyed real files), and `derive_settings` goes to lengths to preserve a consumer's foreign settings keys/hooks. A blind prune reintroduces exactly that class of hazard.

## The distinguishing signal that already exists (partially)

- `strip_archive()` already does a **targeted** prune: `rm -rf "$OUT/skills/_archive"` — precedent that deploy prunes a *known* path, not arbitrary orphans.
- But there is **no record of what the harness itself deployed**, so a deleted-harness-skill and a consumer-added-skill are indistinguishable at re-sync time.

## The only safe way to tell them apart

Record what the harness deploys. On the next deploy, prune only entries that **were harness-deployed last time and are gone from source now** — never entries the harness never claimed. A deployed-manifest makes the prune **safe by construction**: consumer additions never enter the manifest, so are never eligible for pruning.

## Constraints for any fix

- Prune only top-level entries under the 5 synced dirs, and only ones the harness previously deployed.
- Never touch: consumer additions, `*.harness-incoming`, `*.proposed`, `.harness-backup-*`, `settings.local.json`, `settings.json*`, `agent-memory/`, `worktrees/`, `.harness-source/`.
- First deploy (no prior manifest) prunes nothing.
- `--dry-run` reports would-be prunes, writes nothing.
- Idempotent: a second identical re-sync prunes nothing new.
- Must land with a test proving a **consumer custom skill survives** a re-sync where it is absent from source (the load-bearing safety test), alongside a test proving a **deleted harness skill is pruned**.
