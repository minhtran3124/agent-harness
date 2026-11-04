**Read the gate mode from the index, not the worktree, and fail closed.** There's one problem with the premise: `harness-manifest.json` no longer exists in this repo. I didn't write any code, because you didn't ask for it; this is design guidance for your hook.

```bash
# fail closed: any answer other than an exact "warn" means block
mode=$(git show :harness-manifest.json 2>/dev/null | jq -r '<your filter>' 2>/dev/null || true)
[ "$mode" = "warn" ] || mode=block
```

`docs/solutions/harness/gate-config-must-read-index.md` records this exact bug. An unstaged edit to `"mode": "warn"` let a commit through while the committed tree still shipped block mode. The rule from that record is that every input to the decision comes from the same tree as the commit.

**The file was removed**
- `CHANGELOG.md:68` says 5.0.0 removed `harness-manifest.json`. It isn't at the repo root, and no tracked path has "manifest" in its name.
- The hook in that record (`risk-corroboration.sh`, later merged into `commit-gate.sh`) is gone too. `plugins/harness/hooks/` has only five scripts, and `secrets-scan.sh` is the only commit-time one.
- All three gate-mode records are more than 30 days old, so treat their specifics as stale; the index-read rule still applies.
- If you're restoring the file, you need to decide what happens in a project without it. The two records disagree:
  - `gate-config-must-read-index.md` treats a missing file as block.
  - `consumer-risk-modes-index-safe.md`, the newer one, falls back to defaults embedded in the hook. It also says never to read `.claude/` or any worktree file. I'd follow this one for consuming projects.

**Things to get right in the hook**
- **Hook timing:** `secrets-scan.sh` is a PreToolUse hook, which runs before the Bash command does. For `git add x && git commit` or `git commit -a`, the index it reads isn't yet what gets committed, so index reads alone don't close the gap in that design. A real git `pre-commit` hook should see the final index, because git points `GIT_INDEX_FILE` at it. I tried to confirm this in a throwaway repo, but the sandbox blocked the run, so it's untested.
- **Staged edits:** an index read only stops unstaged edits. A staged change to `warn` still loosens the gate, but it's visible in that commit's diff. The records accept this by design.
- **Failure mode:** `jq` missing, a parse error or a merge conflict in the file must all end in block. `CLAUDE.md` says every hook except `merge-guard.sh` fails open, so update that line and `docs/hooks.md` when you add this one.

**Regression test:** commit a block-mode manifest, change the worktree copy to warn without staging it, stage a gated change, and assert the hook blocks. Fixtures must stage the manifest. The original tests wrote it only to the worktree, so they locked in the bug.
