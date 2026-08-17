---
problem_type: knowledge
module: harness
tags: templates-structure, init-structure, scaffold, template-instance-parity, techstacks, create-if-missing, consumer-reach, silent-divergence
severity: standard
applicable_when: Editing any file under the repo root that has a source twin in `templates/structure/` (e.g. `techstacks/README.md` ↔ `templates/structure/techstacks-README.md`) — before committing the instance edit alone.
affects:
  - templates/structure/techstacks-README.md
  - techstacks/README.md
  - scripts/init-structure.sh
supersedes: null
confidence: high
confirmed_at: 2026-08-17
---
## Applicable When

You are editing a repo-root file that `scripts/init-structure.sh` also ships as a
`templates/structure/` source (the mapping lives in that script, e.g. line 23:
`techstacks-README.md|techstacks/README.md`), or reviewing a diff that touches only one side of
such a pair.

## Pattern

These files are a **source/instance pair**: `templates/structure/<name>` is what
`init-structure.sh` scaffolds into consumer projects; the repo-root copy is this repo's own
scaffolded instance. Editing only the instance silently deprives every *future* consumer of the
change; editing only the template silently diverges from what this repo's agents read. No
standing test asserts parity — `tests/scripts/init-structure.test.sh` checks existence only — so
the drift is invisible to the suite (confirmed on test-layer-ladder: Task 1.3 edited the
instance, every gate stayed green, a human task reviewer caught it, and an unplanned Task 1.4
restored parity).

## How to Use

- Edit **both** files in the same task/commit, with identical line-wrap points, and prove parity
  with a re-runnable row: `diff -q templates/structure/<name> <instance-path>` → exit 0.
- Reviewing a diff that touches one side: treat the untouched twin as a finding until shown
  intentional.
- Know the reach limit: `init-structure.sh` is **create-if-missing** (`[ -e "$target" ]` → skip),
  so a template change reaches **new scaffolds only** — existing consumers keep their copy
  forever. Record that limit in the change's SUMMARY instead of claiming delivered coverage.

## Gotchas

- The parity invariant is only maintainable while this repo treats its own instance as
  template-shaped. The instance is declared project-owned in consumer repos ("the harness never
  overwrites it") — a byte-parity check belongs to *this* meta-repo, never to consumers.
- A one-shot `diff -q` SC row proves parity at ship time only; the next instance edit re-opens
  the gap. Re-cite this entry (or add a standing parity assertion to
  `tests/scripts/init-structure.test.sh`) when the pair churns.

## Related

- docs/solutions/harness/techstacks-project-owned-stack-profiles.md
- docs/solutions/harness/deploy-harness-does-not-prune-deleted-orphans.md
