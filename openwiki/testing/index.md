# Files

- [Behavioral Evals](behavioral-evals.md) - How the evals/ tree measures the judgment of prompt-driven skills and agents (review chain, test-runner, feature-intake classifier, context-boundary delivery, prompt-refactor corpus) with labeled fixtures, blind model runs, deterministic scorers, and strict claim discipline, and which parts run in CI versus by hand.
- [Deterministic Test Suite](test-suite.md) - How scripts/run-tests.sh runs the harness's deterministic tests (L1 syntax and lints, L2 hook contract tests, L3 script integration tests, then pytest), how tests/lib.sh builds hermetic throwaway git repos for hook tests, and how to add tests and fixtures.
