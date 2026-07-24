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

import argparse
import fcntl
import json
import os
import re
import sys
import uuid
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


REQUIRED_EVENT_KEYS = ("event_id", "seq", "ts", "slug", "run_id", "to_state")


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
                event = json.loads(line)
            except json.JSONDecodeError as e:
                raise StorageError(f"corrupt event log {path}:{lineno}: {e}")
            if not isinstance(event, dict) or not all(
                k in event for k in REQUIRED_EVENT_KEYS
            ):
                raise StorageError(
                    f"malformed event log {path}:{lineno}: missing required "
                    f"key(s) {REQUIRED_EVENT_KEYS}"
                )
            events.append(event)
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


# --- CLI ---------------------------------------------------------------


def cmd_init(args):
    slug = args.slug
    with locked_run(slug):
        ev_path = events_path(slug)
        if os.path.exists(ev_path):
            existing = read_events(slug)
            existing_run_id = existing[0].get("run_id")
            if args.run_id is None or existing_run_id == args.run_id:
                print(f"already initialized (run_id={existing_run_id})")
                return 0
            raise ConflictError(f"{slug} already initialized with a different run_id")
        run_id = args.run_id or str(uuid.uuid4())
        event = {
            "event_id": str(uuid.uuid4()),
            "seq": 1,
            "ts": now_iso(),
            "slug": slug,
            "run_id": run_id,
            "from_state": None,
            "to_state": "queued",
            "event": "run.init",
            "waiting_on": None,
            "resume_event": None,
            "sha": None,
            "metadata": {},
        }
        with open(ev_path, "w") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        atomic_write_json(run_json_path(slug), project(read_events(slug)))
    print(f"initialized {slug} run_id={run_id} state=queued")
    return 0


def cmd_transition(args):
    slug = args.slug
    with locked_run(slug):
        events = read_events(slug)
        current = project(events)
        from_state = current["state"]

        if args.event_id:
            for ev in events:
                if ev["event_id"] == args.event_id:
                    # Note: do NOT compare ev["from_state"] to the freshly recomputed
                    # `from_state` here — by replay time the projection has already
                    # advanced past this event, so from_state now equals the event's
                    # recorded to_state, not its from_state. Matching on to_state/event/
                    # waiting_on/resume_event/sha is sufficient since event_id already
                    # scopes the lookup to one historical event.
                    same = (
                        ev["to_state"] == args.to
                        and ev["event"] == args.event
                        and ev.get("waiting_on") == args.waiting_on
                        and ev.get("resume_event") == args.resume_event
                        and ev.get("sha") == args.sha
                    )
                    if same and ev["event_id"] == events[-1]["event_id"]:
                        print(
                            f"idempotent no-op: {slug} already at "
                            f"{ev['to_state']} via event_id={args.event_id}"
                        )
                        return 0
                    if same:
                        raise ConflictError(
                            f"event_id {args.event_id} matches a stale "
                            f"historical transition; current state is "
                            f"{from_state}, not {ev['to_state']}"
                        )
                    raise ConflictError(
                        f"event_id {args.event_id} already used for a "
                        "different transition"
                    )

        validate_transition(from_state, args.to, args.waiting_on, args.resume_event)

        if args.to == "shipped":
            if not args.sha or not SHA_RE.match(args.sha):
                raise InvalidTransitionError(
                    "shipped requires --sha matching a git SHA (7-40 hex chars)"
                )

        event = {
            "event_id": args.event_id or str(uuid.uuid4()),
            "seq": events[-1]["seq"] + 1,
            "ts": now_iso(),
            "slug": slug,
            "run_id": current["run_id"],
            "from_state": from_state,
            "to_state": args.to,
            "event": args.event,
            "waiting_on": args.waiting_on,
            "resume_event": args.resume_event,
            "sha": args.sha,
            "metadata": args.meta,
        }
        with open(events_path(slug), "a") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        atomic_write_json(run_json_path(slug), project(read_events(slug)))
    print(f"{slug}: {from_state} -> {args.to}")
    return 0


def cmd_status(args):
    data = read_json(run_json_path(args.slug))
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        for k in (
            "slug",
            "run_id",
            "state",
            "seq",
            "waiting_on",
            "resume_event",
            "sha",
            "updated_at",
        ):
            print(f"{k}: {data.get(k)}")
    return 0


def cmd_list(args):
    specs_root = "specs"
    results = []
    if os.path.isdir(specs_root):
        for slug in sorted(os.listdir(specs_root)):
            path = run_json_path(slug)
            if not os.path.isfile(path):
                continue
            try:
                data = read_json(path)
            except StorageError as e:
                print(f"warning: {slug}: {e} (run rebuild --check)", file=sys.stderr)
                continue
            if args.active and data.get("state") in TERMINAL_STATES:
                continue
            results.append(data)
    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        for data in results:
            print(
                f"{data.get('slug')}: {data.get('state')} "
                f"(waiting_on={data.get('waiting_on')})"
            )
    return 0


def cmd_rebuild(args):
    slug = args.slug
    with locked_run(slug):
        rebuilt = project(read_events(slug))
        if args.check:
            current = read_json(run_json_path(slug))
            if current != rebuilt:
                print("DRIFT: RUN.json does not match events.jsonl", file=sys.stderr)
                return 3
            print(f"{slug}: RUN.json matches events.jsonl (seq={rebuilt['seq']})")
            return 0
        atomic_write_json(run_json_path(slug), rebuilt)
    print(f"{slug}: rebuilt RUN.json from events.jsonl (seq={rebuilt['seq']})")
    return 0


def parse_meta(pairs):
    meta = {}
    for pair in pairs:
        if "=" not in pair:
            raise RunStateError(f"invalid --meta {pair!r}; expected key=value")
        k, v = pair.split("=", 1)
        meta[k] = v
    return meta


def build_parser():
    p = argparse.ArgumentParser(prog="run_state.py")
    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--slug", required=True)
    p_init.add_argument("--run-id")

    p_tr = sub.add_parser("transition")
    p_tr.add_argument("--slug", required=True)
    p_tr.add_argument("--to", required=True, choices=sorted(ALL_STATES))
    p_tr.add_argument("--event", required=True)
    p_tr.add_argument("--event-id")
    p_tr.add_argument("--waiting-on")
    p_tr.add_argument("--resume-event")
    p_tr.add_argument("--sha")
    p_tr.add_argument("--meta", action="append", default=[])

    p_st = sub.add_parser("status")
    p_st.add_argument("--slug", required=True)
    p_st.add_argument("--json", action="store_true")

    p_ls = sub.add_parser("list")
    p_ls.add_argument("--active", action="store_true")
    p_ls.add_argument("--json", action="store_true")

    p_rb = sub.add_parser("rebuild")
    p_rb.add_argument("--slug", required=True)
    p_rb.add_argument("--check", action="store_true")

    return p, sub


def main(argv=None):
    parser, sub = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "init": cmd_init,
        "transition": cmd_transition,
        "status": cmd_status,
        "list": cmd_list,
        "rebuild": cmd_rebuild,
    }
    try:
        if args.command == "transition":
            args.meta = parse_meta(args.meta)
        return handlers[args.command](args)
    except RunStateError as e:
        print(str(e), file=sys.stderr)
        return e.exit_code


if __name__ == "__main__":
    sys.exit(main())
