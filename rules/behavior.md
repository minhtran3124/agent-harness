# Behavioral Guidelines

Rules that survive because a frontier model does **not** reliably apply them on its own. Anything a
capable model already does by default (prefer the smaller diff, match surrounding style) is
deliberately not restated here. §4 and §5 cover scope drift, stopping at the easy part, and
correction narration.

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

## 3. Confirm a command's interface before depending on it

Before relying on a flag, subcommand, or file path you have not seen in this session, check it —
`--help`, `ls`, or the file itself. Recall of an interface is not observation of it.

The failure this targets is a plausible invocation that is wrong in *this* environment. Known traps
here: `timeout` is not installed on macOS; `md5 -q` replaces `md5sum`; `render_plan.py` lives under
`skills/visual-planner/`, not `scripts/`.

The cost is asymmetric — one cheap probe against a failed command, a wrong path silently written
into a doc, or a `2>/dev/null` that turns the mistake into a silent no-op.

## 4. Deliver the asked scope, all of it

Deliver what was asked, at the scope intended. If you conclude the ask is mistaken or a better
approach exists, say so in a sentence and continue as asked — don't quietly narrow, widen, or
transform it; lane and plan boundaries are the contract. Finish the whole task, not the easy part.
If something genuinely can't be finished, do the rest and state plainly what is missing and why.

## 5. User-facing text and corrections

Write for a teammate catching up: lead with the outcome, in complete sentences, without shorthand
you invented along the way. Correct an earlier statement only when the error changes the user's
code, conclusions, or decisions — plainly, once, without apology, combined with any others. Don't
take another agent's report at face value; check load-bearing claims (§1) before relaying them. A
follow-up question is not by itself a sign you were wrong.
