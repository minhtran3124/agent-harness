#!/usr/bin/env python3
"""Durable run-state engine and CLI for harness-skills specs (GitHub issue #129, Phase A).

Storage layout per slug (specs/<slug>/):
  events.jsonl      - append-only event log, one JSON object per line (see Event schema)
  events.jsonl.lock - fcntl lock file guarding the read-validate-append-project sequence
  RUN.json           - atomic projection of the current run state, rebuildable from events.jsonl

Event schema (one line of events.jsonl):
  {
    "event_id": str,          # idempotency key; client-supplied via --event-id, else uuid4
    "seq": int,                # monotonic, assigned by the engine, starts at 1
    "ts": str,                  # ISO-8601 UTC, e.g. "2026-07-24T10:00:00Z"
    "slug": str,
    "run_id": str,
    "from_state": str | None,   # None only for the synthetic init event
    "to_state": str,
    "event": str,                # "namespace.action", e.g. "agent.plan_ready"
    "waiting_on": str | None,
    "resume_event": str | None,
    "sha": str | None,
    "metadata": dict,
  }

RUN.json projection schema:
  {
    "slug": str, "run_id": str, "state": str, "seq": int,
    "waiting_on": str | None, "resume_event": str | None, "sha": str | None,
    "created_at": str, "updated_at": str, "last_event_id": str,
  }

Exit codes: 0 success or idempotent no-op; 2 invalid input or invalid transition;
3 missing/corrupt storage or I/O failure.
"""

import fcntl
import json
import os
import re
from datetime import datetime, timezone


class RunStateError(Exception):
    """Base for engine errors; carries the process exit code to use."""

    exit_code = 2


class InvalidTransitionError(RunStateError):
    exit_code = 2


class ConflictError(RunStateError):
    exit_code = 2


class StorageError(RunStateError):
    exit_code = 3


def spec_dir(slug):
    return os.path.join("specs", slug)


def events_path(slug):
    return os.path.join(spec_dir(slug), "events.jsonl")


def lock_path(slug):
    return os.path.join(spec_dir(slug), "events.jsonl.lock")


def run_json_path(slug):
    return os.path.join(spec_dir(slug), "RUN.json")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomic_write_json(path, obj):
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise StorageError(f"missing: {path}")
    except json.JSONDecodeError as e:
        raise StorageError(f"corrupt JSON in {path}: {e}")


def read_events(slug):
    path = events_path(slug)
    if not os.path.exists(path):
        raise StorageError(f"missing: {path}")
    events = []
    with open(path) as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise StorageError(f"corrupt event log {path}:{lineno}: {e}")
    if not events:
        raise StorageError(f"empty event log: {path}")
    return events


class locked_run:
    """Context manager: fcntl-exclusive-locks the slug's events.jsonl.lock for the
    duration of a read-validate-append-project sequence. Blocks until acquired.
    POSIX-only (fcntl) - matches this repo's macOS/Ubuntu-only CI, no Windows target."""

    def __init__(self, slug):
        self.slug = slug
        self._fh = None

    def __enter__(self):
        os.makedirs(spec_dir(self.slug), exist_ok=True)
        self._fh = open(lock_path(self.slug), "a+")
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
        except Exception:
            self._fh.close()
            raise
        return self

    def __exit__(self, *exc):
        fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        self._fh.close()
        return False


# --- FSM: states, valid transitions, projection fold -----------------------

TERMINAL_STATES = {"shipped", "cancelled", "superseded"}
INTERRUPT_STATES = {"blocked", "escalated"}
WAITING_STATES = {"awaiting_confirmation", "awaiting_ci", "awaiting_review"}
ACTIVE_STATES = {
    "queued",
    "investigating",
    "awaiting_confirmation",
    "planning",
    "implementing",
    "verifying",
    "awaiting_ci",
    "fixing_ci",
    "awaiting_review",
    "addressing_review",
    "ready_to_merge",
}
ALL_STATES = ACTIVE_STATES | INTERRUPT_STATES | TERMINAL_STATES

# Happy-path forward edges. Every active state may ALSO go to blocked/escalated/
# cancelled/superseded at any time (added by valid_targets) — those are universal
# interrupts, not modeled per-state here to avoid repeating them 11 times.
FORWARD_TRANSITIONS = {
    "queued": {"investigating"},
    "investigating": {"awaiting_confirmation", "planning"},
    "awaiting_confirmation": {"planning"},
    "planning": {"implementing"},
    "implementing": {"verifying"},
    "verifying": {"awaiting_ci", "ready_to_merge"},
    "awaiting_ci": {"fixing_ci", "awaiting_review", "ready_to_merge"},
    "fixing_ci": {"awaiting_ci", "verifying"},
    "awaiting_review": {"addressing_review", "ready_to_merge"},
    "addressing_review": {"awaiting_review", "verifying"},
    "ready_to_merge": {"shipped"},
}

SHA_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)


def valid_targets(state):
    """States `state` may transition to. Empty set for terminal states."""
    if state in TERMINAL_STATES:
        return set()
    if state in INTERRUPT_STATES:
        # Resume into any active state, or give up.
        return ACTIVE_STATES | {"cancelled"}
    targets = set(FORWARD_TRANSITIONS.get(state, set()))
    targets |= {"blocked", "escalated", "cancelled", "superseded"}
    return targets


def validate_transition(from_state, to_state, waiting_on, resume_event):
    if from_state not in ALL_STATES:
        raise InvalidTransitionError(f"unknown from_state: {from_state!r}")
    if to_state not in ALL_STATES:
        raise InvalidTransitionError(f"unknown to_state: {to_state!r}")
    if from_state in TERMINAL_STATES:
        raise InvalidTransitionError(
            f"{from_state} is terminal; no further transitions"
        )
    if to_state not in valid_targets(from_state):
        raise InvalidTransitionError(
            f"{from_state} -> {to_state} is not a valid transition"
        )
    if to_state in WAITING_STATES and not waiting_on:
        raise InvalidTransitionError(f"{to_state} requires --waiting-on")
    if to_state in INTERRUPT_STATES and not resume_event:
        raise InvalidTransitionError(f"{to_state} requires --resume-event")


def project(events):
    """Pure fold: replay an ordered event list into the current RUN.json projection."""
    if not events:
        raise StorageError("no events to project")
    first = events[0]
    state = first["to_state"]
    waiting_on = first.get("waiting_on")
    resume_event = first.get("resume_event")
    sha = first.get("sha")
    for ev in events[1:]:
        state = ev["to_state"]
        waiting_on = ev.get("waiting_on")
        resume_event = ev.get("resume_event")
        if ev.get("sha"):
            sha = ev["sha"]
    last = events[-1]
    return {
        "slug": first["slug"],
        "run_id": first["run_id"],
        "state": state,
        "seq": last["seq"],
        "waiting_on": waiting_on,
        "resume_event": resume_event,
        "sha": sha,
        "created_at": first["ts"],
        "updated_at": last["ts"],
        "last_event_id": last["event_id"],
    }
