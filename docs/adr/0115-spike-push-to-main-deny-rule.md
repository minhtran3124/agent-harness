---
ticket: #530
stage: spike
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: implement; reworked after owner review of PR #532)
date: 2026-10-31
---

# 0115. Spike: the push-to-main deny rule blocks the common forms; server-side protection is the real control

## Context

Related: ADR 0114. The `permissions.deny` list blocked `git push * main` and `git push * master` only. Ticket #530 asked which push forms reach main despite it. `tests/scripts/push-deny-forms.test.sh` emulates the matcher with bash `case` (after splitting compound commands) over the list in `settings.json`, and really runs each form against a local bare remote (no network) to see whether the remote ref moves.

Result before the change: `HEAD:main`, `HEAD:refs/heads/main`, `+main` and `+HEAD:main` (and the master forms) were ALLOWED and reached the remote. `git push origin main`, `--force` and `-f` forms were BLOCKED.

## Options

- Add deny patterns for the refspec and plus forms, document the rest as known gaps
- Add broad patterns such as `git push*main*`, which also block unrelated commands
- Do nothing and rely on server-side protection

## Decision

Add exactly 6 patterns to both rule lists (`settings.json` and `RULES` in `merge-deny.sh`), for a total of 14 rules (8 original plus 6): `Bash(git push *:main)`, `Bash(git push *:refs/heads/main)`, `Bash(git push * +main)` and the same three for master. These are the patterns the owner confirmed.

An earlier draft grew the list to 72 rules (trailing-flag, quoted, separator and `*refs/heads/main*` forms). The owner cut it back: keep the common cases strict, and list every other form as a known gap in `docs/hooks.md`, each with the reason a glob cannot express it. The draft also failed on its own terms: its separator rules were redundant (see the matcher result below) and its trailing-flag rules denied a legitimate feature push that mentioned `main`.

Known gaps (ALLOWED, and they reach main on the remote): trailing flags (`HEAD:main --no-verify`), `refs/heads/main` without a colon, quoted branch or refspec, bare `git push` with an upstream of main, `git -C <dir> push ...`, aliases and a refspec built in a shell variable. Each is a gap row in the test and is listed in `docs/hooks.md`.

## Matcher evidence

Docs (https://code.claude.com/docs/en/permissions): `*` in a Bash rule matches any text, including spaces. For compound commands "deny and ask rules apply when any subcommand matches", with `&&`, `||`, `;`, `|`, `|&`, `&` and newlines as separators. `git -C . push origin main` and `git 'push' origin main` are listed as forms that `Bash(git push *)` does not stop.

Real run (2026-10-31, Claude Code 2.1.314): a throwaway project with a local bare remote and a project `.claude/settings.json` holding exactly the 14 rules; `claude -p "Run exactly this bash command ..." --model haiku --permission-mode default --allowedTools Bash --setting-sources project --output-format json --max-budget-usd 0.25`. A denial was read from `permission_denials` in the JSON, and the bare remote's `main` and `master` were compared with their start value.

| Form | Real matcher | Remote moved |
|---|---|---|
| `git push origin HEAD:main`, `HEAD:refs/heads/main`, `+main`, and the three master forms | denied | no |
| `git push origin HEAD:main; echo ok` | denied (compound split) | no |
| `git push origin HEAD:main --no-verify` | allowed | yes |
| `git -C . push origin HEAD:main` | allowed | yes |
| `git push origin 'HEAD:main'` | allowed | yes |
| `git push origin HEAD:"main"` | allowed | yes |
| `git push origin feat/x; git checkout main` (control) | allowed | no (main untouched) |
| bare `git push` from a `feat/x` branch | allowed | no (git refused the push, `push.default`); not run from `main`, so the gap is proven only by the emulation |

The test emulation agrees with every row. The matrix is therefore proven by the real matcher for 6 blocked forms and 4 gap forms, and emulated for the remaining gap rows (full ref without colon, other quote placements, variable refspec, `git push origin main --no-verify`).

## Why

The patterns close the forms a glob can express without blocking other commands. The gaps cannot be closed by a prefix glob, so the deny list is a mistake guard, not a sandbox. Server-side branch protection on GitHub (require PR, block force-push and deletion) is the real control. It is a manual owner step: `docs/hooks.md` holds a TODO placeholder, and the workflow never changes GitHub settings.

## Consequences

Setup merges 14 rules instead of 8 into consuming projects. A `git push` whose command text ends in `:main` or `:refs/heads/main` (or has `+main`) is denied, even when the refspec's source is a feature branch. Until the owner enables branch protection, the known gaps stay open. `tests/scripts/settings-wiring.test.sh` fails when the `RULES` literal in `merge-deny.sh` differs from the `settings.json` deny list, and the rule counts in the tests are derived from that list.

## How to reverse

Remove the six patterns from `settings.json` and `merge-deny.sh`; the tests derive the counts. Move the matching gap rows to `expect-blocked` or delete them. ADR 0114 is not edited.
