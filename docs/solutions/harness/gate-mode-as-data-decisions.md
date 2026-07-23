---
problem_type: decision
module: hooks/risk-corroboration.sh + harness-manifest.json (gate-mode contract)
tags: [manifest-as-authority, gate-modes, config-as-data, fail-closed, settings-json-resync, env-vars, enforcement-vs-classification, index-vs-worktree]
severity: standard
applicable_when: Loosening/adding a commit-gate mode, adding a settings.json key meant for consumers, or any env var a PreToolUse hook must read — check these recorded trade-offs first.
affects:
  - harness-manifest.json
  - hooks/risk-corroboration.sh
  - scripts/check_manifest.py
  - scripts/check_gate_modes_smoke.py
supersedes: null
confidence: high
confirmed_at: 2026-07-23
---

## Applicable When

Loosening/adding a commit-gate mode, adding a `settings.json` key meant for consumers, or any env
var a PreToolUse hook must read.

## Decision 1 — gate mode is data, not code

### Context
Gate modes lived in a `case` statement that `scripts/check_manifest.py` regex-parsed back out of
the hook source — the manifest was *declared* the authority while being validated against the
hook. Loosening one gate = 4-file coordinated edit + CI.
### Options Considered
- Delete `category_mode()` outright — rejected 2026-07-16: the checker regex-parses the branches, deletion fails CI on 8 slugs.
- Status quo (hand-mirrored case).
- Make `mode` load-bearing data in the manifest; hook reads it at runtime; drop the source-regex.
### Decision & Rationale
Data. Removes the *reason* the deletion objection existed instead of fighting the checker.
Fail-safe: slug absent / mode missing / manifest unreadable-or-absent ⇒ `block`. Consumer repos
never get the manifest (deliberate — the 85% firing rate is a meta-repo artifact; consumers stay
strict). Cost of a future loosening: one JSON field.
- Always: when a checker regex-parses source to validate config, invert it — config becomes the runtime input, regex dies.
- Never: hand-mirror the same policy in code and data with a regex bridging them.
### Consequences
`RISK_WARN_CATEGORIES` only loosens (block→warn), never re-tightens — accepted; the manifest edit
is the durable path. `check_gate_modes_smoke.py` pins 2-warn/7-block in CI.

## Decision 2 — where the loosening knob lives (not settings.json)

### Context
Review item said: add an `env` block to root `settings.json` with
`RISK_WARN_CATEGORIES="weakening-validation"`.
### Options Considered
- `env` in root `settings.json` — rejected: `deploy-harness.sh` re-sync merges with the **consumer's** file as base and replaces only `.hooks`; a new top-level key ships on first install and is silently dropped on every re-sync.
- Inline `VAR=x git commit` prefix — impossible: a PreToolUse hook runs *before* the command with the **session** env; the prefix sets the var only for the `git` process. Reproduced empirically.
- Manifest `mode` for durable + `.claude/settings.local.json → env` for session-scoped.
### Decision & Rationale
Split honestly: durable loosening in the manifest; session override in `settings.local.json → env`
(the only place a PreToolUse hook actually inherits env from); delete the impossible advice.
- Always: check deploy-harness merge semantics before adding a top-level `settings.json` key for consumers.
- Never: advise `VAR=x git commit` to influence a PreToolUse hook.
### Consequences
"Reachable knob" = machine-local gitignored config; a shared in-repo knob remains an open
follow-up (intent-review advisory).

## Decision 3 — enforcement mode ≠ risk classification

### Context
Flipping two gates to warn raised: should `/feature-intake` also stop classifying them
`Lane: high-risk` (65% of specs are high-risk)?
### Options Considered
- Loosen both axes together — invalidates intake eval fixture LC-11, redefines intake semantics.
- Warn-mode changes enforcement only.
### Decision & Rationale
Enforcement only. Fixes the pain (blocked commit, no working override) without redefining intake;
LC-11 stays valid; warn still prints to stderr so the signal survives. The 65% rate is a
*classification* problem → separate spec.
- Always: change one axis (enforcement vs classification) per spec.
### Consequences
High-risk lane rate stays inflated until the classification spec lands. Blocking-gate trip rate
expected 85% → ~15%.

## Decision 4 — policy read is index-side

### Context
Codex PR #160: hook read the manifest from the worktree while all gated signals are index-side.
### Options Considered
- Worktree read (simpler) — an uncommitted local edit weakens the gate for a commit that doesn't contain it.
- `git show :harness-manifest.json`, fail-closed.
### Decision & Rationale
Index — the policy input must come from the same tree as the signals it gates. Loosening now
requires *staging* the manifest edit, auditable in the same commit.
- Always: commit-time gates read policy files from the index (`git show :<path>`).
- Never: let an unstaged worktree edit change the enforcement outcome for a staged commit.
### Consequences
A manifest staged for deletion or unreadable from the index blocks rather than allows. Full story:
[gate-config-must-read-index](gate-config-must-read-index.md).

## Related

- docs/solutions/harness/gate-config-must-read-index.md
- docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md
- docs/solutions/harness/resync-protected-files-decisions.md
