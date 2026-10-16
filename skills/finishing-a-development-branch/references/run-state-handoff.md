# Run-state handoff

Why the finish flow stages `RUN.json` and `events.jsonl`, and why it makes one more commit after
the PR opens.

## Step 3: the spec record

`RUN.json` and `events.jsonl` are tracked artifacts. `.gitignore` excludes only the `.lock`. A
fresh `RUN.json` stays untracked unless named, and the commit gate (`check_run_state` in
`hooks/commit-gate.sh`) blocks that.

## Push and PR: the `ready_to_merge` commit

The post-merge `shipped` transition depends on this hop. `shipped` is legal only from
`ready_to_merge`, so a run left at `verifying` never terminalizes. The transition rewrites
`RUN.json` and appends to `events.jsonl` **after** the last commit. The open PR gets the new
commit. Without this commit, git keeps the run at its last committed pre-`ready_to_merge` state
and it never terminalizes.
