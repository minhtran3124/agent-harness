#!/bin/bash
# Unit tests for scripts/bookkeeping.sh — offline proof of the logic the GitHub
# Action wraps (the Action itself can't run locally).
source "$(dirname "$0")/../lib.sh"

SCRIPT="$ROOT/scripts/bookkeeping.sh"

# Build a throwaway repo layout: VERSION, CHANGELOG, ledger, and an optional SUMMARY.
make_fixture() {
  local d slug="$2"
  d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  printf '%s\n' "${1:-0.2.0}" > "$d/VERSION"
  mkdir -p "$d/docs/harness-experimental"
  printf '# Trust Metrics Ledger\n\n## Ledger\n\n| Date | Slug | Lane | Affects | Confidence | Flags | Escalated | Outcome | Notes |\n|---|---|---|---|---|---|---|---|---|\n| 2026-06-14 | old | normal | - | high | none | no | shipped | seed row |\n' > "$d/docs/harness-experimental/trust-metrics.md"
  printf '# Changelog\n\n## [Unreleased]\n\n## [0.2.0] — 2026-06-14\n\n### Changed\n- seed\n' > "$d/CHANGELOG.md"
  if [ -n "$slug" ]; then
    mkdir -p "$d/specs/$slug"
    printf 'Lane: high-risk\nConfidence: medium\nFlags: existing-behavior, weak-proof\nAffects: hooks/foo.sh\n' > "$d/specs/$slug/SUMMARY.md"
  fi
  echo "$d"
}

# ── ledger row appended, fields parsed from SUMMARY ──────────────────────────
t "appends a ledger row with Lane/Confidence/Flags/Affects parsed from the SUMMARY"
d=$(make_fixture 0.2.0 my-feature)
bash "$SCRIPT" --pr 42 --title "add a thing" --sha abc123 \
  --files "$(printf 'specs/my-feature/SUMMARY.md\nskills/foo/SKILL.md')" --date 2026-07-03 --root "$d" >/dev/null
row=$(tail -1 "$d/docs/harness-experimental/trust-metrics.md")
if echo "$row" | grep -q 'my-feature' && echo "$row" | grep -q 'high-risk' \
   && echo "$row" | grep -q 'medium' && echo "$row" | grep -q 'hooks/foo.sh' \
   && echo "$row" | grep -q 'PR #42' && echo "$row" | grep -q 'add a thing'; then pass
else fail "row missing expected fields: $row"; fi

# ── minor bump when a contract path (skills/) changed ────────────────────────
t "bumps MINOR when the diff touches a contract path (skills/)"
d=$(make_fixture 0.2.0 my-feature)
bash "$SCRIPT" --pr 42 --title T --sha s --files "skills/foo/SKILL.md" --date 2026-07-03 --root "$d" >/dev/null
if [ "$(cat "$d/VERSION")" = "0.3.0" ]; then pass; else fail "want 0.3.0, got $(cat "$d/VERSION")"; fi

# ── patch bump for a docs-only diff ──────────────────────────────────────────
t "bumps PATCH for a docs-only diff"
d=$(make_fixture 0.2.0 my-feature)
bash "$SCRIPT" --pr 42 --title T --sha s --files "$(printf 'docs/x.md\nspecs/my-feature/SUMMARY.md')" --date 2026-07-03 --root "$d" >/dev/null
if [ "$(cat "$d/VERSION")" = "0.2.1" ]; then pass; else fail "want 0.2.1, got $(cat "$d/VERSION")"; fi

# ── CHANGELOG gets a new dated version section under [Unreleased] ─────────────
t "inserts a dated version section into CHANGELOG under [Unreleased]"
d=$(make_fixture 0.2.0 my-feature)
bash "$SCRIPT" --pr 7 --title "cool fix" --sha s --files "hooks/x.sh" --date 2026-07-03 --root "$d" >/dev/null
cl=$(cat "$d/CHANGELOG.md")
# new section must be 0.3.0 (hooks/ = minor), dated, with the entry, and above the old 0.2.0
if echo "$cl" | grep -q '## \[0.3.0\] — 2026-07-03' && echo "$cl" | grep -q 'cool fix (PR #7)' \
   && [ "$(grep -n '## \[0.3.0\]' "$d/CHANGELOG.md" | cut -d: -f1)" -lt "$(grep -n '## \[0.2.0\]' "$d/CHANGELOG.md" | cut -d: -f1)" ]; then pass
else fail "CHANGELOG section wrong:\n$cl"; fi

# ── idempotency: re-running for the same PR is a no-op (no double row/bump) ───
t "is idempotent — second run for the same PR does not double-append or double-bump"
d=$(make_fixture 0.2.0 my-feature)
bash "$SCRIPT" --pr 99 --title T --sha s --files "skills/x/SKILL.md" --date 2026-07-03 --root "$d" >/dev/null
v1=$(cat "$d/VERSION"); n1=$(grep -c 'PR #99' "$d/docs/harness-experimental/trust-metrics.md")
bash "$SCRIPT" --pr 99 --title T --sha s --files "skills/x/SKILL.md" --date 2026-07-03 --root "$d" >/dev/null
v2=$(cat "$d/VERSION"); n2=$(grep -c 'PR #99' "$d/docs/harness-experimental/trust-metrics.md")
trend_lines=$(wc -l < "$d/docs/harness-experimental/audit-log.jsonl" | tr -d ' ')
if [ "$v1" = "$v2" ] && [ "$n1" -eq 1 ] && [ "$n2" -eq 1 ] && [ "$trend_lines" -eq 1 ]; then pass
else fail "not idempotent: version $v1->$v2, rows $n1->$n2, trend lines $trend_lines (want 1)"; fi

# ── appends a well-formed JSONL trend row tagged with the PR number ───────────
t "appends a valid JSONL trend row to audit-log.jsonl with the right pr field"
d=$(make_fixture 0.2.0 my-feature)
bash "$SCRIPT" --pr 42 --title "add a thing" --sha abc123 \
  --files "$(printf 'specs/my-feature/SUMMARY.md\nskills/foo/SKILL.md')" --date 2026-07-03 --root "$d" >/dev/null
trend_row=$(tail -1 "$d/docs/harness-experimental/audit-log.jsonl")
pr_field=$(printf '%s' "$trend_row" | python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["pr"])')
if printf '%s' "$trend_row" | python3 -c 'import json,sys; json.loads(sys.stdin.read())' >/dev/null 2>&1 \
   && [ "$pr_field" = "42" ]; then pass
else fail "trend row invalid or wrong pr: $trend_row"; fi

# ── no SUMMARY in the PR: slug falls back to pr-N, fields to '-' ──────────────
t "falls back to slug pr-N and '-' fields when the PR added no SUMMARY"
d=$(make_fixture 0.2.0 "")
bash "$SCRIPT" --pr 5 --title "chore thing" --sha s --files "docs/only.md" --date 2026-07-03 --root "$d" >/dev/null
row=$(tail -1 "$d/docs/harness-experimental/trust-metrics.md")
if echo "$row" | grep -q 'pr-5' && echo "$row" | grep -q 'PR #5'; then pass
else fail "fallback row wrong: $row"; fi

# ── #1 injection: a title with a literal \n must NOT forge a CHANGELOG heading ──
t "title with literal backslash-n does not inject a CHANGELOG heading (awk ENVIRON, not -v)"
d=$(make_fixture 0.2.0 my-feature)
bash "$SCRIPT" --pr 11 --title 'evil\n## [9.9.9] — hijack' --sha s --files "docs/x.md" --date 2026-07-03 --root "$d" >/dev/null
# A real forged heading would be at line-start; literal backslash-n stays mid-line (harmless text).
if grep -qE '^## \[9.9.9\]' "$d/CHANGELOG.md"; then fail "heading injection: 9.9.9 forged at line start"; else pass; fi

# ── #2 no [Unreleased] section: still inserts (no silent drop) ────────────────
t "CHANGELOG without [Unreleased] still gets a version section (no silent drop)"
d=$(make_fixture 0.2.0 my-feature)
printf '# Changelog\n\n## [0.2.0] — 2026-06-14\n\n- seed\n' > "$d/CHANGELOG.md"
bash "$SCRIPT" --pr 12 --title "t" --sha s --files "hooks/x.sh" --date 2026-07-03 --root "$d" >/dev/null
if grep -q '## \[0.3.0\] — 2026-07-03' "$d/CHANGELOG.md"; then pass; else fail "section dropped:\n$(cat "$d/CHANGELOG.md")"; fi

# ── #3 idempotency anchors to the outcome marker, not free-text notes ─────────
t "a free-text 'PR #N' in notes does not block recording the real PR #N"
d=$(make_fixture 0.2.0 my-feature)
printf '| 2026-06-01 | z | normal | - | high | none | no | shipped | revert PR #77 broke things |\n' >> "$d/docs/harness-experimental/trust-metrics.md"
bash "$SCRIPT" --pr 77 --title "real 77" --sha s --files "docs/x.md" --date 2026-07-03 --root "$d" >/dev/null
if grep -qF "shipped (PR #77, " "$d/docs/harness-experimental/trust-metrics.md"; then pass; else fail "real PR #77 was wrongly skipped"; fi

# ── #4 a pipe in the title does not add ledger table columns ──────────────────
t "title containing '|' is escaped so the ledger row keeps 9 columns"
d=$(make_fixture 0.2.0 my-feature)
bash "$SCRIPT" --pr 13 --title 'fix a | b | c' --sha s --files "docs/x.md" --date 2026-07-03 --root "$d" >/dev/null
row=$(tail -1 "$d/docs/harness-experimental/trust-metrics.md")
# 9 columns => 10 unescaped pipe delimiters; escaped \| must not count. Strip \| first.
delims=$(printf '%s' "$row" | sed 's/\\|//g' | tr -cd '|' | wc -c | tr -d ' ')
if [ "$delims" -eq 10 ]; then pass; else fail "row has $delims delimiters (want 10): $row"; fi

# ── #5 bold **Lane:** in a SUMMARY is parsed, not degraded to '-' ─────────────
t "bold **Lane:** in SUMMARY is parsed into the ledger row"
d=$(make_fixture 0.2.0 bold-feature)
printf '**Lane:** high-risk\n**Confidence:** high\n' > "$d/specs/bold-feature/SUMMARY.md"
bash "$SCRIPT" --pr 14 --title t --sha s --files "specs/bold-feature/SUMMARY.md" --date 2026-07-03 --root "$d" >/dev/null
if tail -1 "$d/docs/harness-experimental/trust-metrics.md" | grep -q 'high-risk'; then pass; else fail "bold Lane not parsed: $(tail -1 "$d/docs/harness-experimental/trust-metrics.md")"; fi

finish
