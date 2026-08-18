# Candidate iteration 1 — rejected

Date: 2026-07-29

The first consolidated-prompt candidate reduced reviewer dispatches from 14 to 7 and median
elapsed time from 24.84s to 14.60s. It failed the quality gate: `minor-only` treated the fixture's
complete evidence as unavailable and emitted `cannot_verify`/Important instead of the expected
Minor-only outcome. The raw first run is preserved in `candidate.json`; it was not overwritten.

Hypothesis: make the evaluation's evidence boundary explicit while preserving `cannot_verify` only
for fixtures that explicitly declare an unavailable external contract. Candidate iteration 2 tests
that change under the same model/client/reasoning settings.
