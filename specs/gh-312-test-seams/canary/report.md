<!-- transcribed by controller from the implementer's inline report -->
- **status:** DONE
- **commits:** [{sha: 0000000, subject: "feat(canary): word count helper with tests"}]
- **files:** canary/wc.py, canary/test_wc.py
- **verify:** pass — `python3 -m pytest canary/test_wc.py -q`: 4 passed
- **blockers:** []
- **deviations:** []
- **lane:** normal
- **Harness-Delta:** none

Added `word_count(text)` with a small `_tokens` helper, and four tests: a simple count, the helper's empty-part handling, a sample sentence, and empty text.
