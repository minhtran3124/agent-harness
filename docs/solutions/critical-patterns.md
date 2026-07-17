# Critical Patterns

Always read when consuming this knowledge base, regardless of query domain. Keep this file short — entries here are high-leverage learnings that apply across many features.

Add an entry only when the pattern:
1. Has caused non-obvious bugs in multiple modules, OR
2. Documents a non-negotiable project rule that can't be expressed in a linter

## Entries

## [2026-06-11] meta-repo-signal-remapping
**Type:** knowledge
**Module:** skills/bootstrap-xia2
**Tags:** meta-repo, signal-remapping, project-md, dual-audience-docs, bootstrap-update-mode, hook-friction
**Applicable when:** Bootstrapping or updating xia2 PROJECT.md (or any risk-classification config) for a repo whose "application" is the tooling itself — skills, hooks, scripts.

A meta/harness repo does have high-blast files, security surfaces, and public contracts — they live in `settings.json`, `hooks/*.sh`, `tests/lib.sh`, `.mcp.json`, and hook-parsed template fields (`Lane:`), not in app code layers. Map each app-centric xia2 signal category to its harness-native analog instead of leaving it empty, grounded in churn + inbound-reference evidence.

**Full doc:** docs/solutions/harness-bootstrap/meta-repo-signal-remapping.md
---

## [2026-06-11] meta-repo-signal-remapping-decisions
**Type:** decision
**Module:** skills/bootstrap-xia2
**Tags:** meta-repo, signal-remapping, project-md, dual-audience-docs, bootstrap-update-mode, hook-friction
**Applicable when:** Bootstrapping, classifying risk, or sourcing conventions in a meta/harness repo whose `.claude/rules` docs describe the *target* projects it deploys into.

Two decisions: (1) `agents/PROJECT.md` convention sources point at `skills/README.md` + `rules/behavior.md` — not `.claude/rules/architecture.md`/`guidelines.md`, which describe the target FastAPI projects and would mislead agents working ON the harness; a maintainer note guards against re-bootstrap regression. (2) Non-applicable risk categories (DB sessions, auth) record "none" PLUS a named harness analog as a Deep trigger (warn↔block hook flips, secrets-scan edits, `.mcp.json` additions), preserving the category's protective intent.

**Full doc:** docs/solutions/harness-bootstrap/meta-repo-signal-remapping-decisions.md
---

## [2026-07-04] bash-empty-array-and-jsonl-parsing-gotchas
**Type:** bug
**Module:** scripts/harness-audit
**Tags:** bash-set-u, empty-array-expansion, jsonl-parsing, defensive-parsing, harness-scripts, ci-macos-ubuntu
**Applicable when:** Before iterating a bash array that can legitimately be empty under `set -u` (especially on macOS's bundled bash 3.2, which this repo's CI matrix specifically targets); or whenever a block is advertised as "advisory / never blocks" and you are about to enforce that with a try/except exception list instead of a `|| true` boundary on the command.

Two crashes in advisory/non-blocking scripts. (1) `scripts/harness-audit.sh` crashed with `unbound variable` iterating a possibly-empty array under `set -u` — bash 3.2 (macOS) treats `"${arr[@]}"` on an empty array as an unset-variable reference, unlike bash 4.4+; fixed with `"${arr[@]+"${arr[@]}"}"`. (2) `scripts/harness-status.sh`'s JSONL trend block took **three** rounds, because the first two enforced "never blocks" with an exception allowlist: round 1 guarded `JSONDecodeError`, round 2 added `KeyError`/`TypeError` — and both left `open()` unguarded (it runs before the loop, outside every `try`), so an unreadable or non-UTF-8 log still killed the script under `set -euo pipefail` and silently swallowed the Drift Audit section. **Do not copy the round-2 pattern.** Fixed by putting the boundary on the command — `python3 - "$LOG" <<'PY' || echo "  [unreadable: $LOG]"` — the `|| true` convention the same file already used one section below.

**Lesson:** an exception-type allowlist cannot be proven complete, so it is the wrong tool for "never fail" semantics; bound the block instead. And the boundary defect was missed by every per-line bug hunt (including `/correctness-review`) — it surfaced only when a reviewer asked "is this fix deep enough, or a bandaid?" Ask that on purpose.

**Full doc:** docs/solutions/scripts/bash-empty-array-and-jsonl-parsing-gotchas.md
---

## [2026-07-04] bash-empty-array-and-jsonl-parsing-gotchas-decisions
**Type:** decision
**Module:** scripts/harness-audit
**Tags:** bash-set-u, empty-array-expansion, jsonl-parsing, defensive-parsing, harness-scripts, ci-macos-ubuntu
**Applicable when:** A future spec or plan says a metric/log/artifact should be recorded "every CI run" and the repo has both a per-push/PR workflow and a separate post-merge/event-sourced workflow — check which one the literal wording actually requires before wiring the write into either, especially when the per-push workflow would need a new write permission it doesn't currently have.

A spec literally asked for a trend JSONL line "every CI run." Chose to emit it from `scripts/bookkeeping.sh` (once per merged PR, via the existing permission-holding `post-merge-maintenance.yml`) instead of adding a new write-back step to the per-push `harness-ci.yml` (which would need a new `contents: write` grant and commit to arbitrary PR branches). Narrows the literal wording to "every merge" — flagged by intent-review as an undocumented divergence, then confirmed correct by the user directly.

**Full doc:** docs/solutions/scripts/bash-empty-array-and-jsonl-parsing-gotchas-decisions.md
---

<!--
Example entry shape:

## Async context propagation

**Applies to:** any background task spawning
**Rule:** Use `contextvars.copy_context()` when spawning; otherwise request-scoped state (user, tenant, trace_id) is lost.
**Reference:** docs/solutions/async/context-propagation.md
-->

## [2026-07-10] test-r-dev-tty-does-not-detect-missing-controlling-terminal
**Type:** bug
**Module:** scripts/deploy-harness
**Tags:** bash, dev-tty, controlling-terminal, curl-pipe-bash, harness-scripts, ci-macos-ubuntu, narrow-guard
**Applicable when:** Watch for this when a shell script decides whether it may prompt the user — `[ -r /dev/tty ]`, `[ -t 0 ]`, and `[ -t 1 ]` are all wrong, and the failure is silent.

`[ -r /dev/tty ]` is an `access(2)` mode-bit check on the `/dev/tty` alias node; those bits stay world-readable after `setsid()`, so it returns true in a process with no controlling terminal. The non-interactive fallback was dead code — a tty-less CI run entered the prompt branch, printed a menu nobody could answer, and reached the safe default only because `read … || true` swallowed `ENXIO`. Correct outcome, wrong mechanism, and the intended warning never printed. The only honest test is to open it: `have_tty() { (exec < /dev/tty) 2>/dev/null; }`.

**Full doc:** docs/solutions/scripts/test-r-dev-tty-does-not-detect-missing-controlling-terminal.md
---

## [2026-07-10] unverified-premise-propagates-through-plan-anchored-reviews
**Type:** failure
**Module:** harness
**Tags:** not-observed-not-absent, false-premise, plan-blind-review, correctness-review, ground-truth, review-oracle, resync-conflict
**Applicable when:** Watch for this when a spec, design, or plan asserts that something "is never shipped" / "does not exist" / "can never conflict", and downstream code, tests, and reviews all treat that absence claim as true without one independent `ls` or `git ls-files` against ground truth.

A design doc asserted the harness ships no `*.proposed`; it shipped two, tracked since `f7d2d58`. Nobody ran `ls skills/xia2/`. Per-task spec review, code-quality review, and the test author all passed the false premise — the test even encoded it as a comment. Only the plan-blind `/correctness-review` caught it. Three reviewers agreeing means nothing when all three read the same wrong sentence: this is `rules/behavior.md` §1 `not_observed != absent`, and it is why the correctness and intent oracles are dispatched blind to the plan.

**Full doc:** docs/solutions/harness/unverified-premise-propagates-through-plan-anchored-reviews.md
---

## [2026-07-17] verify-row-must-be-pipe-free-and-under-60s
**Type:** failure
**Module:** verify_summary / ci-strict-gate
**Tags:** verify-table, summary-md, pipe-cell-split, strict-gate, timeout, plan-format-guardrail
**Applicable when:** Writing a `### Verify` row in a spec SUMMARY.md — before pasting any command with a pipe or a whole-suite/build invocation.

The `### Verify` table is machine-parsed data, not prose. `verify_summary` splits each row on `|`, so any pipe in a command (`||`, `&&|`, alternation `a|b`, `cmd | wc`) collides with the delimiter and the row never matches (hit 6× in one session). Separately, `ci-strict-gate` re-runs each Verify command under a 60s cap (= plan-format Guardrail 3), so a full-suite row (`bash scripts/run-tests.sh`) TIMES OUT on cold CI and blocks the PR (hit 1×). Rule: Verify commands must be pipe-free (`grep -e a -e b`, `X; a=$?; test -a`) AND <60s re-runnable — the full suite is a CI `tests` job, cited in prose, never a Verify row.

**Full doc:** docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md
---
