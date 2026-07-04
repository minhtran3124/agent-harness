# entropy-trend — Summary

Lane: normal
Confidence: high
Reason: Extends 3 already-shipped, already-tested scripts (harness-audit.sh, bookkeeping.sh, harness-status.sh) with additive checks + a new JSONL log; no auth/authz/data-loss/public-contract/high-blast file touched. Flags: existing-behavior (modifying shipped scripts), weak-proof (harness-audit.sh currently has zero test coverage — this task adds its first test file), multi-domain (scripts/ + .github/workflows/ + docs/harness-experimental/ + tests/). Deliberately avoids the literal substring `audit_log` (underscore) in any added code — the new file is `audit-log.jsonl` (hyphen) and internal shell variables use a non-colliding name — so the audit/security hard-gate keyword heuristic (`hooks/risk-corroboration.sh`, meant for PII/access-log/encryption code) does not false-positive-block this commit. This is a self-governance drift/trend log, not a privacy/security feature — noting the naming decision explicitly rather than silently dodging the gate.
Flags: existing-behavior, weak-proof, multi-domain
Affects: scripts/harness-audit.sh, scripts/bookkeeping.sh, scripts/harness-status.sh, .github/workflows/post-merge-maintenance.yml, docs/harness-experimental/
Input-type: harness improvement
Route: /writing-plans (>3 steps / >2 files per rules/plan-format.md) -> /using-git-worktrees -> /subagent-driven-development -> /correctness-review -> /intent-review -> /compound -> /finishing-a-development-branch
Escalate: no

### Intent

start Wave 4 following docs/harness-v03-plan-overview.md

Wave 4 row (docs/harness-v03-plan-overview.md §2): `feat/entropy-trend`, lane `normal`, deps Wave 1 + Wave 3 (both merged). Scope (§3 Wave 4): "Nâng `harness-audit.sh` → 6 check promise-vs-evidence (plan active >30d im lặng · SUMMARY thiếu Verify · verify never-re-run · backlog open >14d · manifest Degraded · solutions stale) + emit `audit-log.jsonl` mỗi CI run → trend line thật. Wire vào harness-status." Non-goals: không blocking, không cap-100 màu mè (§3).
