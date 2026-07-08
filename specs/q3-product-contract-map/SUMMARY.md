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

Added a declarative `contracts` block to `harness-manifest.json` (5 contracts, each `{surface[], consumers[]}`) mapping every internal product-contract surface to the files that depend on it. `scripts/check-contract-impact.sh` maps changed files → impacted contracts → consumers to re-verify (advisory, exit 0; `--changed` reads the working-tree diff). `scripts/check_manifest.py` gained a validation pass that fails if any contract path is missing on disk. `scripts/harness-audit.sh` gained an advisory "section 7" that surfaces contract-impact reminders for dirty surfaces — counted separately from drift `findings`/`band`. No `hooks/*` or `settings.json` edited (intake scope decision).

### Rationale

Level A (static manifest in `harness-manifest.json` + a lookup script) was chosen over graph-derived (B) or contract-tests (C) because it is ~0-cost, reuses the existing manifest + `blast-radius-check.sh`, and directly closes the Q3 file-level→contract-level gap for the non-code contracts the code-review-graph cannot see (settings.json keys, template columns, prose handoff edges).

### Alternatives considered

- Level B (auto-derive consumers from code-review-graph) — deferred: only covers code contracts, still needs manual entries for non-code surfaces.
- Level C (contract tests asserting surface↔consumer) — deferred to the highest-churn contracts (SUMMARY schema, hard-gate vocab) once Level A exists.

### Deviations

- Rule 2 — Added a `CLAUDE.md` stub to `build()` in `scripts/test_check_manifest.py` so the OK-fixture stays green with the new `contracts` block referencing it. Commit `acf0d10`.
- Rule 1 — (correctness-review fix) Added defensive `isinstance` guards to `check_manifest.py` section C so malformed contract shapes (non-dict value, string `surface`/`consumers`, non-string path element) emit a clean drift diagnostic instead of crashing with a traceback. Matches the `bash-empty-array-and-jsonl-parsing-gotchas` compound lesson. Commit `56735d0`.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Full harness suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN — 151 passed, 1 skipped; incl. doc-truth lint + manifest consistency |
| Manifest checker (contracts pass) | `python3 scripts/check_manifest.py` | 0 | "consistent"; fails if any contract path missing |
| Contract impact mapper | `bash scripts/check-contract-impact.sh templates/SUMMARY.template.md` | 0 | prints `artifact-schema-summary` + its 3 consumers |
| Audit reminders (json) | `bash scripts/harness-audit.sh --json` | 0 | `checks.contract_impact` present; excluded from `findings`/`band` |

### Rollback

- Revert manifest + script + hook edits: `git revert <sha>` (single feature branch, fully reversible; no data/schema/migration touched).

### Harness-Delta

- backlog — `hooks/blast-radius-check.sh` warned on every edit that files were outside `specs/entropy-trend/PLAN.md`'s `<files>` set: a stale `status: active` plan (`entropy-trend`) on `v2` is picked as "the active plan" even though our `q3-product-contract-map` plan is also active. The hook has no notion of *which* active plan owns the current worktree → false blast-radius warnings when >1 plan is active. Worth a `/compound` note.
