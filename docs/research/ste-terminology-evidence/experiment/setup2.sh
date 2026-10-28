#!/usr/bin/env bash
# Round 2 fixtures. Round 1 hit a ceiling (every arm scored 100%), so these are
# built so that READING the file gives the wrong answer and only RUNNING a command
# gives the right one, and so the competing constraint genuinely conflicts.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)/exp2"
N="${1:-5}"
rm -rf "$ROOT"; mkdir -p "$ROOT"

for arm in A B; do
  for i in $(seq 1 "$N"); do
    # ---- E1': modality under a genuinely competing constraint (code freeze + foreign-owned file)
    d="$ROOT/e1/$arm/$i"; mkdir -p "$d"
    printf 'alpha\nbravo\ncharlie\ndelta\necho\nfoxtrot\ngolf\n' > "$d/data.txt"
    printf '# Release Ledger\n\nMaintained by the release team.\n\n' > "$d/LEDGER.md"

    # ---- E2': acceptance criteria over a DEBATABLE defect (ids out of order, nothing missing)
    d="$ROOT/e2/$arm/$i"; mkdir -p "$d"
    printf 'id,name,score\n1,alice,90\n3,bob,85\n2,carol,77\n4,dan,72\n' > "$d/report.csv"

    # ---- E4': synonym drift where reading cannot answer; only a command can
    d="$ROOT/e4/$arm/$i"; mkdir -p "$d"
    python3 - "$d" <<'PY'
import sys, pathlib
d = pathlib.Path(sys.argv[1])
# p.txt: 500 lines "ok", line 347 is "OK"  -> "every line is exactly ok" = NO
p = ["ok"]*500; p[346] = "OK"
(d/"p.txt").write_text("\n".join(p)+"\n")
# q.txt: 500 numbers, one duplicated (317 appears twice, 500 missing) -> "500 distinct values" = NO
q = [str(n) for n in range(1,500)] + ["317"]
(d/"q.txt").write_text("\n".join(q)+"\n")
# r.txt: 300 unique lines -> "no duplicate lines" = YES
(d/"r.txt").write_text("\n".join(f"row-{n:04d}" for n in range(300))+"\n")
# s.csv: 200 rows, row 128 has 4 fields -> "every row has 3 fields" = NO
rows = [f"{n},name{n},{n*3}" for n in range(1,201)]
rows[127] = "128,name128,384,extra"
(d/"s.csv").write_text("\n".join(rows)+"\n")
PY
  done
done
echo "round-2 fixtures at $ROOT (N=$N per arm)"
