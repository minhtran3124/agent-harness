<!--
  Open-questions register. Copy to specs/<slug>/QUESTIONS.md (usually the parent spec of a
  multi-phase effort). Optional: only non-blocking unknowns that a later phase must close.
  Checked by scripts/check_open_questions.py --slug <slug> when <slug> ships: an open question
  whose closes-at names that slug is reported (warn-first; REQUIRE_QUESTIONS_CLOSED=1 blocks).
-->

# <slug> — Open questions

A question that blocks work does not belong here: write it in ESCALATIONS.md.

Fields: `closes-at` is `<slug>` or `<slug>#<task-id>`; `decided-by` is `measurement` or `owner`;
`status` is `open` or `closed`; `closed-by` is required when `status: closed`. An `OQ-<n>` ID is
never reused. Other bullet lines (dated progress notes) are allowed and ignored by the check.

---

## OQ-1

- raised-by: <document and section that raised it, e.g. design.md §D4>
- closes-at: <slug or slug#task-id of the phase that must close it>
- decided-by: measurement
- default-until-closed: <the value used while the question is open>
- status: open
- closed-by: <one-line evidence; required when status: closed>
- <YYYY-MM-DD>: <optional progress note>

<!-- copy the OQ-<n> block for each new question -->
