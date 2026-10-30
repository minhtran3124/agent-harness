# Design template

A depth L design goes to two places. Write it to `specs/<slug>/design.md` (local scratch) from
`${CLAUDE_PLUGIN_ROOT}/templates/specs/design.md`, which has the same fields. Return it as a
`decisions[]` entry with `stage: design`; the ADR stage of `decision-record` writes
`docs/adr/NNNN-*.md`. Keep each field short; drop one that has nothing to say.

```text
title: <the chosen design, as a decision>
ticket: <ticket>
stage: design
context: |
  Goal in one or two sentences. Current state: what exists that the change builds on, with file
  pointers. Pins: <repo short sha the claims were checked against>, <YYYY-MM-DD>.
options: |
  Two or three approaches, their trade-offs, and which one was chosen.
decision: |
  The design: components, data flow, interfaces, error behavior.
why: |
  The evidence that made this approach win.
consequences: |
  Tests (commands and expected results) and non-goals (what this change does not do).
how_to_reverse: |
  The exact steps to undo it.
confidence: high | medium | low
needs_review: true | false
```
