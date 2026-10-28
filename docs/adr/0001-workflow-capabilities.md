---
ticket: 340
stage: research
status: accepted
needs_review: false
confidence: high
decided_by: claude (main session)
date: 2026-10-28
---

# 0001. What the Workflow tool can do for Harness v5

## Context

The Harness v5 design (epic #338) runs each ticket through stage agents inside one Workflow script, `workflows/ship.js`, for 1..N tickets. Five assumptions in that design were unverified. Issue #340 asked to probe them before building #341 and #347.

All probes ran on 2026-10-28 in Claude Code against a throwaway git repo in the session scratchpad. Workflow agents used Sonnet 5.5 at low effort, except the isolation probe (Haiku 5.5).

## Results

| ID | Question | Result | Evidence |
| --- | --- | --- | --- |
| K1 | Can a Workflow agent run the built-in `/code-review` skill? | **Yes** | The agent called the Skill tool with `code-review` and `low <path>`. The skill ran in a forked context and reported the planted off-by-one (`range(1, len(xs))`) in the probe file. Run `wf_2a7dc9f6-15c`. |
| K2 | Does one script handle 1 ticket and N tickets with dependencies? | **Yes** | 1 ticket: phases run `tickets:1`, no integration branch, final branch `t1` (run `wf_62f20aed-82b`). 3 tickets (2 and 3 independent, 4 depends on 2): `setup-integration, tickets:2,3, merge-g1, tickets:4, merge-g2`; ticket 4 was cut from the merged integration branch, so it contains ticket 2 (run `wf_3e3afab2-e49`). |
| K3 | Can a Workflow agent spawn an advisor agent itself? | **No** | The agent's tool list has no Agent or Task tool (it has Skill, Bash, Read, Write, Edit, ToolSearch and MCP tools). |
| K4 | Does a Workflow agent read a `SKILL.md` and follow its auto mode? | **Yes** | Given only the skill path and "auto mode", the agent wrote the exact file content the skill asked for, returned the one decision in `decisions[]`, and asked no one. |
| K5 | Is a named workflow in `.claude/workflows/` callable by name with `args`? | **No, in this session** | `Workflow({name: "probe-ship"})` returned "not found. Available: deep-research" twice after the file was created mid-session. The same file ran fine through `Workflow({scriptPath, args})`, and `args` arrived intact. Unknown whether the name registry loads only at session start. |

Extra finding (not in the issue): an agent with `isolation: 'worktree'` starts from the **main checkout's HEAD**, not from the remote base branch. In the probe the worktree was at `d031ec2` (the local checkout) while the v5 base on the remote was `c5dd856`. The worktree was removed automatically because it was unchanged.

## Decision

1. **Review runs inside the workflow (K1).** A review stage agent calls the Skill tool with `code-review <low|medium|high> <PR>`. The fallback (main session reviews between two workflow runs) is not needed.
2. **The script calls the advisor (K3).** Stage schemas carry `needs_advisor` and `advisor_question`. When set, `ship.js` runs `agent(advisorPrompt, { model: ADVISOR_MODEL, effort: 'high' })` and reruns the stage once with the advice. `ADVISOR_MODEL` defaults to `'opus'`; `'fable'` for special cases. Agents never try to spawn agents.
3. **Stage agents read skills by path (K4).** Each prompt names `skills/<stage>/SKILL.md` and "auto mode". No skill text is pasted into prompts.
4. **`/autopilot` launches by `scriptPath` (K5).** It calls `Workflow({scriptPath: "<repo>/workflows/ship.js", args})`. A name lookup is not relied on.
5. **One script, branch on `single` (K2).** `single = tickets.length === 1` skips the integration branch and merge stages.
6. **Every isolated agent checks out its base explicitly.** The first step of each worktree agent is `git fetch <remote>` and `git checkout -b <branch> <remote>/<base>`. Never trust the worktree's starting commit.

## Consequences

- #341: the advisor is a plain read-only agent definition; no "subagent may call the advisor" rule.
- #346: `/autopilot` passes the absolute `scriptPath` and the args object.
- #347: `ship.js` implements decisions 1, 2, 5 and 6.
- If a later Claude Code version gives workflow agents the Agent tool, decision 2 can be simplified. The script-side call keeps working either way.

## How to reverse

Re-run the probes (the probe script is reproduced below) on a newer Claude Code version and supersede this ADR with a new one.

```js
// probe-ship.js (trimmed): one script, 1..N tickets
const { repo, wt, tickets } = args
const single = tickets.length === 1
const base = single ? 'main' : 'int/probe'
if (!single) await agent(`create branch int/probe from main in ${repo}`, …)
const indep = tickets.filter(t => !(t.deps || []).length)
const dep = tickets.filter(t => (t.deps || []).length)
const r1 = await parallel(indep.map(t => () => ticketAgent(t)))   // worktree, commit, keep branch
if (!single) {
  await mergeAgent(r1.map(r => r.branch))
  if (dep.length) await mergeAgent((await parallel(dep.map(t => () => ticketAgent(t)))).map(r => r.branch))
}
```
