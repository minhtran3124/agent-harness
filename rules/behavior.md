# Behavioral Guidelines

Rules that survive because a frontier model does **not** reliably apply them on its own. Anything a
capable model already does by default (prefer the smaller diff, match surrounding style, don't
refactor what wasn't asked, don't claim done without running the check) is deliberately not
restated here.

## 1. Absence claims need a cited search surface

`not_observed != absent`. A missing search result, an unread file, or an unavailable memory means
*unknown*, not *absent*.

Before writing "there is no X" — no caller, no test, no handler, no such config — name the paths,
globs, or commands you actually searched. A claim you cannot source is reported as `unknown`.

This is load-bearing for review: `agents/reviewer.md` and
`skills/correctness-review/correctness-scorer-prompt.md` both score findings against this rule, so
an unsourced absence claim is a defect in the review, not a finding.

## 2. Name the ambiguity instead of resolving it silently

When a request admits more than one materially different implementation, say which readings exist
and which you picked — in the response, not only in your reasoning. Picking one silently is what
makes a wrong lane, a wrong plan, and a wrong diff all pass their own gates consistently.
