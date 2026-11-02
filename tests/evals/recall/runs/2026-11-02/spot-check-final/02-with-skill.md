Verdict: known risk

**Do first**
- Take the project root from the runtime, not from where the script lives. Use `ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"`. Keep the git-from-CWD fallback. Add no `SCRIPT_DIR` fallback at any position. Use `SCRIPT_DIR` only to find the script's own libraries. Source: `docs/solutions/harness/hook-root-must-not-come-from-install-location.md` (confirmed_at 2026-09-09).
- Add a guard for when the root cannot be resolved. It must match the script's documented posture. A blocking gate prints a named reason to stderr and does `exit 2`. A non-blocking script prints a note to stderr and does `exit 0`. Source: the same record (confirmed_at 2026-09-09).
- Run `bash scripts/check-hook-root-source.sh` on the new or changed script. Also add a case that hosts the script inside a foreign git repo while the working directory is the real project. Source: `docs/solutions/harness/ratchet-matches-spelling-not-property.md` (confirmed_at 2026-09-09).

**Avoid**
- Do not use `git -C "$SCRIPT_DIR" rev-parse --show-toplevel`, `dirname "$0"`, `${BASH_SOURCE[0]}` or `realpath "$0"` to find the root. A marketplace install is a git clone, so the command exits 0 and returns the wrong repo. Your script then reads and edits the wrong repo and reports success.
- Do not trust a ratchet whose match list came from the same grep pass as the fix. The first lint matched the name `SCRIPT_DIR`. It missed `HOOK_DIR` in `session-knowledge.sh`. The test run was green and the defect stayed in place.
- Do not give every script one fail-open or fail-closed posture. Always fail-closed breaks ordinary edits. Always fail-open brings back the silent wrong-repo pass.

**Check before done**
- Run the script from a copy inside a different git repo, with the working directory set to the real project. Confirm it acts on the project. The record's test (`tests/hooks/repo-root-resolution.test.sh`) was 13 cases, and 5 of the original 11 failed against the pre-fix hooks.
- Run `scripts/check-hook-root-source.sh` and read its green as "no known spelling present". It does not prove the property holds. Run the new check against the pre-fix tree and confirm it fails there.
- Run `grep -nE 'dirname|BASH_SOURCE|realpath|_DIR' <your script>` for other self-locating idioms that the lint's regex does not cover.

**Possibly stale**
- `docs/solutions/harness/hook-root-must-not-come-from-install-location.md` is not out of date. The advice still holds.
  - Its `affects` hooks (`blast-radius-check.sh`, `branch-guard.sh`, `commit-quality-gate.sh`, `render-plan-on-write.sh`, `risk-corroboration.sh`, `ruff-on-edit.sh`, `scope-gate.sh`, `session-knowledge.sh`) are not under `plugins/harness/hooks/`. The record notes they were merged into `commit-gate.sh` or removed on 2026-09-29, and `commit-gate.sh` is not in the repo.
  - The record cites `tests/hooks/repo-root-resolution.test.sh`, which I did not find.
  - `scripts/check-hook-root-source.sh` exists.
  - It is 54 days old (2026-09-09 to 2026-11-02), which is over 30 days.
- `docs/solutions/harness/ratchet-matches-spelling-not-property.md` is not out of date.
  - `scripts/check-hook-root-source.sh` exists.
  - `hooks/session-knowledge.sh` and `tests/hooks/repo-root-resolution.test.sh` were not found.
  - It is 54 days old, which is over 30 days.
- The plugin copy `plugins/harness/hooks/session-rules.sh:6` has `ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"`. This finds the plugin's own files, which is acceptable. Do not use it as the project root.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/hook-root-must-not-come-from-install-location.md`, `docs/solutions/harness/ratchet-matches-spelling-not-property.md`. I also searched `plugins/harness/hooks/` and `scripts/` with Bash `ls`, `find` and `grep`.
