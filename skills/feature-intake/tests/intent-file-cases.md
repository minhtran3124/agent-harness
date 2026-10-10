# intent.md canaries

When `specs/<slug>/intent.md` exists, intake reads and pins it before classifying, then records
it in SUMMARY `### Intent`. These pin Steps 1, 4, 5, and 6 of `../SKILL.md` and the re-pin rules in
`../references/re-pin.md`. A case passes when intake takes the expected action and writes nothing
else.

| ID | Setup | Expected |
|----|-------|----------|
| IF-00 | chat request only; no intent.md | `### Intent` holds the chat request verbatim and in full; **no** `Intent-source:` line |
| IF-01 | intent.md has `Status: approved` and is committed | writes `Intent-source: specs/<slug>/intent.md @ <sha>` (the pin) plus the chat request verbatim in `### Intent` |
| IF-02 | intent.md has `Status: draft` | **stops** — not approved |
| IF-03 | intent.md is untracked (never committed) | **stops** — empty pin |
| IF-04 | intent.md is committed, then edited and not committed | **stops and asks for the intent to be committed** — drift command exits non-zero |
| IF-05 | intent.md is deleted, then re-created and not committed | **stops** — drift command exits non-zero |
| IF-06 | SUMMARY already has `Intent-source:`; intent.md re-committed; re-checked lane matches SUMMARY | **re-pin** — only the `Intent-source:` line changes and one dated `### Intake notes` line records old → new SHA; nothing else in SUMMARY changes; run state is not re-initialized |
| IF-07 | slug started from chat (no `Intent-source:`); intent.md now added, approved and committed; re-checked lane matches SUMMARY | **re-pin** — adds only the `Intent-source:` line and one dated `### Intake notes` line (old `none`); nothing else in SUMMARY changes; run state is not re-initialized |
| IF-08 | chat request conflicts with intent.md | **escalates** — ambiguous direction, confidence `low` (`../SKILL.md` Step 4) |
| IF-09 | intent.md is the unedited template (empty `Status:`) and is committed | **stops** — not approved |
| IF-10 | terse chat request ("do the intent"); approved, committed intent.md describes a hard-gated change (e.g. a schema migration) | lane `high-risk` — classified from intent.md, not the chat request |
| IF-11 | re-pin (as IF-06 or IF-07), but the re-checked lane differs from SUMMARY, or confidence is `low` | **stops** and shows the user the old and new values; writes nothing (SUMMARY unchanged, no `ESCALATIONS.md` block) |
| IF-12 | SUMMARY has `Intent-source:`, but intent.md was deleted | **stops before classifying** (routed by Step 1 to re-pin step 1) and tells the user to restore intent.md or remove the `Intent-source:` line; writes nothing |
| IF-13 | intent.md header line has `Status: draft`; body text contains `Status: approved` | **stops** — not approved |
| IF-14 | SUMMARY has `Intent-source:` with the same SHA intake now pins (re-run, intent.md unchanged) | **no-op** — nothing in SUMMARY changes, no Intake notes line; `verify_summary.py --lane` still runs |
| IF-15 | re-pin; re-checked lane matches SUMMARY but confidence (not `low`) or flags differ | **re-pins** as IF-06; the dated Intake notes line also records the confidence or flags change; `Confidence:` and `Flags:` lines are not edited |
| IF-16 | after an IF-11 stop, the user edits SUMMARY's `Lane:` (and related lines) to the new lane and runs intake again | **re-pins** as IF-06 — the re-check now matches |
| IF-17 | slug started from chat; an unapproved (`Status: draft`) or uncommitted intent.md is added; intake runs again | **stops** at re-pin step 2 (not approved / not committed); writes nothing |
| IF-18 | re-pin (as IF-06) where `### Intake notes` holds only `- none` | the `- none` line is replaced by the dated re-pin note, not kept beside it |

## Notes

- Intake reads `Status` from the header line only; `approved` in body text does not count.
- Agent notes go to `### Intake notes`, never `### Intent` or intent.md.
- On re-pin, intake never edits classification lines. A changed lane (or `low` confidence)
  stops and is shown to the user, who updates SUMMARY and runs intake again; no `ESCALATIONS.md`
  block is written.
