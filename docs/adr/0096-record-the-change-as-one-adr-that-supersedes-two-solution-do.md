---
ticket: 464
stage: intent
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0096. Record the change as one ADR that supersedes two solution docs

## Context

The ticket removes a public setup contract: /harness:setup no longer creates agents/PROJECT.md or techstacks/. It is a breaking change for consumers that already ran setup.

## Options

- One ADR for the whole layout change
- No ADR, a changelog note only

## Decision

Return one decision with needs_review: true so the ADR stage writes one ADR in docs/adr/. The ticket asks for it, and the two docs/solutions entries are marked superseded by it.

## Why

It changes a public contract (setup output, agent file inputs) and the ticket requires an ADR.

## Consequences

A reviewer confirms the one-release fallback policy and the removal of the scaffold.

## How to reverse

Restore techstacks-README.md, PROJECT.template.md and the setup steps from git history.
