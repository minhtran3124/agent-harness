#!/usr/bin/env bash
# Build isolated sandboxes for the STE wording experiment.
# 3 experiments x 2 arms x N trials. Each trial gets its own dir so agents cannot collide.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)/exp"
N="${1:-5}"
rm -rf "$ROOT"; mkdir -p "$ROOT"

for arm in A B; do
  for i in $(seq 1 "$N"); do
    # ---- E1: modality (should vs must) ----
    d="$ROOT/e1/$arm/$i"; mkdir -p "$d"
    printf 'alpha\nbravo\ncharlie\ndelta\necho\nfoxtrot\ngolf\n' > "$d/data.txt"
    printf '# Ledger\n\n' > "$d/LEDGER.md"

    # ---- E2: vague vs measurable acceptance criteria ----
    d="$ROOT/e2/$arm/$i"; mkdir -p "$d"
    printf 'id,name,score\n1,alice,90\n2,bob,85\n3,carol,\n4,dan,72\n' > "$d/report.csv"

    # ---- E4: synonym drift (mixed verbs vs one verb) ----
    d="$ROOT/e4/$arm/$i"; mkdir -p "$d"
    : > "$d/a.txt"                                  # empty        -> non-empty = NO
    printf 'ready\n' > "$d/b.txt"                   # no "ok"      -> contains ok = NO
    printf 'one\ntwo\nthree' > "$d/c.txt"           # 3 lines, no trailing NL -> wc -l says 2 (trap); = YES
    printf '{"a": 1,}\n' > "$d/d.txt"               # trailing comma -> valid JSON = NO
  done
done
echo "fixtures built at $ROOT (N=$N per arm)"
find "$ROOT" -maxdepth 2 -type d | sort | head -20
