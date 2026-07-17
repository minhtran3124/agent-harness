# Intake-Classifier Benchmark Run — <date> <label>

- **Measured skill:** `/feature-intake`
- **Skill commit sha:** `<sha the run measured>`
- **Date:** `<YYYY-MM-DD>`
- **Runner:** manual v1, blind subagents (see `../README.md`)

## Scorecard

<!-- paste the `score_intake_eval.py --run` output table here -->

| Fixture | Produced lane | Produced conf | Verdict | Notes |
|---|---|---|---|---|
| typo-fix | | | | |
| add-validation | | | | |
| multi-domain | | | | |
| auth-change | | | | |
| edit-hook | | | | |
| db-migration | | | | |
| ambiguous | | | | |

## Headline numbers

- **Lane accuracy:** `n/N` (fixtures asserting a lane)
- **Hard-gate respect:** `n/N` (must be N/N)
- **Confidence accuracy:** `n/N`
- **Fully-correct fixtures:** `n/7`

## Notes

- Misclassifications (plain): …
- Answer-key doubts (if any): …
- Scope reminder: measures only `/feature-intake` against these 7 fixtures — not other skills,
  not the full chain, not real-world rate (`not_observed != absent`).
