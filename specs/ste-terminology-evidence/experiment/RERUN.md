# Fresh benchmark rerun — 2026-08-13

This rerun checks whether the original terminology decisions survive a fresh sample. It does
not replace the original archived ledger; the new raw outputs and protocol are stored under
`reruns/` so both samples remain auditable.

## Protocol

- Recovered the 14 distinct prompt/model groups from the original Claude Code session and
  reproduced 76 launches: 70 Sonnet and 6 Opus.
- Ran Claude Code 2.1.229 in a fresh temporary directory per trial, with safe mode and no
  session persistence. The aliases resolved to Claude Sonnet 5 and Claude Opus 5; Claude
  Haiku 4.5 also appears in CLI auxiliary model usage.
- Scored only filesystem artifacts, never the model's self-report.
- The first full rerun inserted one extra paragraph break before the closing reply request in
  the four E4 prompt groups. H1 and H2 were byte-for-byte prompt matches and are taken from
  that 76-trial run. After checking all 14 templates against the original transcript, E4 was
  corrected and rerun separately for 20 trials; those exact-prompt results are the H3 result
  reported below.

The main run completed and scored 76/76 trials for $4.259050. The exact E4 supplement completed
and scored 20/20 for $1.057917. Total recorded benchmark cost was $5.316967. The pilot runs used
to validate the runner are excluded from every metric.

## Comparison

| Hypothesis | Original result of record | Fresh exact-prompt result | Interpretation |
| --- | --- | --- | --- |
| H1 modality, round 2 | `should` 0/10; `must` 4/10; p=0.0867 | `should` 5/10; `must` 6/10; p=1.0000 | Rates did not replicate; no evidence that changing the modal is a dependable compliance lever |
| H2 acceptance, round 2 pooled | vague 1/8; stated 8/8; p=0.0014 | vague 0/8; stated 8/8; p=0.0002 | Strong replication; observable criteria remain the only measured wording intervention with a large effect |
| H3 terminology, round 2 | mixed 20/20; one-verb 20/20 | mixed 20/20; one-verb 20/20 | Exact replication of the null on these assertion tasks |

Round 1 remained at ceiling: H1 was 5/5 vs 5/5, H2 was 5/5 vs 5/5, and the exact E4
supplement was 20/20 vs 20/20. The fresh sample therefore leaves all three decisions unchanged:
adopt machine-decidable acceptance criteria, keep one-concept-one-word advisory, and do not
treat `must` as an enforcement mechanism.

## Reproduce and inspect

Run a new sample:

```bash
python3 specs/ste-terminology-evidence/experiment/rerun.py \
  --output specs/ste-terminology-evidence/experiment/reruns/<new-run>
```

Regenerate a stored run's metrics without making model calls:

```bash
python3 specs/ste-terminology-evidence/experiment/rerun.py \
  --output specs/ste-terminology-evidence/experiment/reruns/2026-08-13-claude-code-2.1.229 \
  --score-only
```

`protocol.json` records the prompts and launch inventory, `raw-results.jsonl` records one row
per trial, and `results.txt` is the derived summary.

## Limits

The original sample used Claude Code's general-purpose subagent tool, while the rerun invokes
the same model aliases directly through `claude -p`. User prompts, fixtures, model aliases, and
filesystem scoring match, but the surrounding system context and orchestration path do not.
The sample sizes remain small, tasks remain synthetic, and H3 tests assertion accuracy rather
than terminology drift across a long document.
