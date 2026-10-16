---
slug: gh-312-canary
status: active
owner: Minh Tran
created: 2026-10-16
---

# Canary: word count helper

## 3. Success Criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
|---|---|---|---|
| SC-1 | `word_count("a b  c")` returns 3 | `python3 -m pytest canary/test_wc.py -q` | exit 0 |

## Global Constraints

- Plan-contract: 2
- Edit only the files your task names.

## 4. Tasks

### Task 1.1 — Word count helper (wave 1)

- **Files:** canary/wc.py, canary/test_wc.py
- **Action:** Add `word_count(text)` in `canary/wc.py`. It returns the number of words, where a word is a run of non-space characters. Add tests in `canary/test_wc.py`.
- **Verify:** `python3 -m pytest canary/test_wc.py -q`
- **Done:** SC-1 exits 0.
- **Criteria:** SC-1
- **Interfaces:** Consumes: a text string. Produces: `canary/wc.py`.
- **Seams:** `word_count()` return value — catches: wrong count for spacing and empty text; misses: callers that pass bytes

## 6. Status Log
