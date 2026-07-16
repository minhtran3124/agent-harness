# brainstorming-gate-fix — Summary

Lane: tiny
Confidence: high
Reason: Prose-only edit to one skill doc (skills/brainstorming/SKILL.md); no hooks, settings, scripts, or contracts touched; direction fixed by review finding C2 and user instruction.
Flags: none
Affects: skills/brainstorming (routing semantics prose; feature-intake stays the routing authority)
Input-type: harness improvement

### Intent

"start for C2 - brainstorming hard-gate" — per docs/reviews/over-engineering-review-2026-07-16.md §2 C2: brainstorming's HARD-GATE ("EVERY project regardless of perceived simplicity") contradicts feature-intake's lane routing; delete the "Too Simple To Need A Design" block and state that brainstorming applies only when intake routes to it.

## What changed

Removed the "Anti-Pattern: This Is Too Simple To Need A Design" block and the "applies to EVERY project" claim that made brainstorming assert gate authority over routing it does not own. Added a "When this skill applies" paragraph: `/feature-intake` decides WHETHER to brainstorm (high-risk lane, real design fork, ambiguous direction); this skill governs HOW once routed. The HARD-GATE itself is kept but re-scoped to "once routed here" — with an explicit escape that mid-brainstorm simplicity discoveries go back to the user for re-routing rather than silently skipping to implementation. Frontmatter description updated to match (was "You MUST use this before any creative work").

### Rationale

Two skills claimed authority over the same decision (brainstorm-everything vs lane routing), forcing an executing LLM to guess which wins. One authority (intake), one job per skill. The gate's real value — no implementation before an approved design *within a brainstorm* — is preserved, arguably strengthened by the explicit no-silent-downgrade rule.

### Alternatives considered

- Delete the HARD-GATE entirely: rejected — inside a routed brainstorm the gate is load-bearing (prevents mid-dialogue implementation jumps).
- Keep "every project" but exempt lanes in a footnote: rejected — keeps two authorities, just better hidden.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| "every project" gate claim gone | `grep -rq -e "EVERY project regardless" -e "Too Simple To Need" -e "MUST use this before any creative work" skills rules` | 1 | no match = C2 closed |
| routing authority stated | `grep -q "feature-intake\` is the routing authority" skills/brainstorming/SKILL.md` | 0 | intake decides WHETHER |
| gate survives, re-scoped | `grep -q "Once routed here" skills/brainstorming/SKILL.md` | 0 | no silent downgrade |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | clean |
| full suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN |

### Rollback

- `git revert <commit>` on the feature branch (single prose commit, no contracts).

### Harness-Delta

- none
