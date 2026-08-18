---
problem_type: failure
module: specs/*/PLAN.md status lifecycle + hooks/blast-radius-check.sh
tags: [plan-status, blast-radius, stale-state, shipped-transition, finishing-branch, false-positive]
severity: standard
applicable_when: An edit triggers a blast-radius warning citing a plan you are not executing, or you are merging a spec branch — check every merged spec still marked `status: active`.
affects:
  - specs/*/PLAN.md
  - hooks/blast-radius-check.sh
supersedes: null
confidence: high
confirmed_at: 2026-07-23
---
## Applicable When

An edit triggers a blast-radius warning citing a plan you are not executing, or you are merging a
spec branch — check for merged specs still marked `status: active`.

## Symptom

`blast-radius-check` warned "edited X which is NOT in the active plan `<files>` set
(specs/slim-skill-surface/PLAN.md)" while executing a *different* spec whose plan listed X. Twice
in one session, two different stale plans (slim-skill-surface PR #158, wire-lane-evidence-gate
PR #120 — both merged, both still `status: active`).

## Wrong Approach

Treating the plan `status:` field as self-maintaining — merging a spec branch without flipping its
PLAN.md to `shipped`, then trusting blast-radius warnings at face value.

## Why It Failed

`hooks/blast-radius-check.sh` arms itself on the **most recently modified `status: active`
plan** (`ls -t` + first grep hit). Any merged-but-active plan shadows the truly active one, so
scope warnings cite the wrong `<files>` set — false positives against the real work and silence
for genuine scope creep. Plans merged outside `/finishing-a-development-branch` (or before its
Step 4 existed) never got the `shipped` transition.

## Correct Approach

Flip merged plans to `status: shipped` the moment the drift is noticed (canonical values:
`proposed | active | paused | shipped`). `/finishing-a-development-branch` Step 4 does this for
branches that go through it; the gap is specs merged any other way.

## Guardrail

proposed: a "merged-but-active" check — fail (or warn) when a `specs/*/PLAN.md` has
`status: active` but its slug's branch is merged into main (e.g. compare against
`git log main --merges --grep=<slug>` or the SUMMARY's shipped marker). Target path:
`scripts/lint-doc-truth.sh` (or a new `scripts/check_plan_status.py` wired into
`scripts/run-tests.sh` L1).

## Related

- docs/solutions/harness/manual-version-bump-collides-with-event-sourced-bookkeeping.md — same class: post-merge bookkeeping that decays when manual
