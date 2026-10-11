# Correctness FIND dispatcher

Run six isolated FIND reviewers over the same diff. Read `review-config.json` for the canonical
angle list, then dispatch one reviewer per angle in parallel. Each child receives only:

1. `prompts/shared.md` — the common runtime-bug contract, inputs, scope, trigger requirement,
   output schema, and required policy reads.
2. `prompts/angles/<angle>.md` — exactly one method: `enclosing-function`, `removed-behavior`,
   `call-site-impact`, `stack-defects`, `guard-completeness`, or `prior-art`.

Do not send every angle block to every child. Compose a prompt with provenance using:

```bash
python3 scripts/render_skill_prompt.py \
  --fragment skills/correctness-review/prompts/shared.md \
  --fragment skills/correctness-review/prompts/angles/<angle>.md
```

Each angle returns every candidate it can name a trigger for. Pool and deduplicate them by
`(file, line)`. Agreement between angles is not evidence; never show it to the independent
scorer. Score each remaining location with `correctness-scorer-prompt.md`, then route it under `review-config.json` and the
auto-correct-scope policy. The controller owns fix-loop, escalation, and residual recording; every
finding is fixed or durably recorded before finishing.
