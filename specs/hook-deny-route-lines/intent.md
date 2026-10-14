# Intent: Every hook deny message states its reason and a route to approval

Author: Minh Tran
<!-- Set Status to approved or draft. Intake proceeds only on approved. -->
Status: approved

## Problem

When a harness hook blocks a commit or an edit, some messages say why but not what to do next.
For example, the secrets scan, the staged `.env` check, a failing targeted test run, the
unresolvable project root, and the strict blast-radius block stop the agent with no route to
approval, so the agent or a person has to read the hook source to find the way forward. Play 10
of the SDLC playbook says a block message is "reason + route" (research note §6, E2).

## Proposed outcome

Every deny or blocking path in `hooks/commit-gate.sh`, `hooks/branch-isolation-guard.sh`, and
`hooks/lib/` prints both the reason and a route: the exact action that clears it, or the approval
step and who takes it (for example "set `BRANCH_ISOLATION_REASON=…`", "record the decision in
ESCALATIONS.md"). Messages that already have both stay as they are.

## Affected users and systems

- Agents (Claude and Codex) that receive the deny text and must decide the next step (assumed).
- People who see a blocked commit in a consumer repo (assumed).
- Hook tests under `tests/hooks/` that assert message text (assumed).

## Constraints

- Message text only: no gate changes what it blocks, its mode, or its profile (assumed).
- No new override or break-glass variable. Where a gate has no override today, the route names the existing fix or says a human must decide (assumed).
- The deny decision and exit codes stay the same: exit 2 for commit-gate blocks, a JSON `permissionDecision: deny` for the JSON paths (assumed).
- A route names only commands, variables, files, and skills that exist in the deployed harness (assumed).

## Out of scope

- Warn-only messages and PASS/skip notices (assumed).
- `scripts/ci-strict-gate.sh` and other CI scripts (assumed).
- Adding, removing, or loosening any gate (assumed).

## Open questions

none

## What success looks like

- Each blocking path in the three locations has a test or fixture that asserts its message contains a route line (assumed).
- `bash scripts/run-tests.sh` stays green (assumed).

## Original request

"trong luc tôi review thì start cho next item theo research doc đi" — after E6, the next item in
the suggested order of `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md` §6 is E2:

| **E2** | **Audit every deny message for "reason + route to approval"** and add the missing route lines (e.g. "set `BRANCH_ISOLATION_REASON=…`", "record decision in ESCALATIONS.md") | Play 10 | `hooks/commit-gate.sh`, `hooks/branch-isolation-guard.sh`, `hooks/lib/` | high-risk (hooks) |
