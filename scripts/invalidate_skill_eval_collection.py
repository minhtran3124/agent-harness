#!/usr/bin/env python3
"""Move an unobserved blocked record to an append-only collection-failure ledger.

This is intentionally narrower than editing an evaluation result: it can only withdraw a
``blocked`` record whose observation explicitly says the model response was unavailable because
of collection or environment failure. The original record is preserved in the ledger before a
captured first observation may be recorded for that case.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


FAILURE_MARKERS = ("did not preserve", "truncation prevented", "invalid environment")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.results.read_text(encoding="utf-8"))
        records = data.get("records")
        if not isinstance(records, list):
            raise ValueError("results has no records list")
        matches = [record for record in records if isinstance(record, dict) and record.get("case_id") == args.case]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one record for {args.case}")
        record = matches[0]
        observation = str(record.get("observation", "")).lower()
        if record.get("verdict") != "blocked" or not any(marker in observation for marker in FAILURE_MARKERS):
            raise ValueError("only explicitly unobserved blocked collection failures may be invalidated")
        ledger = []
        if args.ledger.exists():
            ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        if not isinstance(ledger, list):
            raise ValueError("ledger must be a JSON list")
        ledger.append({
            "case_id": args.case,
            "invalidated_at": datetime.now(timezone.utc).isoformat(),
            "reason": args.reason,
            "record": record,
        })
        data["records"] = [item for item in records if item is not record]
        args.ledger.parent.mkdir(parents=True, exist_ok=True)
        args.ledger.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        args.results.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"skill-eval-invalidate: {exc}", file=sys.stderr)
        return 1
    print(f"skill-eval-invalidate: moved {args.case} to {args.ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
