---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-07-17
---

# 0014. Remap app-centric risk signals to harness-native Deep triggers

## Context

xia2's PROJECT.md template defines risk-signal categories (Session/Transaction Primitives, Auth Surfaces, dependency manifests, public API surfaces) that literally don't exist in this repo — no DB, no auth, no app framework. Leaving them empty would silently weaken xia2's Deep-review override, since the classes of dangerous change those categories were designed to catch still exist here in different forms.

## Options

- Option A: Mark the non-applicable categories "none" and move on. Trade-off: factually accurate and prevents the classifier from hallucinating a DB, but loses the Deep-review signal entirely for the equivalent harness risks.
- Option B: Record "none" for the literal category PLUS map each to the closest harness-native analog as a named Deep trigger: session/transaction primitive → hook fail-open↔fail-closed semantics (warn↔block switches like `RISK_CORROBORATION_STRICT`); auth surface → `commit-quality-gate.sh` secrets scan; dependency manifest → `.mcp.json` MCP-server list; public API → skill names in SKILL.md frontmatter + template field names (e.g. `Lane:`) parsed by hooks. Trade-off: requires judgment about which analogs genuinely match, and the mapping must be defensible on re-runs.

## Decision

Option B — dual recording: "none" for the literal category so the classifier doesn't invent infrastructure, plus the named analog as a Deep trigger.

## Why

The deciding factor: the analogs are the changes with the same blast-radius character the category was designed to catch — silent, cross-cutting, security-relevant — so dropping them would discard the category's protective intent, not just its label. (This is also why `.mcp.json` additions became a Deep trigger despite not being a classic dependency manifest — it follows from the mapping, not a separate choice.)

## Consequences

Enables: the Deep-review override stays meaningful on the harness — fail-open/fail-closed flips, secrets-scan edits, MCP-server additions, and hook-parsed contract fields (skill names, `Lane:`) all trigger Deep. Constrains: the analog mappings are judgment calls embedded in PROJECT.md and must be re-validated when hooks or templates change; a future maintainer could mistake an analog for over-reach and remove it without seeing the category it stands in for.

Applies when: Make this decision when porting a risk-classification template into a repo whose stack lacks the template's literal categories (no DB/auth/framework) but has changes with equivalent blast-radius character.

Status note: **Status (2026-07-17):** the `/bootstrap-xia2` update-mode and `skills/xia2/PROJECT.md` these decisions were made during no longer exist (bootstrap-xia2 retired; xia2 zero-config). Decision 1's concrete premise is also resolved — `rules/architecture.md` + `rules/guidelines.md` are now thin pointers to project-owned `techstacks/`, not FastAPI-describing docs — but the durable rule holds: **don't point harness-working agents at target-project docs**, and record harness-native Deep triggers rather than empty risk categories. Both decisions are preserved as the reasoning behind today's `agents/PROJECT.md` (historical) convention pointers.

Related:
- docs/solutions/harness-bootstrap/meta-repo-signal-remapping.md

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness-bootstrap/ before #567 and is in git history.
