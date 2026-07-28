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
