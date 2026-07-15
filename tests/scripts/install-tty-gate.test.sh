#!/bin/bash
# Integration tests for the existing-harness re-sync gate in scripts/install-harness.sh.
#
# Covers the two ways a tty-less re-sync used to go wrong (both reproduced before the fix):
#   1. `[ -r /dev/tty ]` reported the alias node readable with no controlling terminal, so
#      the prompt branch ran and `printf > /dev/tty` killed the script under `set -e` with a
#      raw shell error instead of the actionable "Re-run with --yes" message.
#   2. `--overwrite-conflicts` did not consent to the re-sync, so a non-interactive
#      `curl … | bash -s -- --overwrite-conflicts` aborted rather than overwriting.
#
# SAFETY: every install invocation targets a mktemp dir and reads stdin from /dev/null —
# never let it inherit this runner's stdin, and never run it without -d (that would rewrite
# THIS repo's real .claude/).
source "$(dirname "$0")/../lib.sh"

INSTALL="$ROOT/scripts/install-harness.sh"
OWNED_TOP_FILE="rules/architecture.md"   # a BOOTSTRAP_OWNED_FILES entry (see deploy-harness.sh)

if ! command -v python3 >/dev/null 2>&1; then
  echo "  skip  install-tty-gate.test.sh: python3 needed to sever the controlling terminal"
  finish
fi

new_target() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); echo "$d"; }

# run_no_ctty <args...> — run install-harness with a genuinely severed controlling terminal
# (os.setsid), so `have_tty()` must report false regardless of how this suite was launched.
# Sets OUT_TXT and RC.
run_no_ctty() {
  local helper
  helper=$(python3 - "$INSTALL" "$@" <<'PYEOF'
import subprocess, sys
argv = sys.argv[1:]
p = subprocess.run(["bash", *argv], start_new_session=True,
                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT, timeout=120, text=True)
print(p.stdout, end="")
print("INSTALL_RC=%d" % p.returncode)
PYEOF
)
  RC=$(printf '%s\n' "$helper" | sed -n 's/^INSTALL_RC=\([0-9]*\)$/\1/p' | tail -1)
  OUT_TXT=$(printf '%s\n' "$helper" | sed '/^INSTALL_RC=[0-9]*$/d')
}

# ---------------------------------------------------------------------------
# Case 1 — tty-less re-sync with no --yes: refuse with the actionable message.
# ---------------------------------------------------------------------------
T1=$(new_target)
bash "$INSTALL" --source "$ROOT" -d "$T1" --yes </dev/null >/dev/null 2>&1
printf 'LOCAL CUSTOMIZATION — case 1\n' > "$T1/.claude/$OWNED_TOP_FILE"
run_no_ctty --source "$ROOT" -d "$T1"

t "case 1: tty-less re-sync without --yes exits non-zero"
if [ "$RC" != "0" ]; then pass; else fail "rc=$RC — a tty-less run must not silently proceed"; fi

# Load-bearing: with `[ -r /dev/tty ]` the prompt branch ran and died on `printf > /dev/tty`,
# so this exact string was NEVER printed. It only appears via the have_tty() false branch.
t "case 1: it prints the actionable 'Re-run with --yes' message"
if printf '%s' "$OUT_TXT" | grep -q 'Re-run with --yes to re-sync it'; then pass
else fail "missing the actionable message; got: $(printf '%s' "$OUT_TXT" | tail -3 | tr '\n' '|')"; fi

# Load-bearing: this is the raw shell error the old code produced. Its absence is the fix.
t "case 1: it does NOT leak a raw /dev/tty shell error"
if printf '%s' "$OUT_TXT" | grep -q '/dev/tty: Device not configured'; then
  fail "raw /dev/tty error leaked — have_tty() is not guarding the prompt"
else pass; fi

t "case 1: the local customization is untouched"
if [ "$(cat "$T1/.claude/$OWNED_TOP_FILE")" = "LOCAL CUSTOMIZATION — case 1" ]; then pass
else fail "local protected file was modified by an aborted install"; fi

# ---------------------------------------------------------------------------
# Case 2 — tty-less `--overwrite-conflicts` (no --yes): consents to the re-sync and
# actually replaces the protected file with the incoming harness copy.
# ---------------------------------------------------------------------------
T2=$(new_target)
bash "$INSTALL" --source "$ROOT" -d "$T2" --yes </dev/null >/dev/null 2>&1
printf 'LOCAL CUSTOMIZATION — case 2\n' > "$T2/.claude/$OWNED_TOP_FILE"
run_no_ctty --source "$ROOT" -d "$T2" --overwrite-conflicts

t "case 2: --overwrite-conflicts alone completes a tty-less re-sync"
if [ "$RC" = "0" ]; then pass; else fail "rc=$RC — --overwrite-conflicts must imply consent to re-sync"; fi

# Load-bearing: before the fix the run aborted at the gate, so the protected file kept the
# local text. Comparing against $ROOT proves the incoming copy actually landed.
t "case 2: the protected file is overwritten with the incoming harness copy"
if cmp -s "$T2/.claude/$OWNED_TOP_FILE" "$ROOT/$OWNED_TOP_FILE"; then pass
else fail "protected file was not replaced: $(head -1 "$T2/.claude/$OWNED_TOP_FILE")"; fi

t "case 2: no .harness-incoming sidecar is left behind under overwrite"
n=$(find "$T2/.claude" -name '*.harness-incoming' | wc -l | tr -d ' ')
if [ "$n" = "0" ]; then pass; else fail "found $n sidecar(s) under the overwrite policy"; fi

finish
