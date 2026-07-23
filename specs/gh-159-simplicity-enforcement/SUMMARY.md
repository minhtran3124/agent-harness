# gh-159-simplicity-enforcement — Summary

Lane: high-risk
Confidence: high
Reason: All four touched files are workflow-engine surface (skills/*/SKILL.md, a dispatch prompt, and hooks/risk-corroboration.sh) — hard gate per harness-manifest.json, warn-mode at commit but classified high-risk at intake regardless.
Flags: workflow-engine
Affects: subagent-driven-development ship chain, intent-review excess classification, implementer dispatch prompt, risk-corroboration.sh
Input-type: harness improvement

### Intent

check gh issue https://github.com/minhtran3124/agent-harness/issues/159
- new spec/ folder and create design + plan files

(Full issue body + the issue author's own follow-up audit comment — design decisions D1-D5,
current-state table, wave-1/wave-2 split — are condensed in `design.md`; the issue itself is the
verbatim source of the acceptance criteria this plan implements.)

## What changed

Wires simplicity enforcement into the existing ship path instead of adding new gates: a
threshold-triggered `/simplify` pass runs before `/correctness-review`, `intent-review`'s
`excess` definition now names config knobs/new public surface explicitly, the implementer
dispatch prompt restates Simplicity First constraints up front, and `risk-corroboration.sh`
gains a warn-only diff-size note suggesting `/simplify` when a diff is disproportionate to its
declared lane.

### Rationale

The issue's own follow-up comment already audited the current tree and proposed D1-D5 (one
existing skill, not three; insertion point before correctness-review; a threshold trigger
instead of lane-manual; warn-only diff-size signal) — implementing that plan directly rather than
re-deriving it avoids relitigating decisions the repo owner already made with file:line evidence.

### Alternatives considered

- A new dedicated hook for the diff-size signal — rejected per the issue's explicit scope note
  (strengthen existing hooks/skills, no new hook).
- Gating `/simplify` on lane alone (manual for tiny) — rejected in favor of D4's line-count
  threshold, which is strictly stronger (still catches an oversized tiny-lane diff).

### Deviations

- Rule 2 — Quality-review fixes: capitalized sentence fragment (`0e121fc`) and removed a
  duplicated phrase (`4669f20`), both flagged by per-task code-quality review.
- Rule 2 — `/simplify` pass fix: removed a redundant Rule-4 parenthetical in the D3 carve-out
  sentence (`7bf20ab`), flagged by the simplification angle.
- Rule 1 — `/correctness-review` fix loop, 2 rounds, on `hooks/risk-corroboration.sh`'s
  diff-size signal (Rule-4-flagged file; escalated to the human before fixing since Task 1.4's
  own literal spec was the root cause, not an implementer slip — human approved the "count
  unfiltered diff lines" direction): round 1 (`8d7aff9`) replaced the keyword-scan-filtered
  `$CODE_ADDED`/`$CODE_REMOVED` reuse with `git diff --cached -U0 --numstat`; a fresh
  re-verification pass caught a NEW bug the round-1 fix introduced (`-U0` forces patch-body
  emission that `--numstat` doesn't suppress, inflating the count ~100x on content with
  numeric-looking tokens); round 2 (`a58181b`) dropped `-U0`, independently re-verified CLOSED
  with no residual issue.

### Advisory Findings

<!-- Findings scored below the correctness-review threshold (75) — not auto-fixed, reported. -->

- **`hooks/risk-corroboration.sh` — stale disk-fallback lane attribution** (score 0). The
  diff-size note can print a lane inferred from an unrelated slug's `SUMMARY.md` (the `ls -t`
  disk fallback) when no `SUMMARY.md` is staged in the current commit. Scored 0: the
  disk-fallback mechanism itself is pre-existing (already used by the block/warn decision before
  this diff) — this diff only adds a second consumer of it, not a new defect in the mechanism.
- **`hooks/risk-corroboration.sh` — `CHANGED_LINES` double-counts modified lines** (score 0,
  superseded). The original `$CODE_ADDED + $CODE_REMOVED` computation counted a single-line
  modification as 2 changed lines (one added, one removed). Scored 0 as spec-literal, non-fatal
  advisory-message imprecision — moot after the round-1/round-2 fix loop above replaced this
  computation entirely with an unfiltered `--numstat` sum, which does not double-count.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| baseline | `bash scripts/run-tests.sh` | 0 | ALL GREEN before implementation (185 python tests + shell suites) | |
| simplify step present | `grep -n "simplify" skills/subagent-driven-development/SKILL.md` | 0 | match at line 140, before the correctness-review pipeline description | SC-1 |
| excess wording present | `grep -q "config knob" skills/intent-review/intent-reviewer-prompt.md` | 0 | match confirmed | SC-2 |
| implementer prompt constraint | `grep -in "minimum code that solves the problem" skills/subagent-driven-development/implementer-prompt.md` | 0 | match at line 11, above the self-check line at 91 | SC-3 |
| hook contract tests | `bash tests/hooks/risk-corroboration.test.sh` | 0 | 33 passed (31 wave-1 + fix-loop rounds 1-2) | SC-4 |
| full suite after fix loop | `bash scripts/run-tests.sh` | 0 | ALL GREEN | SC-5 |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | passes after all skill/prompt edits | SC-5 |

### Rollback

- `git revert <sha>` (per task commit, or the wave-boundary commit if squashed)

### Context-Propagation Audit

**Verdict: PASS.** Range `5aef660..HEAD` (07f76b8, 31e6784, 9d972ad, 514f8cc, 0e121fc, 4669f20,
a03bc97). Trigger: all four task files match the `workflow-engine` inventory
(`skills/*/SKILL.md`, dispatch prompts, `hooks/*.sh`).

| Source | Consumer | Execution context | Delivery | Proof |
|---|---|---|---|---|
| New "Simplify pass" paragraph, `skills/subagent-driven-development/SKILL.md` | Whoever executes `/subagent-driven-development` | main session / parallel session (orchestrator) | **always-loaded** — the entire SKILL.md is pasted wholesale into the invoking session on `Skill` dispatch (not path-scoped, no partial load) | Inspected call site: this very session received the full file body verbatim from the `Skill` tool result when `/subagent-driven-development` was invoked (see this session's own transcript) |
| New `excess` wording + D3 carve-out, `skills/intent-review/intent-reviewer-prompt.md` | The isolated intent-review reviewer subagent | reviewer (isolated, blind to PLAN.md) | **pasted** — `intent-review/SKILL.md` instructs the orchestrator to paste `intent-reviewer-prompt.md`'s content directly into the reviewer's dispatch prompt (no Read-based indirection) | Inspected call site: `skills/intent-review/SKILL.md` dispatch section names `intent-reviewer-prompt.md` as the template to paste, not to reference |
| Mirrored `excess` sentence, `skills/intent-review/SKILL.md` | Whoever executes `/intent-review` (orchestrator) | main / parallel session | **always-loaded** — same wholesale-paste mechanism as above | Same as row 1 |
| New "Simplicity First" constraint block, `skills/subagent-driven-development/implementer-prompt.md` | Isolated implementer subagent | implementer (isolated, fresh context per task) | **pasted** — `subagent-driven-development/SKILL.md` Step 2 instructs pasting `implementer-prompt.md`'s full templated body into each task's dispatch prompt (explicit: "A subagent must never be told to go read PLAN.md itself: it gets exactly the constructed context") | Inspected call site: `subagent-driven-development/SKILL.md` §Step 2.1; corroborated live in this session — all 4 wave-1 implementer subagents received the full template body pasted, including the new block, per their dispatch prompts issued this session |
| `hooks/risk-corroboration.sh` diff-size note | The hook's own execution (PreToolUse on `git commit`) | hook execution context (not a prompt/instruction consumer) | **n/a** — this is executable shell code invoked directly by the harness on every commit, not an instruction referenced by a separate isolated context | `tests/hooks/risk-corroboration.test.sh` (31/31 passing) exercises the code path directly |

**"No stale/duplicate copy" check** (search surface: `grep -rln` over `.` for each new phrase —
`"excess.*NOBODY asked"` / `"excess.*scope beyond the intent"`, `"Did I avoid overbuilding"`,
`"Simplify pass"` / `"/simplify"` restricted to `skills/`, `rules/`, `agents/`): each phrase
appears only in its own source file(s) plus this SUMMARY/design.md — no second, independently
maintained inline copy exists anywhere else in the repo that could silently drift from these four
changes. No hard-fail rule (assumed/unconfirmed delivery, main-session-as-proof-for-child-context,
unanchored inline subset) is tripped.

### Harness-Delta

- none
