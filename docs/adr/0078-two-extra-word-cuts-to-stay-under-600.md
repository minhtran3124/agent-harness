---
ticket: 439
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0078. Two extra word cuts to stay under 600

## Context

After the five owner-listed cuts the file was 606 words, over the 600 ceiling.

## Options

- Cut 'for review in the PR diff' and 'Do not retry.'
- Move detail to references/

## Decision

Cut 'for review in the PR diff' (step 4 of Start config) and 'Do not retry.' (Base mode step 4); the file is now 597 words.

## Why

These are the smallest cuts and no test pins them. #441 still has room for its pointer line only if it cuts about 10 more words itself.

## Consequences

Base mode no longer says 'Do not retry.' explicitly. 'Commit nothing.' stays.

## How to reverse

Re-add the two phrases and cut the same number of words elsewhere.
