# Ground truth — context-rule-unread

- **Defect class:** Context propagation (instruction referenced but never delivered to the
  isolated execution context). Not a runtime bug and not an intent gap — a *delivery* defect:
  the dispatch prompt relies on a rule that will never enter the subagent's context.
- **Location:** `skills/demo-dispatch/worker-prompt.md`, the "Self-fix classification" line
  — `Classify every self-fix you apply against \`.claude/rules/auto-correct-scope.md\`
  (Rule 1–3 vs Rule 4 STOP)`. This line *names and relies on* the rule but contains no
  instruction to Read it. `.claude/rules/auto-correct-scope.md` is path-scoped (`paths:
  ["specs/**"]`) — it auto-loads only when a matching `specs/**` file is read. An isolated
  worker subagent given only this prompt never reads such a file and is never told to Read the
  rule, so the rule text never lands in its context. The worker is instructed to apply a
  classification it cannot see — Rule 1–4 semantics are silently absent, so its self-fixes are
  unclassified (or mis-classified) with no signal that anything is missing.
- **Expected oracle:** `/context-propagation-audit` — the Phase-2 consumer audit that models
  whether a referenced instruction/rule/context is actually *delivered* to the isolated
  consumer that relies on it. This oracle does not yet exist in the corpus; this fixture is its
  acceptance target (built in Task 2.1). The fix mirrors real commit d61e155: prepend an explicit
  "FIRST: Read `.claude/rules/auto-correct-scope.md` now" so the isolated context loads the rule
  before relying on it.
- **Expected verdict if caught:** flags the reference line as a rule relied on but never
  delivered to the isolated context, and recommends an explicit `Read` step (or inlining the
  rule text) so the path-scoped rule is present before the worker classifies self-fixes.
- **`/correctness-review` and `/intent-review` are EXPECTED to record `missed` here — by
  design, not a failure of those oracles.** `/correctness-review` reads code/diff for runtime
  bugs (None/async/DB/auth/concurrency/contract); there is no runtime defect in a Markdown
  prompt. `/intent-review` checks the diff against the original request; the diff *does* add a
  dispatch prompt that classifies self-fixes against the rule, so it satisfies the stated intent
  on its face. Neither oracle models instruction delivery across isolated contexts, so neither
  can structurally see this defect. Record them as `missed`, not as their failure — this fixture
  exists to prove a defect class the two existing oracles cannot catch.
- **What a false-positive would look like:** flagging a variant of this prompt that pastes the
  FULL text of `.claude/rules/auto-correct-scope.md` inline (or includes an explicit "Read
  `.claude/rules/auto-correct-scope.md` now" step). That is *correct* delivery — the rule is
  present in the isolated context — so there is no defect to report. Flagging it anyway is a
  false positive.
