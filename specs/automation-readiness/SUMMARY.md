# automation-readiness — Summary

Lane: tiny
Confidence: high
Reason: Additive knowledge-base entry only (docs/solutions/*); no hard gate — touches no hooks/settings.json/skill-engine.
Flags: none
Affects: none
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> "triển khai phương án A" — following the researched option A: "viết critical-pattern
> 'automation-readiness' + một dòng tham chiếu trong bước design của high-risk lane";
> shape defined earlier as a design-checklist reference in `docs/solutions/` (a
> critical-patterns entry) consulted by the high-risk design step when the diff adds a
> hook / CI job / scheduled loop, with 2 questions (fail-safe + warranted), advisory
> (enforce-by-consultation), **not** a new intake gate or blocking hook.

## What changed

Added a `critical`-severity knowledge entry `docs/solutions/harness/automation-readiness.md`
capturing a loop-readiness / automation-readiness design gate (fail-safe & stop condition;
warranted & objectively verifiable) for any *standing* automation (new hook, CI/scheduled
workflow, or scheduled `/loop`). Promoted a summary into `critical-patterns.md` so it
auto-loads at planning time, and rebuilt `INDEX.md` (15 → 16 entries).

### Rationale

Option A over B/C: the risk-lane gate already forces `high-risk` for hooks/settings
(the *risk* question), so the only residual gap is the *design* question "should this
automation exist / will it fail loud" — best placed where automations are designed
(the auto-loaded critical-patterns channel), not as a new feature-intake step or a
blocking hook (which would itself have to pass this same readiness gate). Cheapest
placement, zero high-blast surface, no per-session execution cost.

### Alternatives considered

- B — new "Automation" input-type + conditional checklist inside feature-intake. Rejected: bloats the short mechanical intake for a narrow slice of traffic; edits a protected skill file.
- C — standalone `automation-readiness` skill/rule routed to on intent. Rejected: over-engineering for a 2-question advisory check.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| entry present + registered | `test -f docs/solutions/harness/automation-readiness.md && grep -q automation-readiness docs/solutions/INDEX.md && grep -q automation-readiness docs/solutions/critical-patterns.md` | 0 | doc exists and is linked from both auto-loaded channels |
| INDEX count is 16 | `grep -q "16 total entries" docs/solutions/INDEX.md` | 0 | header count matches rebuilt table |

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
