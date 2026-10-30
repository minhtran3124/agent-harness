# Autopilot dry run (written, not recorded)

Nobody ran these sessions end to end. The triage verdicts and owner answers are invented to show the
flow. The `plan_groups.py` output is real: it was produced by running the script on the sample JSON.
Repo `acme/shop`, remote `origin`, checkout `/work/shop`, current branch `main`.

## A. One ticket: `/autopilot #346`

Triage returns `Verdict: CONFIRM`, `Depth: S`, `Deps: none`, one question ("Keep the old flag
name? Recommended: yes"). The owner answers yes in the single clarify round. No grill. The skill
posts a "Confirmed decisions" comment on #346.

```text
echo '[{"n":346,"deps":[]}]' | python3 skills/autopilot/scripts/plan_groups.py
[{"n": 346, "group": 1}]
```

Base `main` (the current branch; no `base=` given). Single run: no integration branch. No merge.

| Ticket | Title | Verdict | Depth | Group | Deps | Confirmed decisions |
| --- | --- | --- | --- | --- | --- | --- |
| #346 | Rename the export flag | CONFIRM | S | 1 | none | Keep the old flag name as an alias |

One question: "Launch the run?"

```js
Workflow({
  name: "harness:autopilot-run",
  args: { repo: "acme/shop", repoDir: "/work/shop", remote: "origin", base: "main", slug: "346-rename-flag",
    tickets: [{ n: 346, title: "Rename the export flag", depth: "S", group: 1, deps: [],
                confirmed: "Keep the old flag name as an alias" }],
    testCmd: "pytest {files}", lintCmd: "ruff check .", fullTestCmd: "bash scripts/run-tests.sh",
    advisorModel: "opus", noAsk: false, local: false } })
```

## B. Milestone with a dependency: `/autopilot "Export v2" base=release`

Tickets: #21 (READY, S), #22 (GRILL, M, depends on #21), #23 (READY, S). All three triage agents run in
one message. #22 touches a public contract, so the `advisor` is also asked. Clarify has no questions.
Grill runs `grilling` on #22 only; it posts its own comment.

```text
echo '[{"n":21,"deps":[]},{"n":22,"deps":[21]},{"n":23,"deps":[]}]' | python3 skills/autopilot/scripts/plan_groups.py
[{"n": 21, "group": 1}, {"n": 22, "group": 2}, {"n": 23, "group": 1}]
```

Base `release` (from `base=`, not the current branch `main`). Integration branch `feat/export-v2`. Multi run.

| Ticket | Title | Verdict | Depth | Group | Deps | Confirmed decisions |
| --- | --- | --- | --- | --- | --- | --- |
| #21 | Add the export schema | READY | S | 1 | none | none |
| #22 | Versioned export endpoint | GRILL | M | 2 | #21 | Endpoint is `/v2/export`; v1 stays for 90 days |
| #23 | Export CSV headers | READY | S | 1 | none | none |

Models: Sonnet stages, Haiku tests, advisor `opus`. Nothing is merged. Then one question: "Launch the run?"

```js
Workflow({
  name: "harness:autopilot-run",
  args: { repo: "acme/shop", repoDir: "/work/shop", remote: "origin", base: "release", slug: "export-v2",
    tickets: [
      { n: 21, title: "Add the export schema", depth: "S", group: 1, deps: [], confirmed: "" },
      { n: 22, title: "Versioned export endpoint", depth: "M", group: 2, deps: [21],
        confirmed: "Endpoint is /v2/export; v1 stays for 90 days" },
      { n: 23, title: "Export CSV headers", depth: "S", group: 1, deps: [], confirmed: "" } ],
    testCmd: "pytest {files}", lintCmd: "ruff check .", fullTestCmd: "bash scripts/run-tests.sh",
    advisorModel: "opus", noAsk: false, local: false } })
```
