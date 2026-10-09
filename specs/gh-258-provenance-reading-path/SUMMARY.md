# gh-258-provenance-reading-path — Summary

Lane: high-risk
Confidence: medium
Reason: workflow-engine hard gate. It changes the design template that the isolated design reviewer is required to read (skills/brainstorming/references/design-template.md) and the xia2 research-brief template, which steer every spec. The same surfaces were classified high-risk in batch 1 (gh-258-spec-evidence-rules).
Flags: workflow-engine, existing behavior, multi-domain
Affects: skills/brainstorming/references/design-template.md, skills/xia2/references/research-brief-template.md, and the design reviewer prompt if it gains a check
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Scope-deciding sentences, in chronological order:

> check issue https://github.com/minhtran3124/agent-harness/issues/258, xem thu da implement het cac item trong table rollout chua?

> ok, chạy tới PR luôn

(The last message answered "Theo rollout của #258, còn lại item 6 và 7 … template prose, batch \"later\"", together with the offer to open issues for two pre-existing problems; those became #276 and #277.)

Items 6 and 7 of GitHub issue #258 (https://github.com/minhtran3124/agent-harness/issues/258), as written in the issue:

> **Item 6 — Pinned provenance header on research and design docs.** Purpose: A reader (or a staleness check) knows exactly what state of the world the document describes and when it was written. Gap: `docs/solutions/` entries carry `confirmed_at` with a 30-day staleness rule, but `research-brief.md` and `design.md` have no machine-readable date or pin. Some have a free-text "Evidence refreshed" line. Target: The research-brief and design templates start with `Written <YYYY-MM-DD>. Pins: <repo sha / tool versions the claims were checked against>`. A later staleness check is optional.
>
> **Item 7 — Reading path and a worked trace for multi-document specs.** Purpose: An agent or reviewer loads the minimum context first, which matters for our context budgets. A worked trace exposes gaps between layers that a per-component description hides. Gap: Multi-document specs (e.g. `codex-support` with `design.md`, `ROADMAP.md`, `packaging-decision.md`, JSON inventories) have no stated entry point or reading order. Target: Optional design-template sections: `## Reading path` (only for specs with more than two documents) and `## Worked trace` (one concrete request followed end to end).

The rollout table lists items 6 and 7 together as the "later" batch ("template prose, small"). Other #258 items are out of scope. The branch is cut from `spec-format`; the PR targets `--base spec-format`.

Confidence is `medium`, not `high`: the targets are written in #258, but two details have a
documented default rather than a single reading, to be settled in brainstorming. (a) Whether the
design reviewer checks the new header. The default is that the reviewer reports a missing or
malformed `Written … Pins:` line, because item 6 says the templates *start with* it, and reviewer
checks are how batch 1 enforced template sections. (b) Whether the optional item-7 sections are
reviewed. The default is no check beyond "if present, it is not a placeholder", because the issue
calls them optional. The item-6 staleness check stays out of scope ("optional", "later").

## What changed

<filled at ship time>

### Rationale

<filled at ship time>

### Alternatives considered

- none yet (brainstorming)

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| intake lane record | `python3 .claude/scripts/verify_summary.py --lane gh-258-provenance-reading-path` | 0 | |

### Rollback

- `git revert -m 1 <merge-sha>` of the PR into `spec-format`.

### Not auto-verified

- none yet

### Harness-Delta

- none
