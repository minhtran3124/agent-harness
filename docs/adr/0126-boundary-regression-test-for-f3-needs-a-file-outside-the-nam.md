---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: owner (minh.tran.dev, after review of PR #541)
date: 2026-10-31
---

# 0126. Boundary: regression test for F3 needs a file outside the named set

## Context

F3 asks for a resolution rule for deps on skipped tickets (exists #n / overlap skipped) in tickets/SKILL.md section 9. The stage also requires a test that fails without the fix. The only suitable test home is a new tests/scripts/tickets-contract.test.sh (pattern: compound-contract.test.sh), which the ticket's file list does not name.

## Options

- Skip and flag for review
- Edit SKILL.md only, with no test
- Add the test file anyway

## Decision

Skipped; changed nothing.

## Why

The boundary rule says a test file is in bounds only when listed, and a fix that needs an out-of-set file must change nothing. Adding the test anyway or omitting it would break one of the stage's explicit rules.

## Consequences

F3 stays open. Suggested fix once the owner allows tests/scripts/tickets-contract.test.sh: in SKILL.md section 9, say that a dep on a skipped ticket is replaced by the existing issue number (exists #n, or overlap #n when the owner chose skip), never left as a draft id like T3. Then add a grep-based test for that sentence.

## How to reverse

Add tests/scripts/tickets-contract.test.sh to the ticket's file list and rerun this fix stage.

## Outcome

Fixed. SKILL.md step 9 maps a dep on a skipped ticket to its `#n`, and process.md allows deps only in the batch or on closed issues. tests/scripts/tickets-contract.test.sh covers it.
