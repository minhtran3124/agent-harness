<!-- Header is machine-read by risk-corroboration.sh (Lane) + trust-metrics ledger. -->

# fix-session-knowledge-root — Summary

Lane: high-risk
Confidence: high
Reason: Hard gate — changes .claude/hooks/session-knowledge.sh (high-blast file); flags 8 (existing hook behavior) + 9 (bug never caught by existing tests).
Flags: existing-behavior, weak-proof
Affects: hooks/session-knowledge.sh (+ .claude/ deployed copy)
Input-type: harness improvement

> Lane drives ceremony; Confidence drives interruption. Hard gate forces high-risk;
> confidence high (bug root-caused + reproduced), so work proceeds autonomously.

### Intent

Wave 0b của harness v0.3 (docs/harness-v03-plan-overview.md): fix DR-2. hooks/session-knowledge.sh resolve knowledge base bằng `$HOOK_DIR/../docs/solutions`, nhưng bản deployed chạy từ `.claude/hooks/` nên tìm `.claude/docs/solutions` (không tồn tại) → mọi session khởi động KHÔNG có knowledge base mà CLAUDE.md tuyên bố được load; `exec 2>/dev/null` che luôn lỗi. Fix: resolve repo root bằng `git rev-parse --show-toplevel` như các hook anh em; thêm regression test chạy hook từ vị trí .claude/hooks/ thật (không dùng SESSION_KNOWLEDGE_DIR override — chính override đó khiến bug lọt test).

## What changed

`session-knowledge.sh` now resolves the repo root with `git -C "$HOOK_DIR" rev-parse
--show-toplevel` (with the `$HOOK_DIR/..` fallback kept for non-git contexts), so the deployed
copy at `.claude/hooks/` finds `docs/solutions/` at the real project root instead of the
non-existent `.claude/docs/solutions`. Added a regression test that runs the hook from a
simulated `.claude/hooks/` location WITHOUT the `SESSION_KNOWLEDGE_DIR` override, asserting it
emits the knowledge-base context — closing the exact test blind spot that let DR-2 ship.

### Rationale

Every sibling hook resolves the root via `git rev-parse --show-toplevel`; this hook alone used
`$HOOK_DIR/..`, which is correct only when run from `hooks/` (source), not `.claude/hooks/`
(deployed — the copy Claude Code actually runs). `exec 2>/dev/null` is KEPT: a SessionStart hook
must stay quiet by design (mirrors state-breadcrumb.sh), and the durable guardrail against a
silent regression is the new deployed-location test, not stderr noise nobody reads.

### Alternatives considered

- Remove `exec 2>/dev/null` (per DR-2 note) — rejected: makes every session noisy; the test is
  the trustworthy guardrail, not hoping a human notices stderr.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| harness test suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN |
| deployed-location regression | `bash tests/hooks/session-knowledge.test.sh` | 0 | 8 passed; new DR-2 test builds a temp `.claude/hooks/` + runs the hook there, proven to fail on the old resolver |

### Rollback

- Revert the PR: `git revert <merge-sha>` (hook is a pure script, no persisted state).
- Per-file: `git checkout HEAD~1 -- hooks/session-knowledge.sh`
- Redeploy: `bash scripts/deploy-harness.sh`

### Harness-Delta

- backlog — a whole class of hooks was untestable at their DEPLOYED path because tests override
  the resolver; consider a shared "run this hook from a simulated .claude/hooks/" test helper.
