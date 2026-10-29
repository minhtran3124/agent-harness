---
ticket: 464
stage: intent
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0010. Remove techstacks/ and agents/PROJECT.md; project rules come from the repo's own files

## Context

The ticket removes a public setup contract: /harness:setup no longer creates agents/PROJECT.md or techstacks/. It is a breaking change for consumers that already ran setup.

## Options

- One ADR for the whole layout change
- No ADR, a changelog note only

## Decision

Ticket #464 removed techstacks/ and agents/PROJECT.md. Project rules now come from the repo's own CLAUDE.md, CLAUDE.local.md and .claude/rules, read through the single rulesCommon(repoDir) text in ship.js. This supersedes the solution docs techstacks-project-owned-stack-profiles and scaffold-template-instance-parity.

## Why

It changes a public contract (setup output, agent file inputs) and the ticket requires an ADR.

## Consequences

Breaking for consumers that already ran /harness:setup: the harness no longer reads agents/PROJECT.md or techstacks/.

## How to reverse

Restore techstacks-README.md, PROJECT.template.md and the setup steps from git history.
