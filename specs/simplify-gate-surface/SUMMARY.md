# simplify-gate-surface — Summary

Lane: high-risk
Confidence: high
Reason: touches hooks/risk-corroboration.sh and the hard-gate list itself (high-blast + workflow-engine); it changes how the commit gate decides to block, so it is gate-defining work.
Flags: high-blast, workflow-engine
Affects: risk-corroboration gate contract (harness-manifest.json ↔ hooks/risk-corroboration.sh ↔ scripts/check_manifest.py)
Input-type: harness improvement
Route: high-risk chain — design.md + PLAN.md written; next `/using-git-worktrees` → `/subagent-driven-development` → `/correctness-review` → `/intent-review`
Escalate: no — the hard gates were narrowed by the human at request time ("muc 1 -> 3"), which scopes the work to review items 1→3 and leaves items 4→7 on the backlog

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> make the deep review code. now I feel we have a lot of scripts and gates. They are making block auto-process sometimes.
>
> I want to review all scripts and related gate/block. Thinking to make it simple and ez maintain.
>
> viet design + plan cho muc 1 -> 3

Items 1→3 of the review's cut list, verbatim as delivered:

1. **Invert the manifest coupling.** Hook reads `harness-manifest.json`; delete `category_mode()` and the source-regex checks in `check_manifest.py`. Unblocks everything else.
2. **Add an `env` block to `settings.json`** so the knobs are reachable — and set `RISK_WARN_CATEGORIES="weakening-validation"` there, which fixes your screenshot incident permanently and correctly.
3. **Make `workflow-engine` warn-mode, not block.** At 85% firing it's noise.

## What changed

- `hooks/risk-corroboration.sh` — `category_mode()` now reads per-gate `mode` from
  `harness-manifest.json` (one `jq` call; fail-safe `block` on absent/invalid manifest, so
  consumer repos keep strict behavior). Comments + BLOCKED message now give a working
  override path (`settings.local.json → env` / manifest `mode`), replacing the impossible
  inline `VAR=x git commit` advice.
- `scripts/check_manifest.py` — dropped the `category_mode` source-regex; the manifest is the
  mode authority. `add_cat` ↔ `detectable` stays bidirectional.
- `harness-manifest.json` — `workflow-engine` (85% firing) and `weakening-validation`
  (precision 0) flipped to `mode: warn`; measurements recorded in each `desc`.
- `scripts/check_gate_modes_smoke.py` (new, wired into `run-tests.sh`) — pins 2-warn/7-block.
- `tests/hooks/warn-mode-smoke.test.sh` (new) — proves the incident commit passes and the
  loosening stays scoped (hooks/ still blocks).
- Docs aligned: `CLAUDE.md:52`, feature-intake HARD-GATE + gate list, `rules/orchestration.md`.
- Intake classification unchanged — both gates still force `Lane: high-risk` (LC-11 valid).

**Activation pending:** the live gate is the deployed copy `.claude/hooks/risk-corroboration.sh`;
a human-confirmed `scripts/deploy-harness.sh` run is required for this change to take effect
in this repo (see PLAN Task 3.1 / design §4b).

### Rationale

The commit gate has lost discriminating power: `workflow-engine` fires on 34 of the last
40 commits (85%) and 41 of 63 specs declare `Lane: high-risk` (65%), so "high-risk" is the
default state and `/feature-intake`'s classification is nullified. The cheapest fix is not
to delete gates but to make their **mode** data (in `harness-manifest.json`) instead of code
(a `case` statement that `check_manifest.py` regex-parses back out of the hook source).
Once mode is data, loosening a noisy gate is a one-line JSON edit instead of a coordinated
4-file change plus CI.

### Alternatives considered

- **Delete `category_mode()` outright** (the 2026-07-16 over-engineering review's proposal) —
  rejected then and now for the same reason recorded in `phase-2-deep-review-2026-07-16.md:17`:
  `check_manifest.py` regex-parses those branches, so deleting them fails CI on 8 slugs.
  This spec removes the *reason* that objection existed rather than fighting it.
- **Add `env` to the root `settings.json`** (review item 2 as originally written) — rejected:
  `scripts/deploy-harness.sh:335-351` merges with `$cur` as the base and only replaces
  `.hooks`, so a new top-level key reaches a consumer on first install but is silently dropped
  on every re-sync. See `design.md` §3.
- **Delete the `weakening-validation` detector** — deferred to review item 6; setting its mode
  to `warn` is reversible and preserves the signal in the log.

### Deviations

- Rule 1 — correctness-review round 1 (3 findings ≥75, all fixed in one round):
  - `scripts/check_gate_modes_smoke.py` — malformed `detectable` entry (missing `slug` /
    non-dict) crashed with a traceback; now reported as a clean `gate-modes:` drift line.
  - `hooks/risk-corroboration.sh` header comment — fail-safe claim narrowed: it assumes `jq`
    (without jq the hook never gates at all — pre-existing behavior, now stated).
  - SUMMARY `### Verify` — the full-suite row violated
    `verify-row-must-be-pipe-free-and-under-60s` and would have turned CI red; replaced with
    the prose line under the table.
- Rule 3 — `specs/slim-skill-surface/PLAN.md` still said `status: active` after its PR merged,
  which mis-aimed `blast-radius-check`; flipped to `shipped` (wave 1 commit).

### Advisory Findings

Correctness-review advisories (scored <75, not auto-fixed — recorded for the human):

- `scripts/check_manifest.py:85` — the same unguarded `g["slug"]` KeyError exposure exists
  here, pre-existing (`unmodified-line`, score 0). Same fix shape as the smoke script if wanted.
- `tests/hooks/risk-corroboration.test.sh` — the pre-existing `workflow-engine → BLOCKED`
  cases now pass only because `new_repo` temp repos carry no manifest (they exercise the
  consumer-repo fallback, not this repo's warn behavior). Coverage drift, not a runtime bug;
  the warn path is covered by the new manifest-mode cases + `warn-mode-smoke.test.sh`.
- `hooks/risk-corroboration.sh:32` — with `jq` absent the hook exits 0 before any gating
  (fail-open), pre-existing on unmodified lines; the header comment now documents it. A
  `command -v jq` fail-closed guard is a possible hardening, deliberately out of this scope.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Hook contract tests (27 cases, incl. 5 manifest-mode) | `bash tests/hooks/risk-corroboration.test.sh` | 0 | 27 passed — wave 1 | SC-1 |
| Mode source-regex gone from checker | `grep -q category_mode scripts/check_manifest.py` | 1 | 0 occurrences — wave 1 | SC-2 |
| Manifest inventory invariant holds | `python3 scripts/check_manifest.py` | 0 | consistent — wave 1 | SC-3 |
| Checker unit tests | `python3 -m pytest scripts/test_check_manifest.py -q --no-header -p no:cacheprovider` | 0 | 11 passed — wave 1 | SC-2 |
| Gate modes pinned (2 warn, 7 block) | `python3 scripts/check_gate_modes_smoke.py` | 0 | wired into run-tests.sh — wave 2 | SC-4 |
| Docs match wiring | `bash scripts/lint-doc-truth.sh` | 0 | + 4 prose sites hand-verified (CLAUDE.md:52, SKILL.md:29, SKILL.md:~95, orchestration.md:39) — wave 2 | SC-6 |
| Working override path documented | `grep -q settings.local.json hooks/risk-corroboration.sh` | 0 | no inline VAR=x advice remains — wave 3 | SC-5 |
| Incident commit passes; loosening scoped | `bash tests/hooks/warn-mode-smoke.test.sh` | 0 | 2 passed against the real manifest — wave 3 | SC-7 |

Full suite: `bash scripts/run-tests.sh` ran ALL GREEN (185 pytest + all hook suites) in wave 3 — re-run by the CI `tests` job; not a Verify row per docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md.

### Rollback

- `git revert <sha>` — the change is source-only (hook + manifest + checker + docs); no
  migration, no deployed state. To roll back only the loosening without reverting the
  refactor, set the two `mode` fields in `harness-manifest.json` back to `"block"`.

### Harness-Delta

- fix-direct — the harness's own escape hatch was documented in a way that produced unusable
  advice (`RISK_WARN_CATEGORIES=… git commit` as an inline prefix never reaches a PreToolUse
  hook). Task 1.1 corrects the hook's comment and block message. Candidate for `/compound`.
