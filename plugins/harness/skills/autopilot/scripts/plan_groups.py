#!/usr/bin/env python3
"""Turn ticket dependencies into execution groups.

Input JSON (stdin, or --input FILE): [{"n": 1, "deps": [2, 3]}, ...]
Output JSON: [{"n": 1, "group": 1}, ...] in input order.
group = 1 + the longest dependency path inside the batch. A dep outside the batch is ignored
(a note goes to stderr): it must already be closed. A cycle exits 2 and names the tickets.
"""
import argparse
import json
import sys


def plan(items):
    nums = [int(i["n"]) for i in items]
    batch = set(nums)
    deps = {}
    for i in items:
        n = int(i["n"])
        inside = []
        for d in i.get("deps") or []:
            d = int(d)
            if d == n:
                continue
            if d in batch:
                inside.append(d)
            else:
                print(f"plan_groups: #{n} depends on #{d}, outside the batch; "
                      f"ignored (it must already be closed)", file=sys.stderr)
        deps[n] = sorted(set(inside))
    group, state = {}, {}

    def visit(n, path):
        if state.get(n) == 2:
            return group[n]
        if state.get(n) == 1:
            cyc = path[path.index(n):] + [n]
            raise ValueError("dependency cycle: " + " -> ".join(f"#{x}" for x in cyc))
        state[n] = 1
        group[n] = 1 + max((visit(d, path + [n]) for d in deps[n]), default=0)
        state[n] = 2
        return group[n]

    for n in nums:
        visit(n, [])
    return [{"n": n, "group": group[n]} for n in nums]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", help="JSON file; default is stdin")
    args = ap.parse_args(argv)
    try:
        raw = open(args.input).read() if args.input else sys.stdin.read()
        out = plan(json.loads(raw))
    except ValueError as e:
        print(f"plan_groups: {e}", file=sys.stderr)
        return 2
    except (OSError, KeyError, TypeError) as e:
        print(f"plan_groups: bad input: {e}", file=sys.stderr)
        return 2
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
