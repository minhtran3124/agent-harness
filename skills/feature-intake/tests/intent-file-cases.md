# intent.md canaries

When `specs/<slug>/intent.md` exists, intake pins it by commit and records it in SUMMARY
`### Intent`. These pin Step 5 of `../SKILL.md`. A case passes when intake takes the
expected action and writes nothing else.

| ID | Setup | Expected |
|----|-------|----------|
| IF-01 | intent.md has `Status: approved` and is committed | writes `Intent-source: specs/<slug>/intent.md @ <sha>` (the pin) plus the chat request verbatim in `### Intent` |
| IF-02 | intent.md has `Status: draft` | **stops** — not approved |
| IF-03 | intent.md is untracked (never committed) | **stops** — empty pin |
| IF-04 | intent.md is committed, then edited and not committed | **stops** — drift command exits non-zero; asks for the intent to be committed |
| IF-05 | intent.md is deleted, then re-created and not committed | **stops** — drift command exits non-zero |
| IF-06 | SUMMARY already has `Intent-source:`; intent.md re-committed | **re-pin** — only the `Intent-source:` line changes; a dated `### Intake notes` line records old → new SHA; every other section kept; lane re-checked |
| IF-07 | slug started from chat (no `Intent-source:`); intent.md now added and committed | **re-pin** — adds the `Intent-source:` line and a dated `### Intake notes` line; every other section kept |
| IF-08 | chat request conflicts with intent.md | **escalates** — ambiguous direction (`../SKILL.md` Step 4) |

## Notes

- Intake reads `Status` from the header line only; `approved` in body text does not count.
- Agent notes go to `### Intake notes`, never `### Intent` or intent.md.
- On re-pin the lane may move up freely; it moves down only when a human narrows scope.
