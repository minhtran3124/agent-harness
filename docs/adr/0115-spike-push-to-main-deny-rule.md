---
ticket: #530
stage: spike
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-31
---

# 0115. Spike: the push-to-main deny rule blocks the common forms; server-side protection is the real control

## Context

Related: ADR 0114. The `permissions.deny` list blocked `git push * main` and `git push * master` only. Ticket #530 asked which push forms reach main despite it. Claude Code's permission matcher cannot run offline, so `tests/scripts/push-deny-forms.test.sh` emulates the prefix glob with bash `case` over the list in `settings.json`, and really runs each form against a local bare remote (no network) to see whether the remote ref moves.

Result before the change: `HEAD:main`, `HEAD:refs/heads/main`, `+main` and `+HEAD:main` (and the master forms) were ALLOWED and reached the remote. `git push origin main`, `--force` and `-f` forms were BLOCKED.

## Options

- Add deny patterns for the refspec and plus forms, document the rest as known gaps
- Add broad patterns such as `git push*main*`, which also block unrelated commands
- Do nothing and rely on server-side protection

## Decision

Add 18 patterns to both rule lists (`settings.json` and `RULES` in `merge-deny.sh`): for main and master, the refspec forms `*:main`, `*:refs/heads/main`, `* +main`, plus (review fix) `*refs/heads/main*` (full ref, with or without `+`), the trailing-flag forms `* main *`, `*:main *`, `* +main *`, and the quoted forms `*main"*` and `*main'*`. The forms listed in the test are BLOCKED and the control `git push origin feat/x` is ALLOWED. Not every form a shell can express is covered (see the known gaps); the first draft's claim that every expressible form is blocked was wrong.

Known gaps (ALLOWED, and they reach main on the remote): bare `git push` or `git push origin` with an upstream of main, `git -C <dir> push ...`, other quoting or escaping of the branch name, aliases, a refspec built in a shell variable. They are listed in `docs/hooks.md`.

## Why

The patterns close the forms a glob can express without blocking other commands. The gaps cannot be closed by a prefix glob, so the deny list is a mistake guard, not a sandbox. Server-side branch protection on GitHub (require PR, block force-push and deletion) is the real control. It is a manual owner step: `docs/hooks.md` holds a TODO placeholder, and the workflow never changes GitHub settings.

## Consequences

Setup merges 26 rules instead of 8 into consuming projects. A command containing `:main` after `git push` is now denied even for a non-main remote branch of that name. Until the owner enables branch protection, the known gaps stay open.

## How to reverse

Remove the added patterns from `settings.json` and `merge-deny.sh`, and update the counts (26) in `tests/scripts/merge-deny.test.sh` and the matrix test. ADR 0114 is not edited.
