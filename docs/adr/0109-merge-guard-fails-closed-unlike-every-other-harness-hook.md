---
ticket: 516
stage: design
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: design)
date: 2026-10-30
---

# 0109. Merge guard fails closed, unlike every other harness hook

## Context

docs/hooks.md said all hooks fail open. A merge guard that fails open would let a merge into base through whenever gh or jq is missing or the base cannot be read.

## Options

- Fail closed: any doubt after a merge command is seen exits 2
- Fail open like the other hooks

## Decision

merge-guard.sh fails closed on no gh, no jq, no PR number, no --repo, a gh error, empty or bad output, a timeout, --auto, graphql mergePullRequest and wrapped merges. A non-merge Bash call still exits 0 at once.

## Why

Owner-confirmed decision D/H. The hook protects the hard rule 'never merge into base', so a false deny costs only a human merge, but a false allow breaks the rule.

## Consequences

A session without gh or jq cannot merge any PR from Claude, and a human merges instead. docs/hooks.md records this exception.

## How to reverse

Change the deny() calls on the doubt paths to exit 0 and update docs/hooks.md.
