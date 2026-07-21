---
problem_type: failure
module: release-bookkeeping
tags: version-bump, changelog, post-merge-maintenance, event-sourced, finishing-branch, double-bump, single-owner
severity: standard
applicable_when: Finishing a branch / opening a PR in harness-skills, or editing VERSION / CHANGELOG.md by hand — anywhere you are tempted to bump the version or add a CHANGELOG entry before merge.
affects:
  - skills/finishing-a-development-branch/SKILL.md
supersedes: null
confidence: high
confirmed_at: 2026-07-21
---
## Applicable When

Finishing a branch / opening a PR in this repo, or hand-editing `VERSION` / `CHANGELOG.md`.
The version bump and CHANGELOG entry have exactly **one** owner here: the post-merge
automation. Doing it manually in the PR double-counts.

## Symptom

After a feature PR merged, the bookkeeping PR bumped `VERSION` a **second** time and created a
duplicate CHANGELOG entry: VERSION went 2.12.0 → 2.13.0 (manual, in the feature PR) → 2.14.0
(automation) for a single PR; the manual `## [Unreleased]` bullet was left orphaned above a
terse auto-generated `## [2.14.0]` section; and version `2.13.0` never got a CHANGELOG section
at all (a skipped version). Reconciling it required a third commit on the bookkeeping branch.

## Wrong Approach

Following `finishing-a-development-branch` Step 1b literally: manually add a `## [Unreleased]`
bullet **and** bump root `VERSION` in the feature PR, committing them with the work.

## Why It Failed

`bookkeeping.sh` (run by `.github/workflows/post-merge-maintenance.yml` on every non-bookkeeping
merge) is the **authoritative event-sourced owner** of the release bump. It unconditionally:
reads the *current* `VERSION` and bumps from it (minor if a contract path changed, else patch),
inserts a fresh dated `## [x.y.z]` section, and appends the trust-metrics + audit-log rows. Its
idempotency guard keys on the **PR number** (never record the same PR twice) — it does **not**
detect that a human already bumped `VERSION`, so it bumps again from the pre-bumped value. It
also inserts a new section *below* `## [Unreleased]` without clearing it, so a manual Unreleased
bullet is orphaned. `feature-intake` already says the quiet part out loud: "Do NOT hand-append
the ledger. CI records it on merge." Step 1b contradicted that — two instructions, two owners,
one PR.

## Correct Approach

Let the automation be the sole owner. Do **not** bump `VERSION` or add a CHANGELOG entry in the
feature PR — merge the feature, then let `post-merge-maintenance.yml` open the bookkeeping PR
that records the trust-metrics row, the CHANGELOG section, and the single VERSION bump, all
parsed from the merged `SUMMARY.md`. Review that PR for correctness instead of pre-writing it.
If a bump has already leaked into a feature PR, reconcile on the bookkeeping branch to a single
coherent release (one dated section, no skipped version, `Unreleased` emptied) before merging it.

## Guardrail

proposed: A CI check that fails a non-bookkeeping PR whose diff touches `VERSION` or the
`## [Unreleased]` section, so the manual bump cannot leak in at all. The doc fix that
accompanies this learning removes the Step-1b instruction that invited the leak; the CI check is
the harder mechanical backstop, tracked in the improvement backlog.

## Related

- docs/solutions/harness/resync-protected-files-decisions.md
