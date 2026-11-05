#!/bin/bash
source "$(dirname "$0")/../lib.sh"
SKILL="plugins/harness/skills/compound/SKILL.md"

t "compound preserves all four complete-track gates"
for track in bug knowledge decision failure; do grep -q "| $track |" "$ROOT/$SKILL" || { fail "missing $track"; finish; }; done
pass

t "compound delegates index construction to its deterministic authority"
grep -q 'scripts/rebuild_solution_index.py' "$ROOT/$SKILL" && grep -q 'Do not manually scan/sort/render' "$ROOT/$SKILL" && pass || fail "index authority missing"

t "compound keeps promotion and proposed-ratchet handling"
grep -q 'critical-patterns.md' "$ROOT/$SKILL" && grep -q 'proposed:' "$ROOT/$SKILL" && pass || fail "promotion or ratchet missing"

t "compound treats a prediction → measured pair as a learning source"
grep -qF 'prediction → measured' "$ROOT/$SKILL" && pass || fail "prediction → measured source missing"

t "compound decision-track docs use plugin-root paths, not repo-relative ones"
D="$ROOT/plugins/harness/skills/compound"
if grep -n 'plugins/harness/scripts/write_adrs\|`docs/adr/README.md`' "$D/templates/decision-consolidated.md" "$D/README.md" >/dev/null; then fail "repo-relative write_adrs path or docs/adr/README.md reference"; else pass; fi

t "compound decision track sources how_to_reverse/confidence from the extractor and links ADRs, not solutions"
if grep -q 'How_to_Reverse' "$D/subagents/decision-extractor-prompt.md" && grep -q 'Never invent a value' "$ROOT/$SKILL" && grep -q 'ADR path' "$ROOT/$SKILL"; then pass; else fail "decision track fields or ADR link missing"; fi

t "compound fallback for empty extractor fields matches the extractor prompt and write_adrs validation"
if grep -q '`\[none\]`' "$ROOT/$SKILL" && grep -q 'not exactly `high`, `medium` or `low`' "$ROOT/$SKILL"; then pass; else fail "fallback does not cover [none] How_to_Reverse and invalid Confidence"; fi

t "no template or solutions entry writes problem_type: decision (one decision store: docs/adr)"
if grep -rlq '^problem_type: decision' "$D/templates" "$ROOT/docs/solutions" || [ -e "$D/templates/decision-track.md" ]; then fail "second decision store still written"; else pass; fi

t "docs/solutions/INDEX.md matches the solution docs (regenerated after a problem_type change)"
if python3 "$ROOT/plugins/harness/scripts/rebuild_solution_index.py" --root "$ROOT" --check >/dev/null 2>&1; then pass; else fail "INDEX.md is stale; run rebuild_solution_index.py"; fi

finish
