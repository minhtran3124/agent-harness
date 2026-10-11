# intent.md canaries

When `specs/<slug>/intent.md` exists, intake reads and pins it before classifying, then records
it in SUMMARY `### Intent`. A new slug (no SUMMARY) whose intent.md is not both approved and
committed goes through `../references/draft-intent.md` first. These pin Steps 1, 4, 5, and 6 of
`../SKILL.md`, the draft procedure, and the re-pin rules in `../references/re-pin.md`. A case passes when intake takes the expected action and writes nothing
else.

| ID | Setup | Expected |
|----|-------|----------|
| IF-00 | new slug; chat request only (not tiny + high); no intent.md | **drafts** intent.md (`Status: draft`, `## Original request` holds the chat verbatim), shows it, **stops**; no SUMMARY, no commit |
| IF-01 | intent.md has `Status: approved` and is committed | writes `Intent-source: specs/<slug>/intent.md @ <sha>` (the pin) plus the chat request verbatim in `### Intent` |
| IF-02 | new slug; intent.md has `Status: draft`; ordinary request | **shows** the file and proposed lane/confidence, **stops**; file not rewritten, no SUMMARY, no commit |
| IF-03 | new slug; intent.md is untracked (never committed); ordinary request | **shows** the file and the proposed lane/confidence, **stops**; not rewritten, not auto-approved, no SUMMARY, no commit |
| IF-04 | new slug; intent.md is committed, then edited and not committed; ordinary request | **shows** the file and the proposed lane/confidence, **stops**; edit kept as-is, no SUMMARY, no commit |
| IF-05 | new slug; intent.md is deleted, then re-created and not committed; ordinary request | **shows** the file and the proposed lane/confidence, **stops**; not rewritten, no SUMMARY, no commit |
| IF-06 | SUMMARY already has `Intent-source:`; intent.md re-committed; re-checked lane matches SUMMARY | **re-pin** — only the `Intent-source:` line changes and one dated `### Intake notes` line records old → new SHA; nothing else in SUMMARY changes; run state is not re-initialized |
| IF-07 | slug started from chat (no `Intent-source:`); intent.md now added, approved and committed; re-checked lane matches SUMMARY | **re-pin** — adds only the `Intent-source:` line and one dated `### Intake notes` line (old `none`); nothing else in SUMMARY changes; run state is not re-initialized |
| IF-08 | chat request conflicts with intent.md | **escalates** — ambiguous direction, confidence `low` (`../SKILL.md` Step 4) |
| IF-09 | new slug; intent.md is the unedited template (empty `Status:`) and is committed; ordinary request | **shows** the file and the proposed lane/confidence, **stops**; not filled from the chat, not auto-approved, no SUMMARY, no commit |
| IF-10 | terse chat request ("do the intent"); approved, committed intent.md describes a hard-gated change (e.g. a schema migration) | lane `high-risk` — classified from intent.md, not the chat request |
| IF-11 | re-pin (as IF-06 or IF-07), but the re-checked lane differs from SUMMARY, or confidence is `low` | **stops** and shows the user the old and new values; writes nothing (SUMMARY unchanged, no `ESCALATIONS.md` block) |
| IF-12 | SUMMARY has `Intent-source:`, but intent.md was deleted | **stops before classifying** (routed by Step 1 to re-pin step 1) and tells the user to restore intent.md or remove the `Intent-source:` line; writes nothing |
| IF-13 | new slug; intent.md header line has `Status: draft`; body text contains `Status: approved`; ordinary request | **shows** the file and the proposed lane/confidence, **stops** — not approved; not rewritten, no SUMMARY, no commit |
| IF-14 | SUMMARY has `Intent-source:` with the same SHA intake now pins (re-run, intent.md unchanged) | **no-op** — nothing in SUMMARY changes, no Intake notes line; `verify_summary.py --lane` still runs |
| IF-15 | re-pin; re-checked lane matches SUMMARY but confidence (not `low`) or flags differ | **re-pins** as IF-06; the dated Intake notes line also records the confidence or flags change; `Confidence:` and `Flags:` lines are not edited |
| IF-16 | after an IF-11 stop (which showed the new `Lane:`, `Confidence:`, `Reason:`, `Flags:`, `Route:`, `Escalate:` lines), the user updates those lines in SUMMARY and runs intake again | **re-pins** as IF-06 — the re-check now matches |
| IF-17 | slug started from chat; an unapproved (`Status: draft`) or uncommitted intent.md is added; intake runs again | **stops** at re-pin step 2 (not approved / not committed); writes nothing |
| IF-19 | after an IF-12 stop, the user removes the `Intent-source:` line, updates the classification lines to match the chat request, and runs intake again | no re-pin (no `Intent-source:`, no intent.md); the existing SUMMARY is left as the user set it |
| IF-20 | re-pin; SUMMARY is `high-risk` from 4+ flags with no hard gate; the re-committed intent.md adds a schema migration (a manifest hard gate) | **stops** and shows the user the old and new lines, as IF-11, even though the lane is unchanged |
| IF-18 | re-pin (as IF-06) where `### Intake notes` holds only `- none` | the `- none` line is replaced by the dated re-pin note, not kept beside it |
| DI-01 | new slug; tiny + high chat request; no intent.md | intent.md written with `Status: approved` and `## Original request`, committed alone (subject ends `(auto-approved: tiny/high)`); SUMMARY pinned (`Intent-source:`); `### Intake notes` says `auto-approved: tiny/high` |
| DI-02 | new slug; normal-lane chat request; no intent.md | draft intent.md with `Status: draft`, `(assumed)` on proposed lines; **stops**; no SUMMARY, no commit |
| DI-03 | after DI-02, a new run with the reply `approve` | `Status: approved`, intent.md committed alone; SUMMARY pinned; `### Intent` holds the `## Original request` text, never "approve" |
| DI-04 | after DI-02, a reply asking for a change (even with "approve") | draft edited and the reply appended verbatim to `## Original request`; **stops**; still `Status: draft`, no SUMMARY, no commit |
| DI-05 | legacy slug: SUMMARY exists, no intent.md | no intent.md written; behavior unchanged (no draft) |
| DI-06 | new slug; a person's `Status: draft` intent.md; tiny + high request | **shown** for approval, **stops**; never auto-approved, not rewritten, no SUMMARY, no commit |
| DI-07 | after DI-02, the user sets `Status: approved` in the file (uncommitted) and replies `done` | intent.md committed alone; SUMMARY written and pinned; `### Intent` holds `## Original request` |
| DI-08 | new slug; a person's `Status: approved` but uncommitted intent.md; ordinary request | file unchanged; **shown**, **stops**; no SUMMARY, no commit |
| DI-09 | after DI-04 (a change made the draft differ from the first request), the user replies `approve` | committed and pinned; the approved file wins over `## Original request` — **not** a chat conflict, confidence not lowered for it |
| DI-10 | after DI-02, a new run whose arguments are only `approve` (no slug) | resolves to the pending draft's slug (named, shown in this conversation, or the only slug with an intent.md and no SUMMARY); **no** new slug is derived from "approve"; several candidates → asks |
| DI-11 | DI-01 or DI-03 while the current branch is `main` | `git switch -c <type>/<slug>` and the intent commit there; intake **stays** on it and finishes (pin, SUMMARY) there — `main` gets no commit; tiny keeps the branch; `using-git-worktrees` switches the main checkout back to `<base>`, then resets the worktree to `<type>/<slug>` and renames with `git branch -M` |
| DI-12 | DI-01, but the post-commit Step 1 classification is not tiny + high | `Status: draft` set and committed again; **stops** for approval; no `auto-approved` note |
| DI-13 | the intent commit is refused (a hook or git) | **stops**, reports the output, says intent.md is still staged; on the auto-approve path `Status: draft` is restored |
| DI-14 | a person's draft (no `## Original request`) and a run that asks to change it | file edited; the change appended under a new `## Original request`; shown, **stops** |
| DI-15 | one abandoned draft slug exists (intent.md, no SUMMARY); a new conversation brings an unrelated new request | a **new** slug is derived; the abandoned draft is not edited |
| IF-21 | SUMMARY has `Intent-source:`; intent.md edited after its commit and not re-committed | **stops** at re-pin step 2 (drift); writes nothing |
| IF-22 | SUMMARY has `Intent-source:`; intent.md `Status:` now empty or `draft` | **stops** at re-pin step 2 (not approved); writes nothing |
| IF-23 | SUMMARY has `Intent-source:`; header `Status: draft`, body contains `Status: approved` | **stops** at re-pin step 2 (header only counts); writes nothing |

## Notes

- Intake reads `Status` from the header line only; `approved` in body text does not count.
- Agent notes go to `### Intake notes`, never `### Intent`; intent.md content comes only from the
  draft procedure (its `(assumed)` proposals) or the user.
- An approval or change reply is never recorded as the request; with no `## Original request` and
  no chat request, `### Intent` records `none — intent.md is the request`.
- On re-pin, intake re-classifies from intent.md plus the original chat request in `### Intent`,
  never from the re-run's own arguments. It never edits classification lines. A changed lane (or `low` confidence)
  stops and is shown to the user, who updates SUMMARY and runs intake again; no `ESCALATIONS.md`
  block is written.
