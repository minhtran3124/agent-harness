# Design — Ticket-source prefix for spec folders

- Slug: `gh-121-spec-ticket-prefix`
- Source: https://github.com/minhtran3124/agent-harness/issues/121
- Status: approved (user, 2026-07-20)
- Lane: high-risk (hard gate: high-blast `hooks/*` in scope — resolved as verify-only, see §4)

## Problem

Spec folders are named `specs/<slug>/` with a free-form kebab-case slug. There is no way to
trace a spec folder back to its originating ticket (GitHub issue, Linear ticket). The folder
name should carry a ticket-source prefix, and every doc/prompt/rule/hook that references the
convention must state — and tolerate — the same thing.

## Decisions already made (human, recorded in ESCALATIONS.md)

- **E001:** High-risk confirmed; full chain (brainstorming → xia2 → writing-plans → worktree → subagent-driven-development).
- **E002:** Issue defaults adopted — `gh-<issue#>-<slug>` / `lin-<TICKET-ID>-<slug>`; **plain `<slug>`** for ticket-less work (no `adhoc-` prefix); existing folders **grandfathered**, not migrated.
- **Enforcement:** convention-only — no new gate, no hook behavior changes. (With a plain-slug
  fallback, an unprefixed folder is indistinguishable from deliberate ticket-less work, so a
  blocking gate is logically impossible; an advisory warn was offered and declined.)

## 1. The convention (normative)

| Ticket source | Folder name | Example |
|---|---|---|
| GitHub issue | `specs/gh-<issue#>-<slug>/` | `specs/gh-121-spec-ticket-prefix/` |
| Linear ticket | `specs/lin-<TICKET-ID>-<slug>/` (ticket ID keeps native case) | `specs/lin-ENG-315-user-quota/` |
| No ticket | `specs/<slug>/` (plain, unchanged) | `specs/fix-hook-command-matching/` |

- `<slug>` stays short kebab-case in all three forms. Case rule, stated explicitly in the
  canonical statement: the prefix (`gh-`/`lin-`) and `<slug>` are lowercase; only the Linear
  ticket ID keeps its native (upper) case — do not normalize it.
- **Grandfathering:** existing folders are never renamed. All gates remain agnostic — they parse
  `specs/<anything>/` and treat the full folder name as the opaque slug.
- **Branch names inherit for free:** the existing `<type>/<slug>` rule now yields
  `fix/gh-121-spec-ticket-prefix` because the slug itself carries the prefix. No separate
  branch-naming rule is introduced.
- Canonical statement lives in `templates/structure/specs-README.md`; this repo's
  `specs/README.md` mirrors it (its "This project uses:" line is updated).

## 2. Derivation at intake (the only behavioral change)

`skills/feature-intake/SKILL.md` (slug-derivation / Arguments section) gains the rule:

1. Request references a GitHub issue (URL, or `#N` resolvable in the working repo) → `gh-<N>-<slug>`.
2. Request references a Linear ticket (URL or `TEAM-###` identifier) → `lin-<TICKET-ID>-<slug>`.
3. Otherwise → plain `<slug>` (today's behavior).

First match wins, in the order above — a request referencing both a GitHub issue and a Linear
ticket gets `gh-`. This clause is stated in the feature-intake edit.

Intake is the single point where the prefix is born. Every downstream skill (writing-plans,
executing-plans, subagent-driven-development, reviews, compound, finishing) uses the folder
name opaquely and needs no logic change — only doc-gloss updates (§3).

## 3. Doc sweep (surgical)

Every file in issue #121's checklist is reviewed; edits are gloss-level only — where a doc
says `<slug>` is "short kebab-case", it now says the folder name may carry a ticket-source
prefix (`gh-`/`lin-`) per the canonical statement. No behavioral prose changes.

- **Templates:** `templates/structure/specs-README.md` (canonical), `templates/SUMMARY.template.md`, `templates/ESCALATIONS.template.md`.
- **Rules:** `rules/plan-format.md` (frontmatter `slug:` gloss), `rules/orchestration.md`, `rules/auto-correct-scope.md`, `rules/wave-parallelism.md`.
- **Skills:** `feature-intake` (§2 — the one real change), `writing-plans`, `executing-plans`, `subagent-driven-development`, `brainstorming` (+ reviewer prompt), `correctness-review` (+ prompts), `intent-review` (+ prompt), `finishing-a-development-branch`, `using-git-worktrees`, `visual-planner`, `compound` (+ README + prompts), `skills/README.md`.
- Constraint: doc-truth lint (`scripts/lint-doc-truth.sh`, run by `scripts/run-tests.sh` and CI) must stay green; all doc updates land together.

## 4. Hooks & scripts: verify, don't modify

Grep evidence (2026-07-20): every parser matches the folder segment generically —
`branch-isolation-guard.sh` (`specs/*` case), `blast-radius-check.sh` (`specs/*` +
`specs/*/PLAN.md` glob), `render-plan-on-write.sh` (`specs/*/PLAN.md`),
`commit-quality-gate.sh` (`^specs/[^/]+/`), `risk-corroboration.sh` (`specs/*/SUMMARY.md`),
`bookkeeping.sh` (`specs/[^/]+/SUMMARY\.md` + `cut -d/ -f2`), `ci-strict-gate.sh`
(`(^|/)specs/[^/]+/SUMMARY\.md$`), `check_lane_evidence.py` / `verify_summary.py` (slug →
`specs/<slug>/SUMMARY.md` path join), `render_plan.py` (path arg), `harness-audit.sh` and
`lint-doc-truth.sh` (generic `specs/*` globs — confirmed by spec review).

None of these key on the slug's *shape*, so **no hook/script code changes**. Instead the suite
run by `scripts/run-tests.sh` gains regression tests using a prefixed fixture (e.g.
`specs/gh-999-fixture/`) asserting, at minimum:

- `commit-quality-gate.sh` slug extraction (Check 1.5 ESCALATIONS gate + Check 1.6 lane evidence) fires for a prefixed folder;
- `check_lane_evidence.py gh-999-fixture` and `verify_summary.py --check gh-999-fixture` resolve the path;
- `bookkeeping.sh` extracts the full prefixed name as the slug;
- `ci-strict-gate.sh` regex matches a prefixed SUMMARY path;
- `render-plan-on-write.sh` / `branch-isolation-guard.sh` / `blast-radius-check.sh` path matches accept prefixed folders.

This converts the issue's "grandfathering is likely fine (must be verified)" from assumption
to proof, per `not_observed != absent`.

The concrete test-file location (existing suite file vs. a new one under the harness test set
run by `scripts/run-tests.sh`) is deliberately left to PLAN.md, which must pin it down so each
task's Verify command is concrete.

## 5. Dogfood

This feature's own folder was renamed `specs/spec-ticket-prefix/` →
`specs/gh-121-spec-ticket-prefix/` at design time — the one and only migration, exercising the
convention end-to-end (branch name, SUMMARY, ESCALATIONS, gates) while every other existing
folder stays grandfathered.

## Non-goals

- No migration of existing spec folders (grandfathered).
- No `adhoc-` prefix for ticket-less work.
- No mechanical enforcement (gate/warn) of the naming convention.
- No new prefix vocabulary beyond `gh-`/`lin-` (extensible later by editing the canonical statement).

## Success criteria

1. `/feature-intake` derives ticket-prefixed folder names per §2.
2. Every doc in §3 states the same convention; doc-truth lint green.
3. New regression tests (§4) pass; full `bash scripts/run-tests.sh` green on an unmodified hook/script set.
4. Existing unprefixed folders keep working — zero gate regressions (proved by the existing suite staying green).

## Error handling / risks

- **Doc drift risk:** many docs restate the convention; mitigated by pointing them at the
  canonical statement rather than duplicating the table everywhere.
- **False confidence risk:** a parser not on the issue's list could still key on slug shape;
  mitigated by xia2's repo-wide sweep for `specs/` path parsing before planning.
- **Rollback:** pure docs/tests change — `git revert <sha>`.
