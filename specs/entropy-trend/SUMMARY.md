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

### Deviations

- Rule 1 — Task 1.1's code-quality review found a real correctness bug: `scripts/harness-audit.sh` crashed with `unbound variable` under `set -u` on bash 3.2 (macOS) when check 4's file-array was empty (no `run-tests.sh`/workflows present). Fixed with the standard `${arr[@]+"${arr[@]}"}` guard + a regression test. Commit `1eddcbd`.
- Rule 1 — Task 2.1's implementer deviated from the plan's literal wording (plain relative call to `harness-audit.sh`) after finding it breaks under `--root` in tests (fixture dirs don't contain their own copy of the script); used `"$(dirname "$0")/harness-audit.sh"` instead, verified correct in both production and test invocation paths. Commit `e3d2146`.
- Rule 1 — Task 2.3's code-quality review found a real correctness bug: the new "Audit Trend" section crashed the entire `harness-status.sh` script (under `set -e`) on a single malformed `audit-log.jsonl` line, contradicting the file's own graceful-degradation design. Fixed with a `try/except` skip-bad-line guard. Commit `5b506ec`.
- Rule 1 — Final correctness-review (whole-diff, adversarial) found the `5b506ec` guard only caught `JSONDecodeError`, not `KeyError` — a syntactically-valid JSON line missing `date`/`findings`/`band` still crashed the script (the `d[...]` dereferences sat in a `print()` outside the `try` block). Fixed by moving `print()` inside `try` and broadening to `except (json.JSONDecodeError, KeyError, TypeError)`. Scored 100/100 by independent scorer. Commit `5590288`.

### Advisory Findings

<!-- Correctness-review findings scored <80 — real but not blocking, recorded per skills/correctness-review/SKILL.md threshold gate. -->

- `scripts/bookkeeping.sh:111` — `$(dirname "$0")/harness-audit.sh"` resolves incorrectly if `bookkeeping.sh` is invoked via a **relative** path together with `--root DIR` pointing at a different tree (after the script's own `cd "$ROOT"`, the relative `dirname "$0"` no longer points at the real `scripts/` dir). Confirmed reproducible via manual repro, but neither the production workflow (`.github/workflows/post-merge-maintenance.yml`, which never passes `--root`) nor the test suite (which invokes via an absolute `$SCRIPT` path) ever exercises this pattern — scored 50/100 (real, but only reachable via a manual invocation style nothing in this codebase uses). Not fixed; left as advisory per the threshold-80 gate. A future maintainer running this manually with `--root` against a different tree via a relative path should resolve `SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"` before the `cd "$ROOT"` if this ever becomes a real usage pattern.

### Intent Findings

<!-- Intent-review findings — the third oracle, blind to PLAN.md, checked against this SUMMARY's ### Intent verbatim. -->

- **drift (behaviorally different, now confirmed by user 2026-07-04)** — the source intent (`docs/harness-v03-plan-overview.md` §2/§3 Wave 4) says emit `audit-log.jsonl` "mỗi CI run" (every CI run). The shipped implementation emits one line per **merged PR only**, via `scripts/bookkeeping.sh` (invoked exclusively by the existing `.github/workflows/post-merge-maintenance.yml`, `pull_request_target: closed`) — not on every push/PR run of `harness-ci.yml`. This was a deliberate choice made while writing `PLAN.md` (its Non-goals section: "No new GitHub Actions workflow and no job that runs on every push — the only write-back-to-repo mechanism in this repo is the existing post-merge bookkeeping PR flow"), but that rationale lived only in PLAN.md, not in this SUMMARY where the intent oracle lives — the intent reviewer correctly flagged it as an undocumented narrowing. Presented to the user as an explicit choice (merge-only vs. a new per-push workflow requiring new `contents: write` permission and commits to arbitrary PR branches — itself a Rule-4-flavored architectural change under this repo's own hard-gate rules); user confirmed **merge-only (as built)** is correct. No code change required. Resolved.
