---
problem_type: decision
module: skills/bootstrap-xia2
tags: meta-repo, signal-remapping, project-md, dual-audience-docs, bootstrap-update-mode, hook-friction
severity: critical
applicable_when: When bootstrapping, classifying risk, or sourcing conventions in a meta/harness repo whose .claude/rules docs describe the *target* projects it deploys into — remap app-centric signals to harness-native analogs and never point harness-working agents at target-project architecture docs.
affects:
  - agents/PROJECT.md
  - skills/xia2/PROJECT.md
supersedes: null
confidence: high
confirmed_at: 2026-06-11
---

## Applicable When
When bootstrapping, classifying risk, or sourcing conventions in a meta/harness repo whose `.claude/rules` docs describe the *target* projects it deploys into — remap app-centric signals to harness-native analogs and never point harness-working agents at target-project architecture docs.

## Decision 1
### Context
During /bootstrap-xia2 update mode, `agents/PROJECT.md` needed convention-source pointers for execution agents. The bootstrap heuristic's default ("first existing of `.claude/rules/architecture.md`, `docs/architecture.md`, ...") would resolve to `.claude/rules/architecture.md`, which exists — but that file (and `.claude/rules/guidelines.md`) describes the TARGET FastAPI projects this harness deploys into (FastAPI layering, repositories, Pydantic, pytest coverage gates), not the harness repo itself (bash hooks + markdown skills). An agent working ON the harness that followed it would be misled — e.g. look for `app/routers/` or apply pytest coverage gates to bash test suites.

### Options Considered
- Option A: Follow the heuristic literally — point `agents/PROJECT.md` at `.claude/rules/architecture.md` + `guidelines.md`. Trade-off: zero judgment required, file demonstrably exists, but the docs describe a different codebase (wrong audience), so agents would be actively misled.
- Option B: Override the heuristic — point at `skills/README.md` (skill inventory + workflow/handoff map, the de facto architecture doc for this repo) + `rules/behavior.md` (declared "single source of truth" for behavior by CLAUDE.md), and add an explicit maintainer note that `.claude/rules/*` describes target projects, not this repo. Trade-off: deviates from the documented heuristic, requires the note to survive future re-runs.

### Decision & Rationale
Option B, with the maintainer note. The convention index exists specifically to prevent agents from being misled; pointing it at docs about a different codebase defeats its purpose regardless of how cleanly the heuristic resolves. The maintainer note is load-bearing: it records the target-project vs. harness-repo distinction so a future bootstrap re-run doesn't "correct" the pointers back to the FastAPI docs.

### Applicable When
Make this decision when a meta/tooling repo carries docs describing the projects it deploys into, and a detection heuristic would select those docs as the repo's own architecture/style reference.

### Consequences
Enables: execution agents on the harness get accurate architecture (`skills/README.md`) and behavior (`rules/behavior.md`) sources; the maintainer note inoculates against heuristic-driven regression on re-bootstrap. Constrains: the bootstrap heuristic is no longer self-sufficient for this repo — any automated re-run must respect the note, and the note itself must be maintained as docs move.

## Decision 2
### Context
xia2's PROJECT.md template defines risk-signal categories (Session/Transaction Primitives, Auth Surfaces, dependency manifests, public API surfaces) that literally don't exist in this repo — no DB, no auth, no app framework. Leaving them empty would silently weaken xia2's Deep-review override, since the classes of dangerous change those categories were designed to catch still exist here in different forms.

### Options Considered
- Option A: Mark the non-applicable categories "none" and move on. Trade-off: factually accurate and prevents the classifier from hallucinating a DB, but loses the Deep-review signal entirely for the equivalent harness risks.
- Option B: Record "none" for the literal category PLUS map each to the closest harness-native analog as a named Deep trigger: session/transaction primitive → hook fail-open↔fail-closed semantics (warn↔block switches like `RISK_CORROBORATION_STRICT`); auth surface → `commit-quality-gate.sh` secrets scan; dependency manifest → `.mcp.json` MCP-server list; public API → skill names in SKILL.md frontmatter + template field names (e.g. `Lane:`) parsed by hooks. Trade-off: requires judgment about which analogs genuinely match, and the mapping must be defensible on re-runs.

### Decision & Rationale
Option B — dual recording: "none" for the literal category so the classifier doesn't invent infrastructure, plus the named analog as a Deep trigger. The deciding factor: the analogs are the changes with the same blast-radius character the category was designed to catch — silent, cross-cutting, security-relevant — so dropping them would discard the category's protective intent, not just its label. (This is also why `.mcp.json` additions became a Deep trigger despite not being a classic dependency manifest — it follows from the mapping, not a separate choice.)

### Applicable When
Make this decision when porting a risk-classification template into a repo whose stack lacks the template's literal categories (no DB/auth/framework) but has changes with equivalent blast-radius character.

### Consequences
Enables: the Deep-review override stays meaningful on the harness — fail-open/fail-closed flips, secrets-scan edits, MCP-server additions, and hook-parsed contract fields (skill names, `Lane:`) all trigger Deep. Constrains: the analog mappings are judgment calls embedded in PROJECT.md and must be re-validated when hooks or templates change; a future maintainer could mistake an analog for over-reach and remove it without seeing the category it stands in for.

## Related
- docs/solutions/harness-bootstrap/meta-repo-signal-remapping.md
