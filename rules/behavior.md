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

## 3. Confirm a command's interface before depending on it

Before relying on a flag, subcommand, or file path you have not seen in this session, check it —
`--help`, `ls`, or the file itself. Recall of an interface is not observation of it.

This is not the generic "don't hallucinate": it is specific to the failure where a plausible
invocation is wrong in *this* environment. Observed in one session in this repo: `timeout` is not
installed on macOS; `render_plan.py` lives under `skills/visual-planner/`, not `scripts/`; `md5 -q`
replaces `md5sum`. Each cost a turn, and each would have been free to check.

The cost is asymmetric — one cheap probe against a failed command, a wrong path silently written
into a doc, or a `2>/dev/null` that turns the mistake into a silent no-op. Adapted from the
external repo `spotify/portal-ai-plugins`, whose setup workflow states it as a rule: "Run
`--help` before relying on a Portal CLI or host command or flag."
