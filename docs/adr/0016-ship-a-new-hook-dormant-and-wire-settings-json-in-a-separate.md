---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-07-17
---

# 0016. Ship a new hook dormant and wire settings.json in a separate step

## Context

A new hook, `hooks/protected-path-guard.sh` (historical), was added to guard protected paths. The hook only takes effect once registered in `settings.json` under a trigger key. The question was whether to wire it into `settings.json` in the same change or ship it unregistered (dormant).

## Options

- **Option A:** Wire immediately — register the hook in `settings.json` as part of this change. Feature is live at once, but the change alters runtime behavior for every session.
- **Option B:** Ship dormant — land the hook script + test unregistered, leave `settings.json` wiring as a separate later step. No runtime behavior changes now; activation is a distinct, explicit action.

## Decision

Chose **Option B** — ship dormant.

## Why

Editing `settings.json` hook registration is itself a Rule-4 / high-blast change (per `rules/auto-correct-scope.md` (historical): "Changes to high-blast-radius files: settings.json (hook registration)") that needs explicit human confirmation. Shipping dormant changes no runtime behavior, keeps the hook landing inside the autonomous lane, and matches the established `auto-test-on-change` precedent (present on disk, unregistered).

## Consequences

Enables: the hook + its test land autonomously with zero runtime-behavior change and zero `settings.json` edit; the CLAUDE.md hook table marks it `⬜ dormant`. Constrains: the hook does nothing until a follow-up human-confirmed step wires it in — there is now a tracked pending activation, and a dormant hook with no scheduled wiring can be forgotten.

Applies when: A future engineer adds a new hook (or other `settings.json`-registered automation) and must decide whether to activate it in the same change — default to shipping dormant and splitting the `settings.json` wiring into a separate Rule-4-gated step.

Related:
- docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
