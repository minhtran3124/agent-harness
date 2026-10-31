---
ticket: 530
stage: implement
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-31
---

# 0116. Deny list stays a mistake guard; bare push, git -C, trailing flags, aliases and delete are documented known gaps

## Context

The prefix glob cannot express every push form. The spike showed bare `git push`, `git push origin`, `git -C <dir> push`, trailing `--no-verify`, `refs/heads/main` without a colon, and quoted branch names still reach main. The `:main` delete form is blocked by the `*:main` rule (ADR 0119). The real Claude Code matcher confirmed `--no-verify`, `git -C`, and quoted refspecs as allowed.

## Options

- Add six refspec and plus patterns and document the rest as gaps
- Add broad `git push*main*` patterns that also block unrelated commands

## Decision

Add the six patterns and list the rest under Known gaps in docs/hooks.md.

## Why

Matches the owner-confirmed decision; broad globs would block legitimate commands.

## Consequences

Until the owner enables GitHub branch protection, the listed gaps stay open.

## How to reverse

Remove the six patterns from settings.json and merge-deny.sh (the test counts are derived from the list) and move the matching gap rows in `tests/scripts/push-deny-forms.test.sh`.
