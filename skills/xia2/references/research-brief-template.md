# Research Brief Template

Use this template as the output contract for every xia research session. Fill every section with evidence — do not leave sections empty if evidence exists.

---

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
| Important constraints | _from CLAUDE.md, AGENTS.md, or .claude/rules/_ |

---

## Feature Understanding and Assumptions

- **Requested feature:** _what the user asked for_
- **What success appears to mean:** _observable outcome when done_
- **Assumptions from the request:** _what I took as given_
- **Assumptions still needing confirmation:** _what would change the recommendation if wrong_

---

## Evidence Ledger

_Highest-signal evidence only. Label every item._

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
- **Follow-up questions for the user:** _(max 2 targeted questions — not open-ended)_

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
