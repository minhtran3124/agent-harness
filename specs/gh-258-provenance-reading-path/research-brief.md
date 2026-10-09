# gh-258-provenance-reading-path — Research Brief

Written 2026-10-09. Pins: repo 8af66dd (spec-format after #274).

Depth: **Deep**, mapped from the intake lane `high-risk` per `rules/research-depth.md`. The
evidence found no reason to raise it. Design: `specs/gh-258-provenance-reading-path/design.md`
(approved 2026-10-09, D1–D4).

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Reuse existing: add text to two templates and two check rows to the existing design reviewer; extend the existing contract test. |
| **Why this is the lightest credible path** | The reviewer already reads the design template through `CONTEXT_MATRIX`, and the contract test already has `has_all` anchors for both templates and the reviewer. |
| **Confidence** | 90% |
| **Next step** | `writing-plans` for `specs/gh-258-provenance-reading-path/` |

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Harness meta-repo: Markdown skills and templates, bash tests |
| Primary language + runtime | Markdown and bash; no runtime code changes |
| Frameworks / platforms | none |
| Relevant packages | none |
| Detectable versions | n/a |
| Important constraints | The design template is a required Read of the isolated design reviewer (`CONTEXT_MATRIX`). The research-brief template's external-surface keywords are pinned by `research-depth-drift.test.sh`. Skill word ceilings do not apply to reference templates (`audit_skill_prompts.py` measures `SKILL.md` and companion prompts). |

## Feature Understanding and Assumptions

- **Requested feature:** #258 items 6 and 7, approved as design D1–D4.
- **What success appears to mean:** design SC-1 to SC-3.
- **Assumptions from the request:** D1–D4.
- **Assumptions still needing confirmation:** none.

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `scripts/render_skill_prompt.py` lines 41–45: the `spec-document-reviewer` context requires and Reads `design-template.md` (batch 1, PR #260). |
| `Local` | `skills/brainstorming/references/design-template.md` goes from its own `# Design Template` instructions straight to `## Goal`; its opening paragraph defines free-form sections up to Non-goals, then three required sections. |
| `Local` | `skills/xia2/references/research-brief-template.md` goes from `# Research Brief Template` to `## Bottom Line`. It has a `Repo Snapshot` table with "Detectable versions", and a Number-labels paragraph (batch 1). |
| `Local` | `skills/brainstorming/spec-document-reviewer-prompt.md` has a `| Category | What to Look For |` check table, which batch 1 extended with template, assumption, ID, number-label and decision rows. |
| `Local` | `tests/scripts/brainstorming-contract.test.sh` defines `TPL`, `REVIEWER`, `BRIEF` and `has_all`; `tests/scripts/research-depth-drift.test.sh` pins multi-word external-surface keywords in the research-brief template and a `## Docs Findings` check. |
| `Local` | Existing free-text provenance appears as `**Evidence refreshed:** 2026-08-10` in `specs/codex-support/design.md:6` and `research-brief.md:6`; `docs/solutions/` uses `confirmed_at` (CLAUDE.md). |
| `Upstream` | `tamnd/rupg` spec documents open with `Written 7 October 2026. Pins: PostgreSQL REL_19_STABLE at 7d3d2db7 …`, and `00-README.md` has "How to read this if you are short of time". Read in the #258 review, 2026-10-08. |

## Local Findings

- **Relevant files:** the two templates, the reviewer prompt, and the two contract tests named above.
- **Extension points:** the design template's opening paragraph and its free-form section list; the reviewer's check table; `has_all` in the contract test.
- **Conventions worth preserving:**
  - fixed anchor strings on one line;
  - the free-form/required split in the design template;
  - the research-brief template's pinned keywords, which must not be reworded.
- **What can be reused:** all of the above. Only text is added.
- **What is missing locally:** a document skeleton in either template, and any date or pin convention for designs and briefs.

## Upstream Findings

- **Repositories inspected:** `tamnd/rupg` `spec/` (header lines and reading path).
- **Pattern present upstream:** a dated provenance line naming exact pins; a short "read these first" path.
- **What to model:** a single-line header with a date and pins; a reading path only for multi-document specs.
- **How closely it matches:** close. rupg writes dates in long form; this repo uses `YYYY-MM-DD`, so headers stay grep-able and match `confirmed_at`.
- **Upstream gaps:** rupg has no revision convention, so D2 (append `Revised`) is local.

## Docs Findings

There is no external surface: no dependency, external system or version-specific API.

## Recommendation

- **Primary recommendation:** reuse the existing template, reviewer and contract-test machinery, adding text only.
- **Why this is the lightest credible path:** the delivery path (`CONTEXT_MATRIX`) and the test scaffolding already exist; nothing new needs wiring.
- **Why the next-best alternative lost:** template prose alone has no enforcement, as `rules/terminology.md` §2 measured. A staleness script is out of scope in #258.
- **What would change this recommendation:** a decision to enforce headers in research briefs too, which would need a reviewer or a lint.

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - An agent filling the template could copy the template's own `# … Template` title. The design mitigates this with a fenced skeleton and an introducing line.
  - Editing the research-brief template near the pinned keywords could break the drift test. Mitigation: add text only, and keep SC-2.
- **Evidence gaps:** whether reviewers actually catch a malformed header was not measured. It is traceability only.
- **Version uncertainties:** none.
- **Follow-up questions for the user:** none.

## Source Pack

- **Local files read:** `skills/brainstorming/references/design-template.md`, `skills/xia2/references/research-brief-template.md`, `skills/brainstorming/spec-document-reviewer-prompt.md`, `scripts/render_skill_prompt.py`, `tests/scripts/brainstorming-contract.test.sh`, `tests/scripts/research-depth-drift.test.sh`, `specs/codex-support/design.md`, `specs/codex-support/research-brief.md`, `rules/terminology.md`.
- **Upstream repositories or pages checked:** https://github.com/tamnd/rupg/tree/main/spec (`00-README.md`, document headers).
- **Official docs domains or pages checked:** - none (local-only; no external surface)

## Evidence Boundary

> Confirmed from artifacts: the reviewer's template delivery; both templates' current shape; the
> reviewer check table; the contract and drift test anchors; the existing free-text provenance.
> Inferred from patterns: that adding text only cannot break the drift keywords.
> Not checked: whether reviewers apply the new rows reliably.
