# Research Brief — terminology delivery for research and summary artifacts

## Bottom Line

| Field | Value |
| --- | --- |
| **Recommendation** | Reuse the existing explicit-Read and context-matrix pattern |
| **Why this is the lightest credible path** | Two authoring instructions and two matrix entries close the write-side gap without a new loader or gate |
| **Confidence** | 95% |
| **Next step** | Implement the single task in `PLAN.md` and run its focused contract checks |

## Repo Snapshot

| Field | Detected |
| --- | --- |
| Repo type | Claude Code skills framework and workflow harness |
| Primary language + runtime | Markdown instruction sources, Python contract tooling, Bash tests |
| Relevant components | `xia2`, `feature-intake`, `terminology.md`, prompt context matrix |
| Important constraints | Path-scoped rules load on read; write-flows need explicit Reads; user intent remains verbatim |

## Feature Understanding and Assumptions

- **Requested feature:** Apply the repository's measured terminology profile when agents author
  `research-brief.md` and `SUMMARY.md`.
- **Success:** Both authoring skills explicitly load the canonical rule before writing, and a
  deterministic test detects removal of either delivery edge.
- **Assumption:** “Apply” means the existing per-section profile, not full ASD-STE100 compliance.
- **Confirmed exclusion:** Research prose keeps uncertainty; `SUMMARY.md ### Intent` stays
  verbatim.

## Evidence Ledger

| Label | Evidence |
| --- | --- |
| `Local` | `writing-plans/SKILL.md` already uses an explicit Read because new files do not trigger `paths:` |
| `Local` | `xia2/SKILL.md` writes the research brief but does not read `terminology.md` |
| `Local` | `feature-intake/SKILL.md` writes the summary but does not read `terminology.md` |
| `Local` | `render_skill_prompt.py` owns the contextual-policy consumer matrix and checks explicit Reads |
| `Inference` | Extending the established matrix is lower risk than introducing another delivery mechanism |

## Local Findings

- `skills/writing-plans/SKILL.md` is the reusable implementation pattern: explicit Read before
  authoring plus a short statement of which rule section matters.
- `scripts/test_render_skill_prompt.py` already checks exact context inventory and mutation-tests
  every required delivery token. Adding the two consumers reuses that proof; bespoke test code is
  unnecessary.
- `rules/terminology.md` already includes both artifact paths and the intended exclusions. The
  missing behavior is write-side delivery, not scope definition.
- `templates/SUMMARY.template.md` and `scripts/verify_summary.py` already structure executable
  evidence. No template or verifier expansion is required.

## Upstream Findings

- No upstream implementation was needed; this repository already contains the exact explicit-Read
  and delivery-matrix pattern to reuse.

## Docs Findings

- No external surface: the change adds no dependency, external integration, or version-specific
  API. Official documentation research does not apply.

## Recommendation

- **Primary:** Add one explicit Read to `xia2`, one to `feature-intake`, and register both in the
  current context matrix.
- **Why:** It fixes the timing problem at the source—before writing—using an already tested local
  pattern.
- **Rejected alternative:** An always-on rule or hook would broaden context and enforcement beyond
  the user's selected scope.
- **What would change the decision:** A future requirement for full ASD-STE100 or deterministic
  prose linting would need a separate measured design.

## Risks, Unknowns, and Follow-Up Questions

- The terminology profile's real-world effect on complete research/summary artifacts has not been
  benchmark-tested; only §3's synthetic acceptance task has measured behavioral evidence.
- No user question remains for this narrow delivery plan.

## Source Pack

- **Local files read:** `rules/terminology.md`, `rules/plan-format.md`,
  `skills/writing-plans/SKILL.md`, `skills/xia2/SKILL.md`,
  `skills/feature-intake/SKILL.md`, `scripts/render_skill_prompt.py`,
  `scripts/test_render_skill_prompt.py`, `templates/SUMMARY.template.md`
- **Upstream repositories or pages checked:** none found; the repository-owned pattern is sufficient
- **Official docs domains or pages checked:** none (local-only; no external surface)

## Evidence Boundary

> Confirmed from artifacts: the two writers lack explicit Reads; the plan writer and context matrix
> provide a reusable pattern; the scope exclusions already exist. Inferred from patterns: two new
> matrix entries are sufficient delivery proof. Not checked: full ASD-STE100 conformance and
> behavioral impact on long-form artifacts.

