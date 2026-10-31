---
ticket: 523
stage: implement
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-30
---

# 0119. Boundary: runner is scripts/compare_symbol_checkers.py (underscored), not compare-symbol-checkers.sh

## Context

The ticket allows 'scripts/compare-symbol-checkers.sh or .py'; the boundary list names only the hyphenated .sh. The test imports the runner as a module, so the filename must be a valid Python module name.

## Options

- scripts/compare_symbol_checkers.py (importable)
- scripts/compare-symbol-checkers.sh (hyphenated)

## Decision

Used scripts/compare_symbol_checkers.py, which the ticket text allows ('.sh or .py'); it is Python so the scoring, LSP client and SQLite reading stay in the standard library.

## Why

The runner speaks LSP over stdio and reads SQLite and JSON, which is not practical in portable bash 3.2, and the test needs to import it.

## Consequences

The file name differs from the hyphenated name in the boundary list; check-shellcheck.sh has nothing new to lint.

## How to reverse

Rename the file and the import in scripts/test_compare_symbol_checkers.py.
