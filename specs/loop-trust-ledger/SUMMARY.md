# loop-trust-ledger — Summary

Lane: normal
Confidence: high
Reason: Design proposal only (one new `specs/` doc + this record); ships no code and touches no hook/script/high-blast file. Normal lane for the record; the change it *proposes* would be high-risk to implement (that's a later spec).
Flags: none
Affects: none
Input-type: harness improvement

### Intent

> new branch sau đó đặc tả nó ra - ledger thành document, sao đó tạo PR để tôi review

(Context from the prior turn: the user asked what we could learn from Boris Cherny's *Steps of
AI Adoption* artifact. My recommendation #1 was to make "loop trust" a measured, governing
signal — not just per-task risk. The user chose to spec out that ledger idea as a document and
open a PR to review.)

## What changed

Added `specs/loop-trust-ledger/design.md` — a proposal to turn the existing (descriptive)
`docs/harness-experimental/trust-metrics.md` ledger into a *governing* loop-trust signal: a
backward-looking, cross-task rolling score (review-catch health, verify-pass rate,
escaped-defect rate, escalation calibration) that modulates fan-out width / autonomy — a third
axis orthogonal to the per-task risk lane and confidence. Includes a measure→surface→govern
phased rollout, anti-Goodhart guardrails, and open questions for review. §11 cites external
prior art (Licaomeng's production on-call harness) that already runs a mechanized
confidence-as-behavioral-gate — a worked confidence-ceiling formula + threshold transitions
to seed §4/§5 and answer the weights open-question. No code, no wiring.

### Rationale

The adoption model's Step-3 trap — "scaling agent count before the loop has earned trust" — is
unguarded in our harness: nothing ties wave fan-out to demonstrated loop reliability. Shipped
as a proposal (design.md, not an implementation) because it would redefine the autonomy
governance model, which is a Rule-4 / redefine-system decision that needs human sign-off before
any code. Measure-before-govern rollout is chosen so the trust signal earns its own trust
before it changes behaviour.

### Alternatives considered

- Write it straight into `docs/harness-experimental/` as an accepted design — rejected: it's a
  proposal, not a decision; `specs/<slug>/design.md` is the right home for something awaiting
  review.
- Skip the doc and open an implementation PR — rejected: redefining the autonomy model is
  Rule-4; direction must be approved first.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Docs-only diff (no code/hook/script touched) | `git diff --name-only main...HEAD` | 0 | only `specs/loop-trust-ledger/*` |

### Rollback

- `git revert <sha>` (or delete `specs/loop-trust-ledger/`) — docs-only, no runtime effect.

### Harness-Delta

- none
