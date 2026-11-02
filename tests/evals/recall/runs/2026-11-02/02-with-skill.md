Verdict: known risk

**Do first**
- Resolve the root as `ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"`. Never use `git -C "$SCRIPT_DIR"`, `dirname "$0"`, `${BASH_SOURCE[0]}` or `realpath "$0"`. Source: `docs/solutions/harness/hook-root-must-not-come-from-install-location.md`, confirmed_at 2026-09-09. Keep `SCRIPT_DIR` only to find the script's own libraries.
- If the root cannot be resolved, fail with a named reason, for example `[ -z "$ROOT" ] && { echo "cannot determine project root" >&2; exit 2; }`. Match the script's documented blocking posture. Same record, confirmed_at 2026-09-09.
- Do not rely on `scripts/check-hook-root-source.sh` alone to find other copies of this bug. It matches `*_DIR` spellings only, so "clean" means "no known spelling present". Search by shape: any `dirname "$0"`, `BASH_SOURCE` or `realpath "$0"` chain that feeds `git rev-parse`. Source: `docs/solutions/harness/ratchet-matches-spelling-not-property.md`, confirmed_at 2026-09-09. Command: `bash scripts/check-hook-root-source.sh`.

**Avoid**
- Deriving the root from the script's own location. A marketplace install is a git clone, so `git -C <script dir> rev-parse --show-toplevel` exits 0 and returns the plugin cache repo. Your script then reads and edits the wrong repo and reports success.
- Writing a guard from the same list as the fix. Seven hooks were fixed and the ratchet matched only that spelling. It reported clean while `hooks/session-knowledge.sh` still had the bug as `HOOK_DIR`.
- Falling back to the script location, even as the last step. That keeps the silent wrong-repo path open. A wrong answer that looks plausible is worse than a failure.

**Check before done**
- Add a foreign-repo case: put the script inside a different git repo, run it with its current directory set to the real project, and assert it acts on the project. The record's version of this is `tests/hooks/repo-root-resolution.test.sh`. Run the new check against the pre-fix code and confirm it fails.
- Run the script with `CLAUDE_PROJECT_DIR` unset and with the current directory inside the project. The `git rev-parse` fallback must still resolve, because the existing tests set no `CLAUDE_PROJECT_DIR`.
- Choose the unresolvable-root behavior to match the script's documented posture. Do not apply one project-wide default.

**Possibly stale**
- `docs/solutions/harness/hook-root-must-not-come-from-install-location.md` is about 54 days old (2026-09-09). Its `affects` paths are `hooks/blast-radius-check.sh`, `branch-guard.sh`, `commit-quality-gate.sh`, `render-plan-on-write.sh`, `risk-corroboration.sh`, `ruff-on-edit.sh`, `scope-gate.sh` and `session-knowledge.sh`. None of them exist under `hooks/`. The record itself says they were merged into `commit-gate.sh` or removed on 2026-09-29. A Glob search for `commit-gate.sh` and `session-knowledge.sh` found nothing in the repo. The premise still holds and matches your symptom.
- `docs/solutions/harness/ratchet-matches-spelling-not-property.md` is about 54 days old. `scripts/check-hook-root-source.sh` exists. `hooks/session-knowledge.sh` and `tests/hooks/repo-root-resolution.test.sh` were not found. Its premise still holds.
- Self-locating idioms still appear in `plugins/harness/hooks/session-rules.sh`, `plugins/harness/scripts/init-structure.sh` and `plugins/harness/skills/setup/scripts/old-install.sh`. I did not open them, so I don't know whether they derive a project root. Check them against the pattern above.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/hook-root-must-not-come-from-install-location.md`, `docs/solutions/harness/ratchet-matches-spelling-not-property.md`. I also ran a Grep for `SCRIPT_DIR|HOOK_DIR` in `hooks/*.sh` and one for the self-locating idioms under `plugins/harness`, plus a Glob for the affects filenames. My Bash existence checks were blocked, so those results come from Glob and Grep only.
