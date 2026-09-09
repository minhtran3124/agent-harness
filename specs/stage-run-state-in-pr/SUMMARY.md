# stage-run-state-in-pr — Summary

Lane: high-risk
Confidence: high
Reason: hard gate `high-blast` (mode=block) — the diff touches `hooks/commit-quality-gate.sh`; no other gate fires
Flags: high-blast, workflow-engine
Affects: commit gate (new Check 1.7) + finishing-a-development-branch staging steps
Input-type: harness improvement
Route: high-risk — direct execution on this branch (no design fork: one mechanism, two tiers)
Escalate: no — the human authorised "làm fix 1+2" after the diagnosis was presented

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`.

### Intent

> hien tai khi agent merge 1 PR nao do thi nhung file nay ko dc commit va di theo PR luon
> specs/close-product-loop-s2-guide-and-map/{RUN.json,SUMMARY.md,events.jsonl}

> ok làm fix 1+2 đi

Fix 1 = `finishing-a-development-branch` stages the spec record by name (including `RUN.json`
and `events.jsonl`) and commits the post-PR `ready_to_merge` transition. Fix 2 = the commit gate
blocks an untracked `RUN.json`/`events.jsonl` beside a staged spec file.

## What changed

- `hooks/commit-quality-gate.sh` — new Check 1.7. For each `specs/<slug>/` touched by the staged
  diff: an on-disk `RUN.json`/`events.jsonl` that is untracked and not staged **blocks** (exit 2);
  tracked but with unstaged changes **warns**. `REQUIRE_RUN_STATE_STAGED=0` downgrades the block.
  Commits that leave the slug untouched are unaffected.
- `skills/finishing-a-development-branch/SKILL.md` — step 3 names the four spec paths in a
  `git add`; the post-PR `ready_to_merge` transition is followed by a commit + second push so the
  event lands in the PR instead of only on one machine.
- `tests/hooks/commit-quality-gate.test.sh` — six cases for Check 1.7.
- `CLAUDE.md` hook table row updated (doc-truth lint).

### Rationale

Ground truth in the consumer repo `travel-pi`: the quoted slug had actually shipped its three
files in PR #172, but two other merged slugs (`side-panel-multi-category-tabs` PR #164,
`agent-system-copy-i18n` PR #145) still had `RUN.json` + `events.jsonl` untracked on disk. Cause:
`feature-intake` creates `RUN.json` best-effort and no skill ever named it in a `git add`;
the finishing skill said "commit the tracked `specs/` update", which by its own wording excludes
a fresh untracked file. `.gitignore` carried a comment that the pair "stay tracked" with nothing
enforcing it. Separately, the `ready_to_merge` transition ran after push, so its event was never
committed and `main` kept `RUN.json` at `ready_to_merge` even after the PLAN said `shipped`.

### Alternatives considered

- **Warn-only for untracked files** — rejected: a warning at commit time in an autonomous run is
  read by nobody; the untracked file is exactly the case that never self-corrects.
- **Block on unstaged modifications too** — rejected: `events.jsonl` is appended at every wave
  boundary, and blocking every mid-wave PLAN commit on it adds friction without protecting the PR
  (the file is already tracked, so the final commit picks it up).
- **Move the `ready_to_merge` transition before the final commit** — rejected: its event is
  `pr.opened`; recording it before the PR exists would make the run log lie.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Gate contract suite incl. Check 1.7 | `bash tests/hooks/commit-quality-gate.test.sh` | 0 | 40 passed (6 new) |
| Hook syntax | `bash -n hooks/commit-quality-gate.sh` | 0 | |
| Doc-truth lint (CLAUDE.md hook row) | `bash scripts/lint-doc-truth.sh` | 0 | |
| Skill bash lint | `bash scripts/lint-skill-bash.sh` | 0 | finishing skill gained a `git add` block |

Full suite, cited not tabled: `bash scripts/run-tests.sh` printed `ALL GREEN` (582 pytest cases).

### Not auto-verified

- **The skill-text change is traceability tier only.** Nothing re-runs a finishing flow to show an
  agent now stages `RUN.json`; the tests prove the gate, not the prose. If an agent ignores step 3,
  Check 1.7 is what catches it — and only for commits that touch the slug.
- **Consumer behaviour is inferred, not observed.** The gate was run under `tests/lib.sh` and in
  this repo; it was not re-run inside `travel-pi` after a redeploy. Same code path
  (`.claude/hooks/commit-quality-gate.sh`), but unobserved.
- **`git diff --quiet` on the unstaged-modification tier does not detect a deleted tracked file** —
  a deleted `RUN.json` is reported as unstaged, which is the right warning, but was not tested.

### Rollback

- `git revert <sha>` — in-repo shell + prose only. Session-scoped: `REQUIRE_RUN_STATE_STAGED=0`.

### Harness-Delta

- **backlog (-> compound):** a `.gitignore` comment ("stay tracked") is not a contract. Anything
  the workflow depends on being committed needs a gate or a named `git add` in a skill, or both.
