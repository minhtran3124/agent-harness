---
problem_type: decision
module: rules / techstacks
tags: tech-stack-decoupling, project-owned, agnostic-core, techstacks, one-canonical-home, auto-loaded-rules, portability
severity: standard
applicable_when: The harness core (rules/skills/templates) carries stack-specific content (framework examples, a bundled stack profile) and you want a new installer to inherit no tech-stack baggage.
affects:
  - rules/architecture.md
  - rules/guidelines.md
  - rules/plan-format.md
  - techstacks/README.md
  - scripts/init-structure.sh
supersedes: null
confidence: high
confirmed_at: 2026-07-17
---
## Applicable When

Decoupling a portable harness from a specific tech stack, so its core ships zero framework assumptions and each consuming project owns its stack rules independently.

## Context

`rules/`, `skills/`, and `templates/stacks/` were coupled to FastAPI: worked examples in `plan-format.md` / `wave-parallelism.md` / `auto-correct-scope.md`, and bundled `templates/stacks/{fastapi,_skeleton}/` profiles copied into the auto-loaded `rules/architecture.md` + `guidelines.md` (which were unfilled placeholders loaded every session). A new installer inherited all of it.

## Options Considered

- **Keep bundled profiles + ship an example stack** — rejected: still couples the core; 2 of 5 profiles (nextjs/django) had no detection path anyway.
- **Deterministic bootstrap script that renders a per-project stack config** — rejected earlier (bootstrap-xia2 removal): per-project config is the coupling, not the cure.
- **A project-owned `techstacks/` folder; core only points at it** — chosen.

## Decision & Rationale

One project-owned root folder **`techstacks/`** (sibling of `specs/`, `docs/solutions/`), scaffolded create-if-missing by `init-structure.sh`, ships **only a `README.md`** convention doc. The project drops its own `techstacks/*.md`; **nothing in the harness depends on the contents**. Core becomes stack-agnostic: `rules/architecture.md` + `guidelines.md` collapse to ~5-line pointers to `techstacks/`; framework examples in the rules are neutralized (`src/<module>`, "your test runner"); `templates/stacks/` is deleted.

The stack now has exactly one home (`techstacks/`) pointed at from a few auto-loaded rules — the "one canonical home per fact" principle. It also drops always-on context (placeholders → pointers) and finishes the earlier instinct to cut bundled profiles.

## Consequences

- A new install inherits no stack; the project fills `techstacks/` or leaves it empty (docs-only/tooling repos work untouched).
- A `techstacks/`-neutral fence (grep-guard that `rules/` carry no framework tokens) is worth keeping as a regression check.
- A consumer that previously copied a bundled profile into its own `rules/architecture.md` keeps working (hand-maintained/protected); only the bundled *source* goes away.

## Related
- docs/solutions/harness-bootstrap/meta-repo-signal-remapping.md
