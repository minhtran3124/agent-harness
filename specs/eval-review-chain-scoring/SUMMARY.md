# eval-review-chain-scoring — Summary

Lane: normal
Confidence: medium
Reason: two flags — existing-behavior (revising answer keys of two fixtures breaks comparability with older result files) and weak-proof (the eval's own grading is what is being replaced); no manifest hard gate (evals/ and a new scripts/ file; no hooks, settings, rules, agents or skill prompts)
Flags: existing-behavior, weak-proof
Affects: evals/skills/review-chain (fixtures intent-gap, soft-delete-filter; README), new scripts/score_review_chain_eval.py and its test
Input-type: harness improvement
Route: using-git-worktrees → writing-plans (>2 files) → subagent-driven-development
Escalate: no (documented default for the one ambiguity, below)

Ambiguity named (rules/behavior.md §2): for `intent-gap`, the owner-scoping repair can be made "requested" by stating it in `intent.md`, or "allowed" by listing it as acceptable in the answer key. Chosen default: state it in `intent.md` (the user would naturally ask that only the owner can rename their watchlist), so a reviewer flagging it as excess is then a genuine false positive.

### Intent

Prior turn (assistant), the proposals the user accepted as "b":

> 1. **Fixture `intent-gap` gây FP hệ thống.** Ở mọi lượt, cả hai model đều đánh dấu phần sửa owner-scoping và nhánh 404 là "excess" với độ tin cậy 85–92. `truth.md` coi đây là phần sửa fixture có chủ ý, nhưng `intent.md` lại không nhắc tới. Cách sửa: bổ sung vào `intent.md` hoặc ghi thẳng vào answer key là chấp nhận được.
> 2. **`soft-delete-filter` không thể trả lời được.** Fixture phụ thuộc vào stack profile đã bị xóa, nên cả hai cấu hình chỉ bắt được với độ tin cậy ≤ 15. Cần ghi quy ước soft-delete vào `intent.md`, nếu không chỉ số "bắt lỗi chính" bị kẹt ở 4/5.
> 4. **Chấm điểm bằng LLM có độ lệch.** … Nên bắt reviewer trả JSON có cấu trúc gồm `oracle`, `class`, `file:line` và `confidence`, rồi chấm bằng script đối chiếu `truth.md`.
>
> Bạn muốn tôi: (a) cập nhật PR #246 với dữ liệu n = 3, và/hoặc (b) mở một nhánh mới để sửa mục 1–2, rồi làm mục 4 (chấm bằng script)?

User, verbatim:

> lam ca a va b

## What changed

Two review-chain fixtures are fixed (fixture v4): `intent-gap`'s request now states owner-only updates and the 404 case, and `soft-delete-filter`'s request states the soft-delete convention instead of relying on a removed stack profile. Every fixture gains a machine-readable `truth.json`. A new runner (`scripts/run_review_chain_eval.py`) asks a tool-less reviewer for structured JSON findings, and a new deterministic scorer (`scripts/score_review_chain_eval.py`) grades them against `truth.json`, replacing LLM grading. The README documents both the manual and the scripted path. A first scripted run is recorded in `evals/skills/review-chain/results/2026-10-02-v4-scripted.md`.

### Rationale

The n = 3 Opus 5 vs 5.5 A/B showed that two fixtures, not the models, produced a recurring false positive and an unanswerable miss, and that LLM grading drifted between runs. Fixing the inputs and making grading deterministic makes later prompt or model changes measurable. The first scripted run confirms it: `soft-delete-filter` is now caught at 85-90 by both arms (never above 15 before), and the `intent-gap` owner-scoping false positive is gone.

### Alternatives considered

- Accept the owner-scoping repair in the answer key instead of `intent.md` — keeps the request text minimal but leaves the reviewer no way to know it was wanted, so flagging it stays a reasonable reading rather than a false positive.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| `intent-gap` request states that only the owner may update a watchlist | `grep -q "Only the owner of a watchlist may update it" evals/skills/review-chain/fixtures/intent-gap/intent.md` | 0 | re-run by controller at 57b12e3 | SC-1 |
| `intent-gap` request states the not-found case | `grep -q "returns 404" evals/skills/review-chain/fixtures/intent-gap/intent.md` | 0 | re-run by controller at 57b12e3 | SC-2 |
| `soft-delete-filter` request states the soft-delete convention | `grep -q "deleted_at" evals/skills/review-chain/fixtures/soft-delete-filter/intent.md` | 0 | re-run by controller at 57b12e3 | SC-3 |
| `soft-delete-filter` answer key no longer cites the removed stack profile | `grep -q "templates/stacks" evals/skills/review-chain/fixtures/soft-delete-filter/truth.md` | 1 | re-run by controller at 57b12e3 | SC-4 |
| Every fixture has a schema-valid `truth.json` | `python3 scripts/score_review_chain_eval.py --check-truth evals/skills/review-chain/fixtures` | 0 | re-run by controller at 57b12e3 | SC-5 |
| Scorer and runner unit tests pass (classification, normalisation, oracle match, missing JSON block, malformed truth, runner with a stub `claude`) | `python3 -m pytest scripts/test_score_review_chain_eval.py -q` | 0 | re-run by controller at 57b12e3 | SC-6 |
| Runner refuses to overwrite an existing output before calling any model | `python3 scripts/run_review_chain_eval.py --claude false --model x --effort low --output scripts/run-tests.sh` | 1 | re-run by controller at 57b12e3 | SC-7 |
| README records fixture revision v4 | `grep -q "v4 (2026-10-02)" evals/skills/review-chain/README.md` | 0 | re-run by controller at 57b12e3 | SC-8 |

### Not auto-verified

- Keyword answer keys classify real reviewer wording as the answer key intends — reached traceability (unit tests on synthetic phrasings + a manual audit of one real run per arm); unusual wordings can still be mis-credited, and the create-side trim FP on `intent-gap` scored `other` in that run.
- Scripted metrics are stable run to run — not measured (n = 1 per arm).

### Minor findings (task reviews, not fixed)

- Task 1.2: runner `--fixtures` on a missing directory raises a traceback; a result with no matching fixture is ignored silently; the not-run warning loop re-derives the fixture list; runner fatal errors print to stdout.
- Task 1.1: `none-deref` planted keeps generic terms (`none`, `optional`) and outcome words that a schema FP mentioning a 500 could still satisfy; `missing-await` has `coroutine` in both gates; phrase-shaped `and_any` may miss terse correct catches ("await is missing").

### Rollback

- `git revert <sha>`

### Harness-Delta

- backlog — `--check-truth` validates structure only; a standing check that each listed false-positive phrasing still classifies as `false_positive` (sample phrasings per fixture) would catch answer-key regressions like the one the Task 1.1 review found.
