# Decision — STE rewrite of the three pilot files

Status: decided on measurement, 2026-10-14. This file closes OQ-1 in `QUESTIONS.md`.

## Result

All three pilot files pass. The pilot measured no accuracy loss from the STE rewrite on any pilot
file (one model, 10 trials per arm). The
rewritten files stay in place. The rollout (Phase 3) can start. Phase 3 planning needs the user.

Verdict lines, copied exactly from the scorer (`pilot.py --score-only`):

- `rules/orchestration.md: PASS`
- `skills/feature-intake/SKILL.md: PASS`
- `skills/subagent-driven-development/SKILL.md: PASS`

This result is "no worse". It is not evidence that STE makes agents more accurate. Most cells are
at the ceiling (see Limitations).

## Question

D2 and D6 in `design.md` say that the rollout of STE prose runs only after a pilot pass. The pilot
asks one question: does the STE rewrite of three harness files lower agent accuracy?

## Protocol

- Runner: `specs/ste100-harness-prose/experiment/pilot.py`. The method is in
  `experiment/README.md`. The pass rule is in `design.md`, section "Phase 2 — pilot".
- Pilot files: `rules/orchestration.md`, `skills/feature-intake/SKILL.md`,
  `skills/subagent-driven-development/SKILL.md`.
- Original arm: each file at the pilot base `0cc7ab7`
  (`0cc7ab7f4b9e99a604faea546c71b2dd1540acfe`), read with `git show`.
- Rewritten arm: the working tree at HEAD `87d204c`. The Task 2.2 rewrite commits are `f49a9d1`,
  `dc867ed` and `87d204c`.
- `harness-manifest.json` is the same at the base and at HEAD.
  `git diff --stat 0cc7ab7 HEAD -- harness-manifest.json` gave no output.
- Probes: 8 questions per file. Each trial answers all 8 into `answers.json`. 10 trials per arm per
  file.
- Workflow: the agent reads `skills/feature-intake/SKILL.md`, `harness-manifest.json` and
  `rules/orchestration.md` from one arm. It classifies 8 fixture requests into
  `classification.json`. An answer is correct only when `Lane`, `Confidence` and `Escalate` all
  match gold. 10 trials per arm.
- Each trial runs in a new temporary directory. The command is
  `claude -p --model sonnet --safe-mode --tools Read,Write --permission-mode acceptEdits --output-format json --max-budget-usd 0.50 --no-session-persistence <prompt>`.
- The scorer reads the output files on disk only. It does not read the reply text.
- Pass rule per method: the rewritten arm needs at least the original arm's correct answers
  minus 2. Probes also have a meaning-change rule: a probe fails when the original arm is right
  10 of 10 times and the rewritten arm is right 7 or fewer times.
  `skills/feature-intake/SKILL.md` must pass both methods. The other two files pass on probes
  alone.
- Run command:
  `python3 specs/ste100-harness-prose/experiment/pilot.py --base 0cc7ab7 --output specs/ste100-harness-prose/experiment/runs/pilot-1`.
  The run was done one time. Raw output is in `experiment/runs/pilot-1/`.

## Environment

| Item | Value |
|---|---|
| CLI version | `2.1.299 (Claude Code)` |
| Model alias | `sonnet` |
| Resolved model (CLI JSON `modelUsage`) | `claude-sonnet-5-5`, in all 80 trials |
| Trials completed | 80 of 80. All exit codes were 0. All output files parsed. |
| Budget stop | No |

## Cost

| Item | USD |
|---|---|
| Pilot run `runs/pilot-1` (sum of CLI `cost_usd` fields) | 2.7293 |
| Smoke runs `runs/smoke-v1` and `runs/smoke` | 0.1834 |
| Total | 2.9127 |
| Cap | 25.00 |

## Metrics

Correct answers per arm. Each cell is out of 80 (8 questions or fixtures × 10 trials).

| File | Method | Original | Rewritten | Rewritten minus original | Verdict |
|---|---|---|---|---|---|
| `rules/orchestration.md` | probes | 78/80 | 80/80 | +2 | PASS |
| `skills/feature-intake/SKILL.md` | probes | 80/80 | 80/80 | 0 | PASS |
| `skills/feature-intake/SKILL.md` | workflow | 79/80 | 80/80 | +1 | PASS |
| `skills/subagent-driven-development/SKILL.md` | probes | 80/80 | 80/80 | 0 | PASS |

Per-probe and per-fixture counts that are not 10 of 10 in both arms:

| File | Item | Original | Rewritten |
|---|---|---|---|
| `rules/orchestration.md` | probe O5 | 8/10 | 10/10 |
| `skills/feature-intake/SKILL.md` | fixture R8 | 9/10 | 10/10 |

All other probes and fixtures are 10 of 10 in both arms. No meaning-change rule fired.

## Raw-answer read

The task asked for a read of the raw answers wherever the two arms differ by 2 or more correct
answers. One cell meets that condition: `rules/orchestration.md` probe O5. I also read the one
workflow miss (R8). In total, the run has 3 misses. All 3 are in the original arm.

- **O5, `probes-orchestration-original-8` and `probes-orchestration-original-10`.** The question:
  "A high-risk task has medium confidence and no other escalation trigger. Does the orchestrator
  escalate or proceed?" Gold: escalate. Both trials wrote `"Proceed"`. The base text says
  "confidence is `low` (any lane), or `medium` on a high-risk task" is an escalation trigger. Thus
  "Proceed" is a real wrong answer, not a scoring artifact. The reply text of trial 10 gives the
  cause. The agent read "no other escalation trigger" as "no trigger at all". So the probe wording
  can cause this error. But the gold answer is correct, and the scorer scored the answer correctly.
- **R8, `workflow-feature-intake-original-3`.** The output file has
  `{"Lane": "high-risk", "Confidence": "high", "Escalate": "yes"}`. Gold is high-risk, high, no.
  The Lane and Confidence values are correct. The Escalate value is wrong. R8 has no hard gate and
  high confidence, so the rules give no reason to escalate. This is a real wrong answer, not a
  scoring artifact.

No scoring artifact was found. No miss would flip a verdict. All misses are in the original arm,
so a different score for them would only make the rewritten arm look better or equal.

## Limitations

- Ceiling effect. 7 of the 8 cells (both arms) are at 79/80 or 80/80. The original arm is at
  78–80/80. The probes and fixtures
  do not separate the two arms well. A pass means "no measured loss". It does not prove that STE
  helps.
- Small n. Each arm has 10 trials per method per file. The +2 on `rules/orchestration.md` is 2
  misses on one probe. It is not a significant difference.
- One model. All trials used `claude-sonnet-5-5`. The result can be different on other models.
- Regex scoring. The patterns can mark a correct but unusual answer as wrong. The raw-answer read
  found no such case in this run. The read covered only the 3 misses. A wrong answer that a
  pattern accepts was not searched for in the correct answers.
- Probe wording. The O5 question has the phrase "no other escalation trigger". One original-arm
  trial (original-10) said that it read the phrase as "no trigger". Trial original-8 gave the same
  wrong answer and stated no reason. The rewritten arm did not make this error. This can be noise
  and not an effect of the rewrite.
- Synthetic tasks. The probes and fixtures are short questions. They are not real `PLAN.md`
  execution. The workflow method tests only `feature-intake` classification Steps 2–4.
- `--safe-mode` disables project customizations. The trial agent did not load harness skills or
  rules. It read only the copied file or files.

## What happens next

- No Task 2.2 commit was reverted. The three pilot files stay at the STE rewrite (HEAD `87d204c`).
- Phase 3 (rollout) is now allowed by D2 and D6. Phase 3 planning stops for the user first.
