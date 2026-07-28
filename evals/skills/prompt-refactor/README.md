# Skill prompt refactor evals

This corpus measures prompt refactors, not general model capability. Each result is tied to a
commit, model snapshot, client version, reasoning setting, and clean dispatch context.

## Corpus

- `activation/` contains should-trigger and near-miss queries for each skill. Each polarity needs
  at least eight cases and at least one holdout.
- `behavior/` contains a golden path, boundary/STOP, and handoff/output-contract case for every
  skill.
- `end-to-end/` contains tiny, normal, high-risk, resume, and workflow-engine chain canaries.
- `corpus-manifest.json` maps every registered skill to its fixtures.

The validator is deterministic:

```bash
python3 scripts/score_skill_eval.py --validate-corpus
```

## Results and honesty rules

Record the first observed result in `results/*.json`; never overwrite a miss by re-running the
same case until it passes. A record must include the model, client version, reasoning setting,
commit SHA, split, verdict, and whether the case is safety-critical. The scorer rejects a
candidate that regresses a passing baseline, adds a false positive, misses a safety-critical case,
or changes the evaluation environment.

```bash
python3 scripts/score_skill_eval.py --compare results/baseline.json results/candidate.json
```

Coverage is bounded by the corpus. A behavior without a fixture is unmeasured, not proven safe.
When the comparison paths are the repository's canonical `results/baseline.json` and
`results/candidate.json`, the scorer also requires both files to contain every activation,
behavior, and end-to-end corpus case; a partial historical collection fails loudly instead of
being reported as SC-9 evidence.

## Recording a live observation

Use the append-only recorder after each actual clean-context dispatch. It rejects unknown cases,
duplicate first-run records, and mixed environments in one result file:

```bash
python3 scripts/record_skill_eval.py \
  --results evals/skills/prompt-refactor/results/candidate.json \
  --case <case-id> --verdict <pass|missed|false-positive|blocked> \
  --model <pinned-model> --client-version <client> --reasoning <setting> \
  --observation "<what happened and the evidence>"
```

The recorder stores only an observation; it does not invoke a model. Record a rerun in a separate
attempt file rather than replacing the first result.

## Capturing a live response

Use the capture helper before grading a real first-run dispatch. It invokes Claude with no tools,
stores the final response plus usage in a transcript, and prints a compact summary; it does not
assign a verdict or write a result record.

```bash
CLAUDE_CONFIG_DIR=~/.claude-edgeful \
python3 scripts/capture_skill_eval.py \
  --output evals/skills/prompt-refactor/results/transcripts/<case-id>.json \
  --prompt '/<skill> ...clean behavior-evaluation probe...'
```

Review the saved transcript, then call `record_skill_eval.py` exactly once for that case. The
profile path above is the current Edgeful CLI profile; use an equivalent pinned profile when the
evaluation environment changes.

For a corpus batch, use `run_skill_eval_batch.py`. It performs an auth preflight and exits before
creating transcripts when the configured profile is logged out; `--skip-auth-check` is intended
only for harness tests, never for evidence collection.

```bash
python3 scripts/run_skill_eval_batch.py --suite behavior \
  --cwd <baseline-or-candidate-worktree> \
  --transcripts /tmp/skill-eval-transcripts \
  --summaries /tmp/skill-eval-summaries \
  --config-dir ~/.claude-edgeful
```

Before starting a long run, inspect readiness and missing case counts:

```bash
python3 scripts/check_skill_eval_readiness.py --config-dir ~/.claude-edgeful
```

When the corpus was introduced after the baseline checkout, run the recorder from the current
corpus root and pass that checkout's immutable SHA explicitly:

```bash
python3 scripts/record_skill_eval.py \
  --results evals/skills/prompt-refactor/results/baseline.json \
  --commit-sha <historical-baseline-sha> \
  # ...the same case/environment/observation fields
```

This preserves the pinned inventory in `baseline.json` while adding a result record. The override
is restricted to hexadecimal Git SHAs, so the evaluated revision remains auditable.
