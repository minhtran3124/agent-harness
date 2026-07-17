# Review-Chain Benchmark Run — &lt;date&gt; &lt;label&gt;

- **Measured skills:** `/correctness-review`, `/intent-review`
- **Skill commit sha:** `<sha the run measured>`
- **Date:** `<YYYY-MM-DD>`
- **Runner:** manual v1 (see `../README.md`)

## Per-fixture results

| Fixture | Defect class | Expected oracle | Caught-by | Verdict | Tokens |
|---|---|---|---|---|---|
| none-deref | None deref (Optional unguarded) | /correctness-review | | | |
| missing-await | Missing await (async) | /correctness-review | | | |
| soft-delete-filter | Soft-delete filter missing | /correctness-review | | | |
| excess-scope | Unrequested refactor (excess) | /intent-review | | | |
| intent-gap | Validation gap (1 of 2 endpoints) | /intent-review | | | |

Verdict ∈ {caught, caught-wrong-reason, missed, false-positive}.

## Headline numbers

- **Catch rate:** `n/5`
- **False positives:** `n`
- **Approx tokens per pass:** correctness-review `~N`, intent-review `~N`

## Notes

- Misses (plain): …
- Caught-wrong-reason (if any): …
- Scope reminder: this measures only these two skills against these five planted defect
  classes — not the full chain, not real-world catch rate (`not_observed != absent`).
