---
name: feature-intake
description: First gate for a change request: classify its risk lane and confidence, record the decision in `specs/<slug>/SUMMARY.md`, then route to the appropriate workflow. Use before research, planning, or edits.
allowed-tools: Read, Write, Grep, Glob, Bash(git log *), Bash(git diff *), Bash(ls *)
---

# Feature Intake — classify and route

<HARD-GATE>
Do not edit, scaffold, or dispatch implementation until intake records `Lane:` and `Confidence:`
in `specs/<slug>/SUMMARY.md`. The lane is risk; confidence is ambiguity. Never ask the user to
classify risk; ask only to resolve a material ambiguity or narrow a hard-gated scope.
</HARD-GATE>

## Procedure

1. Read `harness-manifest.json` for canonical hard-gate vocabulary and modes. Read
   `rules/orchestration.md` and `rules/auto-correct-scope.md` for routing and branch policy.
2. Classify the input: new spec, spec slice, change request, initiative, maintenance, or harness
   improvement. Mark applicable risk flags: auth, authorization, data model, audit/security,
   external systems, public contracts, cross-platform, existing behavior, weak proof, and
   multi-domain.
3. Assign the lane: a manifest hard gate is `high-risk`; otherwise 0–1 flags is `tiny` only for
   one-file/no-new-public-callable work (else `normal`), 2–3 is `normal`, and 4+ is `high-risk`.
   A human may lower a hard-gated lane only by narrowing scope.
4. Assign confidence: `high` for one clear interpretation, `medium` for a safe documented
   default, and `low` for materially different plausible interpretations. Low confidence stops
   for human confirmation regardless of lane.
5. **Read `rules/terminology.md`** before authoring — it is path-scoped and writing a new
   `SUMMARY.md` does not load it. §3 applies to `### Verify` rows (state the observable — exact
   string, count, or exit code — never "is correct"); Rationale/Alternatives are advisory; and
   `### Intent` stays verbatim, excluded from every rule. Then write `SUMMARY.md` using
   `templates/SUMMARY.template.md`, including the user intent verbatim:

   ```text
   Lane: <tiny | normal | high-risk>
   Confidence: <high | medium | low>
   Reason: <flags/hard gate or none>
   Flags: <comma-separated or none>
   Affects: <contract/module from PROJECT.md or none>
   Input-type: <type>
   Route: <path>
   Escalate: <yes (reason) | no>
   ```

6. Initialize `runtime/run_state.py` as `investigating` on a best-effort basis. For normal and
   high-risk lanes, transition to `planning`; failures are observability failures, never an intake
   blocker. Run `python scripts/verify_summary.py --lane <slug>` before handoff.

## Routes

| Lane | Route |
| --- | --- |
| tiny | Create a branch, make the direct patch, and retain quick-check proof. |
| normal | `using-git-worktrees` → `subagent-driven-development`. |
| high-risk | `brainstorming` → `xia2` → `writing-plans` → `using-git-worktrees` → `subagent-driven-development`; use `compound` for durable decisions. |

All lanes require branch isolation. Artifact requirements scale by signal: plan for more than
three steps or two files, research for unfamiliar code or high-risk work, and a design for a real
design fork or high-risk work. `FULL_ARTIFACTS=1` forces all artifacts.

## Research-depth handoff

When intake metadata exists, xia2 must use it: `high-risk` starts **Deep**, `normal` starts
**Standard**, and `tiny` may be **Quick** only after every Quick condition in
`rules/research-depth.md` passes. Xia2 does not re-score risk; it can only increase research depth
when evidence reveals a deeper signal.

## Arguments

`$ARGUMENTS` is the requested change. Derive `<slug>` using the ticket-prefix convention in
`templates/structure/specs-README.md`; never rename an existing spec directory.

## References

- `harness-manifest.json` — hard gates and modes (authority)
- `rules/orchestration.md` — artifact and escalation policy
- `rules/auto-correct-scope.md` — branch and autonomy boundaries
- `skills/feature-intake/tests/lane-classification-cases.md` — lane canaries
- `skills/feature-intake/tests/confidence-escalation-cases.md` — ambiguity canaries
