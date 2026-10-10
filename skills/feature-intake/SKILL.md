---
name: feature-intake
description: First gate for a change request: classify its risk lane and confidence, record the decision in `specs/<slug>/SUMMARY.md`, then route to the appropriate workflow. Use before research, planning, or edits.
allowed-tools: Read, Write, Grep, Glob, Bash(git log *), Bash(git diff *), Bash(git add *), Bash(git commit *), Bash(git config user.name), Bash(ls *), Bash(python3 scripts/verify_summary.py *), Bash(python3 runtime/run_state.py *)
---

# Feature Intake — classify and route

<HARD-GATE>
Do not edit, scaffold, or dispatch implementation until intake records `Lane:` and `Confidence:`
in `specs/<slug>/SUMMARY.md`. The lane is risk; confidence is ambiguity. Never ask the user to
classify risk; ask only to resolve a material ambiguity or narrow a hard-gated scope.
</HARD-GATE>

## Procedure

1. If SUMMARY exists and either has an `Intent-source:` line or `specs/<slug>/intent.md` exists,
   follow `references/re-pin.md` instead. With no SUMMARY, first follow
   `references/draft-intent.md` unless intent.md is `Status: approved` and committed. Read
   `harness-manifest.json` (hard gates), `rules/orchestration.md` and
   `rules/auto-correct-scope.md` (routing, branches). Read intent.md if present (shape:
   `templates/INTENT.template.md`): stop unless its header line (`Status:` above
   the first `##`) is exactly `approved`; pin with
   `git log -1 --format=%H --diff-filter=AM -- specs/<slug>/intent.md` (empty: stop); if
   `git diff --exit-code <pin> -- specs/<slug>/intent.md` is non-zero, stop and ask to
   commit the intent. Classify from intent.md plus the chat request.
2. Input type: new spec, spec slice, change request, initiative, maintenance, or harness
   improvement. Mark risk flags: auth, authorization, data model, audit/security,
   external systems, public contracts, cross-platform, existing behavior, weak proof, and
   multi-domain.
3. Assign the lane: a manifest hard gate is `high-risk`; otherwise 0–1 flags is `tiny` only for
   one-file/no-new-public-callable work (else `normal`), 2–3 is `normal`, and 4+ is `high-risk`.
   A human may lower a hard-gated lane only by narrowing scope.
4. Assign confidence: `high` for one clear interpretation, `medium` for a safe documented
   default, `low` for materially different plausible readings (including a chat request
   conflicting with intent.md). Low confidence always stops for human confirmation.
5. The pin line is `Intent-source: specs/<slug>/intent.md @ <sha>`; only legacy slugs (SUMMARY,
   no intent.md) have none.
6. For a new SUMMARY, write it from `templates/SUMMARY.template.md`. `### Intent` holds the pin
   line, then the request verbatim and in full: intent.md's `## Original request`, else the chat
   request, else `none — intent.md is the request`; never an approval or change reply. Agent
   notes go in `### Intake notes`, not `### Intent`; intent.md content comes only from the draft
   procedure or the user:

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

7. For a new SUMMARY, initialize `runtime/run_state.py` as `investigating`, then `planning` for
   normal and high-risk; failures never block intake. Always run
   `python3 scripts/verify_summary.py --lane <slug>` before handoff.

## Routes

- tiny: branch, patch directly, keep quick-check proof; report done only when it
  passes, else state what is missing.
- normal: `using-git-worktrees` → `subagent-driven-development`.
- high-risk: `brainstorming` → `xia2` → `writing-plans` → `using-git-worktrees` →
  `subagent-driven-development`; use `compound` for durable decisions.

All lanes require branch isolation. Artifacts scale by signal: a plan for more than three steps
or two files, research for unfamiliar code or high-risk, a design for a real design fork or
high-risk (`FULL_ARTIFACTS=1` forces all).

## Research-depth handoff

When intake ran, xia2 starts `high-risk` at **Deep**, `normal` at **Standard**, and `tiny` at
**Quick** only if every Quick condition in `rules/research-depth.md` passes. It never re-scores
risk; evidence of a deeper signal can only raise depth.

## Arguments

`$ARGUMENTS` is the requested change. Derive `<slug>` using the ticket-prefix convention in
`templates/structure/specs-README.md`; never rename an existing spec directory.
