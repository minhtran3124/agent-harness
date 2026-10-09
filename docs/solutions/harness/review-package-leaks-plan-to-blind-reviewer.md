---
problem_type: failure
module: skills/subagent-driven-development
tags: review-package, intent-review, plan-blindness, oracle-independence, review-chain
severity: standard
applicable_when: Handing an SDD branch review package to a reviewer whose contract forbids reading PLAN.md or research-brief.md (intent-review), on any branch that commits its specs/ artifacts.
affects:
  - skills/subagent-driven-development/scripts/review_package.py
supersedes: null
confidence: high
confirmed_at: 2026-10-09
---
## Applicable When

Handing an SDD branch review package to a reviewer whose contract forbids reading `PLAN.md` or
`research-brief.md` (intent-review), on any branch that commits its `specs/` artifacts.

## Symptom

On `install-uv-autoinstall` the intent reviewer reported that the branch package
(`review_package.py --base <merge-base> --head HEAD`) embedded the full diffs of
`specs/<slug>/PLAN.md` and `research-brief.md`; it could not avoid reading them while reading
the package it was told to read first.

## Wrong Approach

Generating one `BASE..HEAD` package for the whole branch and passing it to both correctness-review
and intent-review, relying on the intent prompt's "do not read the plan" instruction for
blindness.

## Why It Failed

`specs/` is tracked, so the plan and research brief are part of the branch diff; the package is a
mechanical diff with no path filter. The blind rule was enforced by instruction while the input
the reviewer was required to read carried the forbidden content — independence by instruction,
not by structure.

## Correct Approach

For the intent pass on this branch, the package was dropped and the reviewer was told to read
`git diff BASE..HEAD -- scripts tests README.md`, excluding `specs/`; the SC rows were supplied
as an extracted file. Durable fix: give the package builder a path filter and have the intent
dispatch exclude `specs/**`.

## Guardrail

proposed: `review_package.py --exclude 'specs/**'` (or an `--intent` mode that drops `specs/`),
used by the intent-review dispatch in `skills/subagent-driven-development/references/review-chain.md`,
with a test asserting no `specs/*/PLAN.md` hunk appears in an intent package.
Target: `skills/subagent-driven-development/scripts/review_package.py`.
