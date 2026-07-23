#!/bin/bash
# End-to-end smoke for the warn-mode loosening (specs/simplify-gate-surface).
# Runs the hook against a COPY OF THE REAL harness-manifest.json — proving the
# shipped manifest, not a fixture, produces the intended behavior:
#   1. The reported incident now passes: a Lane: normal commit whose diff trips
#      only weakening-validation (a removed `raise` line) is allowed with a note.
#   2. The loosening is scoped: the same commit ALSO touching hooks/ trips
#      high-blast (block-mode) and is still denied.
source "$(dirname "$0")/../lib.sh"

H=risk-corroboration.sh
COMMIT_JSON=$(json_cmd 'git commit -m x')

t "real manifest: removed raise + Lane: normal → warn-mode note, allowed (exit 0)"
repo=$(new_repo $H)
cp "$ROOT/harness-manifest.json" "$repo/"
stage "$repo" "app/svc.py" 'def f(x):
    if not x:
        raise ValueError("x")
    return x'
git -C "$repo" commit -qm base
printf '%s\n' 'def f(x):' '    return x' > "$repo/app/svc.py"
git -C "$repo" add app/svc.py
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "warn-mode"

t "real manifest: same diff + hooks/ file → high-blast still blocks (exit 2)"
repo=$(new_repo $H)
cp "$ROOT/harness-manifest.json" "$repo/"
stage "$repo" "app/svc.py" 'def f(x):
    if not x:
        raise ValueError("x")
    return x'
git -C "$repo" commit -qm base
printf '%s\n' 'def f(x):' '    return x' > "$repo/app/svc.py"
git -C "$repo" add app/svc.py
stage "$repo" "hooks/new-gate.sh" '#!/bin/bash'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

finish
