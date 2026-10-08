# gh-253-codex-full-payload — Summary

Lane: high-risk
Confidence: high
Reason: hard gate high-blast — the change edits `hooks/commit-gate.sh` and the Codex installer/deployer scripts every Codex consumer runs.
Flags: high-blast, existing behavior, cross-platform, public contracts
Affects: Codex adapter (`scripts/render_codex_adapter.py`, `scripts/deploy-codex-adapter.sh`, `scripts/install-codex-harness.sh`), `hooks/commit-gate.sh` helper lookup
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

Item 1 is GitHub issue #253 ("Codex Phase 6.1: ship the full harness payload with the Codex
install"), tracked under #257. Its Target checklist is the scope of this slug.

## What changed

<pending — intake only>

### Rationale

Confidence is `high`: the issue's Target is concrete, and the design follows an existing
precedent — `scripts/deploy-harness.sh` already defines the canonical consumer subset
(`CONSUMER_SCRIPTS`/`CONSUMER_DATA`) and rewrites root-relative helper paths in derived Markdown.
The Codex adapter already owns `.codex/.agent-harness/` per `docs/codex-alpha-install.md`, so the
payload location has one interpretation that respects the existing ownership boundary.

### Alternatives considered

- To be recorded in `design.md`.

### Deviations

- Rule 1 — The controller fixed Task 1.3's review findings directly. The docs claimed `--remove` behaves "as the Claude installer does", but the Claude installers have no `--remove` path (`grep -c -- --remove` is 0 in both). The wording came from `design.md`, so it was corrected there too. The docs now also name the `.codex/*` and negated `!` skip forms the installer honours. Two pinned skip forms were added to `tests/scripts/codex-install-gitignore.test.sh`. Files: `docs/codex-alpha-install.md`, `tests/scripts/codex-install-gitignore.test.sh`, `specs/gh-253-codex-full-payload/design.md`.
- Process — Implementers left changes uncommitted; the controller committed each task separately so two parallel implementers in one worktree could not collide on git's index lock.

Minor review findings, carried to the final review:
- Task 1.2: the `codex_lane_repo` case in `tests/hooks/commit-gate-evidence.test.sh` does not assert that the source and `.claude/` copies of `verify_summary.py` are absent, so a future `new_repo` change could let it pass for the wrong reason.
- Task 1.1: until Task 2.1 lands, wave 1 leaves `codex-install.test.sh` red by plan ordering (closed by Task 2.1's Verify).
- Task 2.2: the `.gitignore` paragraph in `docs/codex-alpha-install.md` describes Task 1.3's behaviour before that code exists. The Task 1.3 implementer builds to that paragraph, and the Task 1.3 reviewer checks the two against each other. The controller accepted placing the `.gitignore` line in its own paragraph instead of the "adapter owns" list, because that list names only manifest-recorded paths.
- Task 2.1 (pre-existing): `deploy-codex-adapter.sh` runs its fixed rmdirs in the order `.codex/agents`, `.codex`, `.codex/.agent-harness`. An unedited `--remove` on a project that had no `.codex/` before install therefore leaves an empty `.codex/`. Forwarded to the final review.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 scripts/verify_summary.py --lane specs/gh-253-codex-full-payload/SUMMARY.md` | 0 | intake | |

### Not auto-verified

- none

### Rollback

- Revert the merge commit of this branch: `git revert -m 1 <merge-sha>`; no data migration is involved.
- Consumers who already installed the new adapter: re-run `bash scripts/install-codex-harness.sh --source <reverted checkout> --directory <project> --yes`. The prune step removes the payload paths the reverted manifest no longer owns; locally edited copies are preserved as conflicts, never deleted.

### Harness-Delta

- backlog — Claude consumers have the same latent gap for `runtime/…` and `rules/…` paths: `deploy-harness.sh` `rewrite_derived_paths` rewrites only `scripts/<consumer subset>`, `harness-manifest.json` and the `render_plan.py` command, so a deployed skill still says `python3 runtime/run_state.py`, `skills/subagent-driven-development/scripts/task_brief.py` and `bash skills/using-git-worktrees/scripts/detect-isolation.sh`, none of which exist at a consumer's root (the payload is under `.claude/`). Observed in a scratch Claude install on 2026-10-08. Out of scope here; file as its own issue.
