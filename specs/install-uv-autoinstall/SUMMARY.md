# install-uv-autoinstall — Summary

Lane: high-risk
Confidence: high
Reason: public-contract hard gate (new installer flag + changed consumer-visible install behavior) plus external download-and-execute of the astral.sh uv installer
Flags: public-contract, external-systems, audit/security, cross-platform, existing-behavior
Affects: scripts/install-harness.sh (consumer installer entry point)
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> có cách nào khi install harness script chúng ta cài luôn uv và code-review-graph ko?
> trước khi cài chúng ta sẽ wwarning trước cho user 1 dòng

Approved design (assistant proposal, user replied "dong y"): install by default when `uvx` is
missing, one-line warning before installing, opt-out `--no-uv`, no install under `--dry-run`,
install failure is non-fatal (warn and continue), pre-fetch code-review-graph through `uvx`.

## What changed

<filled at ship>

### Rationale

<filled at ship>

### Alternatives considered

- Opt-in `--install-uv` flag instead of default-on — rejected: the user asked to install as part of the harness install ("cài luôn").
- Interactive y/N prompt — rejected: the primary entry is `curl … | bash -s -- --yes`, which has no tty.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |

### Not auto-verified

- <filled at ship>

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
