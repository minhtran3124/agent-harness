---
ticket: 394
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0029. Hook parsing approach

## Context

Need to match only a real merge command in bash 3.2 without associative arrays or mapfile.

## Options

- awk plus sed text reduction
- jq-only regex
- a full shell tokenizer

## Decision

Two awk passes (drop heredoc bodies, then drop quoted strings) and a sed split on && || ; | & into segments; check each segment after stripping env assignments. The awk code uses \047 for the single quote so BSD awk accepts it.

## Why

Portable to macOS and small; only the commands in the ticket need to match.

## Consequences

Unusual forms are not matched and so do nothing (fail-safe): `sudo gh pr merge`, `bash -c 'gh pr merge 7'`, and `env X=1 gh pr merge`.

## How to reverse

Revert commit e2494e6.
