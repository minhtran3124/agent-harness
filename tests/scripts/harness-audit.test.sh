#!/bin/bash
# Unit tests for scripts/harness-audit.sh — the advisory drift detector.
source "$(dirname "$0")/../lib.sh"

SCRIPT="$ROOT/scripts/harness-audit.sh"

# Portable date math (avoid GNU/BSD `date -d`/`-v` divergence): python3, the same
# tool the script's own days_since() helper uses.
days_ago() { python3 -c "from datetime import date, timedelta; print(date.today() - timedelta(days=int('$1')))"; }

# jf <json> <key path via python expr on the loaded dict, e.g. "['checks']['plan_stale']">
jf() { python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d$2)" "$1"; }

# Fresh throwaway fixture root; nothing pre-populated.
make_fixture() {
  local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  echo "$d"
}

# ── 1. empty fixture -> healthy, zero findings ────────────────────────────────
t "empty fixture (no specs/, no backlog) -> findings 0, band healthy"
d=$(make_fixture)
out=$(bash "$SCRIPT" --root "$d" --json)
if [ "$(jf "$out" "['findings']")" = "0" ] && [ "$(jf "$out" "['band']")" = "healthy" ]; then pass
else fail "unexpected: $out"; fi

# ── 2. verify_missing ─────────────────────────────────────────────────────────
t "SUMMARY.md with no ### Verify heading -> verify_missing >= 1"
d=$(make_fixture)
mkdir -p "$d/specs/x"
printf 'Lane: normal\nConfidence: high\n' > "$d/specs/x/SUMMARY.md"
out=$(bash "$SCRIPT" --root "$d" --json)
if [ "$(jf "$out" "['checks']['verify_missing']")" -ge 1 ]; then pass
else fail "want verify_missing >= 1: $out"; fi

# ── 3. plan_stale ──────────────────────────────────────────────────────────────
t "active PLAN.md with a date >30 days old -> plan_stale >= 1"
d=$(make_fixture)
mkdir -p "$d/specs/x"
printf -- '---\nstatus: active\ncreated: 2020-01-01\n---\n\n# X\n\n- 2020-01-01 — drafted\n' > "$d/specs/x/PLAN.md"
out=$(bash "$SCRIPT" --root "$d" --json)
if [ "$(jf "$out" "['checks']['plan_stale']")" -ge 1 ]; then pass
else fail "want plan_stale >= 1: $out"; fi

t "active PLAN.md with a date 10 days old -> plan_stale == 0"
d=$(make_fixture)
mkdir -p "$d/specs/x"
recent=$(days_ago 10)
printf -- '---\nstatus: active\ncreated: %s\n---\n\n# X\n\n- %s — drafted\n' "$recent" "$recent" > "$d/specs/x/PLAN.md"
out=$(bash "$SCRIPT" --root "$d" --json)
if [ "$(jf "$out" "['checks']['plan_stale']")" = "0" ]; then pass
else fail "want plan_stale == 0: $out"; fi

# ── 4. backlog_stale ────────────────────────────────────────────────────────────
t "improvement-backlog.md open row dated >14 days ago -> backlog_stale >= 1"
d=$(make_fixture)
mkdir -p "$d/docs/harness-experimental"
printf '# Backlog\n\n| Date | From failure (slug) | Proposed guardrail | Target path | Status |\n|---|---|---|---|---|\n| 2020-01-01 | old-bug | do X | scripts/y.sh | open |\n' > "$d/docs/harness-experimental/improvement-backlog.md"
out=$(bash "$SCRIPT" --root "$d" --json)
if [ "$(jf "$out" "['checks']['backlog_stale']")" -ge 1 ]; then pass
else fail "want backlog_stale >= 1: $out"; fi

t "improvement-backlog.md done row (old date) -> backlog_stale == 0"
d=$(make_fixture)
mkdir -p "$d/docs/harness-experimental"
printf '# Backlog\n\n| Date | From failure (slug) | Proposed guardrail | Target path | Status |\n|---|---|---|---|---|\n| 2020-01-01 | old-bug | do X | scripts/y.sh | done |\n' > "$d/docs/harness-experimental/improvement-backlog.md"
out=$(bash "$SCRIPT" --root "$d" --json)
if [ "$(jf "$out" "['checks']['backlog_stale']")" = "0" ]; then pass
else fail "want backlog_stale == 0 (done row): $out"; fi

t "improvement-backlog.md recent open row -> backlog_stale == 0"
d=$(make_fixture)
mkdir -p "$d/docs/harness-experimental"
recent=$(days_ago 1)
printf '# Backlog\n\n| Date | From failure (slug) | Proposed guardrail | Target path | Status |\n|---|---|---|---|---|\n| %s | new-bug | do X | scripts/y.sh | open |\n' "$recent" > "$d/docs/harness-experimental/improvement-backlog.md"
out=$(bash "$SCRIPT" --root "$d" --json)
if [ "$(jf "$out" "['checks']['backlog_stale']")" = "0" ]; then pass
else fail "want backlog_stale == 0 (recent open row): $out"; fi

# ── 7. --json is exactly one line and round-trips through json.loads ─────────────
t "--json output is exactly one line and parses as JSON"
d=$(make_fixture)
mkdir -p "$d/specs/x"
printf 'Lane: normal\n' > "$d/specs/x/SUMMARY.md"
out=$(bash "$SCRIPT" --root "$d" --json)
lines=$(printf '%s\n' "$out" | wc -l | tr -d ' ')
if [ "$lines" = "1" ] && printf '%s' "$out" | python3 -c 'import json,sys; json.loads(sys.stdin.read())' 2>/dev/null; then pass
else fail "not a single valid JSON line ($lines lines): $out"; fi

# ── 8. --strict regression ────────────────────────────────────────────────────────
t "--strict exits 1 when a finding is present"
d=$(make_fixture)
mkdir -p "$d/specs/x"
printf 'Lane: normal\n' > "$d/specs/x/SUMMARY.md"
bash "$SCRIPT" --root "$d" --strict >/dev/null 2>&1
if [ "$?" -eq 1 ]; then pass; else fail "want exit 1 with a finding present"; fi

t "--strict exits 0 when no findings are present"
d=$(make_fixture)
bash "$SCRIPT" --root "$d" --strict >/dev/null 2>&1
if [ "$?" -eq 0 ]; then pass; else fail "want exit 0 with no findings"; fi

finish
