# Claude handoff — skill prompt refactor

Date: 2026-07-29  
Repository: `harness-skills`  
Branch: `refactor/skill-prompt-surface`  
Remote: `github/refactor/skill-prompt-surface`  
Draft PR: #179 into `loop`  

## Goal

Continue implementing the plan in `specs/skill-prompt-refactor/PLAN.md` to the end. Do not
declare completion until every success criterion has authoritative evidence, the deployed harness
matches source, the final review receipt is valid at the reviewed HEAD, and the draft PR is ready
for human review.

## Current state

- Latest pushed commit: `30c3178 chore(evals): use standard claude CLI`.
- All repository references use the standard `claude` executable and the default `~/.claude`
  profile.
- Full `bash scripts/run-tests.sh` is green: 272 Python tests plus all shell contracts.
- Corpus validation and the candidate behavior gate pass:
  `python3 scripts/score_skill_eval.py --validate-corpus`
  and `python3 scripts/score_skill_eval.py --suite behavior --candidate`.
- Prompt inventory is valid; measured prompt reduction is 67.9% (34,034 to 10,913 words).
- `git status` is clean except for the intentionally untracked file
  `docs/research/2026-07-22-self-improving-harness-adoption.md`. Preserve it and never stage or
  overwrite it.

## Unfinished work

### Task 7.1 — controlled A/B and regression rejection

Still incomplete. Authenticated model observations are required for:

- 192 activation cases (baseline and candidate; three runs where the protocol requires it).
- Full baseline and candidate behavioral comparison (candidate has 36/36 passing; baseline has
  only 8 recorded behavioral observations).
- The existing review-chain corpus.
- Context-boundary probes.
- Five end-to-end canaries.
- A strict baseline/candidate comparison with complete canonical corpus coverage.

The strict scorer now rejects partial canonical comparisons. Do not fabricate records from auth
errors, and do not overwrite first-run misses. Preserve invalid collections in
`evals/skills/prompt-refactor/results/invalid-collections.json`.

### Task 8.1 — final workflow proof and evidence

Still incomplete. After Task 7.1 passes:

1. Run the focused checks and full `bash scripts/run-tests.sh`.
2. Run context-propagation, correctness-review, and intent-review over the complete diff.
3. Fill every `SUMMARY.md` Verify row and map all SC-1 through SC-12 without coverage warnings.
4. Write a review receipt at the reviewed HEAD.
5. Run `bash scripts/deploy-harness.sh`; verify deployed smoke, manifest, and documentation truth.
6. Mark the plan shipped only when source, deployed state, receipt, and evidence agree.
7. Keep PR #179 draft/open for human review; never merge it automatically.

## Readiness evidence at handoff

`python3 scripts/check_skill_eval_readiness.py --config-dir ~/.claude --claude claude` currently
reports `ready: false` and auth status failure (`logged_in: false`). Current corpus counts:

| Suite | Expected | Baseline | Candidate |
| --- | ---: | ---: | ---: |
| activation | 192 | 0 | 0 |
| behavior | 36 | 8 | 36 |
| end-to-end | 5 | 0 | 0 |

The goal is blocked only by the missing authenticated model access and the resulting required
evidence; deterministic implementation is not the blocker.

## Resume commands

```bash
cd /Users/minhtran/Documents/minhtran3124/developer/harness-skills
git switch refactor/skill-prompt-surface
git status --short --branch
claude auth status
python3 scripts/check_skill_eval_readiness.py --config-dir ~/.claude --claude claude
```

If authenticated, rebuild/recreate the historical baseline worktree at
`924af147e9721c0e09fb5d3f25a71e4465ea9b10`, deploy it, then run batches with closed stdin:

```bash
python3 scripts/run_skill_eval_batch.py --suite activation \
  --cwd /tmp/harness-skills-baseline-ab \
  --transcripts /tmp/harness-baseline-activation-transcripts \
  --summaries /tmp/harness-baseline-activation-summaries \
  --config-dir ~/.claude --claude claude

python3 scripts/run_skill_eval_batch.py --suite behavior \
  --cwd /tmp/harness-skills-baseline-ab \
  --transcripts /tmp/harness-baseline-behavior-transcripts \
  --summaries /tmp/harness-baseline-behavior-summaries \
  --config-dir ~/.claude --claude claude
```

Review each raw transcript before using `scripts/record_skill_eval.py`. Use `--commit-sha
924af147e9721c0e09fb5d3f25a71e4465ea9b10` when recording historical-baseline observations. Then
repeat on the candidate worktree and run the strict comparison; a partial collection must fail.

## Important contracts

- Use `claude`, not another CLI alias.
- Keep first-run evidence append-only and honest.
- Do not stage the existing untracked research note.
- Do not mark SC-2, SC-6, or SC-9 complete without direct evidence.
- Do not mark the plan shipped or close/merge PR #179 without the final receipt and human review.
