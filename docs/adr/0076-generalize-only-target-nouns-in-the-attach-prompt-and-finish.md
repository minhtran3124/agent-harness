---
ticket: 427
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0076. Generalize only target nouns in the attach prompt and finish text

## Context

Owner decision 3 says to change 'GIF' to 'evidence file' in the attach prompt target and the finish text without changing wording owned by #425. Test a8 asserts the 'must not contain an image line', '--attach' and '2.99.0' substrings.

## Options

- Change only the noun 'the GIF' in two sentences and the finish text
- Rewrite the whole attach prompt and the decision title

## Decision

Change only the noun 'the GIF' in two sentences and the finish text

## Why

This keeps the diff small and avoids overlap with #425, which owns the attach prompt wording. The decision title 'Attach the verify GIF by hand' stays as is.

## Consequences

The manual-attach decision title still says GIF even when the file is a PNG. #425 can fix that.

## How to reverse

Edit the title string in stageAttach.
