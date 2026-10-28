# Workflow args for `workflows/ship.js`

Pass `args` as a JSON object (not a string). `scriptPath` is absolute: a named workflow was not
found mid-session (`docs/adr/0001-workflow-capabilities.md`, decision 4).

Which file: `<repoDir>/workflows/ship.js` in the harness source repo, and
`<repoDir>/.claude/workflows/ship.js` in a repo that installed the harness (the deploy copies
`workflows/` into `.claude/`). Check with `ls`; use the one that exists. If neither exists, stop
and tell the owner the harness is not installed.

```text
{ repo: "owner/name", repoDir: "/abs/path", remote: "origin", base: "<base>",
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
