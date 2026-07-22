<!--
  Canonical SUMMARY.md shape. Copy to specs/<slug>/SUMMARY.md at intake.

  The header block is machine-read:
    - hooks/risk-corroboration.sh greps the `Lane:` line to corroborate it
      against the staged diff (a hard-gate signal in the diff + a Lane below
      high-risk = blocked).
    - the trust-metrics ledger reads Lane / Confidence / Flags per task.
  Keep the five header fields present and on their own lines. Do not delete them.
-->

# <slug> — Summary

Lane: tiny | normal | high-risk
Confidence: high | medium | low
Reason: <one sentence — why this lane (which flags / hard gates fired, or none)>
Flags: <comma-separated risk flags that fired, or `none`>
Affects: <affected contract/module, from PROJECT.md High-Blast/Shared-Contracts list or module name; 'none' if not applicable>
Input-type: new spec | spec slice | change request | new initiative | maintenance | harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<!-- The user's request VERBATIM at intake — do NOT paraphrase or summarize. This is the
     oracle for /intent-review (the final stage of subagent-driven-development): the third
     reviewer is blind to PLAN.md and checks the finished diff against this text. If the
     request came over several conversational turns, quote the scope-deciding sentences in
     chronological order. Capturing intent here, not in the plan, is what keeps the intent
     oracle independent of the plan oracle. -->

<paste the original request, verbatim>

## What changed

<one short paragraph: the product delta — what the work actually did>

### Rationale

<!-- Why this approach — the decision + the key constraint/signal that drove it.
     This is the audit record for autonomous (no-human) work: write it so the
     decision can be reconstructed later WITHOUT re-reading the diff. -->

<one or two sentences>

### Alternatives considered

<!-- Other options weighed + why not. `- none` if it was the single obvious
     approach (typical for tiny lane). -->

- none

### Deviations

<!-- Every Rule 1–3 auto-fix per rules/auto-correct-scope.md, labeled by rule.
     Leave a single `- none` line if there were none. -->

- none

### Verify

<!-- Evidence over assertion: one row per check that was actually RUN.
     A claim of "done" is only valid with a re-runnable command + its result.
     Do not list a command that was not run.
     The trailing `Criterion` column is optional: name an `SC-n` from PLAN.md §3
     when the row satisfies one; every SC must be covered by >=1 passing row
     (enforced by scripts/verify_summary.py). Leave blank for rows that map to no SC. -->

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| <unit / lint / build / behavior> | `<command>` | 0 | <output excerpt on fail> | <SC-n or blank> |

### Rollback

<!-- Required for any high-risk / Rule-4 action: the exact command(s) to undo it.
     For reversible tiny/normal work, `git revert <sha>` is sufficient. -->

- `git revert <sha>`

### Harness-Delta

<!-- What friction did this task reveal about the workflow itself?
     fix-direct (done in this task) or backlog (-> /compound -> docs/solutions/).
     Leave `- none` if the workflow needed no change. -->

- none
