# Workflow args for the ship workflow

Pass `args` as a JSON object (not a string). `scriptPath` is absolute: a named workflow was not
found mid-session (`docs/adr/0001-workflow-capabilities.md`, decision 4).

`scriptPath` and `pluginDir` come from the plugin's own directory. SKILL.md step 8 gives both
values, already resolved. `repoDir` is the owner's checkout, not the plugin.

```text
{ repo: "owner/name", repoDir: "/abs/path", pluginDir: "<plugin directory>", remote: "origin", base: "<base>",
  slug: "<milestone-or-ticket slug>",
  tickets: [ { n: 346, title: "...", depth: "S|M|L", group: 1, deps: [345],
               confirmed: "owner-confirmed decisions text, may be empty" } ],
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

## Launch notes

- Readable script: the Workflow tool refuses a `scriptPath` the session cannot read ("scriptPath must be
  a script path this tool returned, or a file you can already read"). The script must be inside the
  working directory or an added directory, or be passed inline through `script`.
- Merge permission: the owner must allow `gh pr merge` into `feat/<slug>*`. Without it the merge stage
  fails with a reason that names this permission. Do not change permission settings and do not work
  around a denial; tell the owner.
- Resume: the merge stage counts a PR already MERGED into the integration branch as merged.
