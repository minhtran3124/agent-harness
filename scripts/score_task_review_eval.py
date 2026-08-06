#!/usr/bin/env python3
"""Score task-review A/B: quality is an absolute gate before efficiency."""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

# A negated mention ("no minor findings", "0 minor") must not be credited as a
# Minor finding — otherwise a reviewer that reports *no* Minor issue still
# satisfies the minor-only fixture on the bare substring.
_NEG_MINOR = re.compile(r"\b(no|zero|0|without|not any|no new)\s+minor\b")


def labels(outputs: list[str]) -> set[str]:
    text = "\n".join(outputs).lower().replace("*", "").replace("`", "")
    found = set()
    if "cannot_verify" in text or "cannot verify" in text: found.add("cannot_verify")
    if "spec_verdict: fail" in text or "spec: fail" in text: found.add("spec_fail")
    if "quality_verdict: needs_fixes" in text or "needs_fixes" in text or "needs fixes" in text: found.add("quality_fix")
    if "minor" in text and not _NEG_MINOR.search(text): found.add("minor")
    if "plan-mandated" in text or "criterion" in text or "secret" in text: found.add("plan_mandated")
    if "spec_verdict: pass" in text or "spec: pass" in text: found.add("spec_pass")
    return found


def record_tokens(record: dict) -> int:
    """Input+output reviewer tokens for one case, summed across its dispatches."""
    total = 0
    for usage in record.get("usage", []):
        if isinstance(usage, dict):
            total += (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0)
    return total


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
                if record_tokens(record) <= 0: errors.append(f"{label}: {record['case_id']} missing token usage")
        if not errors:
            old = statistics.median(sum(r["elapsed_seconds"]) for r in b.values()); new = statistics.median(sum(r["elapsed_seconds"]) for r in c.values())
            if new > old: errors.append(f"median runtime regressed: {old} -> {new}")
            # SC-8 also promises candidate median reviewer *tokens* do not exceed baseline.
            old_tok = statistics.median(record_tokens(r) for r in b.values()); new_tok = statistics.median(record_tokens(r) for r in c.values())
            if new_tok > old_tok: errors.append(f"median reviewer tokens regressed: {old_tok} -> {new_tok}")
    if errors:
        print("\n".join(errors), file=sys.stderr); return 1
    print("task-review-eval: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
