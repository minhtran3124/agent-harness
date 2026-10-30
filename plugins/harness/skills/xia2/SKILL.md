---
name: xia2
description: "Find out how something actually works here before building on it. Use when the user asks to add a feature to code they have not explained, names a library or API the repo does not already use, or asks how an existing part of the system works — and NOT when the question is which of several approaches to take, which is brainstorming. Produces a research brief: local scratch at specs/<slug>/research-brief.md for depth L, a short inline brief otherwise."
allowed-tools: Glob, Grep, Read, Write, WebSearch, WebFetch, Bash(git log *), Bash(git show *), Bash(ls *)
---

# Xia2 — research before building

Find what already exists before anything is built. This is read-only work: edit nothing except the
brief. It runs on the Haiku `researcher` agent.

## Steps

1. Read `AGENTS.md`, `CLAUDE.md` and `README.md` if present. Search `docs/solutions/` and `docs/adr/`
   for related work.
2. Detect the stack and versions from manifests. Map local reuse, extension points, tests and
   configuration.
3. Look outside the repo only when the change has an external surface: it adds or upgrades a
   dependency, integrates an external system, or relies on a version-specific API. Then read
   the version-matched official docs and one or two upstream implementations. Failure to reach them
   is not a blocker.
4. Write the brief (see `references/research-brief-template.md`). Cite every fact as `file:line`
   or a URL. Label inferences as inference.
5. Recommend in this order: reuse, adapt upstream, use a built-in, build new. Say why the
   alternatives lost.

Depth L writes `specs/<slug>/research-brief.md` (local scratch, not committed) or returns it inline.
Depth S and M return a short brief inline.

## Auto mode

- The caller names the mode in the prompt: `Mode: interactive` (default) or `Mode: auto`.
- Interactive: you may ask the owner with AskUserQuestion, one batch at a time, each question with a
  recommended answer.
- Auto: never ask the owner. On any ambiguity pick the recommended option and record it in
  `decisions[]`: `{title, context, options, decision, why, consequences, how_to_reverse,
  confidence: high|medium|low, needs_review: boolean}`. Do not write ADR files.
- Set `needs_advisor: true` with `advisor_question` when you are BLOCKED, have low confidence, or a
  finding affects other tickets or a public contract. The calling script runs the advisor. Do
  not spawn agents (`docs/adr/0001-workflow-capabilities.md`).
