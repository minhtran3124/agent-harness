---
name: xia2
description: "Find out how something actually works here before building on it. Use when the user asks to add a feature to code they have not explained, names a library or API the repo does not already use, or asks how an existing part of the system works — and NOT when the question is which of several approaches to take, which is brainstorming. Produces a specs/<slug>/research-brief.md."
allowed-tools: Glob, Grep, Read, Write, WebSearch, WebFetch, Bash(git log *), Bash(git show *), Bash(cat *), Bash(ls *)
---

# Xia2 — research before code

<HARD-GATE>
Do not write code, scaffold, or edit anything except the research brief until the brief is saved
and delivered. An explicit “skip research”/“just implement” waiver skips the workflow, but still
requires a one-line warning for every Deep signal; never waive this gate yourself.
</HARD-GATE>

## Decide depth

Read `rules/research-depth.md` and `references/depth-classifier.md`. If intake metadata exists,
start with its mapping: high-risk → Deep, normal → Standard, tiny → Quick only when every Quick
condition passes. Do not independently reclassify risk. Without intake, use the portable
classifier. New evidence may raise depth, never lower it; uncertainty is Standard.

## Workflow

1. Check for an explicit waiver and report any Deep warning.
2. Read available `AGENTS.md`, `CLAUDE.md`, and `README.md`. Search `docs/solutions/INDEX.md`,
   `critical-patterns.md`, and at most three relevant solution files; scan relevant recent `specs/`.
3. Detect the stack and versions from manifests/configuration, then map local reuse, extension
   points, tests, and configuration. Do not infer a stack from directory names or stop after one
   empty search.
4. At Standard/Deep, search upstream implementations, and version-matched official documentation
   when the change has an external surface (adds/upgrades a dependency, integrates an external
   system, or relies on a version-specific API). Label each finding `Local`, `Upstream`, `Docs`,
   or `Inference`; upstream failure is non-blocking. With no external surface, record that in
   Source Pack as `- none (local-only; no external surface)` — never leave it silently empty.
5. Re-run the depth classifier with evidence. State any upgrade and its source.
6. Fill `references/research-brief-template.md`, save it to the supplied spec directory (or
   `specs/research-brief.md`), and deliver it. Recommend reuse → adapt upstream → built-in →
   build, explaining why rejected alternatives lost.

Quick performs local artifact and reuse search only. Standard adds upstream patterns. Deep adds
broad local coverage and explicit risk analysis. Official docs, multiple upstream sources, and
changelogs are required by *external surface*, not by depth alone — see `rules/research-depth.md`
§Coverage. Depth sets how broadly to look; surface sets whether to look outside the repo.

## Arguments

`$ARGUMENTS` is the feature to research; ask for it if absent. A caller may specify quick,
standard, or deep, but a requested depth that conflicts with a Deep signal must be surfaced.

## References

- `rules/research-depth.md` — canonical depth policy
- `references/depth-classifier.md` — portable signals and decision details
- `references/research-brief-template.md` — required output shape
