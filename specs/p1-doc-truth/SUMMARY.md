# p1-doc-truth — Summary

Lane: normal
Confidence: high
Reason: Docs/config truthfulness fixes from harness audit; no risk flags fired, no hard gate (no edits to settings.json, hooks/*, or skill engines).
Flags: none
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

## What changed

Restored the project MCP config as tracked `.mcp.json` (code-review-graph via uvx) and
updated `mcp.json` references in README.md/CLAUDE.md; scaffolded `docs/solutions/`
(README, INDEX, critical-patterns) from bootstrap-xia2 templates; corrected the
risk-corroboration missing-Lane wording (warn-by-default, `RISK_CORROBORATION_STRICT=1`
opt-in) in `rules/orchestration.md` and `skills/feature-intake/SKILL.md`.

### Rationale

CLAUDE.md/README pointed at paths that do not exist (`mcp.json`, `docs/solutions/INDEX.md`)
and overstated hook enforcement; these docs load into every session, so falsehoods misdirect
the agent. Restoring the file as `.mcp.json` (the name Claude Code actually reads) fixes the
mismatch functionally instead of rewording two docs.

### Alternatives considered

- Reword docs to drop the MCP config claims instead of restoring the file — rejected: the
  code-review-graph workflow in CLAUDE.md depends on the server being wired.
- Mark `docs/solutions/` as "created on bootstrap" — rejected: scaffolding it makes the
  existing pointers true and the KB usable immediately.

### Deviations

- Rule 2 — also corrected the same false "missing Lane = fail-closed" claim in
  `skills/feature-intake/SKILL.md` (user-approved scope named CLAUDE.md/orchestration.md;
  the SKILL.md carries the identical falsehood). Audit found CLAUDE.md's hook-table row is
  actually accurate, so it was left unchanged.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| No stale non-dotted `mcp.json` refs | `grep -rn '[^.]mcp\.json' CLAUDE.md README.md HARNESS.md rules/ skills/README.md` | 1 | no matches |
| No stale `fail-closed` claims | `grep -rn "fail-closed" rules/ skills/ CLAUDE.md \| grep -v STRICT` | 1 | no matches |
| Referenced paths exist | `ls .mcp.json docs/solutions/{INDEX,critical-patterns,README}.md` | 0 | |
| `.mcp.json` valid JSON | `jq . .mcp.json` | 0 | |
| `.mcp.json` no longer gitignored | `git check-ignore .mcp.json` | 1 | not ignored |
| `.claude/` clone resynced | `bash scripts/deploy-harness.sh && diff -rq skills/ .claude/skills/` | 0 | also cleared stale clone README |

### Rollback

- `git revert 3798ab3`

### Harness-Delta

- backlog — recurring doc drift (2nd occurrence); proposal: lint script asserting that
  repo-relative paths referenced in CLAUDE.md/README.md/HARNESS.md/skills/README.md exist.
