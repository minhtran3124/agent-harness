# Diagnosing bugs — phase techniques

Read this file during Phases 1 to 4 of the `diagnosing-bugs` skill.
Each list is a menu, not a checklist. Use the first item that fits the bug.

## Phase 1 — loop techniques, in preference order

A good loop is fast, deterministic, and runs without a human. Try these in order:

1. **A test.** Run an existing test that fails on the bug, or write one new failing test.
2. **A command with fixed input.** Call the script or CLI with the input that shows the bug.
   Compare its output or exit code with the value that the user expects.
3. **A request to a local service.** Send one HTTP request to a local server and compare the
   response.
4. **A replay.** Feed a captured input, log, or trace back into the code that failed.
5. **A throwaway harness.** Write a short script that calls the failing unit directly.
   Put it outside the source tree, or delete it in Phase 4.
6. **A headless browser.** Drive the page with a script when the bug is only visible in a
   browser.
7. **A repeat loop.** Run an intermittent failure many times. Record the failure rate as the
   red signal.
8. **A bisect loop.** When a known-good commit exists, let `git bisect run` drive the loop.
9. **A differential loop.** Run the same input through a known-good version and the current
   version. Compare the two outputs.
10. **A human-in-the-loop script.** Use this only when a human must act. Copy
    `hitl-loop.template.sh` from this skill's `scripts` folder (SKILL.md Phase 1 gives the full path). Replace its example steps with
    `step` and `capture` calls for this bug.

Make the loop deterministic before you trust it:

- Fix each random seed.
- Fix the clock, or inject the time.
- Remove network calls that the bug does not need.
- Run the loop three times. Each run must give the same result.

## Phase 2 — minimisation tactics

- Delete one input element at a time. Run the loop after each deletion.
- When the input is large, delete half of it. Keep the half that still fails.
- Replace each remaining value with the simplest value that still fails.
- Remove configuration, flags, and environment variables one at a time.
- Lower concurrency to one worker when the bug does not need more.
- Stop when each remaining element is necessary.

## Phase 3 — hypothesis patterns

- Rank the hypotheses by likelihood first, then by the cost of a probe.
- Write a prediction for each hypothesis. A prediction states what a probe shows when the
  hypothesis is true.
- Spread the hypotheses across layers: input, state, environment, dependency version, and
  timing.
- Include one hypothesis about a recent change. Read `git log` for the files near the symptom.
- Make each pair of hypotheses give different predictions. Two hypotheses with the same
  prediction cannot be told apart by a probe.

## Phase 4 — probe patterns

- Log one value at a boundary, for example a function input or a return value.
- Add a temporary assertion for an invariant that the hypothesis says breaks.
- Change one variable: an environment variable, a flag, an input value, or a dependency
  version.
- Run the loop after each probe. Record the result next to its prediction.
- Use one tag for the whole diagnosis. A tag is `[DEBUG-` plus four hex characters and `]`.
- A probe that refutes its hypothesis is a result. Record it.
