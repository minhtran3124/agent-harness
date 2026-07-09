#!/bin/bash
# Integration tests for the BOOTSTRAP_OWNED_FILES protected-file resync logic in
# scripts/deploy-harness.sh (preflight_protected / sync_protected_file / sync_protected_dir).
# Mirrors tests/scripts/settings-merge.test.sh: mktemp target, deploy from the real $ROOT,
# assert via lib.sh. run-tests.sh globs tests/scripts/*.test.sh — no registration needed.
#
# SAFETY: every deploy invocation below redirects stdin (from /dev/null, or a controlled
# here-string) so a stray interactive prompt fails loudly instead of hanging CI — never
# invoke $DEPLOY without --target (that would rewrite THIS repo's real .claude/) and never
# let it inherit this test-runner's own stdin unredirected.
source "$(dirname "$0")/../lib.sh"

DEPLOY="$ROOT/scripts/deploy-harness.sh"

# Mirrors BOOTSTRAP_OWNED_FILES in scripts/deploy-harness.sh. Kept as a literal list (like
# settings-merge.test.sh hardcodes hook names) — if that array changes, update here too.
OWNED_TOP_FILE="rules/architecture.md"        # a plain protected FILE entry
OWNED_NESTED_FILE="skills/xia2/PROJECT.md"    # a protected file living inside a synced DIR

new_target() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); echo "$d"; }

# run_deploy <target> [extra deploy args...] — stdin always from /dev/null.
run_deploy() {
  local tgt="$1"; shift
  OUT_TXT=$(bash "$DEPLOY" --target "$tgt" "$@" </dev/null 2>&1); RC=$?
}

tree_snapshot() { # tree_snapshot <dir> — file list + content hashes, paths relativized
  find "$1" -type f -exec shasum {} \; | sed "s|$1||" | sort
}

# ---------------------------------------------------------------------------
# Case 1 — first install copies protected skeleton files normally, no sidecar.
# ---------------------------------------------------------------------------
T1=$(new_target)
run_deploy "$T1"

t "case 1: first install copies protected files byte-identical to source"
if [ "$RC" -eq 0 ] \
   && cmp -s "$T1/.claude/$OWNED_TOP_FILE" "$ROOT/$OWNED_TOP_FILE" \
   && cmp -s "$T1/.claude/$OWNED_NESTED_FILE" "$ROOT/$OWNED_NESTED_FILE"; then pass
else fail "rc=$RC — files not copied / not identical"; fi

t "case 1: first install writes no .harness-incoming sidecar"
n=$(find "$T1/.claude" -name '*.harness-incoming' | wc -l | tr -d ' ')
if [ "$n" = "0" ]; then pass; else fail "found $n sidecar(s) on a fresh install"; fi

# ---------------------------------------------------------------------------
# Case 2 — customize a protected file, then --yes re-sync: keep + sidecar + rc0.
# ---------------------------------------------------------------------------
T2=$(new_target)
run_deploy "$T2"
printf 'LOCAL CUSTOMIZATION — do not clobber\n' > "$T2/.claude/$OWNED_TOP_FILE"
local_content_2=$(cat "$T2/.claude/$OWNED_TOP_FILE")
run_deploy "$T2" --yes

t "case 2: --yes re-sync on a conflict keeps the local copy"
if [ "$RC" -eq 0 ] && [ "$(cat "$T2/.claude/$OWNED_TOP_FILE")" = "$local_content_2" ]; then pass
else fail "rc=$RC content=[$(cat "$T2/.claude/$OWNED_TOP_FILE" 2>&1)]"; fi

t "case 2: --yes re-sync writes the incoming content to <file>.harness-incoming"
if cmp -s "$T2/.claude/$OWNED_TOP_FILE.harness-incoming" "$ROOT/$OWNED_TOP_FILE"; then pass
else fail "sidecar missing or does not match source incoming"; fi

# ---------------------------------------------------------------------------
# Case 3 — same customization + --overwrite-conflicts: overwritten with incoming.
# ---------------------------------------------------------------------------
T3=$(new_target)
run_deploy "$T3"
printf 'LOCAL CUSTOMIZATION — expect this to be clobbered\n' > "$T3/.claude/$OWNED_TOP_FILE"
run_deploy "$T3" --overwrite-conflicts

t "case 3: --overwrite-conflicts replaces local content with incoming"
if [ "$RC" -eq 0 ] && cmp -s "$T3/.claude/$OWNED_TOP_FILE" "$ROOT/$OWNED_TOP_FILE"; then pass
else fail "rc=$RC — file not overwritten with incoming source"; fi

t "case 3: --overwrite-conflicts leaves no stale .harness-incoming sidecar"
if [ ! -e "$T3/.claude/$OWNED_TOP_FILE.harness-incoming" ]; then pass
else fail "sidecar unexpectedly present after overwrite"; fi

# ---------------------------------------------------------------------------
# Case 4 — no-/dev/tty fallback (no --yes): must keep + rc 0, and must NOT consume stdin.
#
# Pinned invariant: `[ -r /dev/tty ]` (access(2)) checks the *static file mode bits* of
# the /dev/tty alias device node, not whether this process currently has a controlling
# terminal — it is true on a normal box even with no ctty at all (verified empirically:
# `test -r /dev/tty` reports true right after os.setsid() severs the controlling terminal). So
# deploy-harness.sh's `elif ... [ ! -r /dev/tty ]` branch is not reliably reachable; the
# real safety net in a genuinely no-ctty environment (the curl|bash case this guards
# against) is that the interactive branch's `read -r ans < /dev/tty` itself fails (ENXIO)
# and is swallowed by `|| true`, falling through to the same POLICY=keep default. We pin
# the OBSERVABLE, environment-independent contract: given a real absence of a controlling
# terminal (forced via os.setsid so this holds under any test runner, tty-backed or not),
# deploy must still (a) exit 0, (b) keep the local file, (c) write the sidecar, and
# (d) never touch our own stdin — proven by piping a sentinel through a here-string shared
# with a trailing `cat`: if deploy had consumed it, the `cat` would come up empty/short.
# ---------------------------------------------------------------------------
T4=$(new_target)
run_deploy "$T4"
printf 'LOCAL CUSTOMIZATION — case 4\n' > "$T4/.claude/$OWNED_TOP_FILE"
local_content_4=$(cat "$T4/.claude/$OWNED_TOP_FILE")

if command -v python3 >/dev/null 2>&1; then
  SENTINEL="SENTINEL-UNCONSUMED-$$"
  helper_out=$(python3 - "$DEPLOY" "$T4" "$SENTINEL" <<'PYEOF'
import subprocess, sys
deploy, tgt, sentinel = sys.argv[1], sys.argv[2], sys.argv[3]
# os.setsid (via start_new_session) genuinely severs the controlling terminal for this
# subprocess tree, so deploy's `read ... < /dev/tty` fails fast (ENXIO) instead of blocking
# — deterministic across an interactive dev shell and a headless CI runner alike.
script = '{ bash "%s" --target "%s"; printf "DEPLOY_RC=%%d\\n" "$?"; cat; } <<< "%s"' % (deploy, tgt, sentinel)
p = subprocess.run(["bash", "-c", script], start_new_session=True,
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    timeout=20, text=True)
print(p.stdout)
PYEOF
)
  deploy_rc=$(printf '%s\n' "$helper_out" | sed -n 's/.*DEPLOY_RC=\([0-9]*\).*/\1/p' | head -1)

  t "case 4: no-ctty fallback (no --yes) exits 0 and keeps local content"
  if [ "$deploy_rc" = "0" ] && [ "$(cat "$T4/.claude/$OWNED_TOP_FILE")" = "$local_content_4" ]; then pass
  else fail "deploy_rc=$deploy_rc content=[$(cat "$T4/.claude/$OWNED_TOP_FILE" 2>&1)]"; fi

  t "case 4: no-ctty fallback writes the .harness-incoming sidecar"
  if cmp -s "$T4/.claude/$OWNED_TOP_FILE.harness-incoming" "$ROOT/$OWNED_TOP_FILE"; then pass
  else fail "sidecar missing or wrong content"; fi

  t "case 4: deploy never consumed the sentinel — it is still fully readable after"
  if printf '%s\n' "$helper_out" | grep -qF "$SENTINEL"; then pass
  else fail "sentinel not found in trailing cat output — stdin may have been consumed"; fi
else
  skip "case 4: no-ctty fallback (x3)" "python3 not available to force ctty detachment"
  skip "case 4: sidecar" "python3 not available"
  skip "case 4: sentinel" "python3 not available"
fi

# ---------------------------------------------------------------------------
# Case 5 — nested protected file (inside a synced dir): customize + --yes → kept (snapshot/restore).
# ---------------------------------------------------------------------------
T5=$(new_target)
run_deploy "$T5"
printf 'LOCAL XIA2 CUSTOMIZATION\n' > "$T5/.claude/$OWNED_NESTED_FILE"
local_content_5=$(cat "$T5/.claude/$OWNED_NESTED_FILE")
run_deploy "$T5" --yes

t "case 5: nested protected file kept through the wholesale dir re-sync"
if [ "$RC" -eq 0 ] && [ "$(cat "$T5/.claude/$OWNED_NESTED_FILE")" = "$local_content_5" ]; then pass
else fail "rc=$RC content=[$(cat "$T5/.claude/$OWNED_NESTED_FILE" 2>&1)]"; fi

t "case 5: nested protected file's incoming is saved as a sidecar"
if cmp -s "$T5/.claude/$OWNED_NESTED_FILE.harness-incoming" "$ROOT/$OWNED_NESTED_FILE"; then pass
else fail "nested sidecar missing or does not match source incoming"; fi

# ---------------------------------------------------------------------------
# Case 6 — nested sidecar (.proposed, never shipped by the harness) survives a re-sync.
# ---------------------------------------------------------------------------
T6=$(new_target)
run_deploy "$T6"
printf 'MY-PROPOSED-CONTENT-NOT-FROM-SOURCE\n' > "$T6/.claude/$OWNED_NESTED_FILE.proposed"
run_deploy "$T6"

t "case 6: .proposed sidecar survives sync_protected_dir's wholesale rm+cp"
if [ "$RC" -eq 0 ] && [ -e "$T6/.claude/$OWNED_NESTED_FILE.proposed" ] \
   && [ "$(cat "$T6/.claude/$OWNED_NESTED_FILE.proposed")" = "MY-PROPOSED-CONTENT-NOT-FROM-SOURCE" ]; then pass
else fail "rc=$RC — .proposed sidecar lost or overwritten by source's own copy"; fi

# ---------------------------------------------------------------------------
# Case 7 — a non-protected harness file altered locally is silently overwritten (no over-protection).
# ---------------------------------------------------------------------------
T7=$(new_target)
run_deploy "$T7"
printf 'LOCAL HACK — should NOT survive\n' > "$T7/.claude/skills/compound/SKILL.md"
run_deploy "$T7"

t "case 7: non-protected file is silently overwritten by re-sync"
if [ "$RC" -eq 0 ] && cmp -s "$T7/.claude/skills/compound/SKILL.md" "$ROOT/skills/compound/SKILL.md"; then pass
else fail "rc=$RC — non-protected local edit survived a re-sync (over-protection)"; fi

# ---------------------------------------------------------------------------
# Case 8 — --dry-run on a conflicting target reports the conflict and writes nothing at all.
# ---------------------------------------------------------------------------
T8=$(new_target)
run_deploy "$T8"
printf 'LOCAL CUSTOMIZATION — dry-run must not touch this\n' > "$T8/.claude/$OWNED_TOP_FILE"
before_8=$(tree_snapshot "$T8/.claude")
OUT_TXT=$(bash "$DEPLOY" --target "$T8" --dry-run </dev/null 2>&1); RC=$?
after_8=$(tree_snapshot "$T8/.claude")

t "case 8: --dry-run reports the conflicting protected file"
if [ "$RC" -eq 0 ] && printf '%s' "$OUT_TXT" | grep -qF "$OWNED_TOP_FILE"; then pass
else fail "rc=$RC — dry-run output missing conflict path: $(printf '%s' "$OUT_TXT" | head -5 | tr '\n' ' ')"; fi

t "case 8: --dry-run leaves the whole .claude/ tree byte-identical"
if [ "$before_8" = "$after_8" ]; then pass
else fail "tree changed under --dry-run: $(diff <(echo "$before_8") <(echo "$after_8") | head -5 | tr '\n' ' ')"; fi

# ---------------------------------------------------------------------------
# Case 9 — protected file identical to incoming: no conflict, no sidecar, no-op.
# ---------------------------------------------------------------------------
T9=$(new_target)
run_deploy "$T9"
run_deploy "$T9"   # re-sync with zero local customization

t "case 9: identical protected file re-syncs with no sidecar anywhere"
n=$(find "$T9/.claude" -name '*.harness-incoming' | wc -l | tr -d ' ')
if [ "$RC" -eq 0 ] && [ "$n" = "0" ]; then pass
else fail "rc=$RC — found $n sidecar(s) with no local customization"; fi

t "case 9: protected files remain byte-identical to source"
if cmp -s "$T9/.claude/$OWNED_TOP_FILE" "$ROOT/$OWNED_TOP_FILE" \
   && cmp -s "$T9/.claude/$OWNED_NESTED_FILE" "$ROOT/$OWNED_NESTED_FILE"; then pass
else fail "protected files drifted from source on a no-op re-sync"; fi

# ---------------------------------------------------------------------------
# Case 10 — stale sidecar cleanup: a leftover .harness-incoming next to an identical
# protected file is removed on the next re-sync.
# ---------------------------------------------------------------------------
T10=$(new_target)
run_deploy "$T10"
printf 'STALE INCOMING FROM A PAST CONFLICT\n' > "$T10/.claude/$OWNED_TOP_FILE.harness-incoming"
run_deploy "$T10"

t "case 10: stale .harness-incoming sidecar is cleaned up on re-sync"
if [ "$RC" -eq 0 ] && [ ! -e "$T10/.claude/$OWNED_TOP_FILE.harness-incoming" ]; then pass
else fail "rc=$RC — stale sidecar still present: $([ -e "$T10/.claude/$OWNED_TOP_FILE.harness-incoming" ] && echo yes || echo no)"; fi

finish
