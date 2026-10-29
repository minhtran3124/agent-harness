---
ticket: 411
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0062. Fixture lives in tests/fixtures/verify-app/ with its own verify.config.json

## Context

The ticket says a tiny app in tests/fixtures/ and a verify.config.json written for the fixture. A root verify.config.json would claim this repo has an app.

## Options

- tests/fixtures/verify-app/ holding the fixture config
- verify.config.json at the repo root
- a temp file written only by the test

## Decision

Keep the fixture and its verify.config.json together under tests/fixtures/verify-app/; the skill still tells agents to write the config at the repo root of the project under test.

## Why

This repo has no app, so a root config would mislead; a committed fixture config lets the no-secrets test and the manual run share one file.

## Consequences

The manual dogfood run points the skill at the fixture directory; the no-secrets test reads this file.

## How to reverse

Move the file and update the test path.
