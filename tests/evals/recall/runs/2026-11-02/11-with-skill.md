Verdict: known risk

**Do first**
- Read the gate mode from the git index with `git show :harness-manifest.json 2>/dev/null | jq -r '.hard_gates.detectable[]? | "\(.slug)=\(.mode // "block")"' 2>/dev/null || true`. Do not read the worktree file. If the manifest is absent, unreadable or invalid, the mode must come out as `block`. (docs/solutions/harness/gate-config-must-read-index.md, confirmed_at 2026-07-23)
- If no manifest is tracked, use embedded in-hook defaults, not a file on disk. The recorded defaults are 2 warn and 7 block. Never read `.claude/harness-manifest.json` or any other worktree policy file, because `.claude/` is gitignored in consumers and so cannot be staged or checked. (docs/solutions/harness/consumer-risk-modes-index-safe.md, confirmed_at 2026-08-06)
- Keep durable loosening as a staged edit to the manifest `mode` field. For a session-only override, use `RISK_WARN_CATEGORIES` in `settings.local.json` `env`, which can only loosen. (docs/solutions/harness/gate-mode-as-data-decisions.md, confirmed_at 2026-07-23)

**Avoid**
- Reading policy from the worktree while every other input comes from the index. An unstaged `"mode": "warn"` edit then lets a commit through, though the committed tree still ships block-mode policy.
- Advising `VAR=x git commit` to influence the hook. A PreToolUse hook runs before the command, so it only sees the session env, and the prefix has no effect.
- Writing tests that put the manifest only in the worktree. The old suite did this, so it locked in the vulnerable read path and passed.

**Check before done**
- Add a regression test. Commit a block-mode manifest, flip the worktree copy to warn without staging it, stage a gated change with `Lane: normal`, and assert the hook blocks (exit 2).
- Stage the manifest in every fixture that sets a manifest mode.
- Audit which tree each `[ -f ]`, `cat` or `jq <file>` in the hook reads from. A manifest staged for deletion or unreadable from the index must block, not allow.

**Already decided**
- gate-mode-as-data-decisions: gate mode is data in the manifest, the policy read is index-side, and a change to enforcement mode does not change risk classification.
- consumer-risk-modes-index-safe: a consumer hook resolves modes only from the index or embedded defaults, never from `.claude/`.

**Possibly stale**
- All three records carry the note "Superseded by specs/simplify-hook-surface (2026-09-29): risk-corroboration.sh merged into hooks/commit-gate.sh".
- The `affects` paths are missing. Searching the worktree found no `hooks/risk-corroboration.sh`, `hooks/commit-gate.sh`, `hooks/lib/gate-modes.default.sh`, `scripts/check_gate_modes_smoke.py` or `scripts/check_manifest.py`.
- `harness-manifest.json` is also missing from the repo root and from `plugins/harness/`. `plugins/harness/hooks/` holds only `clean-worktrees.sh`, `hooks.json`, `merge-guard.sh`, `pr-opened.sh`, `secrets-scan.sh` and `session-rules.sh`.
- I did not find the regression test file `tests/hooks/risk-corroboration.test.sh`. I did not search `tests/` for it by name.
- Commit `880eb15` and the test name "Codex PR#160" cannot be checked from the files I read.
- The CI drift guard for the embedded defaults (`check_gate_modes_smoke.py`) no longer exists, so that safeguard is not in the repo.
- The commands that need the missing files are out of date: the smoke-check and manifest-checker scripts, and any edit to `risk-corroboration.sh`. The index-read principle still holds, because it needs only `git show` and `jq`.
- All three records are over 30 days old. At today's date, 2026-11-04, they are 103 days (2026-07-23, two records) and 90 days (2026-08-06).
- The detail that "2 warn / 7 block parity" is the embedded default may have changed with the hook merge.

**Search surface:** docs/solutions/INDEX.md, docs/solutions/critical-patterns.md, docs/solutions/harness/gate-config-must-read-index.md, docs/solutions/harness/consumer-risk-modes-index-safe.md, docs/solutions/harness/gate-mode-as-data-decisions.md. Also searched for the `affects` paths with `ls` and `find` under the repo root and `plugins/harness/hooks`.
