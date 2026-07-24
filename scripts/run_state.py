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
        fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        self._fh.close()
        return False
