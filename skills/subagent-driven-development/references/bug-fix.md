# Diagnosed bug fix

This reference applies when SUMMARY says `Input-type: bug fix` and `specs/<slug>/diagnosis.md`
exists. The `diagnosing-bugs` skill writes that file.

## Context

Name the `specs/<slug>/diagnosis.md` path in the Context of the fix task.

## Task review

Give the `specs/<slug>/diagnosis.md` path to the `task-reviewer` as `DIAGNOSIS_PATH`.

## Seam check before dispatch

Do these steps before you dispatch the fix task:

1. Confirm that `PLAN.md` has the `- Plan-contract: 2` marker.
2. Confirm that the fix task has a `Seams:` line.
3. Take the first seam of `Seams:`. A ` | ` separates two seams.
4. Take the seam point of that seam: the text before ` — catches:`. With no ` — catches:`, use the full seam text.
5. Take the seam point of the `Seam:` value in `diagnosis.md` by the same rule.
6. Compare the two seam points. The two strings must be equal.

A missing marker is a mismatch. A missing `Seams:` line is a mismatch. Two different seam points are a
mismatch.

## Mismatch

On a mismatch, do not dispatch the fix task. Then use the lane in SUMMARY:

- Normal lane: correct `Seams:` in `PLAN.md` yourself, then do the seam check again.
- High-risk lane: return the fix task to `writing-plans`, then do the seam check again.

The budget is two seam checks. On a second mismatch, write a `specs/<slug>/ESCALATIONS.md` block with
`decision: pending` and stop.
