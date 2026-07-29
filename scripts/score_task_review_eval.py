#!/usr/bin/env python3
"""Score task-review A/B: quality is an absolute gate before efficiency."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path


def labels(outputs: list[str]) -> set[str]:
    text = "\n".join(outputs).lower().replace("*", "").replace("`", "")
    found = set()
    if "cannot_verify" in text or "cannot verify" in text: found.add("cannot_verify")
    if "spec_verdict: fail" in text or "spec: fail" in text: found.add("spec_fail")
    if "quality_verdict: needs_fixes" in text or "needs_fixes" in text or "needs fixes" in text: found.add("quality_fix")
    if "minor" in text: found.add("minor")
    if "plan-mandated" in text or "criterion" in text or "secret" in text: found.add("plan_mandated")
    if "spec_verdict: pass" in text or "spec: pass" in text: found.add("spec_pass")
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare", nargs=2, type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, default=Path("evals/skills/task-review/fixtures"))
    parser.add_argument("--quality-gate", action="store_true")
    parser.add_argument("--efficiency-gate", action="store_true")
    args = parser.parse_args()
    base, candidate = (json.loads(p.read_text()) for p in args.compare)
    errors = []
    if base["environment"] != candidate["environment"]: errors.append("environment mismatch")
    b = {r["case_id"]: r for r in base["records"]}; c = {r["case_id"]: r for r in candidate["records"]}
    if set(b) != set(c): errors.append("case collections differ")
    for name, record in c.items():
        truth = json.loads((args.fixtures / name / "truth.json").read_text())
        seen = labels(record["outputs"])
        for required in truth["required"]:
            if required not in seen: errors.append(f"{name}: missed required {required}")
        for forbidden in truth["forbidden"]:
            if forbidden in seen: errors.append(f"{name}: unsafe/false-positive {forbidden}")
    if args.efficiency_gate:
        if sum(r["dispatches"] for r in c.values()) >= sum(r["dispatches"] for r in b.values()): errors.append("review dispatches did not fall")
        for label, collection in (("baseline", b), ("candidate", c)):
            for record in collection.values():
                if not record.get("elapsed_seconds"): errors.append(f"{label}: missing elapsed time")
        if not errors:
            old = statistics.median(sum(r["elapsed_seconds"]) for r in b.values()); new = statistics.median(sum(r["elapsed_seconds"]) for r in c.values())
            if new > old: errors.append(f"median runtime regressed: {old} -> {new}")
    if errors:
        print("\n".join(errors), file=sys.stderr); return 1
    print("task-review-eval: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
