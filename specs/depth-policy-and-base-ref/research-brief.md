# Research Brief — depth-policy-and-base-ref

**Depth: Deep** (intake lane `high-risk` → Deep per `rules/research-depth.md`). No later upgrade.

**External surface: none.** No dependency added or upgraded, no external system integrated, no
version-specific API relied upon. The change edits one policy document and two in-repo build
files. Under the corrected Coverage rule this brief therefore carries broad local mapping and
explicit risk analysis, and records an empty Source Pack explicitly rather than by omission.

---

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing — scope the policy to what is checkable; repair the check that already exists |
| **Why this is the lightest credible path** | Both defects are unenforced assertions; neither needs new machinery, and the proposed new machinery could not enforce them honestly. |
| **Confidence** | 90% |
| **Next step** | Apply the two edits, prove the lint fires with a resolved base, ship. |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | tooling / meta-repo (skill + governance framework, no application stack) |
| Primary language + runtime | Bash + Python 3 (`scripts/*.py`, `hooks/*.sh`) |
| Frameworks / platforms | GitHub Actions (`harness-ci.yml`), pytest |
| Relevant packages | none — stdlib only |
| Detectable versions | `actions/checkout@v4`, `actions/setup-python@v5` |
| Important constraints | `CLAUDE.md` gate-verifiability tiers; `harness-manifest.json` gate modes (2 warn / 7 block parity, CI-guarded); `techstacks/` is empty by design |

---

## Feature Understanding and Assumptions

- **Requested feature:** correct `rules/research-depth.md` so its Coverage requirement matches
  real work, and fix the dead base-ref in the verify-row lint — both on one branch.
- **What success appears to mean:** the depth policy states a requirement that can actually be
  satisfied and observed; the verify-row lint executes instead of skipping.
- **Assumptions from the request:** the two changes ship together as one PR; the user's two
  `AskUserQuestion` selections pin the variant of each.
- **Assumptions still needing confirmation:** none material — both forks were resolved
  explicitly at intake.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | 21 `specs/*/research-brief.md` measured: 19 cite zero URLs; 13 declare Standard/Deep, 12 of those cite nothing. Only 5 contain a `## Source Pack` section. |
| `Local` | No script or hook reads `research-brief.md` — `grep -rn "research-brief" scripts/ hooks/ settings.json` returns empty. The xia2 template's Evidence Ledger / Source Pack / Evidence Boundary sections are unenforced. |
| `Local` | `origin/main` does not resolve: the only remote is `github` (`git remote -v`). |
| `Local` | Base = `main` yields 36 changed spec files and 7 pre-existing lint violations; base = `simplify` (the real PR base) yields 0. Guessing a branch name is therefore actively harmful, not merely imprecise. |
| `Local` | `ci-strict-gate.sh` always receives an explicit base from `harness-ci.yml:55`, so its `origin/main` default affects local invocation only. |
| `Local` | Gap B is shipped (`templates/SUMMARY.template.md:75`, `verify_summary.py:250-305`); Gap C is shipped (`CLAUDE.md:63-67`). |
| `Provenance` | CI log for run `31239698394` prints `skip — no python3 or no origin/main ref` on **both** ubuntu-latest and macos-latest — the lint has never executed. Re-derived from the actual run, not inferred from the script. |
| `Inference` | `actions/checkout@v4` default `fetch-depth: 1` is why the CI ref is absent; corroborated by the CI log skip, not by reading the action's source. |
| `Docs` | none — no external surface. |

---

## Local Findings

- **Relevant files:** `rules/research-depth.md`, `scripts/run-tests.sh:32-46`,
  `.github/workflows/harness-ci.yml:19`, `scripts/check_verify_rows.py`,
  `scripts/ci-strict-gate.sh:30`, `skills/xia2/references/research-brief-template.md`.
- **Existing abstractions or extension points:** the warn-first rollout pattern
  (`REQUIRE_NOT_AUTO_VERIFIED`, `REQUIRE_SCRIPTS_PROOF`) and the changed-files scoping model
  shared by `run-tests.sh` and `ci-strict-gate.sh`.
- **Conventions worth preserving:** every gate declares `Verifies:` / `Does not verify:`; gates
  claim exactly one evidence tier; parity guards (`check_gate_modes_smoke.py`,
  `lint-doc-truth.sh`) must stay green.
- **What can likely be reused:** the xia2 template already defines Source Pack — the policy only
  needs to say when it must be non-empty. No new artifact shape.
- **What appears missing locally:** nothing that this change should add. A `check_research_brief.py`
  is deferred deliberately (see SUMMARY Alternatives).

---

## Upstream Findings

Not applicable — no external surface. No upstream implementation is being modelled; both files
are repo-local governance artifacts with no counterpart elsewhere.

---

## Docs Findings

Not applicable — no external surface. No dependency version, external API, or third-party
behaviour is load-bearing for this change. The one inferred third-party behaviour
(`actions/checkout` default depth) was confirmed empirically from CI output instead, which is
stronger evidence than the documentation would have been.

---

## Recommendation

- **Primary recommendation:** reuse existing — narrow the policy, repair the check.
- **Why this is the lightest credible path:** the failure in both cases is an assertion nobody
  verifies. Adding a verifier for the depth policy before correcting the policy would pin a gate
  to a requirement that 12 of 13 briefs already ignore.
- **Why the next-best alternative lost:** the `sources.json` + `quote ⊆ evidence` design compares
  two agent-authored strings, so it passes precisely when the model hallucinated. It would be the
  first gate here to claim a tier above what it delivers.
- **What would change this recommendation:** if external-surface work became common in this repo,
  `check_research_brief.py` becomes worth its ~150 lines.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:** turning the lint on exposes latent violations in newly-changed specs; the
  base-ref choice determines the blast radius, which is why branch-name guessing was rejected.
- **Evidence gaps:** `fetch-depth: 0` fixing CI is verified only at traceability tier until this
  PR's own CI run executes.
- **Version uncertainties:** none.
- **Follow-up questions:** none — both forks resolved at intake.

---

## Source Pack

- **Local files read:** `rules/research-depth.md`, `skills/xia2/SKILL.md`,
  `skills/xia2/references/research-brief-template.md`, `scripts/run-tests.sh`,
  `scripts/ci-strict-gate.sh`, `scripts/check_gate_modes_smoke.py`,
  `scripts/check_slim_surface.py`, `scripts/lint-doc-truth.sh`, `scripts/verify_summary.py`,
  `templates/SUMMARY.template.md`, `harness-manifest.json`, `CLAUDE.md`,
  `.github/workflows/harness-ci.yml`, all 21 `specs/*/research-brief.md`.
- **Upstream repositories or pages checked:** `- none (local-only; no external surface)`
- **Official docs domains or pages checked:** `- none (local-only; no external surface)`

---

## Evidence Boundary

> **Confirmed from artifacts:** the URL/depth counts across all 21 briefs; the absence of any
> reader of `research-brief.md`; the absence of an `origin` remote; the 36-vs-0 changed-file
> measurement; the CI log showing the lint skipping on both runners.
>
> **Inferred from patterns:** that `actions/checkout@v4`'s shallow default is the specific cause
> of the CI-side skip (the log proves the skip, not its mechanism); that 19/21 local-only briefs
> reflect the nature of this repo's work rather than research that should have happened.
>
> **Not checked:** whether the 12 Standard/Deep briefs citing nothing were *correct* to cite
> nothing — the count measures behaviour, not whether the behaviour was right. Whether consumer
> repos of this harness have external-surface work often enough that the loosened policy costs
> them signal.
