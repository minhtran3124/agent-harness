# feature-intake — behavioral test cases

`/feature-intake` is a prompt skill: its classification is produced by the model, so it
cannot be asserted by a deterministic shell test the way the hooks are. These canaries are
the analogue of `skills/xia2/tests/` — input prompts paired with the lane / confidence /
escalation the skill **must** produce. They are run by a human or a meta-eval session, not
in per-commit CI (an LLM call per case costs money and is non-deterministic).

## What is deterministic vs. not

- **Deterministic (the rule):** once the risk flags are known, lane assignment is a fixed
  mapping (`0–1 → tiny|normal`, `2–3 → normal`, `4+ → high-risk`, `any hard gate →
  high-risk`). `lane-classification-cases.md` pins that mapping.
- **Model-judged (the classification):** which flags a prompt trips, and whether the
  direction is ambiguous. That is what the canaries exercise against the live skill.

## How to run

Manual, or batched through a headless session:

```bash
# one case at a time, against the real skill
claude -p "/feature-intake <case prompt>" --output-format text
# then check the emitted Lane / Confidence / Escalate against the Expected row
```

A case **passes** when the emitted `Lane`, `Confidence`, and `Escalate` match the Expected
columns. A hard-gate case that comes back below `high-risk` is a **regression** — the gate
leaked. Re-run after editing Step 2/3 (flags/lane), Step 4 (confidence), or the hard-gate
list in `SKILL.md`.

## Files

- `lane-classification-cases.md` — lane + hard-gate canaries (the load-bearing safety net).
- `confidence-escalation-cases.md` — the interruption axis: when a human must be asked.
