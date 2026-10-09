# gh-258-provenance-reading-path — Design

Written 2026-10-09. Pins: repo 8af66dd (spec-format after #274).

Issue #258 items 6 and 7. Intake: `specs/gh-258-provenance-reading-path/SUMMARY.md` (high-risk, medium).

## Goal

Every design and research brief says when it was written and which state of the repository its
claims were checked against (item 6). A multi-document spec can state its reading order and walk
one request end to end (item 7). The isolated design reviewer checks the header, and checks the
optional sections only when they are present.

## Current state

- `skills/brainstorming/references/design-template.md` is the output contract for `design.md`.
  The isolated design reviewer reads it (registered in `CONTEXT_MATRIX` in batch 1, PR #260).
  `skills/brainstorming/spec-document-reviewer-prompt.md` holds the reviewer's check table.
- `skills/xia2/references/research-brief-template.md` is the output contract for
  `research-brief.md`. No reviewer checks a research brief.
- Neither template carries a date or a pin. Some specs have a free-text line instead:
  `**Evidence refreshed:** 2026-08-10` (`specs/codex-support/design.md:6`,
  `specs/codex-support/research-brief.md:6`).
- `docs/solutions/` entries carry `confirmed_at` with a 30-day staleness rule, as stated in
  CLAUDE.md.
- `tests/scripts/brainstorming-contract.test.sh` pins the template and reviewer anchors with
  `has_all`. `tests/scripts/research-depth-drift.test.sh` pins the external-surface keywords in
  the research-brief template; the new header text must not disturb them.

## Approaches considered

1. **Template plus a reviewer check (chosen).** The templates gain the header and the optional
   sections, and the design reviewer gains two check rows. This is the same mechanism batch 1
   used: the reviewer loop that already runs keeps the new sections real, and no new gate is
   added.
2. **Template prose only.** This is the literal reading of "template prose" in the rollout table.
   It was rejected because `rules/terminology.md` §2 measured that wording alone does not hold a
   step under pressure.
3. **Approach 1 plus a staleness script.** Rejected: #258 calls the staleness check "optional" and
   "later", and it would touch `scripts/`.

## Architecture

### 1. Provenance header (item 6), in both templates

Neither template shows a document title today: each goes straight from its own instructions to
the first `##` section. Each template gains a short **document skeleton** block, placed before
the first section (`## Goal` in the design template, `## Bottom Line` in the research-brief
template). The block shows the title and the header line together:

```text
# <slug> — Design            (research brief: # <slug> — Research Brief)

Written <YYYY-MM-DD>. Pins: <repo short sha the claims were checked against; tool or dependency versions they depend on, if any>
```

- The skeleton sits inside a fenced block, introduced by one line saying it is the start of the
  output document, so an agent does not copy the template's own `# Design Template` title.
- The header is the **first non-blank line after the H1 title**.
- `Written` is the date the document was first written.
- `Pins` names at least the repository commit (short sha) the claims were read at. If they were
  read from uncommitted work, pin `HEAD` and append `+ uncommitted`. Add tool or dependency
  versions only when a claim depends on them, for example `Codex CLI 0.147.0`. In a research
  brief, `Pins` names what the claims rest on. The `Repo Snapshot` table stays the inventory of
  detected versions, and the two are not merged.
- A later revision keeps every earlier line and appends `Revised <YYYY-MM-DD>. Pins: <…>` directly
  after the last header line, so the lines read oldest first. Earlier lines are never edited.
  This keeps the history visible, as item 4 does for numbers.

Both templates carry the same wording, with two examples:
`Written 2026-10-09. Pins: repo 8af66dd; Codex CLI 0.147.0` and
`Revised 2026-10-12. Pins: repo 3c4d5e6 + uncommitted`.

### 2. Optional sections (item 7), design template only

- `## Reading path`: placed directly after `## Goal`. It is only for a spec with more than two
  documents (budget, taken from #258). It lists the documents in reading order, each with one line
  on why it comes at that point and what the reader can skip.
- `## Worked trace`: placed directly after `## Architecture`. It follows one concrete request
  through the components the design names, from start to end, to show the hand-offs between
  layers.

Both sit in the free-form part of the template, before `Non-goals`, so the template's existing
split stays intact: free-form sections up to `Non-goals`, then the three required sections. The
template's opening paragraph names them as optional. When a design does not use one, the section
is left out rather than filled with `- none`.

### 3. Reviewer checks

Two rows in `skills/brainstorming/spec-document-reviewer-prompt.md`:

| Category | What to look for |
|---|---|
| Provenance header | The first non-blank line after the H1 title is not a `Written <YYYY-MM-DD>. Pins: <…>` line, the date is not `YYYY-MM-DD`, or `Pins:` is empty or a placeholder. A `Revised` line with any of the same defects, or `Revised` dates not in ascending order. `+ uncommitted` after the sha is valid. |
| Optional sections | `## Reading path` or `## Worked trace` present but holding placeholder text. An absent optional section is not an issue. |

The reviewer reads the template already, so its delivery needs no change.

## Error behavior

These are prose contracts, with no runtime. A missing or malformed header is reported by the
design reviewer as an Issue, and the spec-review loop blocks approval until it is fixed. A research
brief has no reviewer, so its header rests on the template alone. That limit is recorded below.

## Tests

`tests/scripts/brainstorming-contract.test.sh` gains fixed-string anchors:

- the design template carries `Written <YYYY-MM-DD>. Pins:`, `Revised <YYYY-MM-DD>. Pins:`,
  `## Reading path` and `## Worked trace`;
- the research-brief template carries `Written <YYYY-MM-DD>. Pins:` and
  `Revised <YYYY-MM-DD>. Pins:`;
- the reviewer prompt carries `Provenance header` and `Optional sections`;
- in each template's fenced skeleton block, the first non-blank line after the `# <slug> — …`
  title line is the `Written <YYYY-MM-DD>. Pins:` line. This is checked by line position rather
  than "anywhere in the file", so header text in the instructions alone cannot satisfy it.

`tests/scripts/research-depth-drift.test.sh` and `render_skill_prompt.py --check-all` must still
pass. Tier: traceability.

## Success criteria

- SC-1: both templates and the reviewer carry the anchors above (`brainstorming-contract.test.sh`).
- SC-2: the research-depth drift anchors in the research-brief template are intact
  (`research-depth-drift.test.sh`).
- SC-3: the isolated-prompt delivery contracts still hold (`render_skill_prompt.py --check-all`).

## Non-goals

- A staleness check or a lint script; no change to `scripts/` or `hooks/`.
- Rewriting existing specs to add headers or the new sections.
- A reviewer for research briefs.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | The isolated design reviewer receives and reads `design-template.md` | provenance: Local, 2026-10-09, `scripts/render_skill_prompt.py` `CONTEXT_MATRIX` design-reviewer entry (batch 1, PR #260); `--check-all` confirms the Read instruction is present (traceability), not that the reviewer follows it | SC-3 | the header and section rules would not reach the reviewer, and the checks would rest on the reviewer prompt alone |
| A2 | Adding header text to the research-brief template does not remove the drift-test keywords | none yet: Inference, 2026-10-09, the header adds text and deletes none | SC-2 | the drift test fails; reword the header without touching the pinned phrases |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| A research brief always carries the header | No reviewer checks research briefs; the template is the only carrier. |
| The pinned sha is the one the claims were actually checked at | The reviewer checks the format, not the truth of the pin. Traceability only. |
| Stale documents are flagged | The staleness check is out of scope (#258: optional, later). |
| `## Reading path` appears only in specs with more than two documents | The reviewer checks for placeholder content, not the document-count condition; a reading path in a smaller spec is harmless. |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | Header line `Written <YYYY-MM-DD>. Pins: <…>` as the first non-blank line after the H1 title of design and research-brief documents, shown in a skeleton block in each template | one grep-able line per document; placement is explicit in the templates | settled |
| D2 | A revision appends a `Revised <YYYY-MM-DD>. Pins: <…>` line after the last header line and never edits earlier lines | the date history stays visible, oldest first | settled |
| D3 | `## Reading path` (after `## Goal`; only for specs with more than two documents, budget from #258) and `## Worked trace` (after `## Architecture`) are optional free-form design-template sections, left out when unused | no `- none` filler; the free-form/required split is unchanged | settled |
| D4 | The design reviewer checks the header's presence and format, and checks the optional sections only for placeholder content | enforcement through the existing review loop; no new gate | settled |
