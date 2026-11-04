Verdict: known risk

**Do first**
- Derive the project root from the runtime, not from where the script lives. Use `ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"`. Keep git-from-CWD as the second step. Add no fallback to `SCRIPT_DIR`, `dirname "$0"`, `${BASH_SOURCE[0]}` or `realpath "$0"`. Record: `docs/solutions/harness/hook-root-must-not-come-from-install-location.md` (confirmed_at 2026-09-09).
- Make the script stop when the root is empty, matching its own blocking posture. Example: `[ -z "$ROOT" ] && { echo "cannot determine the project root" >&2; exit 2; }`. Do not return a guess. Same record (2026-09-09).
- Run `bash scripts/check-hook-root-source.sh` on the script. Also test it the way the record does, by hosting the script inside a foreign git repo and checking which repo it acts on. The static check only knows some spellings. Records: `hook-root-must-not-come-from-install-location.md` and `ratchet-matches-spelling-not-property.md` (both 2026-09-09).

**Avoid**
- Do not use `git -C "$SCRIPT_DIR" rev-parse --show-toplevel`, or the same call under any other `*_DIR` name. A marketplace install is a git clone. The command exits 0 and returns the wrong repo, so the script reads and edits that repo and reports success.
- Do not write a guard from the same list of names you used for the fix. The first ratchet matched only `SCRIPT_DIR`, reported clean, and missed `HOOK_DIR` in `session-knowledge.sh`. Its green result looked like proof that the work was complete.

**Check before done**
- Install the script from a clone-based location (marketplace cache). Run it from a separate project. Confirm it acts on that project and not on the repo that holds the script. The record's test hosts the script in a foreign repo whose staged content would trip a gate.
- Show your new guard failing on the pre-fix version before you trust its green.
- Confirm the script still works when `CLAUDE_PROJECT_DIR` is unset and CWD is inside the project. The existing tests depend on that path.

**Possibly stale**
- Both records are 56 days old (confirmed_at 2026-09-09, today 2026-11-04). That is more than 30 days.
- The `affects` hook paths no longer exist under `plugins/harness/hooks/`: `blast-radius-check.sh`, `branch-guard.sh`, `commit-quality-gate.sh`, `render-plan-on-write.sh`, `risk-corroboration.sh`, `ruff-on-edit.sh`, `scope-gate.sh`, `session-knowledge.sh`. The record's own note says they were merged into `hooks/commit-gate.sh` or removed (simplify-hook-surface, 2026-09-29). No `commit-gate.sh` was found. The principle still holds. Drop the per-hook steps.
- `tests/hooks/repo-root-resolution.test.sh` was not found anywhere, so the "add a case there" step is out of date. Keep the foreign-repo test technique and write the test yourself.
- `scripts/check-hook-root-source.sh` exists, but the record scoped it to `hooks/`. Whether it scans `plugins/harness/` was not checked.
- The per-hook exit-code table (exit 2 for gates, exit 0 for the others) refers to removed hooks. Only the idea of matching the script's own documented posture still applies.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/hook-root-must-not-come-from-install-location.md`, `docs/solutions/harness/ratchet-matches-spelling-not-property.md`. I also listed `plugins/harness/hooks` and `plugins/harness/scripts`. I searched the repo for `check-hook-root-source.sh`, `repo-root-resolution.test.sh`, `commit-gate.sh` and `session-knowledge.sh`. I grepped `plugins/harness/hooks` for `SCRIPT_DIR`/`HOOK_DIR`/`BASH_SOURCE` together with `rev-parse`/`toplevel` and found no hits.
