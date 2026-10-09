# gh-255-codex-hook-trust — Summary

Lane: high-risk
Confidence: high
Reason: the installer and the doctor decide the enforcement claim a Codex user sees (`enforced` / `advisory` / `unsupported`); the change also runs `init-structure.sh` against consumer repos from the installer (existing behavior, cross-platform).
Flags: audit/security, existing behavior, cross-platform, public contracts
Affects: `scripts/install-codex-harness.sh`, `scripts/codex_harness_doctor.py`, `specs/codex-support/capability-matrix.json` + `evidence/`, `docs/codex-alpha-install.md`
Input-type: spec slice
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> current the hook scripts are not available with codex
> and the claude code now support AGENTS.md file
> let review and checking if we can support user with codex if they want to install our harness-skill

> writing plan to the github first with seperate to each section with detail purpose and target
> after that, start for item 1 first

> approve design
> notes: - to avoid any breaking on main, let create branch call "codex" - all PRs related to it, let open to codex branch

> do for next step after this PR, continue based on it

> ok, let check sub-agent profile issue. and go to next phase 6 itme

"The next phase 6 item" after #254 is item 3, GitHub issue #255 ("Codex Phase 6.3: make hook
trust visible and actionable"). Its Target checklist is the scope of this slug. The sub-agent
profile check was done separately and filed as #268. The branch stacks on
`feat/gh-254-codex-agents-md-rules` (PR #267), because both items edit
`docs/codex-alpha-install.md` and the installer; the PR targets `codex`.

## What changed

<pending>

### Rationale

<pending>

### Alternatives considered

- none

### Deviations

- none

### Task review log

- Task 1.3 (`6795c61`): spec pass, quality approved, no findings.
- Task 1.1 (`d5ba42b`): spec pass, quality approved. Minor M1: the `MANIFEST_INVALID` skip of
  the helper check is untested (only `INSTALL_MISSING` is); M2: the drift test compares
  candidate tuples, so a pure reorder in a hook fails it (order decides which helper a hook
  picks, so strictness is defensible).

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 scripts/verify_summary.py --lane gh-255-codex-hook-trust` | 0 | intake |  |

### Not auto-verified

- none yet — filled at the end of the run.

### Rollback

- Code: `git revert` the branch's commits, or close the PR unmerged; nothing reaches `codex` until merge.
- Consumers: re-run `bash scripts/install-codex-harness.sh --source <pre-#255 checkout>`; the installer's next-step text and `init-structure.sh` call disappear, and directories `init-structure.sh` created stay (it only creates, never deletes).

### Harness-Delta

- none
