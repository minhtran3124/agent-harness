<!-- Header is machine-read by risk-corroboration.sh (Lane) + trust-metrics ledger. -->

# fix-skill-doc-truth — Summary

Lane: normal
Confidence: high
Reason: Doc-truth fixes to SKILL.md prose (not high-blast engines/hooks); flags 8 (existing documented behavior). No hard gate — skill markdown is not a high-blast file per Rule 4.
Flags: existing-behavior
Affects: skills/*/SKILL.md + two reviewer-prompt templates (documentation only)
Input-type: harness improvement

> Lane drives ceremony; Confidence drives interruption. Normal lane, high confidence
> (factual contradictions verified against CLAUDE.md / actual repo), proceed autonomously.

### Intent

Wave 0c của harness v0.3 (docs/harness-v03-plan-overview.md): sửa doc-truth trong skills. Cụ thể (từ deep review): finishing-a-development-branch nói "specs/ gitignored" (sai — CLAUDE.md nói specs/ tracked + shipped transition được commit) và hardcode `cd apps/api && python -m pytest` (repo này dùng scripts/run-tests.sh); executing-plans thiếu review chain dù docs nói tương đương sdd; subagent-driven-development dispatch agent phantom superpowers:code-reviewer không có fallback; create-pr default base `dev` (repo dùng main); câu tiếng Việt sót trong 3 file; mâu thuẫn brainstorming↔using-git-worktrees.

## What changed

Corrected factual drift across eight skill docs so the prose matches how the repo actually
behaves:
- **finishing-a-development-branch** — replaced the 4 false "`specs/` is gitignored" claims with
  "`specs/` is tracked → commit the `shipped` transition" (per CLAUDE.md); replaced the hardcoded
  `cd apps/api && python -m pytest` with project-generic guidance + this repo's `bash scripts/run-tests.sh`.
- **executing-plans** — added the missing final review chain (`/correctness-review` → `/intent-review`)
  so the "separate session" path ships the SAME gates sdd advertises; fixed the stale "present
  options, execute choice" description of finishing.
- **subagent-driven-development/code-quality-reviewer-prompt** — added an in-repo fallback
  (`reviewer` agent / `/code-review`) for when the external `superpowers:code-reviewer` is absent.
- **create-pr** — default base branch now derives the repo default (falls back to `main`), was `dev`.
- **using-git-worktrees** — fixed the "Called by: brainstorming — REQUIRED" line (brainstorming
  hands off only to xia2 → writing-plans; it never calls worktrees).
- Translated 3 leftover Vietnamese sentences to English (sdd, correctness-review SKILL + prompt).

### Rationale

Every changed line was a verified contradiction: the "specs/ gitignored" claim is refuted by
CLAUDE.md and by Wave 0a's own committed spec files; `apps/api` does not exist in this repo;
`superpowers:code-reviewer` is tiered documented-only (not present); the brainstorming line
contradicts brainstorming's own "ONLY xia2 → writing-plans" rule. Doc-truth drift is the exact
failure class the deep review flagged as eroding trust.

### Alternatives considered

- Fix visual-planner's `apps/api` path comments too — rejected: they live in the high-blast
  skill engine (`render_plan.py`/`view_plan.py`, Rule 4) and are example/search-path context, not
  a misleading contract; out of scope for a normal-lane doc PR. Noted for a later wave.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| harness test suite + doc-truth lint | `bash scripts/run-tests.sh` | 0 | ALL GREEN; doc-truth lint passes (no missing paths, hook table matches settings.json) |
| no leftover drift strings | `bash -c '! grep -rn "cho dù" skills/ && ! grep -rn "cd apps/api && python -m pytest" skills/finishing-a-development-branch/'` | 0 | Vietnamese + hardcoded apps/api test cmd gone |

### Rollback

- `git revert <merge-sha>` (docs-only; no runtime state).

### Harness-Delta

- backlog — a doc-truth linter that catches PROSE contradictions (not just missing paths) would
  have caught "specs/ gitignored" vs CLAUDE.md; candidate for the manifest/entropy work (Wave 2/4).
