---
ticket: pd-prefix
stage: design
status: accepted
confidence: high
decided_by: owner (2026-11-19)
date: 2026-11-19
---

# 0042. Every harness skill carries the pd- prefix on the podbay branch

## Context

ADR 0041 added four fleet skills named pd-orchestrate, pd-work, pd-review and pd-advise; the other 23 skills kept their names. On 2026-11-19 the owner asked to rename all skills with the prefix pd, because the podbay branch only works with Pod Bay.

## Options

- Rename every skill to pd-<name> (chosen).
- Prefix only the four fleet skills. Rejected by the owner: one plugin with two naming schemes.
- Rename the plugin instead of the skills (for example a plugin named pd). Rejected: the marketplace, install commands and hook messages name the plugin harness, so the change would reach every consuming project at once.

## Decision

All 23 skills that had no prefix are renamed to pd-<name> (for example /harness:pd-intake, /harness:pd-autopilot). The four fleet skills keep their names. Agents, the plugin name harness and the workflow harness:autopilot-run keep their names. Every reference in code, tests and docs follows; CHANGELOG entries and ADR texts keep the old names as history, except paths that ADRs cite.

## Why

One prefix marks every skill of this branch as part of the Pod Bay way of working, and a reader no longer has to tell fleet skills from the rest.

## Consequences

Users type /harness:pd-<name>. A permission rule, script or document outside this repo that names harness:<old> or skills/<old>/ must change. ship.js and the autopilot skill keep working under the new names until phase 3 of ADR 0041 removes them.

## How to reverse

Revert the rename pull request.
