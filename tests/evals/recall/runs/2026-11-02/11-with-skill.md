Verdict: known risk. Read the gate mode from the git index, not the worktree.

**Do first.**
- Read the mode with `git show :harness-manifest.json 2>/dev/null | jq -r '.hard_gates.detectable[]? | "\(.slug)=\(.mode // "block")"' 2>/dev/null || true`. Treat a missing, unreadable or invalid manifest as `block`. Source: `docs/solutions/harness/gate-config-must-read-index.md`, confirmed_at 2026-07-23. Reason: a worktree read lets an unstaged `"mode": "warn"` edit loosen the decision for a tree that still ships `block`.
- Take modes from only two sources: the index manifest, then embedded in-hook defaults. In `hooks/lib/gate-modes.default.sh`, those defaults were 2 warn and 7 block. Never read `.claude/` or any worktree file for policy. Source: `docs/solutions/harness/consumer-risk-modes-index-safe.md`, confirmed_at 2026-08-06. Reason: `.claude/` is gitignored in consumers, so an agent can edit it and the index can never check it.
- Make loosening a staged change. A durable block-to-warn change is a staged manifest edit. A session-scoped override goes in `settings.local.json` under `env` as `RISK_WARN_CATEGORIES`, which can only loosen. Source: `docs/solutions/harness/gate-mode-as-data-decisions.md`, confirmed_at 2026-07-23, Decisions 2 and 4. The record gives no test command for this.

**Avoid.**
- Do not stage the manifest in your test fixtures and then assert a pass. The old suite wrote the manifest to the worktree without staging it, so it locked in the vulnerable read path. A test with no unstaged case misses the bypass.
- Do not leave one worktree-side read in the hook, such as `[ -f ]`, `cat` or `jq <file>`. That single read is a bypass. The record names one remaining case: `commit-quality-gate.sh` Check 1.6 falls back to the worktree SUMMARY or PLAN when `git show :$path` fails, including on staged deletion.
- Do not advise `VAR=x git commit` to set a hook override. A PreToolUse hook runs before the command and only sees the session environment.

**Check before done.**
- Add this regression case, modelled on the one in `tests/hooks/risk-corroboration.test.sh`. Commit a block-mode manifest. Flip the worktree copy to warn without staging it. Stage a gated change with `Lane: normal`. Assert exit 2 (BLOCKED).
- Test the failure cases. A manifest staged for deletion, or unreadable from the index, must block, not allow.
- Confirm the hook file is mode 100755 in the index if `settings.json` registers it as a bare command. Source: `bare-command-hook-must-be-executable-in-index`, listed in INDEX and critical-patterns; I did not open this record, so it is unverified here.

**Already decided.**
- `docs/solutions/harness/consumer-risk-modes-index-safe.md`: consumers resolve modes from the index manifest or embedded defaults only, never from `.claude/`. This replaces the old block-all fallback with 2-warn/7-block parity.
- `docs/solutions/harness/gate-mode-as-data-decisions.md`: gate mode is manifest data. The policy read is index-side. Enforcement mode and risk classification are separate axes.

**Possibly stale.**
- All three records: every `affects` path is missing from this worktree. That covers `hooks/risk-corroboration.sh`, `hooks/lib/gate-modes.default.sh`, `harness-manifest.json`, `tests/hooks/risk-corroboration.test.sh`, `scripts/check_manifest.py` and `scripts/check_gate_modes_smoke.py`. `plugins/harness/hooks/` holds no commit-gate, risk-corroboration or gate-modes file, and no `harness-manifest.json` exists outside `docs/solutions`. The records may describe a different checkout layout. I found no moved copy under `plugins/harness/`.
- All three records: each carries a footer saying `risk-corroboration.sh` was merged into `hooks/commit-gate.sh` (specs/simplify-hook-surface, 2026-09-29). The hook-specific details are outdated, and the file names may differ. The index-versus-worktree principle does not depend on them.
- `docs/solutions/harness/gate-config-must-read-index.md`: confirmed_at 2026-07-23 is over 30 days before 2026-11-02.
- `docs/solutions/harness/gate-mode-as-data-decisions.md`: confirmed_at 2026-07-23 is over 30 days before 2026-11-02.
- `docs/solutions/harness/consumer-risk-modes-index-safe.md`: confirmed_at 2026-08-06 is over 30 days before 2026-11-02.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/gate-config-must-read-index.md`, `docs/solutions/harness/consumer-risk-modes-index-safe.md`, `docs/solutions/harness/gate-mode-as-data-decisions.md`. I also checked the `affects` paths with ls and find, and listed `plugins/harness/` and `plugins/harness/hooks/`.
