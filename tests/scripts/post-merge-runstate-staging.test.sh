#!/bin/bash
# The post-merge workflow transitions a merged spec's run to `shipped`, then opens the
# bookkeeping PR. `git commit` there has no `-a`, so ANY file the transition writes that
# is not staged is discarded with the runner — the step reports success and the run stays
# non-terminal forever (found by external review on PR #176, P1).
#
# This test does not grep for wording. It measures which files a real transition writes,
# then asserts the workflow stages every one of them — so adding a third artifact to the
# engine fails here instead of silently vanishing in CI.
source "$(dirname "$0")/../lib.sh"

WF="$ROOT/.github/workflows/post-merge-maintenance.yml"
RS="$ROOT/runtime/run_state.py"

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
