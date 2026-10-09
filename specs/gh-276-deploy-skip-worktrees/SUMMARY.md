# gh-276-deploy-skip-worktrees — Summary

Lane: normal
Confidence: medium
Reason: no manifest hard gate in the expected diff (scripts/deploy-harness.sh + a tests/scripts test); 2 flags — existing behavior (derive-time transforms) and cross-platform (CI runs the deploy on ubuntu + macos)
Flags: existing-behavior, cross-platform
Affects: scripts/deploy-harness.sh (rewrite_derived_paths, strip_maintenance_docs)
Input-type: change request
Route: branch fix/gh-276-deploy-skip-worktrees → using-git-worktrees → subagent-driven-development (or direct patch if the plan stays ≤3 steps / ≤2 files)
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

/feature-intake for https://github.com/minhtran3124/agent-harness/issues/276

Issue #276 — "deploy-harness in the main checkout rewrites tracked files in harness worktrees under .claude/worktrees/" (verbatim scope-deciding sections):

> ## Expected
>
> A deploy in one checkout never modifies another worktree's files.
>
> ## Fix direction
>
> - Make the derive-time transforms in `deploy-harness.sh` skip `.claude/worktrees/` (and any nested git worktree).
> - Add a regression test that deploys into a target containing `.claude/worktrees/x/skills/foo.md` and asserts the file is unchanged.
> - Optionally, have SDD dispatch check `git status --short` for unexpected modifications before handing out a task.

### Intake decisions (ambiguity named, default chosen)

- **Optional SDD dispatch check — out of scope (default).** The issue marks it optional; it would
  edit `skills/subagent-driven-development/` (workflow-engine signal → high-risk lane). Defer to a
  follow-up issue unless the user asks for it here.
- **"Any nested git worktree"** — read as: the `rglob('*.md')` walks in both transforms prune
  `.claude/worktrees/` and any subdirectory of `.claude/` that carries its own `.git` entry
  (file or dir), not only the literal `worktrees/` path.
- **Other `$OUT` walks** (`strip_skill_tests`, `prune_orphans`) are scoped to `$OUT/skills` or the
  manifest list and do not reach `.claude/worktrees/`; the plan should confirm, not change, them.

## What changed

`scripts/deploy-harness.sh`'s two derive-time Markdown transforms (`rewrite_derived_paths`,
`strip_maintenance_docs`) now walk `.claude/` through one shared `derived_md()` helper
(`DERIVED_MD_PY`) instead of `rglob('*.md')`. The walk prunes the top-level `.claude/worktrees/`
and any directory with its own `.git` entry (file or dir), except a synced top-level dir
(`skills/`, `rules/`, …) that the consumer keeps under git, since harness entries are merged into
it. It keeps the existing `.harness-incoming` / `.proposed` sidecar skip. New regression suite
`tests/scripts/deploy-worktree-isolation.test.sh` (5 cases). The full suite
(`bash scripts/run-tests.sh`) ran ALL GREEN locally; it is cited here, not as a Verify row,
because it exceeds the 60s Verify-row cap.

### Rationale

Worktree, nested-checkout and nested-repo files are source, not derived, so pruning them at the
walk keeps a deploy in one checkout from writing into another. One shared helper means a future
third transform cannot reintroduce the bare `rglob`. With no nested checkout present, the old and
new scripts produce a byte-identical derived tree (`diff -r` of two fresh deploys from one source).

### Alternatives considered

- Skip only the literal `.claude/worktrees/` path — rejected; the issue also asks to cover any nested git worktree, and the `.git` probe costs one `lexists` per directory.
- Restrict the walk to the synced dirs (`skills/ agents/ rules/ hooks/ scripts/`) — rejected; it would silently stop transforming any other derived `.md`, a behavior change beyond the bug.
- Optional SDD pre-dispatch `git status --short` check — deferred (see Intake decisions); it is a workflow-engine change needing its own high-risk intake.

### Deviations

- Rule 1 — correctness-review advisory (score 50) at `scripts/deploy-harness.sh:82`: the first cut's `.git` prune also skipped a synced dir the consumer keeps under git (e.g. `.claude/skills/.git`), leaving harness docs inside it untransformed — a regression vs the old `rglob`. Fixed by exempting synced top-level dirs from the `.git` prune; test case 5 added.

### Advisory Findings

- `scripts/deploy-harness.sh:77` (score 0, pre-existing) — the walk still transforms consumer-owned Markdown under `.claude/` that the deploy did not produce: `.claude/.harness-backup-<TS>/` (so a `backup`-policy copy is no longer verbatim), `.claude/CLAUDE.md`, `.claude/commands/*.md`. Same class as #276 but present at base via `rglob`; narrowing the walk to deployed entries would stop transforming consumer-added skills too, which is removing behavior (Rule 4). Recommend a follow-up issue. The `derived_md` comment was corrected to stop claiming it yields only derived files.
- `scripts/deploy-harness.sh:82` (score 50) — fixed; see Deviations.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| regression: worktree, nested checkout and nested repo docs byte-identical after deploy; derived docs still rewritten, including inside a git-managed `.claude/skills/` | `bash tests/scripts/deploy-worktree-isolation.test.sh` | 0 | 5 passed; before the fix cases 1–3 FAILED | |
| deploy prune contract unchanged | `bash tests/scripts/deploy-prune.test.sh` | 0 | 8 passed | |
| deploy profile contract unchanged | `bash tests/scripts/deploy-profile.test.sh` | 0 | 23 passed | |

### Not auto-verified

- Old vs new derived tree is byte-identical without nested checkouts — reached truth once, by hand (`diff -r` of two scratch deploys); not a Verify row because it needs the pre-fix script extracted from `HEAD`.
- macOS behavior — not run locally (Linux only); the helper is stdlib `os.walk` / `os.path.lexists`, and CI runs the suite on macos.
- Repair of worktrees already damaged by an earlier deploy — out of scope; the fix prevents new damage only.

### Rollback

- `git revert <sha>`

### Harness-Delta

- backlog: restrict the derive-time transforms to deployed entries so consumer-owned `.claude/` Markdown and `.harness-backup-*` copies are never rewritten (advisory at `:77`).
- backlog: optional SDD pre-dispatch `git status --short` check for unexpected modifications (issue #276, third fix-direction bullet) — needs its own high-risk intake.
