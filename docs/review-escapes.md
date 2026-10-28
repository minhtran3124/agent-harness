# Review-Escape Ledger

**The rule:** every post-push finding by an **external or heterogeneous reviewer** — one that
did not run inside our local review chain (e.g. Codex reviewing a GitHub PR: a different
model + harness, with no inherited Claude plan assumptions) — becomes **(a)** a durable row in
the table below **and (b)** either a regression fixture/test that would now catch it, or a
documented won't-fix.

**Why it matters:** the in-chain oracles (`/correctness-review`, `/intent-review`) share our
context, our plan, and our blind spots. An external reviewer arrives with fresh context and no
inherited assumptions, so it structurally catches classes of defect the in-chain oracles cannot
see — the escapes that slip *past* a passing local chain. Left as one-off comments those lessons
evaporate; converted into a fixture-or-test they become permanent regression coverage. This ledger
is the compounding mechanism: one escape today is a standing guard against its whole class forever.

Each escape below is a data row whose `PR` cell begins with `PR #`. The `fixture` cell points at the
regression artifact (a fixture under `evals/skills/review-chain/fixtures/`, a test file, or a
documented won't-fix). See `evals/skills/review-chain/README.md` → **Feeding the ledger** for how a
new escape becomes a fixture.

## Ledger

| date | PR | finder | class | severity | fixture | status |
|---|---|---|---|---|---|---|
| 2026-07-21 | PR #141 | Codex | context-propagation | P1 | `evals/skills/review-chain/fixtures/context-rule-unread/` | fixed (d61e155) + fixture (gh-143 wave 1) |
| 2026-07-21 | PR #141 | Codex | stale-inline-policy | P2 | `evals/skills/review-chain/fixtures/stale-inline-policy/` | fixed (1c0f01d) + fixture (gh-143 wave 1) |
| 2026-07-22 | PR #153 | Codex | missing-regression-guard | P1 | `tests/scripts/scorer-threshold-contract.test.sh` | fixed (test added in PR #153) |
