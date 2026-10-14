# Intent: A reusable runtime eval for the review prompts, with a bait fixture and a variance check

Author: Minh Tran
<!-- Set Status to approved or draft. Intake proceeds only on approved. -->
Status: approved

## Problem

The runtime A/B eval of the review prompts (PR #288, `specs/review-policy/runtime-eval.md`) ran from a script that
lives in a session scratchpad, so it cannot be re-run when a review prompt changes again. It also left two gaps:
no fixture measures whether the policy's do-not-report list suppresses style, naming and generated-file findings,
and every cell ran once, so a difference of one finding could not be told from noise.

## Proposed outcome

1. **A tested tool in `scripts/`** that runs the real review prompts of two git revisions on the planted-defect
   fixtures under identical conditions and reports the comparison. It does what the scratchpad driver did:
   builds each arm's prompts from that revision's own files, runs `claude -p` in a minimal Read-only environment
   with a per-call and a total budget cap, never overwrites a recorded result, and reports catches, false
   positives, parse rate, policy-Read rate and cost per arm (assumed).
2. **Bait fixtures** in `evals/skills/review-chain/fixtures/` whose diff holds one real bug plus bait the
   do-not-report list should keep out: style and naming nits, and a change to a generated file (assumed). The
   scorer counts a reported bait item as a false positive.
3. **A variance check**: re-run the `minor-only` task-review fixture several more times in both arms, using the
   new tool, and record the attempts next to the first run without changing it (assumed: 5 further attempts per
   arm).

## Affected users and systems

- Maintainers who change a review prompt or rule and want runtime evidence (assumed).
- `scripts/`, `evals/skills/review-chain/`, and the eval README (assumed).
- `bash scripts/run-tests.sh`, which runs `score_review_chain_eval.py --check-truth` on the real fixtures (assumed).

## Constraints

- The tool's tests make no model call: they use a stub `claude` executable (assumed).
- The tool is manual and is not wired into CI, because it needs an authenticated client and costs money (assumed).
- A first-run result is never overwritten or rerun to turn a miss into a pass; later attempts are recorded separately.
- Each arm's prompts come from that revision's own files; a test proves the base arm cannot receive head-only text (the `--root` pitfall found in the first run) (assumed).
- New fixtures pass `--check-truth`, and the existing scorer and tests keep passing unchanged (assumed).
- No change to any review prompt, rule, skill or agent (assumed).

## Out of scope

- Changing what the review prompts say, or the policy (assumed).
- A significance test or an effect-size claim; the variance check only reports counts (assumed).
- Running the full 116-call comparison again (assumed).
- E2 (deny messages), which has its own pending intent (assumed).

## Open questions

- Q1. Tool name and shape. Proposed: one script `scripts/run_review_prompt_eval.py` plus `scripts/test_run_review_prompt_eval.py` (assumed).
- Q2. Number of further `minor-only` attempts. Proposed 5 per arm, about $0.4 in total (assumed).
- Q3. Whether bait fixtures may carry a real bug, as the scorer requires a planted defect (assumed: yes, one real bug plus bait per fixture).

## What success looks like

- `python3 -m pytest -q scripts/test_run_review_prompt_eval.py` passes with no model call (assumed).
- `python3 scripts/score_review_chain_eval.py --check-truth evals/skills/review-chain/fixtures` passes with the bait fixtures included (assumed).
- A real run of the tool on the bait fixtures and the `minor-only` repeats records its results under `specs/review-prompt-eval-tool/` (assumed).
- `bash scripts/run-tests.sh` stays green (assumed).

## Original request

"làm cả 3" — a reply to the three follow-ups listed at the end of the runtime eval report
(`specs/review-policy/runtime-eval.md`, §Follow-ups):

1. Promote the driver into a tested `scripts/` tool, so the A/B can be re-run on any later prompt change. Today it lives in the session scratchpad.
2. Add a style-and-generated-file bait fixture so the do-not-report list is measured.
3. A second attempt on the discordant cells (`minor-only`) if variance matters for a decision.
