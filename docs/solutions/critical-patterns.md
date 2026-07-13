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
