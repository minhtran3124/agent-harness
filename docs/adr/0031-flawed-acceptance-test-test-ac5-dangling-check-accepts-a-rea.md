---
ticket: 567
stage: implement
status: needs-review
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-11-05
---

# 0031. Flawed acceptance test: test_ac5_dangling_check_accepts_a_real_later_adr_and_flags_a_missing_one

## Context

tests/acceptance/test_adr_prune_566.py line 161 asserts that 'see ADR 0014' is a dangling reference, which holds only while the folder ends at 0012. The ticket requires ADRs 0013-0030, so 0014 now exists. The test is also run by test_adr_store_567.py::test_ac3_prune_566_still_passes, so two tests fail.

## Options

- Edit the #566 test to use a number above 0030, such as ADR 0999
- Leave the test as it is and report it
- Skip the 0013-0030 migration

## Decision

Left tests/acceptance untouched and reported the failure. The migration was done as the ticket requires.

## Why

The rules forbid editing, skipping or weakening anything under tests/acceptance. The migration to 0013-0030 is required by the ticket.

## Consequences

Two acceptance tests fail until the owner changes the hard-coded 0014 in test_adr_prune_566.py to a number that will never exist. All other tests in both files pass.

## How to reverse

Replace the 0014 reference in test_adr_prune_566.py line 161 with a high number such as 0999.
