# branch-per-lane

Lane: high-risk
Confidence: high
Reason: Hard gate — edits a wired hook (`hooks/branch-isolation-guard.sh`, high-blast: auto-runs on every Write/Edit of every session) and redefines the workflow's lane→route contract. Direction was given explicitly by the user, so confidence is high; the gate still requires high-risk ceremony.
Flags: high-blast file (hooks/*), workflow redefinition

### Intent

> "I want to update that every lane: tiny, normal, high-risk that always create branch before
> starting implement. I dont want to code directly on main or feature branch"

Clarified by the user when I misread it as a protected-branch blocklist:

> "ko phai la cam branch nao, ma la nen tao branch cho bat ky lane nao"
> (it is not about forbidding branches — it is that a branch should be created for any lane)

So the rule is **positive**, not a blocklist: *every lane creates a branch before implementing.*
The set of protected branches is deliberately **unchanged** (`HARNESS_SHARED_BRANCHES`, default
`main master`).

### What changed

The hole was that `hooks/branch-isolation-guard.sh` fired only when an active `PLAN.md` existed.
The tiny lane has no plan **by definition**, so tiny-lane edits wrote straight to `main` — and
`skills/feature-intake/SKILL.md` documented that as intentional ("no branch — lands on the current
branch **by design**"). Branch creation was otherwise prompt-only, which the hook's own header
already called out as the gap it exists to close.

- `hooks/branch-isolation-guard.sh` — dropped the active-plan condition. The hook now denies an
  implementation edit on a shared branch for **every** lane. `specs/` stays exempt so intake can
  write `SUMMARY.md` *before* the branch exists (otherwise the rule would be unsatisfiable: you
  cannot record the lane that tells you to branch).
- `tests/hooks/branch-isolation-guard.test.sh` — 6 → 9 cases. The first case is the regression
  lock: *"TINY LANE (no plan at all) on main → DENY"*. It **fails against the old hook**.
- `skills/feature-intake/SKILL.md` — lane table + a new "The branch rule" section: tiny gets
  `git checkout -b`, normal/high-risk get `/using-git-worktrees`. Ceremony scales with risk; the
  branch does not.
- `rules/auto-correct-scope.md`, `CLAUDE.md`, `skills/README.md` — lane tables and workflow
  diagrams that claimed "tiny → direct edit (no branch)".

### Deviations

- Rule 2 — Added two test cases beyond the literal ask (`specs/` writable with **no** plan
  present; break-glass on the tiny lane). Both are reachable states the change newly creates:
  without the first, tiny-lane intake could not write `SUMMARY.md` at all.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| hook contract, incl. the closed hole | `bash tests/hooks/branch-isolation-guard.test.sh` | 0 | 9 passed. Case 1 (tiny lane, no plan, on main → DENY) fails against the pre-change hook — it is the regression lock. |
| full suite (hooks + scripts + python + doc-truth + manifest) | `bash scripts/run-tests.sh` | 0 | ALL GREEN |
| the rule holds for the harness itself | `git branch --show-current` | 0 | `feat/branch-per-lane` — this change was implemented on a branch cut before the first edit, per the rule it introduces. |

### Rollback

- Revert the whole change: `git revert <sha>` (single commit; hook + tests + docs move together).
- Emergency, without a revert: `export HARNESS_SHARED_BRANCHES=""` — the hook then protects no
  branch and silently allows every edit (it exits 0 when the current branch is not in the list).
- Per-edit escape hatch, kept deliberately: `BRANCH_ISOLATION_REASON="<why>"` allows a single
  write and appends the reason to `docs/harness-experimental/break-glass-log.md`.

### Blast radius / who this bites

This hook is **wired** and fires on every `Write|Edit` in every session, in this repo and in every
project the harness is deployed into. The behavior change is a **tightening**: work that used to
be silently allowed on `main` (any tiny-lane edit; any edit at all when no plan was active) is now
denied. That is the intent, but it means anyone mid-edit on `main` will start seeing denials with
no code change on their side. The deny message names both fixes (`git checkout -b` for tiny,
`/using-git-worktrees` otherwise) and the break-glass variable.
