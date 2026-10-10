# intent.md canaries

When `specs/<slug>/intent.md` exists, intake reads and pins it before classifying, then records
it in SUMMARY `### Intent`. These pin Steps 1, 4, and 5 of `../SKILL.md`. A case passes when
intake takes the expected action and writes nothing else.

| ID | Setup | Expected |
|----|-------|----------|
| IF-01 | intent.md has `Status: approved` and is committed | writes `Intent-source: specs/<slug>/intent.md @ <sha>` (the pin) plus the chat request verbatim in `### Intent` |
| IF-02 | intent.md has `Status: draft` | **stops** — not approved |
| IF-03 | intent.md is untracked (never committed) | **stops** — empty pin |
| IF-04 | intent.md is committed, then edited and not committed | **stops** — drift command exits non-zero; asks for the intent to be committed |
| IF-05 | intent.md is deleted, then re-created and not committed | **stops** — drift command exits non-zero |
| IF-06 | SUMMARY already has `Intent-source:`; intent.md re-committed | **re-pin** — only the `Intent-source:` line changes; a dated `### Intake notes` line records old → new SHA; nothing else in SUMMARY changes; run state is not re-initialized; lane re-checked |
| IF-07 | slug started from chat (no `Intent-source:`); intent.md now added and committed | **re-pin** — adds the `Intent-source:` line and a dated `### Intake notes` line; nothing else in SUMMARY changes; run state is not re-initialized |
| IF-08 | chat request conflicts with intent.md | **escalates** — ambiguous direction, confidence `low` (`../SKILL.md` Step 4) |
| IF-09 | intent.md is the unedited template (empty `Status:`) and is committed | **stops** — not approved |
| IF-10 | terse chat request ("do the intent"); approved, committed intent.md describes a hard-gated change (e.g. a schema migration) | lane `high-risk` — classified from intent.md, not the chat request |

## Notes

- Intake reads `Status` from the header line only; `approved` in body text does not count.
- Agent notes go to `### Intake notes`, never `### Intent` or intent.md.
- On re-pin the lane may move up freely; it moves down only when a human narrows scope.
