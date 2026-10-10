---
name: feature-intake
description: First gate for a change request: classify its risk lane and confidence, record the decision in `specs/<slug>/SUMMARY.md`, then route to the appropriate workflow. Use before research, planning, or edits.
allowed-tools: Read, Write, Grep, Glob, Bash(git log *), Bash(git diff *), Bash(ls *), Bash(python3 scripts/verify_summary.py *), Bash(python3 runtime/run_state.py *)
---

# Feature Intake — classify and route

<HARD-GATE>
Do not edit, scaffold, or dispatch implementation until intake records `Lane:` and `Confidence:`
in `specs/<slug>/SUMMARY.md`. The lane is risk; confidence is ambiguity. Never ask the user to
classify risk; ask only to resolve a material ambiguity or narrow a hard-gated scope.
</HARD-GATE>

## Procedure

1. If the slug's SUMMARY exists and has an `Intent-source:` line or `specs/<slug>/intent.md`
   now exists, follow `references/re-pin.md` instead of this procedure. Read
   `harness-manifest.json` (hard gates), `rules/orchestration.md` and
   `rules/auto-correct-scope.md` (routing, branches). If intent.md exists (shape:
   `templates/INTENT.template.md`), read it first: stop unless its header line (`Status:` above
   the first `##`) is exactly `approved` (empty stops); pin with
   `git log -1 --format=%H --diff-filter=AM -- specs/<slug>/intent.md` (empty: stop); if
   `git diff --exit-code <pin> -- specs/<slug>/intent.md` is non-zero, stop and ask for the
   intent to be committed. Classify from intent.md plus the chat request.
2. Classify the input: new spec, spec slice, change request, initiative, maintenance, or harness
   improvement. Mark applicable risk flags: auth, authorization, data model, audit/security,
   external systems, public contracts, cross-platform, existing behavior, weak proof, and
   multi-domain.
3. Assign the lane: a manifest hard gate is `high-risk`; otherwise 0–1 flags is `tiny` only for
   one-file/no-new-public-callable work (else `normal`), 2–3 is `normal`, and 4+ is `high-risk`.
   A human may lower a hard-gated lane only by narrowing scope.
4. Assign confidence: `high` for one clear interpretation, `medium` for a safe documented
   default, and `low` for materially different plausible interpretations (including a chat
   request that conflicts with intent.md). Low confidence stops for human confirmation
   regardless of lane.
5. The pin line is `Intent-source: specs/<slug>/intent.md @ <sha>`; chat-only intake writes none.
6. For a new SUMMARY, write it from `templates/SUMMARY.template.md`. `### Intent` holds the pin
   line when Step 1 pinned, then the chat request verbatim and in full; agent notes go in
   `### Intake notes`, never in `### Intent` or intent.md:

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

7. For a new SUMMARY, initialize `runtime/run_state.py` as `investigating` (best effort); for
   normal and high-risk, transition to `planning`. Failures never block intake. Always run
   `python3 scripts/verify_summary.py --lane <slug>` before handoff.

## Routes

| Lane | Route |
| --- | --- |
| tiny | Create a branch, make the direct patch, and retain quick-check proof; report done only when that check passes, else state what is missing. |
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
