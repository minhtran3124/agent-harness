---
problem_type: decision
module: hooks/risk-corroboration.sh + hooks/lib/gate-modes.default.sh (consumer gate-mode fallback)
tags: [consumer-fallback, gate-modes, index-vs-worktree, fail-closed, policy-toctou, dot-claude-gitignored, manifest-as-authority, embedded-defaults, break-glass]
severity: critical
applicable_when: Deciding where a consumer repo's commit-gate hook reads per-gate block/warn modes from — it must resolve only from the git index (`git show :harness-manifest.json`) or embedded in-hook defaults, never from `.claude/` or any worktree file, because `.claude/` is gitignored in consumers and therefore agent-writable and un-index-checkable.
affects:
  - hooks/risk-corroboration.sh
  - hooks/lib/gate-modes.default.sh
  - harness-manifest.json
supersedes: null
confidence: high
confirmed_at: 2026-08-06
---

## Applicable When

Deciding where a consumer repo's `risk-corroboration.sh` (or any commit-gating hook) reads its
per-gate block/warn policy from, or reviewing a proposal to add a policy read from `.claude/`.

## Problem

Before this change, a consumer repo never received `harness-manifest.json` (deploy-harness ships
only `.hooks`), and the hook's fail-safe treated an absent/unreadable manifest as **`block` for
every gate** — see `gate-mode-as-data-decisions.md` Decision 1 ("consumers stay strict"). Net
effect on a consumer: **block-all**. Every commit that tripped any detectable hard-gate signal was
denied below the `high-risk` lane, with no working parity to the meta-repo's 2-warn/7-block split
(`workflow-engine` and `weakening-validation` are warn-mode upstream). Consumers were stuck.

The obvious "fix" — ship the manifest to `.claude/` and read modes from
`.claude/harness-manifest.json` at commit time (the rejected **B-hybrid**, B2+B3) — reintroduces a
**critical** vulnerability.

## Decision — B3-only: index or embedded defaults, never `.claude/`

A consumer's `risk-corroboration.sh` resolves gate modes from exactly **two index-safe sources**,
in order:

1. `git show :harness-manifest.json` — used only when the consumer **opts in** to tracking a root
   `harness-manifest.json` (index-side, staged, auditable in the same commit).
2. **Embedded defaults** baked into the hook — `hooks/lib/gate-modes.default.sh`, hand-mirrored
   from the meta-repo `harness-manifest.json` and CI-drift-guarded to give **2 warn / 7 block
   parity**. This is the source for every ordinary consumer (no tracked manifest).

The hook **never** reads `.claude/harness-manifest.json` or any worktree/on-disk policy file.

## Why not `.claude/` (the rejected B-hybrid)

`.claude/` is **gitignored in consumers** → its files can never be staged → the index check that
protects every other gate input cannot protect a policy read from there. An agent editing
`.claude/harness-manifest.json` to `"mode": "warn"` would loosen the gate for the very tree being
committed, without that edit ever entering the commit. That is exactly the policy-TOCTOU that
[[gate-config-must-read-index]] (commit `880eb15`, severity **critical**) closed by moving the
manifest read to `git show :harness-manifest.json`, fail-closed. "Harness-owned / derived" and
"only loosens to parity" are **not write-guards** — nothing forces the on-disk file to match
upstream at commit time. B3 keeps policy in hook **code** (high-blast, index-checked when edited),
so there is no agent-writable, un-index-checkable vector at all.

## Consequences

- Absent-manifest fallback changes from **block-all** to **embedded 2-warn/7-block parity**. This
  revises `gate-mode-as-data-decisions.md` Decision 1's "consumers stay strict" fail-safe: the
  fail-safe is now parity, not deny-everything.
- **Drift risk** (embedded defaults vs manifest) is mitigated by `scripts/check_gate_modes_smoke.py`,
  which pins the hand-mirrored `hooks/lib/gate-modes.default.sh` to `harness-manifest.json` in CI; a
  mismatch fails CI, so the duplicate never silently diverges. (The mirror is manual — change the
  manifest, then update the defaults file; CI enforces they match.)
- **Break-glass loosening** (unchanged mechanism, per `gate-mode-as-data-decisions.md` Decision 2):
  durable block→warn lives in the manifest `mode` field; session-scoped override is
  `RISK_WARN_CATEGORIES` in the machine-local `settings.local.json` `env` block — the only place a
  PreToolUse hook actually inherits env. `RISK_WARN_CATEGORIES` only loosens, never re-tightens.
- If a consumer later wants its own tracked policy, use path (1) index-side only — **never** add
  back a `.claude/` read.

## Related

- docs/solutions/harness/gate-config-must-read-index.md — the critical policy-TOCTOU this decision refuses to reopen
- docs/solutions/harness/gate-mode-as-data-decisions.md — gate mode is data; where the loosening knob lives; index-side policy read
