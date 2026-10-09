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
`tests/scripts/deploy-worktree-isolation.test.sh` (10 cases). `strip_skill_tests` is now a Python
`os.walk` with the same `lexists(.git)` prune that deletes files one by one and then only emptied
dirs (never a whole tree), so a consumer's nested checkout anywhere below `skills/` — including
inside a `tests/` dir, or one whose `.git` is a dangling symlink — is left intact. It stays
best-effort like the old `find … || true`: an undeletable file warns instead of aborting. The full suite
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

- Rule 1 — intent-review gap against "A deploy in one checkout never modifies another worktree's files.": `strip_skill_tests` (`rm -rf skills/*/tests`, `find … -delete`) was not nested-checkout aware and would delete a consumer nested checkout's tests. Fixed with a `.git` skip; test case 6 added.
- Rule 1 — correctness re-review of that fix (`1b819bf`): its bash/find version (a) `rm -rf`'d a `skills/<x>/tests` that was itself a nested checkout, (b) used `[ -e ]`, so a dangling `.git` symlink did not count (disagreeing with `derived_md`'s `lexists`), (c) narrowed `test_*.py` removal to regular files, dropping symlinks. Rewrote `strip_skill_tests` as an `os.walk` with the shared `lexists` probe; test cases 7–8 added.
- Rule 1 — correctness re-review of that rewrite (`63a7ff5`, fix round 3 = cap): (a) an uncaught `PermissionError` aborted the deploy mid-pipeline where the old `find … || true` was best-effort, (b) `rmtree` of `skills/<x>/tests` still deleted a nested checkout deeper inside it, (c) dot-named entries under `skills/` were treated as skills, unlike the old glob. Now file-by-file deletes with warn-on-error, empty-dir-only `rmdir`, root dot-entries skipped; test cases 9–10 added. Round cap reached — any further finding here escalates rather than re-looping.

### Intent Findings

- drift (advisory) — "skip … (and any nested git worktree)": a synced top-level dir (`.claude/skills/`, `rules/`, …) the consumer keeps under git is deliberately still walked, because `copy_dir` merges harness entries into it and skipping it would leave those harness docs untransformed (test case 5). Nested checkouts *inside* it are still skipped.
- gap (deferred, optional) — "Optionally, have SDD dispatch check `git status --short` …": not implemented; intake scoped it out (workflow-engine change, high-risk lane). Tracked under Harness-Delta.

### Advisory Findings

- `scripts/deploy-harness.sh:77` (score 0, pre-existing) — the walk still transforms consumer-owned Markdown under `.claude/` that the deploy did not produce: `.claude/.harness-backup-<TS>/` (so a `backup`-policy copy is no longer verbatim), `.claude/CLAUDE.md`, `.claude/commands/*.md`. Same class as #276 but present at base via `rglob`; narrowing the walk to deployed entries would stop transforming consumer-added skills too, which is removing behavior (Rule 4). Recommend a follow-up issue. The `derived_md` comment was corrected to stop claiming it yields only derived files.
- `scripts/deploy-harness.sh:82` (score 50) — fixed; see Deviations.
- `scripts/deploy-harness.sh:89` (re-review of the `:82` fix, P3, Rule 4) — the synced-dir exemption covers the whole git-managed synced dir, so a consumer-authored doc tracked there (e.g. `.claude/rules/mine/a.md`) is still transformed. Matches base (`rglob`) behavior; the precise fix (walk only `DEPLOYED_LIST` entries inside it) is the same Rule-4 narrowing as the `:77` item — folded into that backlog item.
- `scripts/deploy-harness.sh` `strip_skill_tests` (re-review, P2, Rule 4, pre-existing) — a consumer-authored skill with no `.git` of its own still loses its `tests/` and `test_*.py` on every deploy (`.claude/` is gitignored in consumers, so unrecoverable). Fix is to strip only `DEPLOYED_LIST` entries — the same Rule-4 narrowing as `:77`; folded into that backlog item.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| regression: worktree, nested checkout and nested repo docs byte-identical after deploy; derived docs still rewritten, including inside a git-managed `.claude/skills/`; nested skill checkouts keep their tests; symlinked test files still stripped; undeletable file does not abort | `bash tests/scripts/deploy-worktree-isolation.test.sh` | 0 | 10 passed; before the fix cases 1–3 FAILED | |
| harness skill tests still stripped from the derived tree | `bash tests/scripts/consumer-subset.test.sh` | 0 | 17 passed | |
| deploy prune contract unchanged | `bash tests/scripts/deploy-prune.test.sh` | 0 | 8 passed | |
| deploy profile contract unchanged | `bash tests/scripts/deploy-profile.test.sh` | 0 | 23 passed | |

### Not auto-verified

- Old vs new derived tree is byte-identical without nested checkouts — reached truth once, by hand (`diff -r` of two scratch deploys); not a Verify row because it needs the pre-fix script extracted from `HEAD`.
- Test case 10 (undeletable file) is skipped when the suite runs as root, since permission bits are not enforced there.
- Test cases 5–10 failing on the code they guard against — reached traceability only (reasoned from the code and the reviewers' reports; a reviewer reproduced case 5 in scratch); not re-run against the earlier scripts.
- macOS behavior — not run locally (Linux only); the helper is stdlib `os.walk` / `os.path.lexists`, and CI runs the suite on macos.
- Repair of worktrees already damaged by an earlier deploy — out of scope; the fix prevents new damage only.

### Rollback

- `git revert <sha>`

### Harness-Delta

- backlog: restrict the derive-time transforms and `strip_skill_tests` to deployed entries (`DEPLOYED_LIST`) so consumer-owned `.claude/` Markdown, `.harness-backup-*` copies, and consumer skills' tests are never rewritten or deleted (advisories above; Rule 4 — needs its own intake).
- backlog: optional SDD pre-dispatch `git status --short` check for unexpected modifications (issue #276, third fix-direction bullet) — needs its own high-risk intake.
