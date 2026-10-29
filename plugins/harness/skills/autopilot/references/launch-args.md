# Workflow args for the ship workflow

Pass `args` as a JSON object (not a string). Launch by name, `Workflow({name: "harness:ship", args})`:
the plugin registers `./workflows/ship.js` in `plugin.json`, and the name works from any working
directory (verified for #396; it supersedes `docs/adr/0001-workflow-capabilities.md`, decision 4).

`pluginDir` comes from the plugin's own directory. SKILL.md step 8 gives it, already resolved. `repoDir` is the owner's checkout, not the plugin.

```text
{ repo: "owner/name", repoDir: "/abs/path", pluginDir: "<plugin directory>", remote: "origin", base: "<base>",
  slug: "<milestone-or-ticket slug>",
  tickets: [ { n: 346, title: "...", depth: "S|M|L", group: 1, deps: [345],
               confirmed: "owner-confirmed decisions text incl. the Verify: row, may be empty" } ],
  testCmd: "<related-tests command or template>", lintCmd: "<lint command>",
  fullTestCmd: "bash scripts/run-tests.sh", advisorModel: "opus", noAsk: false, local: false }
```

- `deps` holds only tickets inside the batch. `group` comes from the plan_groups.py helper.
- One ticket means single mode: no integration branch (ADR 0001, decision 5).
- `noAsk: true` when `--no-ask` was given. `local` stays false unless the owner asks for a run
  without GitHub writes.

## Completion report

Short, in the owner's language: final PR link, per-ticket status, what was skipped and why, review
rounds and findings, full-suite counts, the ADRs in `docs/adr/` and the artifact link.

Name the script that ran: take it from the `Script file:` line of the Workflow result. If it is not
the repo's `plugins/harness/workflows/ship.js`, say so. If the result has no such line, write
`script path not shown`. Do not read the session directory to find it.

## Launch notes

- Name not found: report it and stop. Do not copy the script to another path. The Workflow tool refuses
  a `scriptPath` the session cannot read, so the fallback is inline `script` or `/add-dir <plugin dir>`.
- Stale name after a plugin update: a session that started before the update can run an old cached
  `harness:ship`. Restart Claude Code to load the new one (the main fix). The plugin CLI help names
  `/reload-plugins`, but that is not confirmed here. If the repo's `plugins/harness/workflows/ship.js`
  is inside the working directory or an added directory, `Workflow({scriptPath: "<abs>/plugins/harness/workflows/ship.js", args})`
  runs the current file; the Workflow tool refuses a path the session cannot read.
- Merge permission: the owner must allow `gh pr merge` into `feat/<slug>*`. Without it the merge stage
  fails with a reason that names this permission. Do not change permission settings and do not work
  around a denial; tell the owner.
- Resume: the merge stage counts a PR already MERGED into the integration branch as merged.
