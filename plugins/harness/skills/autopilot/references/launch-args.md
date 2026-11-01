# Workflow args for the ship workflow

Pass `args` as a JSON object (not a string). Launch by name, `Workflow({name: "harness:autopilot-run", args})`:
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

Then save the run journal, so the owner can see time and tokens per stage. Write `out.journal` (a JSON array) to
`<parent of repoDir>/.ship-<name of repoDir>/journals/journal-<run id>.json` with the Write tool; the run id is the `wf_...`
id the Workflow result names. Outside the repo. Run
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_report.py <run id> --journal <that file>` and add its top five rows
to the report. The owner may be asked to allow that command once; the run is already finished. If the result
has no `out.journal`, or the report fails, say so in one line and go on.

## Launch notes

- Name not found: report it and stop. Do not copy the script to another path. The Workflow tool refuses
  a `scriptPath` the session cannot read, so the fallback is inline `script` or `/add-dir <plugin dir>`.
- Stale name after a plugin update: a session that started before the update can run an old cached
  `harness:autopilot-run`. Restart Claude Code to load the new one (the main fix). The plugin CLI help names
  `/reload-plugins`, but that is not confirmed here. If the repo's `plugins/harness/workflows/ship.js`
  is inside the working directory or an added directory, `Workflow({scriptPath: "<abs>/plugins/harness/workflows/ship.js", args})`
  runs the current file; the Workflow tool refuses a path the session cannot read.
- Merge policy: the workflow merges only ticket PRs into `feat/<slug>`, and only tickets that pass the
  per-ticket gate (CI, review, intent review, no open `needs_review` decision). Everything into `base`
  or `main`, the final PR and a single-ticket PR included, is a human merge (`Merge: human` in the PR body).
  The merge guard hook blocks any other merge and fails closed. Local mode has no PRs: no guard, no gate.
- Merge permission: the owner must allow `gh pr merge` into `feat/<slug>*`. Without it the merge stage
  fails with a reason that names this permission. Do not change permission settings and do not work
  around a denial; tell the owner. A ticket whose gate failed is not merged; its PR stays open with a
  `needs_review` decision that holds the exact command.
- Resume: the merge stage counts a PR already MERGED into the integration branch as merged.
