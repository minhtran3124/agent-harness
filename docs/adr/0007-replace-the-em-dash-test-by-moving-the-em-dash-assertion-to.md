---
ticket: 381
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-28
---

# 0007. Replace the em-dash test by moving the em-dash assertion to an optional field

## Context

The existing em-dash test builds an entry without applicable_when and asserts '| — | — | — |'. That fixture is now invalid for --check, but build() still renders em-dash for missing fields.

## Options

- Replace with a test whose entry has applicable_when but lacks severity/tags and still asserts em-dash plus the ordering assertion
- Replace with only a new --check failure test and drop the em-dash/ordering coverage

## Decision

First option, plus separate new --check failure tests

## Why

Owner said replaced, not deleted or weakened; this preserves the ordering and marker coverage and adds the new behavior.

## Consequences

Test count grows; build() rendering contract still covered.

## How to reverse

Revert the test file change.
