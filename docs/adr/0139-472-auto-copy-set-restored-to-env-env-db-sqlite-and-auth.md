---
ticket: run
stage: intent-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent-fix)
date: 2026-10-29
---

# 0139. #472 auto-copy set restored to .env, .env.*, *.db, *.sqlite and .auth

## Context

Commits fdd84cd and 8e010b7 made the classifier send credential and state files to unknown. That needed a manifest copy line and contradicted the owner request, which asks that small config and state files be copied by default.

## Options

- Keep the stricter rule
- Revert to the copy-by-default rule

## Decision

Reverted both commits. Config-named files up to 5 MB are copied by default. Files over 5 MB and prod-named files stay unknown. A manifest copy line still wins over the prod rule.

## Why

The owner decisions for #472 do not cover making credential files fail provisioning.

## Consequences

An unattended agent gets a copied .env when the project has one. Tests are back to the earlier expectations.

## How to reverse

Revert commit ac3f3c7.
