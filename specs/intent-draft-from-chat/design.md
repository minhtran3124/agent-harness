# intent-draft-from-chat — Design

Written 2026-10-10. Pins: repo a2b148c

## Goal

Every new slug gets a `specs/<slug>/intent.md` with the same structure, whatever the lane. A **new
slug** is one with no `specs/<slug>/SUMMARY.md`. When the user gives the request only in chat,
intake drafts intent.md from the template and the chat. Lanes differ only in approval: an intent
that intake drafted in the current run and classified tiny + high confidence is auto-approved;
everything else waits for the user to approve in chat or edit the file.

## Current state

- PR #284 (`specs/intent-md-entry/`) made intent.md an optional entry artifact. Intake Step 1
  (`skills/feature-intake/SKILL.md:17-25`) reads it when present, requires `Status: approved`,
  pins it by SHA, and classifies from intent.md plus chat. With no intent.md, intake is chat-only
  and writes no `Intent-source:` line (Step 5).
- Re-running intake on a slug with a SUMMARY goes to `references/re-pin.md`.
- `skills/feature-intake/SKILL.md` is at 599 words (measured 2026-10-10 `audit_skill_prompts.py`)
  against a ceiling of 600 (budget).
- Its `allowed-tools` has `git log` and `git diff` but **no `git add` / `git commit`**
  (`SKILL.md:4`), so intake cannot commit an intent today.
- Step 6 (`SKILL.md:39-40`) says agent notes never go "in `### Intent` or intent.md".
- `templates/INTENT.template.md` opens with a comment telling a human to copy it and set Status.
- `rules/terminology.md:79` calls intent.md "the human-written intent";
  `templates/structure/specs-README.md:32` lists its author as "a human (optional)".
- The branch guard exempts `specs/*` **edits** (`hooks/branch-isolation-guard.sh`); nothing in
  `hooks/commit-gate.sh` restricts which branch a commit lands on. PR #284 already intended a
  person to commit intent.md on the current branch, including `main`.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| **A (chosen)** | New `skills/feature-intake/references/draft-intent.md`; Step 1 gains one pointer sentence | No new skill; users keep calling `/feature-intake`; costs a few words trimmed elsewhere in SKILL.md |
| B | Separate `intent-draft` skill called by intake | Another skill to deploy, audit and render for Codex; heavier than needed |
| C | Instructions only in the template comment | No mandatory step; the model can skip it |

## Architecture

**Entry rule (SKILL.md Step 1, one sentence).** A new slug (no SUMMARY) follows
`references/draft-intent.md` unless its intent.md is `Status: approved` **and** committed (no
uncommitted change). Unchanged: SUMMARY + (`Intent-source:` or intent.md) → re-pin; approved and
committed intent.md with no SUMMARY → today's Step 1.

**`references/draft-intent.md` procedure** — two cases, keyed on whether the file exists:

1. **intent.md is absent → draft it.** Write it from `templates/INTENT.template.md`: drop the copy
   comment; `Author:` = git `user.name` (or `unknown` if unset); `Status: draft`. Fill each section
   from the chat. Where the chat says nothing, propose content and end the line with `(assumed)`.
   Do not state a goal the chat does not. Append `## Original request` holding the chat request
   verbatim and in full. Classify the draft plus the chat (SKILL.md Steps 2–4) without writing
   SUMMARY. Tiny + high: set `Status: approved`, commit (step 3), continue at SKILL.md Step 1, and
   note `auto-approved: tiny/high` in `### Intake notes`. Otherwise: ask and stop (step 2's last
   bullet).
2. **intent.md exists** (any state other than approved and committed — a person's file or an
   earlier run's draft). Never rewrite it from the template and never auto-approve it. By the
   current message:
   - approves it (`approve`, or "edited, done" — even if the user already set `Status: approved`):
     set `Status: approved` if not already, commit (step 3), continue at SKILL.md Step 1;
   - asks for changes (even together with "approve"): edit the file, then ask and stop;
   - anything else: **ask and stop** — show the file and the proposed lane/confidence; ask the
     user to reply `approve`, ask for changes, or edit the file and say done. Write no SUMMARY
     and no commit.
3. **Commit** only this file, on the current branch:
   `git add -- specs/<slug>/intent.md` then
   `git commit -m "docs(specs): intent for <slug>" -- specs/<slug>/intent.md` (suffix
   `(auto-approved: tiny/high)` when step 1 approved it — the durable record of auto-approval). The pathspec keeps anything else the
   user staged out of the commit. If there is nothing to commit (the file already matches HEAD),
   skip the commit.

After approval, SKILL.md Step 1 pins the committed file and classifies from it; that
classification is the one recorded, so a user edit that changes the lane takes effect.

SUMMARY `### Intent` holds the pin line, then the verbatim request: `## Original request` when
intent.md has one; else the chat request; and when the chat holds only an approval or change reply,
`none — intent.md is the request`. An approval or change reply is never recorded as the request.

**Other changes:**

- `SKILL.md` `allowed-tools`: add `Bash(git add *)` and `Bash(git commit *)`.
- `SKILL.md` Step 6: agent notes never go in `### Intent`; intent.md content comes only from the
  draft procedure (its `(assumed)` proposals) or the user. Step 5 "chat-only intake writes none"
  now applies only to legacy slugs. Trim words elsewhere so the file stays ≤600 (budget).
- `templates/INTENT.template.md` comment: a person copies it, or intake drafts it from chat (and
  then appends `## Original request`).
- `rules/terminology.md:79`: intent.md is "approved by a human, or auto-approved by intake for
  tiny/high"; its `## Original request` (when present) is the verbatim request; editing a draft
  before approval is outside the exclusion.
- `templates/structure/specs-README.md:32`: author "a human, or intake from chat".
- Canary cases appended to `skills/feature-intake/tests/intent-file-cases.md`.

## Worked trace

User: "đổi tiêu đề README thành Demo API" → `/feature-intake readme-title`. No SUMMARY, no
intent.md → draft procedure step 1: Problem/Outcome from chat; Out of scope "Any code change
(assumed)"; success "`head -1 README.md` prints `# Demo API` (assumed)"; `## Original request`
holds the chat. Classified tiny, high → approved, committed. Step 1 pins the SHA; SUMMARY gets
`Intent-source:` + the original request; route tiny.

If the chat had been "add login rate limiting": step 1 classifies high-risk → it shows the
draft and stops. Later, possibly in a new session, the user runs `/feature-intake <slug>` with
"approve" → step 2 commits → Step 1 pins → SUMMARY's `### Intent` takes the request from
`## Original request`, not from "approve".

## Error behavior

| Case | Behavior |
|---|---|
| intent.md exists (draft, empty, or approved but uncommitted), no SUMMARY | Step 2: never rewritten or auto-approved; committed on approval, else shown and stop |
| Legacy slug: SUMMARY exists, no intent.md | Unchanged: entry rule needs no SUMMARY, so no draft |
| SUMMARY + intent.md | re-pin, unchanged |
| git `user.name` unset | `Author: unknown` |
| Approved file already matches HEAD | Commit skipped; Step 1 pins the existing commit |
| Other files already staged | Not included: commit uses the intent.md pathspec |
| Commit refused by a hook | Stop and report the hook output; never bypass |
| Lane after approval differs from the draft's proposed lane | The approved classification wins; nothing to undo since SUMMARY did not exist |
| Approval in a later session for a person's draft with no `## Original request` | `### Intent` records `none — intent.md is the request`, never "approve" |
| Low confidence on the draft | Not tiny+high, so step 1 shows it and stops; open points go in Open questions |

## Tests

- `bash scripts/run-tests.sh` (runtime-neutral and skill-bash lint, `check_skill_tool_conformance.py`)
  and `python3 scripts/audit_skill_prompts.py` — truth.
- Review chain: context-propagation audit, correctness review, intent review.
- Real install (`install-harness.sh` into a scratch repo, `claude -p "/feature-intake <slug>"`),
  one trial each — truth:
  1. tiny/high chat → intent.md committed with `Status: approved` and `## Original request`; SUMMARY pinned; Intake notes say auto-approved;
  2. normal chat → draft intent.md with `Status: draft`, no SUMMARY, no commit;
  3. scenario 2, then a new `claude -p "/feature-intake <slug> approve"` → intent committed, SUMMARY `### Intent` holds the original request (not "approve");
  4. scenario 2, then "change X" → draft edited, still no SUMMARY/commit;
  5. legacy slug (SUMMARY, no intent.md) → no intent.md written;
  6. a person's `Status: draft` intent.md on a tiny change → shown for approval, not auto-approved;
  7. scenario 2, then the user sets `Status: approved` in the file (uncommitted) and runs `/feature-intake <slug> done` → intent committed, SUMMARY written;
  8. a person's approved but uncommitted intent.md with an ordinary request → file unchanged, shown, stop.

## Success criteria

- SC-1: `python3 scripts/audit_skill_prompts.py` exits 0 (feature-intake ≤600 words, budget).
- SC-2: `bash scripts/run-tests.sh` ends `ALL GREEN`.
- SC-3: real-install scenarios 1–8 above each match (recorded in SUMMARY; truth, one trial).
- SC-4: `grep -c "^allowed-tools:.*Bash(git commit \*)" skills/feature-intake/SKILL.md` prints 1.

## Non-goals

- No change to re-pin rules, intent-review, or commit-gate.
- No `Approved-by:` field, no C-n/Q-n IDs (still deferred from §7).
- No GitHub issue or connector path.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | A commit staging only `specs/<slug>/intent.md` passes commit-gate with no SUMMARY | truth: Local, 2026-10-10, `tests/hooks/commit-gate-evidence.test.sh:224-239` | SC-2 | Intake cannot commit; ask the user to commit instead |
| A2 | Intake can write intent.md on any branch (specs/* edit exemption) and commit it there (no branch check at commit) | provenance: Local, 2026-10-10, `hooks/branch-isolation-guard.sh`, `hooks/commit-gate.sh` | SC-3 scenario 1 | Intake must create a branch first; add that step |
| A3 | A later session re-enters the procedure from files alone and recovers the verbatim request from `## Original request` | none yet: Inference — the procedure keys on files, and the request is stored in the draft | SC-3 scenario 3 | Store the request in a sidecar file instead |
| A4 | Adding `git add`/`git commit` to `allowed-tools` passes the Codex render and `check_skill_tool_conformance.py` | none yet: Inference — allowed-tools entries are rendered as text | SC-2 | Adjust the render or conformance allowlist |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| A human read every line of every intent | Tiny + high is auto-approved; its `(assumed)` lines enter the oracle unread (user's choice) |
| An auto-approved intent is always tiny when SUMMARY is written | Step 1 classifies the committed file again; with the same inputs a different result is unlikely but not prevented, and is not stopped on (keeps the procedure to two cases) |
| Headless runs complete without a human | Every case except a fresh tiny + high draft stops for approval |
| `(assumed)` lines are correct | They are proposals; approval (or auto-approval) makes them part of the oracle |
| Intent commits land on a feature branch | Intake commits on the current branch, which may be `main` (as a person would in PR #284) |
| Intake can only commit intent.md | `Bash(git commit *)` allows any commit; the procedure restricts it by pathspec, not by permission (accepted risk) |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | Draft intent.md for every lane on a new slug (no SUMMARY) | Same spec structure for all lanes | settled |
| D2 | A draft intake wrote in the current run, classified tiny + high, is auto-approved and committed | Tiny work stays autonomous; its intent is not human-read | settled |
| D3 | All other cases: user approves by replying in chat, or edits the file and says done | Intake stops once per new non-tiny slug | settled |
| D4 | Sections the chat does not cover are proposed by the AI and marked `(assumed)` | Fuller draft; assumptions enter the oracle once approved | settled |
| D5 | Procedure lives in `references/draft-intent.md`; SKILL.md gains one pointer | SKILL.md stays ≤600 words (budget) | settled |
| D6 | Drafting applies only when the slug has no SUMMARY | Legacy chat-only slugs keep today's behavior | settled |
| D7 | The drafted intent keeps the chat verbatim under `## Original request`; SUMMARY copies it | The oracle survives a cross-session approval | settled |
| D8 | Intake commits intent.md alone (pathspec) on the current branch | Matches PR #284's human flow; may land on `main` | settled |
