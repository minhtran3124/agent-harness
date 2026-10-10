# intent-md-entry — Design

Written 2026-10-10. Pins: repo 49a1c93 + uncommitted
Revised 2026-10-10. Pins: repo 600c854 + uncommitted

## Goal

Let anyone write `specs/<slug>/intent.md` to the AI-native SDLC playbook standard, mark it
approved, commit it, and hand the slug to the team. `/feature-intake <slug>` then starts the
workflow from that file, and `/intent-review` judges the finished diff against it, pinned at the
commit intake recorded. Requests made only in chat keep working exactly as today.

## Current state

- `/feature-intake` copies the user's chat request verbatim into `SUMMARY.md` `### Intent`
  (`skills/feature-intake/SKILL.md` step 5). There is no intent file and no approval step.
- `/intent-review` reads `### Intent` as its oracle (`skills/intent-review/SKILL.md` step 1;
  `intent-reviewer-prompt.md` pastes that block into the reviewer).
- The oracle already mixes in agent prose: `specs/gh-258-sc-goalpost-guard/SUMMARY.md` `### Intent`
  carries an agent-written confidence paragraph after the user's lines.
- A commit that stages only a file under `specs/<slug>/`, with no `SUMMARY.md`, passes
  `hooks/commit-gate.sh` today, and `specs/*` edits are allowed on `main`
  (`hooks/branch-isolation-guard.sh:166`).
- `scripts/install-harness.sh:34` ships the whole `templates/` directory to consumer repos.

Background and the playbook comparison: `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md` §7.

## Approaches considered

1. **Copy a snapshot into SUMMARY, checked by hash.** Survives any later change to the file, but
   duplicates the intent and needs a script to copy and hash it.
2. **Pointer to a commit SHA; `/intent-review` reads the old version with `git show`.** One copy,
   but adds a tool permission to `intent-review`, changes the reviewer prompt and the Codex render.
3. **Pointer to a commit SHA; any change after the pin stops the review until intake re-pins.**
   One copy, no new tool, no script. **Chosen.** The user's argument: spec files are committed and
   never deleted, and git history restores any version, so a copy buys nothing. A change after the
   pin stops the review instead of judging the old text — stricter, and still nobody moves the
   goalposts silently.

## Architecture

| File | Change |
|---|---|
| `templates/INTENT.template.md` (new) | `Author:`, `Status:` left empty with a note to set `approved` or `draft` (revised 2026-10-10 by the user after intent review); sections Problem · Proposed outcome · Affected users and systems · Constraints · Out of scope · Open questions · What success looks like |
| `skills/feature-intake/SKILL.md` | One step: when `specs/<slug>/intent.md` exists, use it as the intent (checks below) |
| `skills/intent-review/SKILL.md` | Step 1: when `### Intent` has an `Intent-source:` line, check drift, then use the file as the oracle |
| `skills/intent-review/intent-reviewer-prompt.md` | The INTENT input line names both sources (the `### Intent` block, or the pinned intent.md text) |
| `templates/SUMMARY.template.md` | `### Intent` may hold an `Intent-source:` line; new `### Intake notes` section for agent-written notes |
| `rules/terminology.md` | Hard exclusion 1 also covers `specs/<slug>/intent.md` |
| `templates/structure/specs-README.md`, `skills/README.md` | List `intent.md` and the new entry point |

Data flow:

```
author:  copy template → specs/<slug>/intent.md → Status: approved → commit (main is fine)
/feature-intake <slug>:
  read intent.md; require the header line Status: approved
  pin = git log -1 --format=%H --diff-filter=AM -- specs/<slug>/intent.md
        (empty = never committed → stop)
  git diff --exit-code <pin> -- specs/<slug>/intent.md → exit 0 = the file on disk is the pinned text
  SUMMARY ### Intent:  Intent-source: specs/<slug>/intent.md @ <pin>
                       + the user's chat request verbatim, as today
  agent notes (confidence reasoning, defaults) → ### Intake notes
/intent-review:
  git diff --exit-code <pin> -- specs/<slug>/intent.md → exit 0 = still the pinned text
  oracle = intent.md text + the chat request in ### Intent
```

One command, used by both skills, is the whole check. `--diff-filter=AM` makes the pin the last
commit that added or modified the file, so the path always exists at the pin. `git diff <pin> --
<path>` compares that commit to the working tree and exits non-zero for every bad case: an edit
after the pin (committed or not), a deletion, a file deleted and re-created with different text or
left unstaged, and an unknown SHA (128). The one passing edge — re-created with the exact pinned
text and staged — is harmless: the text on disk is the pinned text. Checked in a scratch repo on
2026-10-10.

The chat request is still copied verbatim in full, as today, so no agent judgment decides what
enters the oracle. When a chat line conflicts with intent.md, that is an ambiguous direction
(error table).

**Re-pin.** Intake on a slug whose `SUMMARY.md` already has an `Intent-source:` line replaces only
that line with the new pin and adds a dated `### Intake notes` line naming the old and new SHA.
Every other SUMMARY section is kept. The lane is re-checked against the changed intent: it may go
up; it goes down only by the existing rule (a human narrows scope). A slug that started from chat
and gets an intent.md later is handled the same way: the `Intent-source:` line is added, the chat
request stays.

**SUMMARY template.** The comment under `### Intent` is rewritten to allow either form (verbatim
chat request, or `Intent-source:` plus the chat request). `### Intake notes` is a new section
directly after `### Intent`.

## Worked trace

1. A teammate copies `templates/INTENT.template.md` to `specs/claims-status/intent.md`, fills it,
   sets `Status: approved`, and commits it on `main` as `a1b2c3d`.
2. Someone runs `/feature-intake claims-status`. Intake reads the file, sees `approved`,
   `git log --diff-filter=AM` returns `a1b2c3d`, `git diff --exit-code a1b2c3d` exits 0. It writes
   `SUMMARY.md` with `Intent-source: specs/claims-status/intent.md @ a1b2c3d`, classifies the lane,
   routes as usual.
3. During implementation the author edits a constraint and commits it as `e4f5a6b`.
4. `/intent-review` runs `git diff --exit-code a1b2c3d -- specs/claims-status/intent.md`, gets
   exit 1, and stops: the intent changed after the pin.
5. `/feature-intake claims-status` re-pins: `Intent-source:` now reads `@ e4f5a6b`, an Intake notes
   line records `a1b2c3d → e4f5a6b`, the lane is re-checked, and the rest of SUMMARY is kept.
   `/intent-review` then passes its check and reviews against the new text.

## Error behavior

| Situation | Behavior |
|---|---|
| The `Status:` header value is not exactly `approved` (including empty) | Intake stops and says the intent is not approved yet |
| No commit added or modified intent.md (empty pin), or `git diff --exit-code <pin>` is non-zero | Intake stops and asks for the current intent to be committed first |
| Slug already pinned | Re-pin: replace `Intent-source:`, add an Intake notes line, keep the rest of SUMMARY |
| No intent.md for the slug | Today's flow: the chat request is copied verbatim |
| Chat request conflicts with intent.md | Ambiguous direction → existing escalation rule (`ESCALATIONS.md`) |
| intent.md changed or deleted after the pin, or the SHA is unknown | `/intent-review` stops, reports drift, asks for intake to re-pin |

## Tests

- Hook test (truth): a commit staging only `specs/<slug>/intent.md` passes `commit-gate.sh`, in
  `tests/hooks/commit-gate.test.sh`. Locks today's behavior.
- Intake cases (traceability): approved, draft, uncommitted, deleted-and-re-created, and re-pin
  cases added to `skills/feature-intake/tests/`.
- Dogfood run (truth, one trial): write an approved intent for a small scratch slug, run
  `/feature-intake`, then edit the intent and run `/intent-review`; record both outcomes in
  `### Verify`.
- `bash scripts/run-tests.sh` (allowed-tools conformance, Codex render tests, doc-truth lint).

## Success criteria

| ID | Outcome | Check |
|---|---|---|
| SC-1 | The template exists with `Author`, `Status`, and the seven sections | grep of `templates/INTENT.template.md` |
| SC-2 | An intent-only commit passes `commit-gate.sh` | new case in `tests/hooks/commit-gate.test.sh` exits 0 |
| SC-3 | Intake on an approved, committed intent writes `Intent-source: … @ <sha>` where `<sha>` equals `git log -1 --format=%H --diff-filter=AM` of the file; a re-pin replaces only that line | dogfood run |
| SC-4 | Intake stops on `Status: draft` and on an uncommitted intent | dogfood run |
| SC-5 | `/intent-review` stops when the intent changed after the pin | dogfood run |
| SC-6 | No new tool permission: `allowed-tools` of both skills unchanged | `git diff` of the two frontmatter lines is empty |
| SC-7 | Full suite green | `bash scripts/run-tests.sh` exits 0 |

## Non-goals

- An authoring helper that interviews the author and drafts intent.md (E001: later).
- Any new script, gate, or `verify_summary.py` change; any hook that blocks deleting intent.md.
- Installer changes (`templates/` already ships).
- GitHub-issue intake.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | A commit staging only `specs/<slug>/intent.md` passes `commit-gate.sh` (standard and strict) | truth: Local, 2026-10-10, scratch-worktree run of `hooks/commit-gate.sh` | SC-2 | Authors cannot commit an intent alone; add the narrowest skip to the failing check |
| A2 | `specs/*`-only edits are allowed on `main` | provenance: Local, 2026-10-10, `hooks/branch-isolation-guard.sh:166` | SC-2 dogfood commit | Authors must branch first; document it in the template |
| A3 | `feature-intake` can run `git log` and `git diff` | provenance: Local, 2026-10-10, `skills/feature-intake/SKILL.md:4` | SC-6 | A tool permission must be added after all |
| A4 | `intent-review` can run `git diff` | provenance: Local, 2026-10-10, `skills/intent-review/SKILL.md:4` | SC-6 | Same as A3 |
| A5 | With the pin from `git log -1 --diff-filter=AM`, `git diff --exit-code <pin> -- <path>` exits non-zero for an edit after the pin (committed or not), a deletion, a delete-and-re-create without a commit, and an unknown SHA | truth: Local, 2026-10-10, scratch-repo probe (`scratchpad/gitprobe`) | SC-5 dogfood | Drift slips through; add the missing case as a second command |
| A6 | `scripts/install-harness.sh` ships a new file under `templates/` with no change | provenance: Local, 2026-10-10, `scripts/install-harness.sh:34` | xia2 check of the deploy path | Add the file to the payload |
| A7 | The pinned SHA stays reachable (intent committed on `main` before the branch) | none yet: Inference from the intended flow | accepted risk: an unreachable SHA fails closed into a re-pin | Re-pin via intake |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| The model always follows the new intake and intent-review steps | They are prose instructions; SC-3–SC-5 are one dogfood trial, not a gate |
| `Status: approved` means someone other than the author approved | The field records a claim; no gate checks who set it |
| intent.md cannot be deleted or edited mid-work | Nothing blocks it; the drift check only detects it at intent-review |
| A stop at `/intent-review` always means the author changed the intent | An unreachable pin (e.g. pinned on a branch later squashed) also stops it; the remedy is the same re-pin |
| The Codex runtime behaves the same | Only the rendered text is tested by `run-tests.sh`; no Codex run is part of this change |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | Intent lives in `specs/<slug>/intent.md`, not a GitHub issue | No GitHub dependency; works offline and in any consumer repo | settled |
| D2 | Approval is `Status: approved` in a committed file | Drafts can be committed for feedback; intake refuses them | settled |
| D3 | Pin by commit SHA; no copy of the intent in SUMMARY | One source of truth; relies on git history | settled |
| D4 | A change after the pin stops `/intent-review` until intake re-pins | Stricter than judging the old text; every re-pin is a recorded intake | settled |
| D5 | Agent-written intake notes go to `### Intake notes`, never `### Intent` | The oracle holds only human-authored text | settled |
| D6 | No new script, gate, or tool permission; plain instructions only | Smaller change; compliance is not mechanically enforced (see What we do not claim) | settled |
