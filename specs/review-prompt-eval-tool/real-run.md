# review-prompt-eval-tool — Real validation run

Written 2026-10-12. Pins: repo 339250c (the tool), arms 33d6ed4 (base) and 0bd1ae6 (head)

First real use of `scripts/run_review_prompt_eval.py`, covering the two follow-ups the first runtime eval
(`specs/review-policy/runtime-eval.md` on PR #288) left open: a fixture that measures the policy's do-not-report
list, and a variance check on the one discordant cell. Per-call records: `real-run-results.json`.

## Method

Base is `33d6ed4` (before the review policy); head is `0bd1ae6`, the tip of `feat/review-policy`, whose prompts are
identical to `f23e4ac`, which the first run used (`git diff f23e4ac 0bd1ae6 -- rules skills agents` is empty). Same
model (`claude-opus-5-5`), effort (`medium`), safe-mode, Read-only tools and per-call budget as the first run.
The tool ran 38 calls in two sets of runs and recorded every result once: no call was rerun and none failed.

1. **Bait.** The six finder angles and the intent reviewer on the two new fixtures `bait-style-naming` and
   `bait-generated-file`, in both arms: 28 calls, $2.58.
2. **Variance.** `minor-only` of the task-review fixtures, task reviewer, attempts 2 to 6 in both arms: 10 calls,
   $0.37, run as five invocations into one directory (the cap is shared, so each invocation reported the money
   already recorded).

Total cost $2.95.

## Results

### Bait (attempt 1, one run per cell)

| | Base | Head |
|---|---|---|
| Planted bug caught (2 fixtures) | 2/2 | 2/2 |
| Calls that Read `rules/review-policy.md` | 0/14 (file absent at base) | 14/14 (finders 12/12, intent 2/2) |
| Parseable JSON block | 14/14 | 14/14 |
| Findings reported against the generated file `specs/demo/PLAN.html` | 3 (2 scored false positives, 1 `other`) | 0 |
| Findings reported against `uv.lock` | 0 | 0 |
| Style, naming or formatting findings on `bait-style-naming` | 0 | 0 |
| False positives by the scorer (confidence ≥ 75) | 2 (0) | 0 (0) |
| Cost | $1.24 | $1.34 (+8%) |

The base arm's three `PLAN.html` findings are the same one: the page writes plan data through `innerHTML` without
escaping. All three came from the finders (enclosing-function, guard-completeness, stack-defects), were marked
`unmodified-line`, and carried confidence 25 to 30, so none would pass the scorer's threshold. The head arm
reported nothing on either generated file.

### Variance: `minor-only` (requires `minor`, forbids `spec_fail`)

| Attempt | Base | Head |
|---|---|---|
| 1 (first run, `runtime-eval.md`) | no (`spec_fail`) | yes |
| 2 | yes | yes |
| 3 | no (`spec_fail`) | yes |
| 4 | yes | yes |
| 5 | yes | no (`spec_fail`) |
| 6 | no (`spec_fail`) | no (`spec_fail`) |
| **Holds** | **3/6** | **4/6** |

The required label `minor` was present in all ten new runs; every miss is the forbidden `spec_fail`. In the five new
attempts both arms hold 3 of 5.

## What this shows

- **Generated-file suppression.** With the policy, the finders reported nothing about a generated file that the
  base prompts criticised in 3 of the 6 finder calls on that fixture. That agrees with the policy's do-not-report list working in
  fresh contexts. It is one run per cell on one fixture: three findings against none is a count, not a rate.
- **Style suppression: no signal.** Neither arm reported a style or naming finding on `bait-style-naming`. The base
  finder prompts already exclude style, so this fixture cannot show a policy effect; the policy changed no
  behavior there. This is a ceiling, not a failure.
- **Planted bugs.** Both arms caught both planted bugs, through several finder angles and the intent reviewer each.
- **The first run's `minor-only` difference is noise.** The fixture produces the forbidden `spec_fail` in about
  half the runs in both arms (base 3 of 6, head 2 of 6). The earlier 6/7 against 7/7 should not be read as an
  improvement.
- **The tool.** It ran to completion on real calls with no failed call, the shared cap behaved as documented, and
  `report` separated failed calls from outcomes (there were none to separate).

## What it does not show

- Variance of the bait results: attempt 1 only. A second attempt on the bait fixtures was not run.
- Anything beyond two fixtures. The patterns in each `truth.json` measure the bait they name; a generated-file finding
  worded without those terms would count as `other`.
- Calls had only a diff and no repository: the call-site-impact angle reported `unknown` for callers in both arms.
- The scorer stage, controller routing and Codex contexts, as in the first run.

## Follow-ups

1. A second attempt on the bait fixtures, if the generated-file result is to carry weight in a decision.
2. A one-line `isinstance` guard for a malformed stream-json `assistant` event (recorded in SUMMARY).
