---
ticket: 480
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0138. Setup step stays instruction-only, no new helper script

## Context

The ticket asks /harness:setup to run the audit and propose a manifest. provision-sandbox.sh --audit already classifies paths on github/feat/sandbox-per-ticket.

## Options

- Instruction-only step in SKILL.md using the existing audit
- New propose-sandbox.sh helper that emits manifest lines

## Decision

Instruction-only step in SKILL.md using the existing audit

## Why

The ticket names no new script, the proposal needs owner judgment, and the SKILL.md cap leaves little room.

## Consequences

The proposal quality depends on Claude following the step; the contract test checks the wording, not generated output.

## How to reverse

Add a helper script later and point the step at it.
