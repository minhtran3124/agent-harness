#!/bin/bash
# Contract tests for scripts/harness-status.sh.
#
# Contract: harness-status.sh is a read-only status report running under `set -euo pipefail`.
# EVERY section is ADVISORY — no state of any input it reads (.claude/settings.json, skills/,
# trust-metrics.md, audit-log.jsonl) may abort the script, because an abort silently swallows
# every section after it. The class is "a command whose failure escapes under set -e", not
# "a python exception the heredoc forgot to catch": an exception allowlist can never be proven
# complete, so each block is bounded at the command (`|| echo`, `|| true`) instead.
#
# Fixture: a throwaway repo holding only what the script reads. A stub harness-audit.sh echoes
# DRIFT_AUDIT_RAN — the script's LAST output. That sentinel appearing is the proof that nothing
# above it aborted the run, which is why every assertion below requires it.
source "$(dirname "$0")/../lib.sh"

STATUS="$ROOT/scripts/harness-status.sh"

# mkrepo → sets $r to a fixture repo dir wired for harness-status.sh.
# Sets a global rather than echoing: `r=$(mkrepo)` would run the body in a subshell, so the
# _CLEANUP_DIRS registration would be discarded and every fixture would leak into TMPDIR.
mkrepo() {
  r=$(mktemp -d); _CLEANUP_DIRS+=("$r")
  mkdir -p "$r/scripts" "$r/.claude" "$r/skills/demo" "$r/docs/harness-experimental"
  cp "$STATUS" "$r/scripts/"
  printf '{"hooks":{}}\n' > "$r/.claude/settings.json"
  printf '#!/usr/bin/env bash\necho DRIFT_AUDIT_RAN\n' > "$r/scripts/harness-audit.sh"
  chmod +x "$r/scripts/harness-audit.sh"
}

# run_status <repo> — sets OUT (stdout+stderr) and RC
run_status() { OUT=$(bash "$1/scripts/harness-status.sh" 2>&1); RC=$?; }

# log <repo> <content> — write the audit-log.jsonl fixture
log() { printf '%s' "$2" > "$1/docs/harness-experimental/audit-log.jsonl"; }

# assert_survived <substring> — the script must exit 0, reach the Drift Audit, say <substring>,
# and degrade CLEANLY: a leaked Python traceback means the block failed loudly into the middle
# of the report, which is a different outcome from a bounded, degraded section.
assert_survived() {
  if [ "$RC" -ne 0 ]; then
    fail "rc=$RC (want 0) — out: $(echo "$OUT" | tail -4 | tr '\n' ' ')"
  elif ! echo "$OUT" | grep -qF 'DRIFT_AUDIT_RAN'; then
    fail "script aborted before the Drift Audit — out: $(echo "$OUT" | tail -4 | tr '\n' ' ')"
  elif echo "$OUT" | grep -qF 'Traceback'; then
    fail "traceback leaked into the report — out: $(echo "$OUT" | grep -A2 Traceback | tr '\n' ' ')"
  elif ! echo "$OUT" | grep -qF "$1"; then
    fail "missing '$1' — out: $(echo "$OUT" | tail -4 | tr '\n' ' ')"
  else pass; fi
}

# chmod 000 is not honored everywhere (root; some container/CI mounts). Probe, don't guess —
# `id -u` only catches the root case.
perms_enforced() {
  local f; f=$(mktemp); printf 'x' > "$f"; chmod 000 "$f"
  if [ -r "$f" ]; then chmod 644 "$f"; rm -f "$f"; return 1; fi
  chmod 644 "$f"; rm -f "$f"; return 0
}

GOOD='{"date":"2026-07-04","findings":3,"band":"green"}'

# ── Audit Trend (the section this suite was originally written for) ────────────────────

t "well-formed log → row rendered, script completes"
mkrepo; log "$r" "$GOOD"$'\n'; run_status "$r"
assert_survived 'band=green'

t "malformed line (truncated append / merge markers) → skipped, script completes"
mkrepo; log "$r" "$GOOD"$'\n{"date": "2026-07-05", "findings": 2, "ba\n'; run_status "$r"
assert_survived 'band=green'

t "valid JSON missing a key (schema drift) → skipped, script completes"
mkrepo; log "$r" "$GOOD"$'\n{"date":"2026-07-05","findings":2}\n'; run_status "$r"
assert_survived 'band=green'

t "valid JSON that is not an object (null) → skipped, script completes"
mkrepo; log "$r" "$GOOD"$'\nnull\n'; run_status "$r"
assert_survived 'band=green'

t "present-but-empty log → says so instead of a bare header"
mkrepo; log "$r" ''; run_status "$r"
assert_survived '[no data rows found]'

t "log present but EVERY row unparseable → says so instead of a bare header"
mkrepo; log "$r" $'nonsense\n{"pr":42}\n'; run_status "$r"
assert_survived '[no data rows found]'

# Asserts the audit-log path specifically. A bare '[not found:' would also match the
# Trust-Metrics section's identical line, so this case would pass even with the Audit Trend
# branch deleted — a vacuous test. (Verified by mutation: it did.)
t "absent log → says so"
mkrepo; run_status "$r"
assert_survived "[not found: $r/docs/harness-experimental/audit-log.jsonl]"

# open() runs before any in-heredoc try/except, so these two are NOT closed by a
# per-exception guard — only by the mechanism-level `|| echo` on the heredoc itself.
t "non-UTF-8 byte in the log → degrades, script completes"
mkrepo
printf '{"date":"2026-07-04","findings":3,"band":"\xff\xfe"}\n' > "$r/docs/harness-experimental/audit-log.jsonl"
run_status "$r"
assert_survived '[unreadable:'

t "unreadable log (bad perms) → degrades, script completes"
if ! perms_enforced; then
  skip "permission bits not enforced here — chmod 000 is still readable"
else
  mkrepo; log "$r" "$GOOD"$'\n'
  chmod 000 "$r/docs/harness-experimental/audit-log.jsonl"
  run_status "$r"
  chmod 644 "$r/docs/harness-experimental/audit-log.jsonl"
  assert_survived '[unreadable:'
fi

# ── Wired Hooks — same class, and it runs FIRST, so an abort here swallows EVERYTHING ──

t "absent settings.json → degrades, script completes"
mkrepo; rm -f "$r/.claude/settings.json"; run_status "$r"
assert_survived '[not found:'

t "malformed settings.json → degrades, script completes"
mkrepo; printf '{"hooks": {' > "$r/.claude/settings.json"; run_status "$r"
assert_survived '[unreadable:'

t "unreadable settings.json (bad perms) → degrades, script completes"
if ! perms_enforced; then
  skip "permission bits not enforced here — chmod 000 is still readable"
else
  mkrepo; chmod 000 "$r/.claude/settings.json"
  run_status "$r"
  chmod 644 "$r/.claude/settings.json"
  assert_survived '[unreadable:'
fi

# ── Skills — `grep -c` exits 1 on zero matches, which set -e turns into an abort ────────

t "empty skills/ → count 0, script completes"
mkrepo; rmdir "$r/skills/demo"; run_status "$r"
assert_survived 'Installed: 0'

t "absent skills/ → says so, script completes"
mkrepo; rm -rf "$r/skills"; run_status "$r"
assert_survived '[not found:'

# ── Trust-Metrics — same class: `rows=$(grep ...)` with no match aborts under set -e, which
# made the section's own `[no data rows found]` branch unreachable dead code. ─────────────

t "trust-metrics.md present with zero data rows → says so, script completes"
mkrepo
printf '# Trust Metrics\n\n| Date | Slug | Lane |\n|---|---|---|\n' > "$r/docs/harness-experimental/trust-metrics.md"
run_status "$r"
assert_survived '[no data rows found]'

t "trust-metrics.md with a data row → row rendered, script completes"
mkrepo
printf '| Date | Slug |\n|---|---|\n| 2026-07-04 | demo-slug | x | normal | x | high | x | ok |\n' \
  > "$r/docs/harness-experimental/trust-metrics.md"
run_status "$r"
assert_survived 'demo-slug'

finish
