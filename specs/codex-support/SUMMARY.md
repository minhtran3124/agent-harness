# codex-support — Summary

Lane: high-risk
Confidence: high
Reason: Adds a second agent-runtime target for the whole harness — touches the workflow engine (skills/, agents/, rules/), every hook, the install/deploy path, and the hard-gate enforcement surface. `workflow-engine` + `high-blast` + `external-provider` fire.
Flags: workflow-engine, high-blast, external-provider, public-contract
Affects: hook-registration, artifact-schema-plan, hard-gate-vocabulary, lane-evidence-mapping (all four contracts gain a second consumer runtime)
Input-type: new initiative

### Intent

> make the deep research and deep review current codebase in current repo (on simplify branch)
> now i want to support for the user with codex. Let thinking and make the overral design + high level spec for it.
> need to high lvl design first, dont go too detail or implementation.

Follow-up (2026-08-08) — the three design decisions:

> 1. mục tiêu là codex chạy các agent đó luôn, chứ ko phải chỉ là reviewer, ngang hàng như với claude code
> 2. codex là runtime ngang hàng
> 3. ship advisory

## What changed

Design only — no code. Produced `design.md`: a runtime-adapter architecture that lets the
existing harness drive OpenAI Codex CLI alongside Claude Code, from one set of sources.

### Rationale

Codex CLI converged on Claude Code's extensibility model during 2026 (skills with the same
`SKILL.md` + `name`/`description` frontmatter, lifecycle hooks with the same stdin-JSON /
exit-2 / `hookSpecificOutput.additionalContext` / `permissionDecision: deny` contract, and
first-class subagents). That convergence makes a **shared-source + thin-adapter** design
viable where a fork would previously have been the only option. The design's centre of gravity
is therefore *neutralising the core*, not writing a Codex port.

### Alternatives considered

- **Fork the harness per runtime** — rejected: doubles the maintenance surface of a repo whose
  core defect class is instruction drift between copies (see `gh-143-context-propagation`).
- **Inline the rules into `AGENTS.md`** — rejected: that is precisely the `stale-inline-policy`
  defect Codex itself caught on PR #141.
- **Codex-only "advisory" harness (docs, no enforcement)** — rejected as the *end state*, but
  adopted per decision D3 as the honest, transitional *degraded mode* of the enforcement layer
  while Codex hook coverage lands upstream (see design §6).
- **Best-effort support tier** — rejected by decision D2; Codex is a peer runtime, so parity is a
  release gate and the ledger becomes an owned, expiring exception list rather than a gap inventory.
- **Codex as reviewer only** — rejected by decision D1; Codex drives the agents, which puts the
  subagent TOML emitter and `sandbox_mode` reviewer isolation on the critical path and forces
  ensemble diversity to become runtime-aware (design §6a).

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Design artifact exists and is non-empty | `test -s specs/codex-support/design.md` | 0 | design-stage only; no code changed | |

### Not auto-verified

- Codex hook payload field names, tool-name aliasing, and event coverage — reached **traceability**
  (official + third-party docs read, cross-checked against two open `openai/codex` coverage issues);
  not re-run because no Codex CLI was executed in this session. Design §7 makes empirical
  confirmation the Phase-0 blocking spike for exactly this reason.
- Claim that the four `file_path`-reading hooks fail *open* under Codex — reached **traceability**
  (read from the hooks' own `jq '// empty'` fallbacks + the documented `apply_patch` payload
  shape); not re-run against a live Codex session.

### Rollback

- `git revert <sha>` — design document only; nothing is wired.

### Harness-Delta

- backlog — the design surfaces a pre-existing single-runtime dependency (path-scoped `paths:`
  rule auto-loading is load-bearing but has no oracle proving delivery). Worth a
  `docs/solutions/` entry independent of whether Codex support ships.
