#!/usr/bin/env python3
"""Check marker order in a replay transcript written by transcript.py.

Exit 0 when the first LOOP-RED < first HYPOTHESIS < first PROBE < first REVIEW.
Exit 1 and name the first failed pair otherwise. Exit 2 on a usage error.
"""
import sys

ORDER = ["LOOP-RED", "HYPOTHESIS", "PROBE", "REVIEW"]


def first_positions(lines):
    first = {}
    for i, line in enumerate(lines, 1):
        marker = line.split("\t", 1)[0].strip()
        if marker in ORDER and marker not in first:
            first[marker] = i
    return first


def main(argv):
    if len(argv) != 2:
        print("usage: check_replay.py <replay.md>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        first = first_positions(f.read().splitlines())
    for a, b in zip(ORDER, ORDER[1:]):
        pa, pb = first.get(a), first.get(b)
        if pa is None or pb is None or pa >= pb:
            print(f"FAIL {a} before {b}: first {a} at line {pa}, first {b} at line {pb}")
            return 1
    print("PASS " + " < ".join(f"{m}@{first[m]}" for m in ORDER))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
