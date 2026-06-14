# Trust Metrics Ledger

Per-task ledger of how the harness classified and verified autonomous work. Appended by the
orchestrator at the DONE disclosure of each task (see `skills/feature-intake/SKILL.md` →
Guardrails). Read alongside `specs/<slug>/SUMMARY.md` — the ledger is the cross-task trend
line; the SUMMARY is the per-task record.

Purpose: calibrate autonomy over time. If under-classification recurs (lane below what the
diff tripped), tighten; if escalations keep resolving as "proceed unchanged", loosen.

## Ledger

<!-- machine-read: the `Affects` column is a contract — always populate with a module/contract name or `-`; do not leave blank -->
| Date | Slug | Lane | Affects | Confidence | Flags | Escalated | Outcome | Notes |
|---|---|---|---|---|---|---|---|---|
| 2026-06-11 | p1-doc-truth | normal | - | high | none | no | shipped (`3798ab3`) | docs/config truthfulness fixes from harness audit |
| 2026-06-11 | p2-doc-cleanup | normal | - | high | none | no | shipped | remaining phantom-reference cleanup + this ledger scaffold |
| 2026-06-11 | mcp-install-wiring | normal | - | high | none | no | shipped | installer wires .mcp.json (merge-not-overwrite) + uvx soft-check; 6-case test suite run |
| 2026-06-11 | p3-hook-fixes | high-risk | - | high | none (hard gate: hooks/*) | human-confirmed | shipped | auto-test hook status-capture fix; strict-default decision: keep warn; audit line-16 claim disproven |
| 2026-06-11 | auto-test-multi-lang | high-risk | - | high | none (hard gate: hooks/*) | human-directed | shipped | auto-test hook ecosystem-aware (py/js/go + AUTO_TEST_CMD/PATTERN); 11-case matrix |
| 2026-06-11 | harness-tests-phase1 | high-risk | - | high | none (corroboration regex false-positive on tests/hooks/) | human-approved | shipped | test framework + 41-case suite (40 pass, 1 xfail) + doc-truth lint + CI matrix |
| 2026-06-11 | harness-tests-phase23 | high-risk | - | high | none (corroboration false-positive on tests/hooks/) | human-directed | shipped | full hook coverage + wiring smoke + 85 recovered pytest + feature-intake canaries |
| 2026-06-11 | hook-bug-fixes | high-risk | - | high | none (hard gate: hooks/*) | human-authorized | shipped | commit-gate `\|\| true` + risk-corroboration regex precision; both xfails → real assertions |
| 2026-06-12 | intent-review-stage | high-risk | templates/SUMMARY.template.md + workflow chain | high | existing behavior, weak proof (hard gate: templates/ + workflow redefine) | human-directed | shipped | /intent-review third oracle (blind to plan; gap/excess/drift); intent captured verbatim at intake; dogfood caught a real gap (uncommitted plan) |
| 2026-06-14 | harness-gap-phase1 | normal | skills/compound prompts + scripts/harness-audit.sh | high | none | no | shipped (`50f5fec`) | gap-closure from 6 research docs; P1-A/P1-D/P2-F found already-done (research stale); built P1-B (ratchet: compound guardrail→backlog) + P1-C (harness-audit.sh advisory drift); suite + lint green; merged PR #18 |
| 2026-06-14 | harness-gap-phase2 | normal | CLAUDE.md (MCP boundary-of-trust note) | high | none | no | done (uncommitted) | Phase 2 ground-truth: P2-E/F/G all already-done (research stale); only P2-H real → added MCP-output-untrusted subsection to CLAUDE.md; lint-doc-truth + suite green |
