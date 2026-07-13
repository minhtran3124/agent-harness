#!/bin/bash
# Contract tests for scripts/harness-status.sh — the Audit Trend section.
#
# Contract: harness-status.sh is a read-only status report. The Audit Trend block is
# ADVISORY — no state of docs/harness-experimental/audit-log.jsonl may abort the script
# (it runs under `set -euo pipefail`), because aborting silently swallows the Drift Audit
# section that follows it.
#
# Fixture: a throwaway repo holding only what the script reads. A stub harness-audit.sh
# echoes DRIFT_AUDIT_RAN — that sentinel appearing in the output is the proof the trend
# block did not abort the run.
source "$(dirname "$0")/../lib.sh"

STATUS="$ROOT/scripts/harness-status.sh"

# mkrepo → echoes a fixture repo dir wired for harness-status.sh
mkrepo() {
  local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  mkdir -p "$d/scripts" "$d/.claude" "$d/skills/demo" "$d/docs/harness-experimental"
  cp "$STATUS" "$d/scripts/"
  printf '{"hooks":{}}\n' > "$d/.claude/settings.json"
  printf '#!/usr/bin/env bash\necho DRIFT_AUDIT_RAN\n' > "$d/scripts/harness-audit.sh"
  chmod +x "$d/scripts/harness-audit.sh"
  echo "$d"
}

# run_status <repo> — sets OUT (stdout+stderr) and RC
run_status() { OUT=$(bash "$1/scripts/harness-status.sh" 2>&1); RC=$?; }

# log <repo> <content> — write the audit-log.jsonl fixture
log() { printf '%s' "$2" > "$1/docs/harness-experimental/audit-log.jsonl"; }

# assert_survived <substring> — the script must exit 0, reach the Drift Audit, and say <substring>
assert_survived() {
  if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF 'DRIFT_AUDIT_RAN' && echo "$OUT" | grep -qF "$1"; then pass
  else fail "rc=$RC (want 0), need DRIFT_AUDIT_RAN + '$1' — out: $(echo "$OUT" | tail -4 | tr '\n' ' ')"; fi
}

GOOD='{"date":"2026-07-04","findings":3,"band":"green"}'

t "well-formed log → row rendered, script completes"
r=$(mkrepo); log "$r" "$GOOD"$'\n'; run_status "$r"
assert_survived 'band=green'

t "malformed line (truncated append / merge markers) → skipped, script completes"
r=$(mkrepo); log "$r" "$GOOD"$'\n{"date": "2026-07-05", "findings": 2, "ba\n'; run_status "$r"
assert_survived 'band=green'

t "valid JSON missing a key (schema drift) → skipped, script completes"
r=$(mkrepo); log "$r" "$GOOD"$'\n{"date":"2026-07-05","findings":2}\n'; run_status "$r"
assert_survived 'band=green'

t "valid JSON that is not an object (null) → skipped, script completes"
r=$(mkrepo); log "$r" "$GOOD"$'\nnull\n'; run_status "$r"
assert_survived 'band=green'

t "present-but-empty log → says so instead of a bare header"
r=$(mkrepo); log "$r" ''; run_status "$r"
assert_survived '[no data rows found]'

t "absent log → says so"
r=$(mkrepo); run_status "$r"
assert_survived '[not found:'

# open() runs before any in-heredoc try/except, so these two are NOT closed by a
# per-exception guard — only by the mechanism-level `|| echo` on the heredoc itself.
t "non-UTF-8 byte in the log → degrades, script completes"
r=$(mkrepo)
printf '{"date":"2026-07-04","findings":3,"band":"\xff\xfe"}\n' > "$r/docs/harness-experimental/audit-log.jsonl"
run_status "$r"
assert_survived '[unreadable:'

t "unreadable log (bad perms) → degrades, script completes"
if [ "$(id -u)" -eq 0 ]; then
  skip "running as root — chmod 000 is still readable"
else
  r=$(mkrepo); log "$r" "$GOOD"$'\n'
  chmod 000 "$r/docs/harness-experimental/audit-log.jsonl"
  run_status "$r"
  chmod 644 "$r/docs/harness-experimental/audit-log.jsonl"
  assert_survived '[unreadable:'
fi

finish
