---
name: autopilot
description: "Use when starting a hands-off run. Triages one ticket or a milestone, asks the owner every open question once, then launches the ship workflow."
disable-model-invocation: true
argument-hint: "<milestone | #n [#m ...] | free text> [base=<branch>] [--no-ask]"
allowed-tools: Read, Write, Grep, Glob, Agent, Skill, AskUserQuestion, Workflow, Bash(gh issue view *), Bash(gh issue list *), Bash(gh issue comment *), Bash(gh repo view *), Bash(git remote *), Bash(git rev-parse *), Bash(git branch *), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/plan_groups.py *), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/load_profile.py *)
---

# Autopilot

Typing `/harness:autopilot` authorizes the launch in step 8, after the owner says go in step 7. This
skill runs in the main session; `${CLAUDE_PLUGIN_ROOT}/workflows/ship.js` is the autonomous half.

1. **Scope.** Parse `$ARGUMENTS`: a milestone, issue numbers, or free text (one ticket, no number).
   Get `<repo>` (`gh repo view --json nameWithOwner -q .nameWithOwner`), the remote name
   (`git remote -v`) and the checkout dir (`git rev-parse --show-toplevel`). For a milestone run
   `gh issue list --repo <repo> --milestone '<name>' --state open --json number,title,labels` (`'`→`'\''`).
   Read each ticket: `gh issue view <n> --repo <repo> --json title,body,labels -q ...`.
   Base = the `base=` argument, else the current branch. Name it in the summary.
   **Profile:** run `python3 ${CLAUDE_SKILL_DIR}/scripts/load_profile.py --repo-dir <checkout dir>`
   (exit 2: show the error, stop) and follow `references/profile.md`.
2. **Triage.** One call per ticket, all in one message. A `researcher` finds facts (code the
   ticket touches, tests, links between tickets). An `intake`-model agent follows the `harness:intake` skill
   and returns verdict `READY | CONFIRM | GRILL | BLOCKED`, depth `S|M|L`, deps and questions.
   For an important ticket (intake: GRILL class) also ask the `advisor` agent.
3. **Groups.** Drop BLOCKED tickets with the reason shown and flag their dependents. Pipe
   `[{"n":1,"deps":[..]}]` into `python3 ${CLAUDE_SKILL_DIR}/scripts/plan_groups.py`. It returns
   `[{"n":1,"group":1}]`. Exit 2 names a dependency cycle: stop and show it.
4. **Clarify** (skip with `--no-ask`). Collect every ticket's CONFIRM questions. Ask with
   AskUserQuestion, at most 4 per call, in the `harness:grilling` "Question format". Evidence goes in the
   option `preview` (`grilling/references/review-layout.md`). One decision each.
5. **Grill** (skip with `--no-ask`). Run the `harness:grilling` skill, interactive, for each GRILL
   ticket, one ticket at a time.
6. **Record.** Post each ticket's confirmed answers as one comment titled "Confirmed decisions":
   `gh issue comment <n> --repo <repo> --body-file <file>`. Grilling posts its own. With `--no-ask` nobody answers: pass the open questions on with
   `noAsk: true` so the workflow records them as `needs_review` decisions.
7. **Summary, then ONE go/no-go question.** Table: ticket, title, verdict, depth, group, deps,
   confirmed decisions (short). State the base branch, the integration branch `feat/<slug>`,
   single or multi, the model plan from the profile and that nothing is merged. This is
   the owner's last question.
8. **Launch.** Call Workflow with `name: "harness:autopilot-run"` and `args` as a real
   object that includes `pluginDir: "${CLAUDE_PLUGIN_ROOT}"` (see `references/launch-args.md`). Take `testCmd`, `lintCmd` and `fullTestCmd` from
   `CLAUDE.md` → `## Run and test`, then the README, never from memory. If one is missing, ask in step 7. With
   `--no-ask`, record a `needs_review` decision and use `fullTestCmd` only. Tell the owner
   the run ID and that `/workflows` shows progress, then wait for completion. Answer
   "done yet?" from the phase and agent counts. On completion report as
   `references/launch-args.md` says.

## Rules

- Nothing is merged into the base or main. Work happens in worktrees, never in the owner's checkout.
- Skip a stuck or very risky ticket and report it.
- The project's CLAUDE.md wins, except the hard rules (merge, force-push, secrets, weakened tests). A bug ticket needs a failing repro test first (the workflow's stage
  prompts enforce it).

## Auto mode

Not applicable: this is the interactive half; `--no-ask` skips steps 4 and 5.
