---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: owner (minh.tran.dev, after review of PR #541)
date: 2026-10-31
---

# 0127. Boundary: regression test for tickets allowed-tools lives outside the named file set

## Context

F6 says SKILL.md line 6 allowed-tools lacks Bash(gh issue view *) and the repo-slug lookup. The fix (add Bash(gh issue view *) to the frontmatter) is inside the named files. The task requires a test that fails without the fix. No existing test covers the tickets skill, and every test file (for example tests/scripts/tickets-contract.test.sh) is outside the named file list.

## Options

- Edit SKILL.md only, with no test
- Add tests/scripts/tickets-contract.test.sh and edit SKILL.md, which breaks the file-set rule
- Skip and report a boundary decision

## Decision

Skip and report a boundary decision

## Why

The file-set rule says a test file is in bounds only when listed, and the task requires a failing-first test. Both cannot be met, so nothing changes.

## Consequences

F6 stays unfixed until the owner adds a test file to the boundary, or accepts a test-less fix. The fix is one line: append ', Bash(gh issue view *)' to allowed-tools in plugins/harness/skills/tickets/SKILL.md.

## How to reverse

Name a tickets contract test file in the ticket's file list and re-run the fix stage.

## Outcome

Closed with no allowed-tools change. `gh issue view` is not needed, because the dedup reads bodies with `gh issue list --json`. `gh repo view` was already allowed. A headless run showed which milestone and body forms pass allowed-tools, and the contract test pins them.
