# Context-Boundary Probes (manual protocol)

Empirical proof of **instruction delivery per execution context**. This subtree exists because
PR #141 shipped a defect (issue #143, class P1) where a path-scoped rule
(`.claude/rules/auto-correct-scope.md`, frontmatter `paths: ["specs/**"]`) was *referenced* in a
subagent dispatch prompt but never actually *delivered* to that subagent's context — the isolated
worker was pointed at a rule it could not see. No oracle in the chain proved the instruction
arrived. These probes are that oracle, run by hand per context.

Sibling of `evals/skills/review-chain/` and built on the same philosophy: a **manual protocol**
with no automated runner — and adding one is explicitly out of scope for this version. It measures
one thing only: *did an instruction reach this context or not*, tested with both a positive case
(something that SHOULD be delivered) and a negative control (a path-scoped rule that should NOT
auto-load there, so its absence confirms the boundary is real and not merely always-on).

## Claim discipline (read first)

A probe result is a claim about **one context, one Claude Code version, one HEAD sha** — nothing
more. Specifically:

- **A main-session result is VALID ONLY for the main session.** Delivery observed in main
  (path-scoped rules inject when a matching `specs/**` file is read) does **not** transfer to any
  child context — implementer, reviewer, or scorer. Generalizing a main-session result to a child
  context is exactly the mistake that caused #141. Each child context must be probed on its own.
- `not_observed != absent` — a context we did not probe is **unmeasured**, not "confirmed
  delivered." A boundary with no recorded probe is `unconfirmed` by default.
- An `unconfirmed` verdict on a **load-bearing** boundary (one an instruction depends on to arrive)
  **lowers confidence or BLOCKS shipment**. It must **never** be silently recorded as "mitigated"
  or "handled." If you cannot prove delivery, you record `unconfirmed` and escalate — you do not
  assume.
- **Which boundaries are load-bearing:** the three isolated **child** contexts (implementer,
  reviewer, scorer). They are where the #141 P1 escape lives — a dispatch that only *references* a
  rule. The **main session is NOT** a load-bearing isolated-dispatch boundary: it receives rules by
  its own file reads, a different mechanism, so an `unconfirmed` main-session result is a
  methodological gap to re-run in a fresh session, not a shipment blocker. It is still recorded
  honestly as `unconfirmed`, never "mitigated."

## The four contexts and how each is invoked

| Context | Probe file | How it is invoked |
|---|---|---|
| **main session** | `probes/main-session.md` | Run the prompt directly in the interactive main session. |
| **implementer subagent** | `probes/implementer-subagent.md` | Dispatch via `Agent(general-purpose)` / the Task tool — the isolated worker that receives pasted task text. |
| **reviewer agent** | `probes/reviewer-agent.md` | Dispatch via the read-only `reviewer` agent type (`agents/reviewer.md`; Write/Edit/Agent excluded). |
| **scorer agent** | `probes/scorer-agent.md` | Dispatch via a cheap-model subagent (e.g. haiku) as the correctness scorer runs. |

Each probe file carries: (1) the exact dispatch prompt to paste into that context; (2) the
**positive marker** — what the context must echo to prove an instruction arrived; (3) the
**negative control** — a path-scoped rule that must NOT auto-load there, whose absence is the
expected result; and (4) a results-recording stanza.

## The positive / negative pair

Both markers are drawn from the harness's own path-scoped rules, so the probe tests the real
delivery mechanism rather than an invented one:

- **Positive marker — `rules/auto-correct-scope.md`** (frontmatter `paths: ["specs/**"]`). Its
  top-level heading is the exact line `# Auto-Correction Scope`. In **main**, reading any
  `specs/**` file injects it. In a **child** context it arrives ONLY if the dispatch prompt
  explicitly instructs a Read — the P1 lesson. If the context can quote the heading, the
  instruction is in context: **delivered**.
- **Negative control — `rules/wave-parallelism.md`** (frontmatter `paths: ["specs/**/PLAN.md"]`).
  Its top-level heading is `# Wave Parallelism Rule`. It is scoped more narrowly (only a `PLAN.md`
  read triggers it) and is deliberately NOT delivered by any probe below. A context that
  **cannot** quote it — a blank or "not available" answer — is the **expected** negative and
  confirms the boundary is real: the harness is not just handing every rule to every context.

A probe is only trustworthy when BOTH halves behave: the positive marker present AND the negative
control absent. A context that echoes the negative control is either mis-run or reveals the
boundary does not hold — record it and investigate before trusting the positive.

## Evidence rules

Every recorded run MUST capture, per context:

- `claude --version` output (the runtime the result is pinned to).
- Repo HEAD sha: `git rev-parse HEAD`.
- Probe (positive / negative), Expected, Observed, and a Verdict of
  **`delivered` / `not-delivered` / `unconfirmed`**.

`delivered` and `not-delivered` are both valid, informative outcomes (the negative control's
*expected* verdict is `not-delivered`). `unconfirmed` means the probe could not be run or its
result was ambiguous — and on a load-bearing boundary that blocks, per Claim discipline above.

Results are recorded under `results/<date>-<label>.md` (Task 3.2 runs the protocol and writes the
baseline; **3.1 is the protocol only — do not fabricate results here**).

## Staleness / version-pinning

Delivery behavior is a property of the Claude Code runtime, not of this repo alone. Therefore:

- Every result is **pinned** to the `claude --version` it was observed under.
- **Re-probe after any Claude Code upgrade.** A result from an older version does not carry
  forward — the injection rules for path-scoped rules could change between releases.
- A probe that can no longer be reproduced on the current version **downgrades the boundary to
  `unconfirmed`** (which blocks, by design), until it is re-run and re-recorded.
