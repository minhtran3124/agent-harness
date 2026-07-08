#!/bin/bash
# Unit tests for scripts/check-contract-impact.sh — advisory contract-impact mapper.
source "$(dirname "$0")/../lib.sh"

SCRIPT="$ROOT/scripts/check-contract-impact.sh"

# Fresh throwaway fixture root with a single contract + stub surface/consumer files.
make_fixture() {
  local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  cat > "$d/harness-manifest.json" <<'JSON'
{
  "contracts": {
    "hook-registration": {
      "surface": ["settings.json"],
      "consumers": ["CLAUDE.md", "scripts/lint-doc-truth.sh"]
    }
  }
}
JSON
  printf '{}\n' > "$d/settings.json"
  printf '# CLAUDE\n' > "$d/CLAUDE.md"
  mkdir -p "$d/scripts"
  printf '#!/bin/bash\n' > "$d/scripts/lint-doc-truth.sh"
  printf '# README\n' > "$d/README.md"
  echo "$d"
}

# ── 1. changed file matches a contract surface -> prints contract + both consumers ──
t "surface file (settings.json) -> stdout mentions contract + both consumers, exit 0"
d=$(make_fixture)
out=$(bash "$SCRIPT" --root "$d" settings.json); rc=$?
if [ "$rc" -eq 0 ] && echo "$out" | grep -q "hook-registration" \
   && echo "$out" | grep -q "CLAUDE.md" && echo "$out" | grep -q "scripts/lint-doc-truth.sh"; then pass
else fail "rc=$rc out=$out"; fi

# ── 2. non-surface file -> no contract line, exit 0 ─────────────────────────────────
t "non-surface file (README.md) -> empty stdout, exit 0"
d=$(make_fixture)
out=$(bash "$SCRIPT" --root "$d" README.md); rc=$?
if [ "$rc" -eq 0 ] && [ -z "$out" ]; then pass
else fail "rc=$rc out=$out"; fi

# ── 3. exit code always 0 (advisory) ────────────────────────────────────────────────
t "exit code is 0 regardless of match"
d=$(make_fixture)
bash "$SCRIPT" --root "$d" settings.json >/dev/null 2>&1
rc1=$?
bash "$SCRIPT" --root "$d" README.md >/dev/null 2>&1
rc2=$?
if [ "$rc1" -eq 0 ] && [ "$rc2" -eq 0 ]; then pass
else fail "rc1=$rc1 rc2=$rc2"; fi

finish
