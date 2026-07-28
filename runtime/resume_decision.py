#!/usr/bin/env python3
"""Return a deterministic, read-only resume decision for one harness run.

This keeps lifecycle branching out of the execution skill.  It deliberately does not transition
state or rebuild a projection; callers must perform an explicit repair after seeing the result.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import run_state as rs


def plan_status(slug: str) -> str | None:
    path = Path("specs") / slug / "PLAN.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip()
    return None


def result(action: str, reason: str, **extra: object) -> dict[str, object]:
    return {"action": action, "reason": reason, **extra}


def decide(slug: str) -> dict[str, object]:
    run_path = Path(rs.run_json_path(slug))
    event_path = Path(rs.events_path(slug))
    has_run, has_events = run_path.is_file(), event_path.is_file()
    if not has_run and not has_events:
        return result("execute-plan", "run was never initialized", state="untracked")
    if has_run and not has_events:
        return result("stop", "RUN.json exists without canonical events.jsonl", state="corrupt")
    if has_events and not has_run:
        return result("rebuild", "events.jsonl exists but RUN.json projection is missing")
    try:
        events = rs.read_events(slug)
        projection = rs.read_json(rs.run_json_path(slug))
    except rs.StorageError as exc:
        return result("stop", str(exc), state="corrupt")
    rebuilt = rs.project(events)
    if projection != rebuilt:
        return result("rebuild", "RUN.json does not match events.jsonl", state=projection.get("state"))
    state = projection.get("state")
    if state not in rs.ALL_STATES:
        return result("stop", f"unknown run state: {state!r}", state=state)
    if state in rs.TERMINAL_STATES:
        return result("stop", "run is terminal; human decision required", state=state)
    if state in rs.WAITING_STATES:
        return result("wait", "run is waiting on an external decision or result", state=state,
                      waiting_on=projection.get("waiting_on"))
    if state in rs.INTERRUPT_STATES:
        origin = events[-1].get("from_state")
        return result("wait", "resolve interrupt then return to recorded origin", state=state,
                      origin_state=origin, waiting_on=projection.get("waiting_on"),
                      resume_event=projection.get("resume_event"))
    if state in {"fixing_ci", "addressing_review"}:
        return result("resume-repair", "resume the named post-PR repair loop", state=state,
                      plan_status=plan_status(slug))
    if state == "verifying":
        return result("resume-review-chain", "tasks passed; resume final review chain", state=state)
    if state in {"queued", "investigating"}:
        return result("execute-plan", "advance legally through planning before implementation", state=state,
                      required_path=["investigating", "planning", "implementing"])
    return result("execute-plan", "resume plan execution", state=state, plan_status=plan_status(slug))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    args = parser.parse_args()
    print(json.dumps(decide(args.slug), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
