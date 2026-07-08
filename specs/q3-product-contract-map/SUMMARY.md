# q3-product-contract-map — Summary

Lane: normal
Confidence: high
Reason: Initially high-risk (edits `hooks/blast-radius-check.sh` = high-blast hard gate); human narrowed scope to wire advisory into `scripts/harness-audit.sh` instead, removing the hook edit and the hard gate. Remaining flags: 1 → normal.
Flags: existing-behavior (modifies scripts/harness-audit.sh)
Affects: harness-manifest.json (contracts block), scripts/check_manifest.py (Shared-Contract surfaces); no high-blast file touched after scope narrowing
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<!-- Verbatim scope the user directed work at: MIN-64 "Level A (static manifest)". The user
     ran `/feature-intake for MIN-64` after approving option A ("ok with A"). The scope-deciding
     text is MIN-64's Scope section, quoted verbatim below. -->

Implement MIN-64 — "Q3 product-contract map — static manifest (Level A) for contract-level blast radius". Scope — Level A (static manifest):

- Thêm khối `contracts` vào `harness-manifest.json`: mỗi contract `{ surface, consumers[] }` cho 5 contract (hook registration, artifact schema, lane→evidence mapping, hard-gate vocabulary, skill handoff edges).
- `scripts/check-contract-impact.sh <file>`: tra ngược file vừa sửa có phải `surface` của contract nào → in danh sách `consumers` cần verify. Exit 0, advisory-only.
- Wire advisory vào `scripts/harness-audit.sh` (human chose this over `hooks/blast-radius-check.sh` at intake to avoid the high-blast hard gate): khi edit chạm surface contract → nhắc consumers. Advisory chạy on-demand khi gọi harness-audit, không tự động PostToolUse.
- `check_manifest.py` mở rộng để guard khối `contracts` (surface/consumer paths tồn tại trên đĩa).

Success criteria: sửa `settings.json` hoặc `templates/SUMMARY.template.md` → advisory in ra đúng danh sách consumers; `scripts/run-tests.sh` xanh; doc-truth lint không gãy. Level B/C ngoài scope.

## What changed

<!-- filled at implementation -->
Not started — intake only.

### Rationale

Level A (static manifest in `harness-manifest.json` + a lookup script) was chosen over graph-derived (B) or contract-tests (C) because it is ~0-cost, reuses the existing manifest + `blast-radius-check.sh`, and directly closes the Q3 file-level→contract-level gap for the non-code contracts the code-review-graph cannot see (settings.json keys, template columns, prose handoff edges).

### Alternatives considered

- Level B (auto-derive consumers from code-review-graph) — deferred: only covers code contracts, still needs manual entries for non-code surfaces.
- Level C (contract tests asserting surface↔consumer) — deferred to the highest-churn contracts (SUMMARY schema, hard-gate vocab) once Level A exists.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| <to be filled at implementation> | `scripts/run-tests.sh` |  |  |

### Rollback

- Revert manifest + script + hook edits: `git revert <sha>` (single feature branch, fully reversible; no data/schema/migration touched).

### Harness-Delta

- none
