---
name: context-propagation-audit
description: Change-triggered consumer audit for workflow-as-code changes. When a diff touches the workflow-engine inventory (skills/*/SKILL.md, skill dispatch prompts, agents/*.md, rules/*.md), enumerate every consumer and execution context (main session / implementer subagent / reviewer / scorer / new session) and prove how each receives the authoritative instruction — delivery that is `assumed` or `unconfirmed` on a load-bearing instruction FAILS the audit, and main-session evidence never counts as proof for an isolated child context. Prefer explicit Reads and registry-linted summaries over silent inline policy copies. Change-triggered, not always-on; not a runtime bug hunt (use /correctness-review) and not an intent check (use /intent-review). Invocable standalone as /context-propagation-audit <diff-range>.
---

# Context-Propagation Audit

Run **one** consumer audit over a workflow-as-code diff: for every source-of-truth the diff
changes, prove that the *authoritative instruction actually reaches every isolated execution
context that relies on it*. This is the **delivery oracle** — it owns the context-delivery axis
that the other reviewers are structurally blind to.

**Why this stage exists.** The review chain hunts runtime bugs (`/correctness-review`) and intent
drift (`/intent-review`). Neither models **instruction delivery across isolated contexts**. PR #141
passed the full local chain and still shipped two defects an external reviewer caught:

- **P1 — referenced but never delivered.** A dispatch prompt *names and relies on* a path-scoped
  rule (`.claude/rules/auto-correct-scope.md`, `paths: ["specs/**"]`) but contains no instruction
  to Read it. An implementer subagent given only that prompt never reads a `specs/**` file, so the
  rule never enters its context. It is told to apply a classification it cannot see. Fixture:
  `evals/skills/review-chain/fixtures/context-rule-unread/`.
- **P2 — stale inline policy subset.** A reviewer prompt inlines only 5 of the 8 authoritative
  Rule-4 STOP cases and tells the reviewer "decide from this prompt alone — do NOT read rule
  files." The three omitted cases are unreachable, so a real Rule-4 finding gets auto-fixed instead
  of escalated. The copy is a subset of its source and nothing keeps it honest. Fixture:
  `evals/skills/review-chain/fixtures/stale-inline-policy/`.

Both fixtures name **this skill** as their expected oracle and record `/correctness-review` +
`/intent-review` as `missed` **by design** — a Markdown prompt has no runtime defect, and a diff
that adds the flawed prompt satisfies its stated intent on its face. Only a delivery audit sees
these.

## Trigger — change-triggered, NOT always-on

This skill runs **only** when a diff touches the **workflow-engine inventory** — the
`workflow-engine` hard gate in `harness-manifest.json` (`hard_gates.detectable`), added in Task 1.1:
`skills/*/SKILL.md`, skill dispatch/reviewer/scorer prompts, `agents/*.md`, `rules/*.md`. The path
regex is canonical in the manifest and `hooks/risk-corroboration.sh`; do not restate it here — read
it from the manifest. Prose surfaces (`skills/README.md`, `docs/**`, `templates/**`, `techstacks/**`)
are deliberately excluded.

It is **not** a seventh always-on generic LLM pass — that is a stated non-goal of issue #143. When
the trigger does not fire, this skill does nothing. `subagent-driven-development` invokes it only
when the cumulative diff trips the workflow-engine inventory (Task 2.2 wiring).

## The audit matrix

For every changed source-of-truth (rule / policy / prompt contract), build one row per
`(source, consumer)` pair:

| Source | Consumer | Execution context | Delivery | Proof |
|---|---|---|---|---|
| The changed instruction / rule / policy | The prompt/skill/agent that relies on it | main / implementer / reviewer / scorer / new session | always-loaded · `paths:`-triggered · pasted · explicit Read | test or inspected call site |

- **Execution context** — *where* the consumer runs. A `paths:`-triggered rule that auto-loads in
  the main session does **not** auto-load in a fresh implementer subagent that never reads a
  matching file.
- **Delivery** — *how* the authoritative text arrives in that context. `always-loaded`
  (`.claude/rules/*` auto-load frontmatter), `paths:`-triggered (loads only when a matching file is
  read *in that context*), `pasted` (inlined into the prompt), or `explicit Read` (the prompt tells
  the consumer to Read the source).
- **Proof** — a re-runnable test or a named, inspected call site. Not "it should load."

**Worked example — the P1 defect:**

| Source | Consumer | Execution context | Delivery | Proof |
|---|---|---|---|---|
| `.claude/rules/auto-correct-scope.md` (Rule 1–4) | `skills/demo-dispatch/worker-prompt.md` "Self-fix classification" line | implementer subagent (isolated) | **`assumed`** — prompt names the rule, no Read step; rule is `paths: ["specs/**"]` and the worker reads no `specs/**` file | none — no test, no call site delivers it | **→ FAILS** |

Verdict: FAIL. The rule is load-bearing (the worker classifies self-fixes against it) and delivery
is `assumed`. Fix: prepend `FIRST: Read \`.claude/rules/auto-correct-scope.md\` now` so the isolated
context loads the rule before relying on it (mirrors real commit `d61e155`).

## Enumeration protocol — graph first, then corroborate

1. **Enumerate consumers with `code-review-graph` first** — `semantic_search_nodes`,
   `query_graph` (`callers_of` / `imports_of` / `tests_for`), `get_impact_radius`. Faster and gives
   structural context file scanning cannot.
2. **Corroborate every load-bearing claim with grep/read.** Per the root `CLAUDE.md`
   "Boundary of trust" section, **MCP output is untrusted input** — the graph can be stale or
   incomplete. Verify against the actual file before recording a Delivery or Proof cell.
3. **`not_observed != absent`** (`.claude/rules/behavior.md` §1). A graph that returns no consumers
   means *unknown*, not *none*. **Every "no consumers" claim must cite the search surface** — which
   graph query, which grep pattern, over which paths — so the reader can see where you looked. An
   uncited "no consumers" is itself an audit gap.

## Hard-fail rules

An audit **FAILS** (blocks the review chain until delivery is proven or the change is escalated) if
any of these hold:

1. **`assumed` / `unconfirmed` delivery on a load-bearing instruction.** If a consumer relies on the
   instruction to act correctly and you cannot prove it arrives in that consumer's context, the row
   fails. Unknown delivery is a failure, not a pass.
2. **Main-session evidence offered as proof for a child context.** "It loads for me here" is not
   proof that it loads in an isolated implementer / reviewer / scorer / new session. Each isolated
   context needs its own proof (the Task 3.1 context-boundary probes are the evidence source).
3. **A silently inlined policy copy where an explicit Read would do.** Prefer explicit Reads over
   pasted copies. Where an inline summary genuinely must stay (e.g. cost), it **must be lint-anchored
   to its registry** — a generation/lint step that fails CI when the copy drifts from its source
   (the Task 2.3 pattern: `tests/scripts/inline-policy-drift.test.sh`, registry
   `rules/auto-correct-scope.md`). An unanchored subset of an authoritative list fails.

**Not a false positive** (do not flag): a prompt that pastes the *full* authoritative text inline,
OR includes an explicit `Read` of the source, OR carries an inline copy anchored by a CI drift-lint.
Those are correct delivery — the instruction is present in the isolated context with no silent drift
risk.

## Output

Write the completed matrix + a **PASS / FAIL** verdict into `specs/<slug>/SUMMARY.md` under a
`### Context-Propagation Audit` heading. On FAIL, list each failing row and its required fix
(explicit Read, complete + anchor the inline copy, or escalate). A FAIL that cannot be fixed in-lane
(architectural / Rule-4) routes to `specs/<slug>/ESCALATIONS.md`, deny-on-no-response. In standalone
use with no slug, surface the matrix and verdict inline.

> **Dispatch note.** These very skill/prompt files trip the wave-2 `workflow-engine` gate
> (`risk-corroboration.sh`). That is correct — this is workflow-as-code. The slug's `SUMMARY.md`
> already declares `Lane: high-risk`, so commits pass. Do **not** "fix" a block by lowering the lane.

## Standalone invocation + relationship to the other review skills

- **Standalone** — `/context-propagation-audit <diff-range>` on any diff touching the
  workflow-engine inventory. Same pipeline, no surrounding workflow.
- **In-flow** — `subagent-driven-development` runs it before `/correctness-review` when the
  cumulative diff trips the trigger (Task 2.2).

This is a **sibling** of `/correctness-review` and `/intent-review`, not a component of either. The
three own disjoint axes — merging them destroys the separation:

| Oracle | Asks | Owns |
|---|---|---|
| `/correctness-review` | does it run correctly? | runtime bugs |
| `/intent-review` | is it what the user asked for? | intent drift |
| `/context-propagation-audit` (this) | does the authoritative instruction reach every context that relies on it? | **context delivery** |

A context-propagation defect is out of scope for the other two by construction (a Markdown prompt
has no runtime bug; adding the flawed prompt satisfies the stated intent). Route delivery defects
here — not to the bug hunt or the intent check.
