# Parallel worktrees

One worker = one worktree = one branch. Never point two workers at the same checkout.

## The 3-step arm recipe

`.claude/` is gitignored (`.gitignore`), so **every fresh worktree has no skill
registry, no hooks, no auto-loaded rules** — the tracked source dirs are there, but the
wiring is not. Spawning is therefore three steps, and step 2 is load-bearing:

```bash
# 1. Create (herdr-native, or /using-git-worktrees for the skill-managed path)
herdr worktree create --branch <type>/<slug> --base <base-ref>

# 2. Arm — deploy the harness into the worktree
bash scripts/deploy-harness.sh --target <worktree-path>

# 3. Gate — hard-fail rather than spawn an ungoverned worker
test -f <worktree-path>/.claude/settings.json || { echo "worktree not armed"; exit 1; }
```

Skipping step 2 does not fail loudly — it produces a worker where `Skill(...)` cannot
resolve project skills, no commit gates fire, and rules never load (confirmed failure
mode; see memory/PR #63 note). Worse than an error.

## Parallelism

- MVP guideline: **≤3 workers at once.** Each worker is a full session (startup cost in
  `model-routing-and-context.md`) plus a human attention surface; panes beyond ~3 stop
  being "visible" in any useful sense.
- Spawn all workers of a wave, then wait on each (`herdr agent wait`) — don't interleave
  spawn/wait one at a time unless tasks depend on each other.
- Independent tasks only. Same-file tasks belong in one worker, sequentially.

## Tests inside a worktree

Bare `python3` in a fresh worktree may lack pytest. Use the shared venv:
`${TMPDIR:-/tmp}/harness-tests-venv/bin/python -m pytest <target>`.

## Cleanup

After the branch is pushed (or the work abandoned deliberately):

```bash
herdr worktree remove --workspace <id>        # or: git worktree remove <path>
```

Never remove a worktree with uncommitted work without surfacing it to the human first.
