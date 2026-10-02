# eval-opus-5-5-ab — Summary

Lane: tiny
Confidence: high
Reason: records eval results only (evals/ result files, no code, prompt, or gate change)
Flags: none
Affects: none
Input-type: maintenance

### Intent

> 3. chay eval review-chain + task review

> (after the results were reported) "Kết quả hiện chỉ nằm trong scratchpad, chưa đưa vào repo. Bạn có muốn tôi ghi vào `evals/skills/*/results/` rồi mở PR không?" → "ok"

## What changed

Adds the review-chain and task-review A/B results comparing the pre-#244 reviewer binding
(`claude-opus-5`) with the post-#244 binding (`claude-opus-5-5` at `medium`), with raw outputs and
the review-chain runner.

### Rationale

The opus-5-5-review-bindings design required measuring the new binding after merge; results
belong next to the existing result files so later changes can trend against them.

### Alternatives considered

- none

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| result JSON parses | `python3 -c "import json; [json.load(open(p)) for p in ('evals/skills/task-review/results/opus-5-5-ab-old.json','evals/skills/task-review/results/opus-5-5-ab-new.json','evals/skills/review-chain/results/raw/2026-10-02-opus-5-ab-old.json','evals/skills/review-chain/results/raw/2026-10-02-opus-5-5-ab-new.json','evals/skills/review-chain/results/raw/2026-10-02-opus-5-ab-old-run2.json','evals/skills/review-chain/results/raw/2026-10-02-opus-5-5-ab-new-run3.json','evals/skills/task-review/results/opus-5-5-ab-new-run3.json')]"` | 0 | seven files load | |
| doc paths resolve | `bash scripts/lint-doc-truth.sh` | 0 | | |

### Not auto-verified

- Grading of review-chain outputs — reached traceability only (LLM graders against `truth.md`, arms anonymized and shuffled); n = 3 per cell.

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
