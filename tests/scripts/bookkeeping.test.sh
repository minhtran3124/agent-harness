#!/bin/bash
# Unit tests for scripts/bookkeeping.sh — offline proof of the logic the GitHub
# Action wraps (the Action itself can't run locally). The script records a merged PR
# in CHANGELOG.md and VERSION only.
source "$(dirname "$0")/../lib.sh"

SCRIPT="$ROOT/scripts/bookkeeping.sh"

# Build a throwaway repo layout: VERSION and CHANGELOG.
make_fixture() {
  local d
  d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  printf '%s\n' "${1:-0.2.0}" > "$d/VERSION"
  printf '# Changelog\n\n## [Unreleased]\n\n## [0.2.0] — 2026-06-14\n\n### Changed\n- seed\n' > "$d/CHANGELOG.md"
  echo "$d"
}

# ── minor bump when a contract path (skills/) changed ────────────────────────
t "bumps MINOR when the diff touches a contract path (skills/)"
d=$(make_fixture 0.2.0)
bash "$SCRIPT" --pr 42 --title T --files "plugins/harness/skills/foo/SKILL.md" --date 2026-07-03 --root "$d" >/dev/null
if [ "$(cat "$d/VERSION")" = "0.3.0" ]; then pass; else fail "want 0.3.0, got $(cat "$d/VERSION")"; fi

# ── patch bump for a docs-only diff ──────────────────────────────────────────
t "bumps PATCH for a docs-only diff"
d=$(make_fixture 0.2.0)
bash "$SCRIPT" --pr 42 --title T --files "docs/x.md" --date 2026-07-03 --root "$d" >/dev/null
if [ "$(cat "$d/VERSION")" = "0.2.1" ]; then pass; else fail "want 0.2.1, got $(cat "$d/VERSION")"; fi

# ── CHANGELOG gets a new dated version section under [Unreleased] ─────────────
t "inserts a dated version section into CHANGELOG under [Unreleased]"
d=$(make_fixture 0.2.0)
bash "$SCRIPT" --pr 7 --title "cool fix" --files "plugins/harness/hooks/x.sh" --date 2026-07-03 --root "$d" >/dev/null
cl=$(cat "$d/CHANGELOG.md")
# new section must be 0.3.0 (hooks/ = minor), dated, with the entry, and above the old 0.2.0
if echo "$cl" | grep -q '## \[0.3.0\] — 2026-07-03' && echo "$cl" | grep -q 'cool fix (PR #7)' \
   && [ "$(grep -n '## \[0.3.0\]' "$d/CHANGELOG.md" | cut -d: -f1)" -lt "$(grep -n '## \[0.2.0\]' "$d/CHANGELOG.md" | cut -d: -f1)" ]; then pass
else fail "CHANGELOG section wrong:\n$cl"; fi

# ── idempotency: re-running for the same PR is a no-op (no double entry/bump) ──
t "is idempotent — second run for the same PR does not double-record or double-bump"
d=$(make_fixture 0.2.0)
bash "$SCRIPT" --pr 99 --title T --files "plugins/harness/skills/x/SKILL.md" --date 2026-07-03 --root "$d" >/dev/null
v1=$(cat "$d/VERSION"); n1=$(grep -c 'PR #99' "$d/CHANGELOG.md")
bash "$SCRIPT" --pr 99 --title T --files "plugins/harness/skills/x/SKILL.md" --date 2026-07-03 --root "$d" >/dev/null
v2=$(cat "$d/VERSION"); n2=$(grep -c 'PR #99' "$d/CHANGELOG.md")
if [ "$v1" = "$v2" ] && [ "$n1" -eq 1 ] && [ "$n2" -eq 1 ]; then pass
else fail "not idempotent: version $v1->$v2, entries $n1->$n2"; fi

# ── only the VERSION and CHANGELOG files are written ──────────────────────────
t "writes nothing but VERSION and CHANGELOG.md"
d=$(make_fixture 0.2.0)
bash "$SCRIPT" --pr 42 --title T --files "docs/x.md" --date 2026-07-03 --root "$d" >/dev/null
extra=$(cd "$d" && find . -type f | sort | tr '\n' ' ')
if [ "$extra" = "./CHANGELOG.md ./VERSION " ]; then pass; else fail "unexpected files: $extra"; fi

# ── injection: a title with a literal \n must NOT forge a CHANGELOG heading ────
t "title with literal backslash-n does not inject a CHANGELOG heading (awk ENVIRON, not -v)"
d=$(make_fixture 0.2.0)
bash "$SCRIPT" --pr 11 --title 'evil\n## [9.9.9] — hijack' --files "docs/x.md" --date 2026-07-03 --root "$d" >/dev/null
# A real forged heading would be at line-start; literal backslash-n stays mid-line (harmless text).
if grep -qE '^## \[9.9.9\]' "$d/CHANGELOG.md"; then fail "heading injection: 9.9.9 forged at line start"; else pass; fi

# ── no [Unreleased] section: still inserts (no silent drop) ───────────────────
t "CHANGELOG without [Unreleased] still gets a version section (no silent drop)"
d=$(make_fixture 0.2.0)
printf '# Changelog\n\n## [0.2.0] — 2026-06-14\n\n- seed\n' > "$d/CHANGELOG.md"
bash "$SCRIPT" --pr 12 --title "t" --files "plugins/harness/hooks/x.sh" --date 2026-07-03 --root "$d" >/dev/null
if grep -q '## \[0.3.0\] — 2026-07-03' "$d/CHANGELOG.md"; then pass; else fail "section dropped:\n$(cat "$d/CHANGELOG.md")"; fi

# ── idempotency anchors to an entry's trailing marker, not any mention ────────
t "a free-text mention of 'PR #N' in another entry does not block recording the real PR #N"
d=$(make_fixture 0.2.0)
printf '\n- revert PR #77 broke things (PR #70)\n' >> "$d/CHANGELOG.md"
bash "$SCRIPT" --pr 77 --title "real 77" --files "docs/x.md" --date 2026-07-03 --root "$d" >/dev/null
if grep -q 'real 77 (PR #77)' "$d/CHANGELOG.md"; then pass; else fail "real PR #77 was wrongly skipped"; fi

# ── the plugin manifest version follows VERSION ───────────────────────────────
t "bumps plugin.json version together with VERSION, touching only that line"
d=$(make_fixture 0.2.0)
mkdir -p "$d/plugins/harness/.claude-plugin"
printf '{\n  "name": "harness",\n  "version": "0.2.0",\n  "description": "d, \\"version\\": x"\n}\n' > "$d/plugins/harness/.claude-plugin/plugin.json"
before=$(grep -v '"version": "0.2.0"' "$d/plugins/harness/.claude-plugin/plugin.json")
bash "$SCRIPT" --pr 50 --title T --files "plugins/harness/skills/x/SKILL.md" --date 2026-07-03 --root "$d" >/dev/null
after=$(grep -v '"version": "0.3.0"' "$d/plugins/harness/.claude-plugin/plugin.json")
if grep -q '^  "version": "0.3.0",$' "$d/plugins/harness/.claude-plugin/plugin.json" && [ "$before" = "$after" ] \
   && bash "$ROOT/scripts/check-plugin-version.sh" --root "$d" >/dev/null; then pass
else fail "manifest not bumped cleanly:\n$(cat "$d/plugins/harness/.claude-plugin/plugin.json")"; fi

t "a re-run for the same PR leaves plugin.json version alone (idempotent)"
bash "$SCRIPT" --pr 50 --title T --files "docs/x.md" --date 2026-07-03 --root "$d" >/dev/null
if grep -q '"version": "0.3.0"' "$d/plugins/harness/.claude-plugin/plugin.json"; then pass; else fail "manifest changed on re-run"; fi

finish
