---
problem_type: knowledge
module: harness
tags: mutation-testing, vacuous-assertions, test-quality, review-oracle, regression-guard, harness-scripts, text-anchored-guards
severity: standard
applicable_when: Use this when a test suite is green and you are about to treat that as evidence — ask which assertions would actually fail if the guard they target were deleted.
affects:
  - tests/scripts/resync-conflict.test.sh
  - runtime/test_run_state.py
supersedes: null
confidence: high
confirmed_at: 2026-07-27
---
## Applicable When

You have a test suite (shell, integration, unit) and want to know whether its assertions guard behavior, or merely co-occur with it. "N passed" answers neither.

## Pattern

**Mutation-test the suite.** For each guard in the code under test, delete or invert it, then re-run the green suite and count how many assertions turn red.

- A mutant that kills **zero** assertions exposes a **vacuous** test — one that cannot fail, and therefore manufactures confidence.
- The kill count per mutant tells you which behaviors are actually pinned.

Pair it with a review question that is cheap to ask and hard to fake: *"would this assertion FAIL if the guard it targets were deleted?"* Ask it per assertion, not per suite.

## How to Use

In this session an independent reviewer applied that question to 18 assertions and found **4 vacuous** — including the two pinning the single most important hazard (the `curl | bash` stdin contract). One of them could not fail because the code path it claimed to test was never reached; another never grepped for the warning text it claimed to assert.

After tightening (commit `8e72f7f`), four mutants were run against the suite and each recorded with its exact kill count:

| Mutant | Assertions that fail |
|---|---|
| `is_protected()` forced to return false — the whole feature deleted | 6 |
| stale-sidecar cleanup (`rm -f <file>.harness-incoming`) removed | 2 |
| `have_tty()` reverted to the broken `[ -r /dev/tty ]` | 1 |
| a shipped `*.proposed` re-added to the source | 1 |

Record the kill counts in the `### Verify` table of `specs/<slug>/SUMMARY.md`, with the mutation as the "command" and exit 1 as the expected result. A mutation row is stronger evidence than a passing row: a passing row says the code works today, a mutation row says the test will notice when it stops.

Mutate by editing the file in place, running the suite, then `git checkout -- <file>`. Confirm the tree is clean afterward.

## Gotchas

- **Label non-load-bearing assertions explicitly.** Baseline sanity checks (e.g. "a first install writes no sidecar") cannot fail even with the feature deleted. Leave a comment saying so, or a future reader counts "22 passed" as 22 guarded behaviors. This suite marks case 1 and case 9 as baselines in-file.
- **A regression test can pin the wrong thing.** The `[ -r /dev/tty ]` bug was caught only because an assertion checked the *warning text*, not just "rc 0 and the file survived". Outcome assertions pass under a safe-by-accident code path; message assertions do not.
- **Some contracts are structurally untestable today** and should say so rather than pretend. The stdin-sentinel assertion here cannot fail while `have_tty()` returns false, because deploy never reaches `read` at all — its comment now states precisely what it pins (a future bare-`read` regression) and what it does not prove.
- **A text-anchored assertion goes vacuous the moment you widen its slice** (2026-07-27, `runtime/test_run_state.py`). A guard that read a table out of `skills/subagent-driven-development/SKILL.md` was anchored between a heading and a *sentence*; a later edit reworded that sentence, so the test errored. The obvious repair — widen the slice to the whole section — made it **pass while asserting nothing**, because the surrounding prose also mentions every state it was checking. Only re-running the mutation caught it. Fixes that generalize: anchor on structure (parse the table's `|` rows) rather than on prose, assert a minimum row count so a parse-to-zero fails loudly instead of trivially passing, and re-run the mutation after *every* edit to either side — the guard or the text it reads.
- **Membership is not executability.** In the same file, a guard asserted the documented successor states were *named* correctly; a documented route that the engine would reject with exit 2 still passed. Upgrading it to actually run each documented transition (and to assert the rejection case, so it cannot pass vacuously) turned a naming check into a behavior check — and a deliberately unreachable row then failed with `documented successor blocked -> shipped is not takeable`.

## Related

- `docs/solutions/harness/unverified-premise-propagates-through-plan-anchored-reviews.md` — the companion failure: a test that encoded a false premise as a comment and passed.
- `docs/solutions/scripts/test-r-dev-tty-does-not-detect-missing-controlling-terminal.md` — the bug whose regression test the `have_tty()` mutant validates.
