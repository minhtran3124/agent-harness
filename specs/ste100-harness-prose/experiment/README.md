# Phase 2 pilot runner

This folder holds the pilot for the ste100-harness-prose spec. The pilot compares the original
text of three harness files with the STE rewrite of the same files. The pass rule comes from
`specs/ste100-harness-prose/design.md`, section "Phase 2 — pilot".

## Files

| File | Content |
|---|---|
| `pilot.py` | The runner and the scorer. Run `--help` for all flags. |
| `probes.json` | 8 questions for each pilot file. Each question has one short gold answer and one or more `accept` patterns. |
| `intake-fixtures.json` | 8 change requests with gold `Lane`, `Confidence`, and `Escalate` values. |
| `runs/smoke/` | The current smoke run: one real trial for each method. |
| `runs/smoke-v1/` | The first smoke run, before the fixture changes from the review. |

## Pilot files

- `rules/orchestration.md`
- `skills/feature-intake/SKILL.md`
- `skills/subagent-driven-development/SKILL.md`

## Method

Each trial runs in a new temporary directory. The runner copies the arm's file into that
directory. Then it starts the CLI with this command:

```text
claude -p --model sonnet --safe-mode --tools Read,Write --permission-mode acceptEdits \
  --output-format json --max-budget-usd 0.50 --no-session-persistence <prompt>
```

The `--safe-mode` flag disables project customizations. Thus the trial cannot load harness skills.
The prompt tells the agent to read the copied file.

- The `original` arm reads each file with `git show <base>:<path>`. You give `<base>` with `--base`.
- The `rewritten` arm reads the working tree.
- A **probe** trial gets one pilot file. It answers all 8 questions into `answers.json`.
- A **workflow** trial gets `skills/feature-intake/SKILL.md`, `harness-manifest.json`, and
  `rules/orchestration.md`, all from the same arm. It follows classification Steps 2–4 only. It
  writes `classification.json` for all 8 requests.
- The full run has 10 trials for each arm for each method for each file. That is 80 trials.

The model alias is `sonnet`. In the smoke run, the CLI resolved it to `claude-sonnet-5-5`.

The scorer reads the output file on disk only. It does not read the reply text. The runner keeps
a copy of each output file in `<output>/trials/<trial>/` and its text in `raw-results.jsonl`.

## Scoring

The unit is one scored answer. One arm of one method has 8 × 10 = 80 answers.

- A probe answer is correct when one `accept` pattern matches it and no `reject` pattern matches
  it. The match ignores case. The patterns look for the meaning, not for the exact words of the
  original file. The rewritten arm reads an STE rewrite, so its answers can use other words.
- A workflow answer is correct only when `Lane`, `Confidence`, and `Escalate` all match gold.
- A missing or unparsable output file makes all answers of that trial wrong.
- **Aggregate rule:** the rewritten arm must have at least the original arm's correct answers
  minus 2.
- **Meaning-change rule** (probes only): a probe fails when the original arm is right in 10 of 10
  trials and the rewritten arm is right in 7 or fewer.
- A file fails when one rule fails. `skills/feature-intake/SKILL.md` must pass both methods. The
  other two files pass on probes alone.
- A file that has no trials in an arm fails with `missing <method> <arm> arm`.
- The thresholds are for 10 trials in each arm. Any other trial count fails the file with
  `unequal trials`. The scorer does not change the thresholds for other counts.
- Some probes have `accept_examples` and `reject_examples`. An accept example is a correct
  answer in other words. A reject example is a wrong answer that looks almost correct. The
  selftest makes sure that each accept example scores right and each reject example scores wrong.

The scorer prints one verdict line for each file: `<path>: PASS` or `<path>: FAIL (<rule>)`.

## Budget

Each trial has a cap of $0.50. The pilot has a cap of $25. The smoke spend counts toward the
pilot cap. The runner reads it from each `runs/smoke*/raw-results.jsonl`. Before each batch, the runner
adds the spend so far and $0.50 for each trial in the batch. When this sum is more than $25, the
runner stops and prints `budget stop`.

## Commands

```text
python3 pilot.py --selftest
python3 pilot.py --dry-run --base HEAD --output /tmp/ste-pilot-dry
python3 pilot.py --smoke --base HEAD --output runs/smoke
python3 pilot.py --base <pilot base sha> --output runs/pilot-1
python3 pilot.py --score-only --output runs/pilot-1
python3 pilot.py --check-parse --output runs/pilot-1
python3 pilot.py --check-decision ../DECISION.md --output runs/pilot-1
```

## Smoke result

- Date: 2026-10-14. CLI: `2.1.299 (Claude Code)`. Base: `HEAD` at that time,
  `a4d596f1f2bb7fe3863ac6bb69b6c656dfabf8a0` (also in `runs/smoke/protocol.json`).
- In smoke mode, both arms read `git show <base>:`. Thus the smoke does not use the parallel edits
  in the working tree.
- Each smoke run has two trials: one probe trial for `skills/feature-intake/SKILL.md` and one
  workflow trial.
- The smoke ran two times. `runs/smoke-v1/` is the first run. `runs/smoke/` is the second run.
  The second run was necessary because the review changed fixture R8.
- In both runs, both output files parsed. The probe trial got 8 of 8. The workflow trial got
  8 of 8. In the second run, R8 got its gold values: high-risk, high, no.
- Cost of the first run: $0.0229 + $0.0713 = $0.0943.
- Cost of the second run: $0.0193 + $0.0698 = $0.0892.
- Total smoke cost: $0.1835. This counts toward the $25 pilot cap.
- The A1 fallback was not necessary.

The smoke verdict lines show `FAIL (missing ...)`. This is correct, because the smoke has no
rewritten arm. The smoke checks that the method works. It does not judge a file.

## Notes for Task 2.2 and Task 2.3

- Task 2.2 records the pilot base sha here. Then it checks each gold answer against the three
  files at that sha.
- In the full run, the rewritten workflow arm also reads `harness-manifest.json` from the working
  tree. Do not change the manifest between the pilot base and the run.

## Pilot base

- Pilot base: `0cc7ab7` (`0cc7ab7f4b9e99a604faea546c71b2dd1540acfe`). Task 2.2 recorded it before
  it edited a pilot file. Use `--base 0cc7ab7` for the full run.
- Gold check: Task 2.2 checked all 24 gold answers against the three files at `0cc7ab7`. Each
  gold answer still matches the base text. No gold answer changed.
- Probe fixes from the Task 2.1 review:
  - F6: the accept pattern now has word boundaries: `\b(stop|halt|block|wait|escalat|ask)\w*\b`.
    The `\w*` suffix keeps "stops" and "escalates" correct. Two new reject patterns catch
    `without (ask|stop|wait|escalat)` and a "proceed" answer that has no stop word. New reject
    examples: "proceed without asking a human", "ask the user and proceed", "run the task list".
  - S5: both accept patterns now need `task` before "first commit". A new reject pattern catches
    "branch's first commit". New reject examples: "the commit before the branch's first commit",
    "the parent of the branch's first commit".
- Selftest after the fixes: `selftest: 124/124 passed`.
