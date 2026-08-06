# Task-review evaluation corpus

Each fixture has an `input.md` passed to reviewers and a `truth.json` used only by the scorer.
The runner never reads `truth.json` into a model prompt. `baseline.json` preserves the first run
of the retired dual-review shape; `candidate.json` preserves the first run of the consolidated
reviewer under the same environment. Do not overwrite either file to improve a score.
