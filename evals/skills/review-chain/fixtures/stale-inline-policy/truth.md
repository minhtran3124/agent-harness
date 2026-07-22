# Ground truth — stale-inline-policy

- **Defect class:** Stale inline policy (drift). An inline copy of an authoritative policy
  list that is (a) an incomplete subset of its source AND (b) not generated from or linted
  against that source, so it can drift silently. Not a runtime bug and not an intent gap — a
  *fidelity* defect: the prompt inlines a policy so it need not read the source, but the copy
  is wrong and nothing keeps it honest.
- **Location:** `skills/demo-review/reviewer-prompt.md`, the "Rule 4 — STOP list" block. It
  inlines only 5 of the 8 authoritative Rule-4 STOP cases from `.claude/rules/auto-correct-scope.md`
  (schema, API contract, removing functionality, external dependency, auth/authz) and OMITS
  three: **session/transaction scope changes**, **changes to high-blast-radius files**
  (`settings.json`, `hooks/*`, core skill engine), and **replacing a service/pattern**. The
  prompt explicitly tells the reviewer to "decide from this prompt alone — do NOT go read specs
  or rule files," and contains no `Read` of the authoritative rule, so the missing three cases
  are unreachable. A real finding matching one of the three omitted cases is classified Rule 1–3
  and auto-fixed instead of escalated — exactly the P2 that escaped PR #141.
- **Expected oracle:** `/context-propagation-audit` — the Phase-2 drift-lint angle that compares
  an inline copy of a policy/list against its authoritative source and flags an incomplete or
  divergent subset that is not generated/linted from that source. This oracle does not yet exist
  in the corpus; this fixture is its acceptance target (built in Phase 2). The fix mirrors real
  commit 1c0f01d: complete the inline list to all 8 cases AND add an explicit Read of
  `.claude/rules/auto-correct-scope.md` so the copy is anchored to its source.
- **`/correctness-review` and `/intent-review` are EXPECTED to record `missed` here — by
  design, not a failure of those oracles.** `/correctness-review` reads code/diff for runtime
  bugs (None/async/DB/auth/concurrency/contract); there is no runtime defect in a Markdown
  prompt. `/intent-review` checks the diff against the original request; the diff *does* add a
  reviewer prompt carrying the Rule-4 STOP criteria so findings can be classified without reading
  specs, so it satisfies the stated intent on its face. Neither oracle compares an inline policy
  copy against its authoritative source, so neither can structurally see this defect. Record them
  as `missed`, not as their failure.
- **Expected verdict if caught:** flags the inline STOP list as an incomplete subset of the
  authoritative 8-case list (names the three missing cases) that is not linted against its
  source, and recommends completing the list to all 8 cases plus an explicit `Read` of (or a
  generation/lint step against) `.claude/rules/auto-correct-scope.md`.
- **What a false-positive would look like:** flagging an inline summary that IS generated from,
  or linted against, the authoritative source — e.g. a copy carried with a generation/lint step
  that fails CI when it diverges, or a complete 8-of-8 copy anchored by a `Read` of the rule.
  That is the *correct* pattern (delivery without drift risk), not a defect. Flagging it anyway
  is a false positive.
