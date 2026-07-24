# Research Brief — Phase B (Portable Deployment)

Depth mode: **Standard** (touches >1 file, so fails Quick; no Deep signal firmly fires — no
schema/migration, no new external dependency, no auth surface; `deploy-harness.sh`'s
`SYNCED_DIRS_RE` is arguably a shared-runtime-contract-adjacent file but the change is additive
registration, not a redesign of the contract itself. Tiebreaker: mapped cleanly, no need to
escalate).

**Stop condition applied:** `specs/gh-129-durable-run-state-phase-b/design.md` (written during
`/brainstorming`, this same session) already performed the equivalent of xia2 Steps 2b–4 in
full — reading `deploy-harness.sh`/`install-harness.sh`/`harness-manifest.json`/
`check_manifest.py` line-by-line, cross-checking `docs/solutions/` decision docs, and confirming
via direct grep that the proposed move is safe. That document fully answers the local-reuse
question, so Steps 5–6 (upstream/docs) are skipped per the skill's own stop condition — this is
pure internal bash/Python-stdlib deploy tooling with no framework or external library in play,
where upstream GitHub patterns and official docs have no applicable target.

---

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Reuse existing (extend `deploy-harness.sh`'s already-generic sync/prune loop; no new mechanism) |
| **Why this is the lightest credible path** | The orphan-pruning mechanism this phase needs already exists and is dir-agnostic (confirmed: it operates on whatever list `SYNCED_DIRS_RE` + the `for d in ...` loop name) — the entire phase is registration into an existing, working system, not new logic. |
| **Confidence** | 90% |
| **Next step** | Proceed to `/writing-plans` using `design.md` §4 as the task source. |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | CLI / harness distribution tooling (a skills-and-hooks framework deployed into consuming repos' `.claude/`) |
| Primary language + runtime | Bash (deploy/install scripts, POSIX-targeted) + Python 3 stdlib-only (`scripts/*.py`) |
| Frameworks / platforms | None — no web framework, no ORM, no package manager manifest in this repo (`ls pyproject.toml requirements.txt setup.py` → all absent, confirmed in Phase A intake) |
| Relevant packages | None (stdlib-only by explicit repo convention, matching `scripts/check_manifest.py`, `scripts/run_state.py`) |
| Detectable versions | N/A — no lockfile/manifest to version-pin against |
| Important constraints | `CLAUDE.md` gotcha: "Re-sync (`scripts/install-harness.sh` / `scripts/deploy-harness.sh`) is conflict-guarded for protected files... a differing local copy is kept by default"; `docs/solutions/harness/resync-protected-files-decisions.md` Decision 3: targeted hardcoded protected-file list, not a checksum manifest — do not generalize it |

---

## Feature Understanding and Assumptions

- **Requested feature:** Make Phase A's `run_state.py` engine reach consuming repos via the
  existing harness distribution mechanism, by relocating it under `runtime/` and wiring that
  directory into the deploy/install/test surfaces the same way `skills/`/`agents/`/`hooks/`/
  `rules/`/`templates/` already are.
- **What success appears to mean:** `bash scripts/deploy-harness.sh --target <dir>` places
  `runtime/run_state.py` + `runtime/test_run_state.py` at `.claude/runtime/`, prunes them on a
  resync if removed from source, survives orphan-pruning without touching consumer-added files,
  and `bash scripts/run-tests.sh` stays green with the moved test file actually running (closing
  the wiring gap discovered mid-brainstorm).
- **Assumptions from the request:** The issue's `harness-manifest.json` registration bullet is
  satisfiable later (Phase C) rather than in this phase — confirmed with the user during
  `/brainstorming` after `check_manifest.py`'s empty-`consumers` rejection was found.
- **Assumptions still needing confirmation:** None outstanding — both open design forks from
  brainstorming (runtime/ move vs. stay, manifest timing) were resolved with the user before this
  research step.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `scripts/deploy-harness.sh:106,146,383,399,411-420` (`SYNCED_DIRS_RE`, its 2 call sites, the sync loop, the summary counters) |
| `Local` | `scripts/deploy-harness.sh:29-34,74-285` (`BOOTSTRAP_OWNED_FILES`, protected-file conflict guard — hardcoded list, confirmed generic-guard does NOT apply per-dir) |
| `Local` | `scripts/deploy-harness.sh:108,302,394-407` (`record_deployed`, `copy_dir` calling it, `prune_orphans` — the existing generic pruning mechanism) |
| `Local` | `scripts/install-harness.sh:33,134,158-167,220,284-299` (`PAYLOAD` array, delegation to `deploy-harness.sh`, legacy-detection, `--keep-sources`) |
| `Local` | `harness-manifest.json:69-76` (`contracts` section shape) + `scripts/check_manifest.py:98-123` (Check C, including the empty-`consumers` rejection that forced the Phase-C deferral) |
| `Local` | `tests/scripts/deploy-prune.test.sh` (56 lines, 6 cases — the pattern the new `runtime-sync.test.sh` mirrors) |
| `Local` | `tests/scripts/install-gitignore.test.sh`, `install-harness.test.sh`, `resync-conflict.test.sh` (adjacent but non-overlapping coverage — `.gitignore` append logic, MCP wiring, protected-file conflicts — none touch directory-sync-set membership) |
| `Local` | `scripts/run-tests.sh:61` (hardcoded `PYTESTS` list, confirmed missing `scripts/test_run_state.py` — verified by running the exact list: `185 passed`, unchanged before/after Phase A) |
| `Local` | `docs/solutions/harness/deploy-harness-does-not-prune-deleted-orphans.md` (`confirmed_at: 2026-07-17` — the pruning "gap" is an already-fixed bug, not a live gap) |
| `Local` | `docs/solutions/harness/resync-protected-files-decisions.md` Decision 3 (targeted list > checksum manifest, deliberate) |
| `Local` | `grep -n "scripts/run_state\|scripts/test_run_state\|__file__\|sys.path" scripts/run_state.py scripts/test_run_state.py` → only `__file__`-relative references, zero hardcoded `"scripts/"` strings — move confirmed safe |
| `Inference` | No `runtime/` directory precedent exists anywhere in this repo's history (`ls runtime/` → absent) — this is a genuinely new top-level source dir, not a rename of something that already had conventions |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** enumerated in the Evidence Ledger above —
  full list already gathered during `/brainstorming`'s exploration step and cross-verified during
  the spec-review loop (two rounds; both factual claims spot-checked against real files, both
  passed on re-verification).
- **Existing abstractions or extension points:** `copy_dir()` + `record_deployed()` +
  `prune_orphans()` are already dir-agnostic — the *only* per-dir-specific surfaces are the
  `SYNCED_DIRS_RE` regex, the `for d in ...` loop literal, the summary-counters block
  (`deploy-harness.sh`), and the separate `PAYLOAD` array (`install-harness.sh`). Four edit
  points, zero new logic.
- **Conventions worth preserving:** `BOOTSTRAP_OWNED_FILES`'s targeted-list philosophy (not
  extended to `runtime/` — nothing there is consumer-customizable); the existing
  `tests/scripts/*.test.sh` file-per-concern layout (favors a new `runtime-sync.test.sh` over
  parametrizing `deploy-prune.test.sh`).
- **What can likely be reused:** the entire prune/sync/manifest-diff mechanism, unchanged.
- **What appears missing locally:** nothing structural — the only genuine gap found was the
  `run-tests.sh` `PYTESTS` wiring omission, unrelated to the runtime/ design fork itself but
  folded into this phase's scope per the user's explicit direction.

---

## Upstream Findings

_Skipped — stop condition applied (see header). This is internal deploy tooling with no
framework/library target; no upstream GitHub pattern search would be applicable._

## Docs Findings

_Skipped — same reason. No official docs domain governs this repo's own bash/stdlib-Python
deploy conventions; the closest thing to "docs" is this repo's own `docs/solutions/`, already
covered under Local Findings._

---

## Recommendation

- **Primary recommendation:** Reuse existing (extend the sync/prune loop + `PAYLOAD`, add one
  new test file, defer manifest registration).
- **Why this is the lightest credible path:** Every mechanism Phase B needs (sync, orphan-prune,
  protected-file exemption philosophy) already exists in a dir-agnostic form; the phase is
  additive registration, confirmed via direct code read, not new engineering.
- **Why the next-best alternative lost:** Building a `runtime/`-specific parallel sync mechanism
  (rather than registering into the existing one) was never seriously on the table — it would
  duplicate `copy_dir`/`prune_orphans` for no benefit, and diverge from the "one generic
  mechanism, N registered dirs" pattern the repo already uses for 5 other dirs.
- **What would change this recommendation:** If `runtime/` were expected to need
  consumer-customizable files (like `rules/behavior.md`), `BOOTSTRAP_OWNED_FILES` would need
  extending too — not the case here; both moved files are fully harness-owned.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:** Low. The move is a pure file relocation (no path-string breakage,
  confirmed by grep); the wiring extensions touch well-tested, already-reviewed scripts, each
  with existing regression coverage the new work extends rather than replaces.
- **Evidence gaps:** None outstanding for this phase's scope.
- **Version uncertainties:** N/A (no dependency versions involved).
- **Follow-up questions for the user:** None — both design forks (runtime/ location, manifest
  timing) were already resolved during `/brainstorming`, before this research step ran.

---

## Source Pack

- **Local files read:** `scripts/deploy-harness.sh`, `scripts/install-harness.sh`,
  `harness-manifest.json`, `scripts/check_manifest.py`, `tests/scripts/deploy-prune.test.sh`,
  `tests/scripts/install-gitignore.test.sh`, `tests/scripts/install-harness.test.sh`,
  `tests/scripts/resync-conflict.test.sh`, `scripts/run-tests.sh`, `scripts/run_state.py`,
  `scripts/test_run_state.py`, `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`,
  `docs/solutions/harness/deploy-harness-does-not-prune-deleted-orphans.md`,
  `docs/solutions/harness/resync-protected-files-decisions.md`,
  `docs/solutions/harness/gate-mode-as-data-decisions.md`,
  `docs/solutions/harness/gap-closure-decisions.md`,
  `docs/solutions/harness/techstacks-project-owned-stack-profiles.md`,
  `specs/gh-129-durable-run-state-phase-b/design.md`,
  `specs/gh-129-durable-run-state-phase-a/SUMMARY.md`.
- **Upstream repositories or pages checked:** none (stop condition applied).
- **Official docs domains or pages checked:** none (stop condition applied).

---

## Evidence Boundary

> Confirmed from artifacts: every file/line reference above (read directly, several spot-checked
> twice across the two spec-review rounds during `/brainstorming`); the `run-tests.sh` wiring gap
> (verified by running the exact hardcoded `PYTESTS` list and comparing counts); the move-safety
> claim (verified by grep for `scripts/`/`__file__` references in both files).
>
> Inferred from patterns: none load-bearing — this brief has no `Inference`-only claims that
> drive the recommendation (the one `Inference` row in the Evidence Ledger is a negative/absence
> observation, corroborated by an actual `ls runtime/` check, not a guess).
>
> Not checked: cross-OS (Ubuntu) behavior of the new test file — `bash scripts/run-tests.sh` is
> only run locally (macOS) in this session; CI will exercise Ubuntu on push, matching how Phase A
> was validated (explicitly out of scope for local research, per this repo's CI setup).
