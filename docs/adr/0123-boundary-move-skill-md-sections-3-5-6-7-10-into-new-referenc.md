---
ticket: 539
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: owner (minh.tran.dev, after review of PR #541)
date: 2026-10-31
---

# 0123. Boundary: move SKILL.md sections 3, 5, 6, 7, 10 into new references/process.md

## Context

The ticket's verbatim SKILL.md is 1009 words, and scripts/audit_skill_prompts.py enforces a 600-word ceiling. AC1 listed exactly three reference files. The ship run first moved five sections to references/process.md, then a fix round dropped that file and compressed SKILL.md to 600 words. That compression lost six condition words, against docs/solutions/harness/deletion-test-for-word-ceiling.md.

## Options

- Keep three references and compress SKILL.md to 600 words
- Relax AC1 and keep the rules whole in a required references/process.md

## Decision

Relax AC1 to four reference files. SKILL.md makes `references/process.md` a required Read and keeps every step. Issue #539 now states this AC.

## Why

The word ceiling and the old AC1 cannot both hold with the full rules. A bare pointer does not make the model read a file, so the Read is required. The rules stay whole, and the fixes for duplicates, deps and labels have room.

## Consequences

The skill has a fourth reference file. tests/scripts/tickets-contract.test.sh pins it and the rules it holds.

## How to reverse

Inline process.md back into SKILL.md and raise the ceiling for this skill, or cut the rules.

