#!/bin/bash
source "$(dirname "$0")/../lib.sh"
CHK="$ROOT/scripts/check_release_summary.py"
FX="$ROOT/tests/fixtures/release-summary"
TMP=$(mktemp -d); _CLEANUP_DIRS+=("$TMP")

t "checker passes the committed sample draft"
python3 "$CHK" "$FX/fact-list.json" "$FX/summary-draft.md" >/dev/null && pass || fail "good draft rejected"

t "checker rejects a (#n) that is not in the fact list"
sed 's/(#15)/(#99)/' "$FX/summary-draft.md" > "$TMP/a.md"
python3 "$CHK" "$FX/fact-list.json" "$TMP/a.md" >/dev/null && fail "unknown PR accepted" || pass

t "checker validates every number in a grouped citation"
sed 's/(#15)/(#15, #99)/' "$FX/summary-draft.md" > "$TMP/g.md"
python3 "$CHK" "$FX/fact-list.json" "$TMP/g.md" >/dev/null && fail "unknown PR in group accepted" || pass

t "checker accepts a grouped citation of known PRs"
sed 's/(#15)/(#15, #16)/' "$FX/summary-draft.md" > "$TMP/h.md"
python3 "$CHK" "$FX/fact-list.json" "$TMP/h.md" >/dev/null && pass || fail "valid grouped citation rejected"

t "checker ignores a bare year after a citation in the same parentheses"
sed 's/(#15)/(#15, 2024)/' "$FX/summary-draft.md" > "$TMP/y.md"
python3 "$CHK" "$FX/fact-list.json" "$TMP/y.md" >/dev/null && pass || fail "prose year flagged as PR"

t "checker rejects a PR that is only in excluded"
sed 's/(#16)/(#14)/' "$FX/summary-draft.md" > "$TMP/e.md"
python3 "$CHK" "$FX/fact-list.json" "$TMP/e.md" >/dev/null && fail "excluded PR accepted" || pass

t "checker rejects a breaking item without a what-you-need-to-do line"
grep -v 'What you need to do:' "$FX/summary-draft.md" > "$TMP/b.md"
python3 "$CHK" "$FX/fact-list.json" "$TMP/b.md" >/dev/null && fail "breaking item without action accepted" || pass

t "checker rejects a fact-list breaking PR missing from Breaking changes"
sed -e '/^## Breaking changes/,/^## What/{/^## What/!d}' "$FX/summary-draft.md" > "$TMP/m.md"
printf -- '- Version 1 of the API is gone (#12).\n' >> "$TMP/m.md"
python3 "$CHK" "$FX/fact-list.json" "$TMP/m.md" >/dev/null && fail "omitted/misplaced breaking PR accepted" || pass

t "checker rejects an unsourced claim without [NEEDS HUMAN]"
{ cat "$FX/summary-draft.md"; printf -- '- The new export is twice as fast.\n'; } > "$TMP/c.md"
python3 "$CHK" "$FX/fact-list.json" "$TMP/c.md" >/dev/null && fail "unsourced claim accepted" || pass

t "checker accepts an unsourced claim tagged [NEEDS HUMAN]"
{ cat "$FX/summary-draft.md"; printf -- '- The new export is twice as fast. [NEEDS HUMAN]\n'; } > "$TMP/d.md"
python3 "$CHK" "$FX/fact-list.json" "$TMP/d.md" >/dev/null && pass || fail "tagged claim rejected"

t "checker exits 2 on a missing file"
python3 "$CHK" "$FX/nope.json" "$FX/summary-draft.md" >/dev/null 2>&1; [ $? -eq 2 ] && pass || fail "expected exit 2"

t "SKILL.md default input lookup covers unversioned.json and a custom path"
grep -q 'docs/releases/unversioned.json' "$ROOT/plugins/harness/skills/release-summary/SKILL.md" && grep -q 'custom `--out`' "$ROOT/plugins/harness/skills/release-summary/SKILL.md" && pass || fail "default lookup misses unversioned.json or custom --out"

finish
