# Worker toolbox

Part of `harness:pd-work`.

Reach for a tool when the situation matches. Skip one when it adds nothing, and note why in the
report when a reader would expect it.

| Situation | Tool |
|---|---|
| The ticket is vague, or two readings differ in what you would build | send `question` to the orchestrator with your recommendation; go on with the parts that do not depend on the answer |
| Wrong behavior, cause not yet known | Read `${CLAUDE_PLUGIN_ROOT}/skills/pd-diagnosing-bugs/SKILL.md` and follow it (the Skill tool cannot load that skill): a failing repro test comes first |
| You do not know how this part of the code or a library works | `harness:pd-xia2`, or a `harness:researcher` agent for a narrow lookup |
| More than one sound approach, or depth L | `harness:pd-brainstorming`; write the design note; ask the `harness:advisor` agent to review it before code |
| Work with more than two or three moving parts | `harness:pd-writing-plans`, then `harness:pd-implement` (one implementer per step, independent steps in parallel) |
| Your branch already holds a commit `Add acceptance tests for #<n>` | those tests are your target and you never edit their directory. If one is wrong or cannot pass for a reason outside your code, send `question` with the evidence; the orchestrator can have it repaired |
| The ticket is risky (protocol, last paragraph) | the `harness:security-reviewer` agent on your diff before you ask for review; fix every critical and high finding. The reviewer runs its own security review; yours only saves a round |
| The same check failed twice after a fix | one question to the `harness:advisor` agent; if still stuck, `escalate` with the attempts, their output and the advisor's answer |
| You chose something a reader might not expect | `harness:pd-decision-record` |
| A test run of more than a few seconds | the `harness:test-runner` agent, so your context stays small |

You may start agents of your own and run independent work in parallel. Choose each agent's model
and effort from the task.

## After you reported or escalated

Stay available. A `findings` message from the orchestrator reopens the ticket: fix, get a new
receipt for the new head, and report again; the 3-round limit starts again for each such cycle. A
second `assign` for the same ticket replaces your brief: it may name an approach and a branch to
fetch from another checkout, which you may then do. After `escalate`, wait for the orchestrator's
`answer` or `assign`.
