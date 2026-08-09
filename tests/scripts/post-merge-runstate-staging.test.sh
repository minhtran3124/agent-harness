#!/bin/bash
# The post-merge workflow transitions a merged spec's run to `shipped`, then opens the
# bookkeeping PR. `git commit` there has no `-a`, so ANY file the transition writes that
# is not staged is discarded with the runner — the step reports success and the run stays
# non-terminal forever (found by external review on PR #176, P1).
#
# This test does not grep for wording. It measures which files a real transition writes,
# then asserts the workflow stages every one of them — so adding a third artifact to the
# engine fails here instead of silently vanishing in CI.
#
# It ALSO guards the trigger/base-branch policy (issue #196): the `branches:` allowlist is
# the one authoritative place for the policy and rots silently. Section 0 pins the branches
# that MUST be present — the active integration branch (`simplify`) and the default branch
# (`main`) — plus the main-sync caveat, so the specific rot that stranded a run at
# `ready_to_merge` cannot silently return. It asserts required members, not an exact list.
source "$(dirname "$0")/../lib.sh"

WF="$ROOT/.github/workflows/post-merge-maintenance.yml"
RS="$ROOT/runtime/run_state.py"

# ---- 0. Trigger policy: the allowlist covers the active integration branch (issue #196) --
# The `branches:` allowlist is the one authoritative place for the base-branch policy. It
# rots silently — a PR merged into a branch missing here fires nothing. These assertions pin
# the two branches that MUST be present (the active integration branch `simplify`, and the
# default branch `main` that pull_request_target reads and that integration ships into) plus
# the main-sync caveat, so the specific rot #196 fixed cannot silently return. This is a
# policy assertion, not "the list equals exactly X" — extra integration branches are fine.
# Isolate the `on:` block (up to the next top-level key) so a `branches:` under an unrelated
# job step cannot be mistaken for the trigger's.
ON_BLOCK=$(awk '/^on:/{f=1} f&&/^[a-z]/&&!/^on:/{exit} f' "$WF")
BRANCHES_LINE=$(echo "$ON_BLOCK" | grep -E '^[[:space:]]*branches:')

t "the pull_request_target trigger declares a base-branch allowlist"
if [ -n "$BRANCHES_LINE" ]; then pass; else fail "no branches: allowlist under pull_request_target — either the trigger is unbounded (over-broad write-token surface) or the filter was lost"; fi

t "the allowlist includes the active integration branch (simplify)"
if echo "$BRANCHES_LINE" | grep -qE '\bsimplify\b'; then
  pass
else
  fail "simplify is not in the branches: allowlist — every PR merged into it silently skips shipped (the exact #196 gap). Add the active integration branch here and sync to main."
fi

t "the allowlist includes the default branch (main)"
if echo "$BRANCHES_LINE" | grep -qE '\bmain\b'; then
  pass
else
  fail "main is not in the branches: allowlist — the default branch that integration ships into would skip terminalization"
fi

t "the shipped decision keys on the tracked run (specs/<slug>/RUN.json), not the base ref"
RUNSTATE_STEP=$(sed -n '/id: runstate/,/Run bookkeeping/p' "$WF")
if echo "$RUNSTATE_STEP" | grep -q 'RUN.json' && ! echo "$RUNSTATE_STEP" | grep -qE 'BASE_REF|base\.ref|base_ref'; then
  pass
else
  fail "run-state step must gate on specs/<slug>/RUN.json presence and not condition its transition on the base ref"
fi

t "the main-sync caveat is documented in the trigger block"
# pull_request_target loads the definition (and this list) from the DEFAULT branch (main);
# the fix is inert until synced there. Keep that load-bearing caveat present.
if echo "$ON_BLOCK" | grep -qiE 'DEFAULT branch|synced on .main.|SYNCED ON .main.|land.* on .main'; then
  pass
else
  fail "the on: block must document that pull_request_target reads its definition/list from main (default branch)"
fi

# ---- 1. Measure the real write set of a `shipped` transition -------------------------
probe=$(mktemp -d)
mkdir -p "$probe/specs/demo"
(
  cd "$probe" || exit 1
  python3 "$RS" init --slug demo --run-id r1 >/dev/null
  for s in investigating planning implementing verifying ready_to_merge; do
    python3 "$RS" transition --slug demo --to "$s" --event e >/dev/null
  done
) || { echo "probe setup failed"; exit 1; }

# snapshot, transition, diff
before=$(cd "$probe" && find specs -type f -exec shasum {} \; | sort)
(cd "$probe" && python3 "$RS" transition --slug demo --to shipped --event ci.merged --sha abc1234 >/dev/null) \
  || { echo "probe transition failed"; exit 1; }
after=$(cd "$probe" && find specs -type f -exec shasum {} \; | sort)

WRITTEN=$(diff <(echo "$before") <(echo "$after") | grep -oE 'specs/demo/[A-Za-z._]+' | sort -u | xargs -n1 basename | sort -u)
rm -rf "$probe"

t "a shipped transition writes a non-empty set of files"
if [ -n "$WRITTEN" ]; then pass; else fail "measured no writes — probe is vacuous, fix the probe"; fi

t "the measured write set is RUN.json + events.jsonl (engine contract unchanged)"
if [ "$(echo "$WRITTEN" | tr '\n' ' ')" = "RUN.json events.jsonl " ] ||
   [ "$(echo "$WRITTEN" | tr '\n' ' ')" = "events.jsonl RUN.json " ]; then
  pass
else
  fail "engine now writes: $(echo "$WRITTEN" | tr '\n' ' ')— update the workflow's git add"
fi

# ---- 2. Every measured file must be staged by the workflow --------------------------
ADD_BLOCK=$(sed -n '/Open the bookkeeping PR/,/gh pr create/p' "$WF" | grep -E '^\s*git add')

for f in $WRITTEN; do
  t "workflow stages $f in the bookkeeping PR"
  if echo "$ADD_BLOCK" | grep -q "$f"; then pass; else fail "$f is written by the transition but never staged — it would be discarded with the runner"; fi
done

# ---- 3. Ordering: the transition must precede the dirty-tree check ------------------
# `changed` decides whether the PR is opened at all. Computed before the transition, a
# run-state-only change reads as "nothing to record" and is lost.
t "run-state step precedes the changed= detection"
rs_line=$(grep -n 'id: runstate' "$WF" | head -1 | cut -d: -f1)
ch_line=$(grep -n 'changed=true' "$WF" | head -1 | cut -d: -f1)
if [ -n "$rs_line" ] && [ -n "$ch_line" ] && [ "$rs_line" -lt "$ch_line" ]; then
  pass
else
  fail "run-state step (line ${rs_line:-?}) must come before changed= (line ${ch_line:-?})"
fi

t "the slug output is published only on a successful transition"
if sed -n '/id: runstate/,/Run bookkeeping/p' "$WF" | grep -qE '^\s*elif python3 .*run_state\.py transition'; then
  pass
else
  fail "transition is not the elif condition — slug could be published after a failure"
fi

# Convert any FAIL into a non-zero exit — without this the script's status is the last
# command's (always 0) and every assertion above, new and pre-existing, silently no-ops.
finish
