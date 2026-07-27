---
problem_type: failure
module: harness
tags: pr-review-loop, review-polling, last-handled-id, skipped-round, gh-api, cursor-tracking
severity: standard
applicable_when: Polling a PR for new automated reviews in a loop — before you decide "new" by comparing against the latest commit or the newest review.
affects:
  - skills/finishing-a-development-branch/SKILL.md
supersedes: null
confidence: high
confirmed_at: 2026-07-27
---
## Applicable When

Any loop that watches a PR for new review feedback and acts on it: a `/loop`-scheduled poll, a babysit
job, or a manual "check if the bot replied yet" pass.

## Symptom

Two Codex reviews landed on PR #173 **nine minutes apart** (on commits `f4ea405` and `221840d`). The
loop handled the later one and never saw the earlier. Its finding — the resume path keyed on run state
while `finishing-a-development-branch` marks `PLAN.md` `shipped` *before* the push — stayed live for two
more rounds before being handled.

## Wrong Approach

Deciding what is new by looking at the newest thing:

- "the latest review" — collapses N unhandled reviews into 1
- "reviews on the current HEAD" — drops every review submitted against an earlier commit, which is
  exactly what an unhandled review is

Both feel correct while exactly one review arrives per push. They break the first time the reviewer
posts twice before you look.

## Why It Failed

Reviews are an append-only stream with monotonically increasing ids; the loop was treating them as a
single mutable "current" value. The failure is silent — nothing errors, the loop reports success on the
review it did handle, and the skipped finding is indistinguishable from one that was never raised.

## Correct Approach

Track the **last-handled review id** and select on it, not on time or commit:

```bash
LAST=4785082792   # the last review id actually handled
gh api repos/<owner>/<repo>/pulls/<n>/reviews \
  -q ".[] | select(.id > $LAST) | \"\(.id) \(.commit_id[0:7])\""
```

Then iterate **every** returned id and fetch each one's inline comments by
`.pull_request_review_id == <id>`, rather than fetching "recent comments" by timestamp. Handle them
oldest-first: a later review often assumes the earlier one was addressed, so processing newest-first
produces replies that contradict each other.

Also note a review with **no inline comments is a real outcome** (the reviewer had nothing to say) — not
a fetch failure. Distinguish "no reviews newer than LAST" from "a newer review with zero findings", or
the loop will keep re-reporting the same clean round as if it were unread.

## Guardrail

`proposed:` a small helper — `scripts/pr_reviews_since.py <pr> <last_id>` — that prints unhandled
reviews oldest-first with their findings, so the id-cursor discipline lives in one tested place instead
of in whichever prompt happens to be polling. Target: `scripts/pr_reviews_since.py` plus a line in
`skills/finishing-a-development-branch/SKILL.md` where the external-review pass is described.

## Related

- `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md` — the other way a review round
  produces no action.
