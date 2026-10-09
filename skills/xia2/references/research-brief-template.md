# Research Brief Template

Use this template as the output contract for every xia research session. Fill every section with evidence — do not leave sections empty if evidence exists.

---

The output document starts with this skeleton, the title and then the provenance header:

```text
# <slug> — Research Brief

Written <YYYY-MM-DD>. Pins: <repo short sha the claims were checked against; tool or dependency versions they depend on, if any>
```

- The `Written` line is the first non-blank line after the title. `Written` is the date the
  document was first written.
- `Pins` names at least the repository short sha the claims were read at. For claims read from
  uncommitted work, pin `HEAD` and append `+ uncommitted`. Add tool or dependency versions only
  when a claim depends on them.
- `Pins` names what the claims rest on. It does not replace the `Repo Snapshot` table, which stays
  the inventory of detected versions.
- A revision keeps every earlier line and appends `Revised <YYYY-MM-DD>. Pins: <…>` directly after
  the last header line, so the lines read oldest first. Earlier lines are never edited.
- Examples: `Written 2026-10-09. Pins: repo 8af66dd; Codex CLI 0.147.0` and
  `Revised 2026-10-12. Pins: repo 3c4d5e6 + uncommitted`.

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | _reuse existing / use built-in / adapt upstream / build from scratch_ |
| **Why this is the lightest credible path** | _one sentence_ |
| **Confidence** | _0–100%_ |
| **Next step** | _specific action for the user or implementer_ |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | _web app / API / CLI / library / monorepo / etc._ |
| Primary language + runtime | _e.g., Python 3.12_ |
| Frameworks / platforms | _e.g., FastAPI 0.115, SQLAlchemy 2.0_ |
| Relevant packages | _packages directly related to the feature_ |
| Detectable versions | _from manifests or lockfiles_ |
| Important constraints | _from CLAUDE.md, AGENTS.md, or rules/_ |

---

## Feature Understanding and Assumptions

- **Requested feature:** _what the user asked for_
- **What success appears to mean:** _observable outcome when done_
- **Assumptions from the request:** _what I took as given_
- **Assumptions still needing confirmation:** _what would change the recommendation if wrong_

---

## Evidence Ledger

_Highest-signal evidence only. Label every item._

_Number labels complement these source labels: the source label says where a fact came from, the
number label says whether a number was observed. A number is **load-bearing** when a decision,
target, threshold or Success Criterion depends on it; each value of one carries exactly one label —
`prediction` (an estimate not yet measured), `budget` (a limit we chose) or
`measured <YYYY-MM-DD> <source>` (a value observed). When a measurement replaces a prediction, keep
the prediction with its label and append the measurement beside it. Illustrative numbers stay
unlabelled._

| Label | Evidence |
|---|---|
| `Local` | |
| `Upstream` | |
| `Docs` | |
| `Inference` | |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:**
- **Existing abstractions or extension points:**
- **Conventions worth preserving:**
- **What can likely be reused:**
- **What appears missing locally:**

---

## Upstream Findings

_(Standard + Deep only. Skip if Quick mode.)_

- **Repositories inspected:**
- **Pattern or capability already present upstream:**
- **Files, modules, or areas worth modeling:**
- **How closely the upstream pattern matches this repo:**
- **Any upstream gaps or uncertainties:**

---

## Docs Findings

_(Standard + Deep, and only when the change has an external surface — it adds or upgrades a
dependency, integrates an external system, or relies on a version-specific API. With no external
surface, say so here in one line rather than deleting the section.)_

- **Official sources checked:**
- **Version-matched vs latest-stable status:**
- **Built-in capabilities that already support the feature:**
- **Current recommended APIs or workflows:**
- **Important caveats, deprecations, or migration notes:**

---

## Recommendation

- **Primary recommendation:** _reuse existing / use built-in / adapt upstream / build from scratch_
- **Why this is the lightest credible path:** _specific reasoning with evidence pointers_
- **Why the next-best alternative lost:** _what ruled it out_
- **What would change this recommendation:** _the condition that would flip the decision_

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
- **Evidence gaps:**
- **Version uncertainties:**
- **Follow-up questions for the user:** _(only questions whose answer would change the recommendation)_

---

## Source Pack

_Never leave a line blank. An empty Source Pack cannot be told apart from research that was
skipped. The two "nothing to report" answers are **not** interchangeable:_

- `- none found` — the search ran and returned nothing.
- `- none (local-only; no external surface)` — the search did not apply, because the change has
  no external surface (see `rules/research-depth.md` §Coverage).

_Only **official docs** is gated by external surface. Upstream search stays unconditional at
Standard/Deep, so its line takes `- none found`, never the not-applicable form._

- **Local files read:** _list paths_
- **Upstream repositories or pages checked:** _list URLs, or `- none found`_
- **Official docs domains or pages checked:** _list URLs, `- none found`, or `- none (local-only; no external surface)`_

---

## Evidence Boundary

_State explicitly what is confirmed vs inferred:_

> Confirmed from artifacts: [list]
> Inferred from patterns: [list]
> Not checked: [list — be honest about gaps]
