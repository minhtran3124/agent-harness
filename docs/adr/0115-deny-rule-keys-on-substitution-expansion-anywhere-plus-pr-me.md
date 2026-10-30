---
ticket: 518
stage: intent
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-30
---

# 0115. Deny rule keys on substitution/expansion anywhere plus 'pr merge' or api merge anywhere

## Context

The segment splitter breaks on ( ) and quotes, so g$(true)h pr merge 7 is cut into fragments that never look like gh pr merge.

## Options

- Parse the full shell
- Whole-command check: $ or backtick plus a pr..merge or api merge form
- Deny every command that has a $ or backtick and the word merge

## Decision

Whole-command check on the folded command: deny when a $ or backtick is present together with a 'pr' word followed by 'merge', or 'api' with a merge path or mergepullrequest; backslash-newline that creates such a form when joined is denied separately.

## Why

This matches the owner's stated assumption, fails closed on doubt about gh, and keeps the fast exit for ordinary commands. A false deny costs one human merge.

## Consequences

A command such as echo $(date); gh pr merge 7 --repo o/r is also denied, so the human must merge it.

## How to reverse

Remove the added check block in merge-guard.sh and its tests.
