---
ticket: 411
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0005. verify.config.json uses a loginEnv array for the variable names

## Context

The ticket says the config holds baseUrl, startCommand and the names of the login env vars but fixes no key name.

## Options

- loginEnv: [names]
- userEnv and passwordEnv keys

## Decision

loginEnv array of names; the contract test allows only baseUrl, startCommand and loginEnv.

## Why

One key, easy to check for upper-case names only.

## Consequences

#413 must read the same key.

## How to reverse

Rename the key in the skill, the fixture config and the test.
