# Parallel worktrees

One worker = one worktree = one branch. Never point two workers at the same checkout.

## The 3-step arm recipe

`.claude/` is gitignored (`.gitignore`), so **every fresh worktree has no skill
registry, no hooks, no auto-loaded rules** — the tracked source dirs are there, but the
wiring is not. Spawning is therefore three steps, and step 2 is load-bearing:

```bash
# 1. Create (herdr-native, or /using-git-worktrees for the skill-managed path).
#    From an orchestrator Bash tool, pass --cwd (or --workspace) — the CLI has no
#    pane context of its own to infer the repo from.
herdr worktree create --cwd "$PWD" --branch <type>/<slug> --base <base-ref> --no-focus --json
WT=<path from the create/list JSON — see "Where herdr puts worktrees" below>

# 2. Arm — deploy the harness into the worktree, using the worktree's OWN script
bash "$WT/scripts/deploy-harness.sh" --target "$WT" --yes

# 3. Gate — hard-fail rather than spawn an ungoverned worker
test -f "$WT/.claude/settings.json" || { echo "worktree not armed"; exit 1; }
```

**Step 2 has two traps.**

- **Run the worktree's copy, not yours.** `deploy-harness.sh` resolves its sources from
  its own path (`ROOT="$(dirname "$0")/.."`), never from git. `bash
  scripts/deploy-harness.sh --target "$WT"` from your checkout therefore arms the worker
  with **your** branch's `skills/ agents/ hooks/ rules/ templates/ runtime/` — invisible
  cross-branch contamination when the worker's branch touches any of them.
- **`--yes` when nobody can answer.** On a *re-arm*, a protected file that differs
  (`rules/behavior.md`, `rules/architecture.md`, `rules/guidelines.md`,
  `agents/PROJECT.md`) makes the script prompt on `/dev/tty` — which hangs a Bash-tool
  call. `--yes` picks "keep local, save incoming as `<file>.harness-incoming`". A
  first-time arm of a fresh worktree has no `.claude/` and so never prompts.

Skipping step 2 entirely does not fail loudly — it produces a worker where `Skill(...)`
cannot resolve project skills, no commit gates fire, and rules never load. Worse than an
error; that is why step 3 is a hard gate rather than a warning.

## Where herdr puts worktrees

`herdr worktree create` does **not** use the repo's `.worktrees/`. It places the checkout
under `~/.herdr/worktrees/<repo-name>/<branch-with-slashes-flattened>` and opens it as a
workspace. Resolve the real path instead of assuming it:

```bash
herdr worktree list --cwd "$PWD" --json     # .result.worktrees[] → {branch, path, …}
```

`open_workspace_id` appears **only while that worktree is open as a workspace** — a
linked worktree nobody has focused reports no id at all. Do not build cleanup around it
unconditionally (see Cleanup).

Two roots for worktrees is a known cost of mixing this with `/using-git-worktrees`
(which prefers a project-local `.worktrees/`): `finishing-a-development-branch` cleans up
only the root it knows. Pick one per feature and stay in it.

## Parallelism

- MVP guideline: **≤3 workers at once.** Each worker is a full session (startup cost in
  `model-routing-and-context.md`) plus a human attention surface; panes beyond ~3 stop
  being "visible" in any useful sense.
- Spawn all workers of a wave, then wait on each (`herdr agent wait`) — don't interleave
  spawn/wait one at a time unless tasks depend on each other.
- Independent tasks only. Same-file tasks belong in one worker, sequentially.

## Tests inside a worktree

Bare `python3` in a fresh worktree may lack pytest. Use the shared venv that
`scripts/run-tests.sh` itself prefers: `${TMPDIR:-/tmp}/harness-tests-venv/bin/python -m
pytest <target>`.

## Cleanup

After the branch is pushed (or the work abandoned deliberately):

```bash
# --workspace takes a workspace id, not a path, and the worktree must be open as one.
herdr worktree remove --workspace <open_workspace_id>
# Not open as a workspace (the common case after closing the pane) → plain git:
git worktree remove <path>
```

Never remove a worktree with uncommitted work without surfacing it to the human first.
