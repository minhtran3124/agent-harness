## Title

fix: keep harness self-contained in .claude/ after install

## Summary

Installing the harness into a project previously dumped source-of-truth dirs (`skills`, `agents`, `hooks`, `rules`, `templates`, `settings.json`, `scripts/`) at the project root alongside the derived `.claude/`, cluttering the consuming repo. This makes the installer leave only a self-contained `.claude/` so a consumer's root stays clean; updating is just re-running the installer.

## Tasks

- Prune the root payload after `.claude/` is built so the project root stays clean
- Add `--keep-sources` to opt out and preserve the editable root-source layout
- Sync `templates/` into `.claude/` so it is self-contained after the prune
- Update README install/update docs to match the new flow

## File Changes

| File | Type | What changed |
|------|------|--------------|
| `scripts/install-harness.sh` | Modified | Prune root source copies after build (default); add `--keep-sources` flag; dry-run aware |
| `scripts/deploy-harness.sh` | Modified | Also sync `templates/` into `.claude/` so it is self-contained |
| `README.md` | Modified | Document `.claude/`-only consumer layout, re-run-installer update flow, and `--keep-sources` |

## Notes

- Behavior change for consumers: the root no longer keeps source dirs, so `deploy-harness.sh` re-sync no longer applies in a consuming project — updates happen by re-running the installer. `--keep-sources` restores the old root-source + `.claude/` layout.
- Verified end-to-end against a temp target: default prune (root = only `.claude/`), `--keep-sources` (root retains sources), and `--dry-run` (writes nothing).
