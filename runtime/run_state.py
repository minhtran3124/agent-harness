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
3 missing/corrupt storage, illegal event chain, projection drift, or I/O failure.
"""

import argparse
import fcntl
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

RUNTIME_MODES = {"enforced", "advisory", "unsupported"}
RUNTIME_EVIDENCE_ID_RE = re.compile(r"^codex-mode-[0-9a-f]{16}$")


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
    except (OSError, UnicodeDecodeError) as e:
        # Round-16 review (Fix 4): FileNotFoundError is an OSError subclass and is
        # matched by the more specific clause above first. Everything else an open()
        # or a read can raise on corrupted/inaccessible storage - IsADirectoryError,
        # PermissionError, a non-UTF-8 byte - used to propagate uncaught (exit 1, a
        # traceback), outside the documented 0/2/3 contract. Corruption is precisely
        # this feature's scenario, not a hypothetical input.
        raise StorageError(f"cannot read {path}: {e}")


REQUIRED_EVENT_KEYS = ("event_id", "seq", "ts", "slug", "run_id", "to_state")


def read_events(slug, validate=True):
    path = events_path(slug)
    if not os.path.exists(path):
        raise StorageError(f"missing: {path}")
    events = []
    try:
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
    except (OSError, UnicodeDecodeError) as e:
        # Round-16 review (Fix 4): the pre-existing os.path.exists check above only
        # rules out a missing file - it does not rule out events.jsonl being a
        # directory (IsADirectoryError), unreadable (PermissionError), or containing
        # a non-UTF-8 byte (UnicodeDecodeError). cmd_status now reads this on every
        # call (the prior commit's Fix 1), so this input class is directly reachable,
        # not hypothetical - and it used to raise uncaught (exit 1, a traceback),
        # outside the documented 0/2/3 contract. StorageError raised deliberately
        # inside this same try (corrupt JSON / malformed event) is not an OSError or
        # UnicodeDecodeError, so it is unaffected and still propagates as-is.
        raise StorageError(f"cannot read {path}: {e}")
    if not events:
        raise StorageError(f"empty event log: {path}")
    if validate:
        validate_chain(events, slug, path)
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


class locked_run_readonly:
    """Read-only counterpart to locked_run, used by cmd_status (Round-16 review,
    Fix 1). cmd_status reads RUN.json, then reads+folds events.jsonl, to compare
    them; without a lock spanning both reads, a transition landing between them
    (cmd_transition holds locked_run across its append+fsync -> atomic_write_json)
    can make the fold newer than the projection it's compared against, reporting
    'projection drift' on a store that was never actually corrupt.

    Two deliberate departures from locked_run, both load-bearing:

    - Only acquires when `spec_dir(slug)` already exists. locked_run.__enter__
      unconditionally does os.makedirs(spec_dir) + open(lock_path, "a+"), so using
      it as-is here would make a read-only command fabricate a directory and a
      .lock file for ANY slug argument, including a typo — status on a slug that
      was never initialized must still fail cleanly with nothing created, exactly
      as it did before this fix (pinned by
      test_status_readonly_lock_does_not_create_storage_for_a_typo_slug).
    - Takes LOCK_SH, not LOCK_EX. A writer's LOCK_EX (locked_run) blocks against
      any LOCK_SH, so this still serializes against a transition in flight - that
      is the property this fix needs. But LOCK_SH does not block other LOCK_SH
      holders, so concurrent `status` calls do not needlessly serialize against
      each other, only against writers.
    """

    def __init__(self, slug):
        self.slug = slug
        self._fh = None

    def __enter__(self):
        if os.path.isdir(spec_dir(self.slug)):
            self._fh = open(lock_path(self.slug), "a+")
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_SH)
            except Exception:
                self._fh.close()
                self._fh = None
                raise
        return self

    def __exit__(self, *exc):
        if self._fh is not None:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            self._fh.close()
        return False


# --- FSM: states, valid transitions, projection fold -----------------------

TERMINAL_STATES = {"shipped", "cancelled", "superseded"}
# GitHub issue #174 follow-up (Fix 2): the only targets a `transition` may reach
# over an INVALID event chain - closing a bricked run, not extending its history.
# `shipped` is deliberately excluded even though it is also terminal: it asserts
# the run finished successfully and requires a real --sha, neither of which this
# bypass has any honest way to earn from a chain it does not trust.
CLOSEABLE_OVER_INVALID_CHAIN = {"cancelled", "superseded"}
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
    runtime_mode = None
    runtime_evidence_id = None
    first_metadata = first.get("metadata")
    if isinstance(first_metadata, dict):
        runtime_mode = first_metadata.get("runtime_mode")
        runtime_evidence_id = first_metadata.get("runtime_evidence_id")
    for ev in events[1:]:
        state = ev["to_state"]
        waiting_on = ev.get("waiting_on")
        resume_event = ev.get("resume_event")
        if ev.get("sha"):
            sha = ev["sha"]
        metadata = ev.get("metadata")
        if isinstance(metadata, dict) and "runtime_mode" in metadata:
            runtime_mode = metadata.get("runtime_mode")
            runtime_evidence_id = metadata.get("runtime_evidence_id")
    last = events[-1]
    result = {
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
    if runtime_mode is not None and runtime_evidence_id is not None:
        result["runtime_mode"] = runtime_mode
        result["runtime_evidence_id"] = runtime_evidence_id
    return result


def runtime_metadata(mode, evidence_id):
    """Validate an optional all-or-nothing sanitized Codex runtime diagnosis."""
    if mode is None and evidence_id is None:
        return {}
    if mode not in RUNTIME_MODES or not isinstance(evidence_id, str) or not RUNTIME_EVIDENCE_ID_RE.fullmatch(evidence_id):
        raise RunStateError(
            "--runtime-mode and --runtime-evidence-id must be supplied together "
            "with a valid Codex runtime diagnosis"
        )
    return {"runtime_mode": mode, "runtime_evidence_id": evidence_id}


def validate_chain(events, slug, path):
    """Pure validator: raises StorageError on the first violation of nine
    invariants (numbered 1-9 below), so that project() only ever folds a history
    that could actually have happened."""
    first = events[0]
    seen_event_ids = set()
    prev = None
    for n, ev in enumerate(events, start=1):
        # 1. seq contiguous from 1. type(...) is int, not isinstance - bool is an int
        # subclass and True == 1 would otherwise satisfy contiguity without being one.
        if type(ev.get("seq")) is not int:
            raise StorageError(f"invalid event chain {path}:{n}: seq is not an int")
        if ev["seq"] != n:
            raise StorageError(
                f"invalid event chain {path}:{n}: expected seq {n}, got {ev['seq']!r}"
            )

        # 2. from_state chains to the previous event's to_state. Genesis (seq 1) has
        # no previous event, so this is skipped for it.
        if prev is not None and ev.get("from_state") != prev["to_state"]:
            raise StorageError(
                f"invalid event chain {path}:{n}: from_state "
                f"{ev.get('from_state')!r} does not match previous to_state "
                f"{prev['to_state']!r}"
            )

        # 3. slug and run_id constant across the whole chain, and the chain's own
        # slug matches the slug argument.
        if ev.get("slug") != first.get("slug"):
            raise StorageError(
                f"invalid event chain {path}:{n}: slug {ev.get('slug')!r} does not "
                f"match chain slug {first.get('slug')!r}"
            )
        if ev.get("run_id") != first.get("run_id"):
            raise StorageError(
                f"invalid event chain {path}:{n}: run_id {ev.get('run_id')!r} does "
                f"not match chain run_id {first.get('run_id')!r}"
            )
        if n == 1 and first.get("slug") != slug:
            raise StorageError(
                f"invalid event chain {path}:{n}: chain slug {first.get('slug')!r} "
                f"does not match requested slug {slug!r}"
            )

        # 4. Genesis carve-out, stated positively: seq 1 must have from_state None
        # and to_state "queued". `!=` is safe against non-str values (no TypeError),
        # so this needs no type guard of its own.
        if n == 1 and (
            ev.get("from_state") is not None or ev.get("to_state") != "queued"
        ):
            raise StorageError(
                f"invalid event chain {path}:{n}: genesis must have from_state None "
                f"and to_state {'queued'!r}, got from_state "
                f"{ev.get('from_state')!r} to_state {ev.get('to_state')!r}"
            )

        # 5. Hop legality, delegated to validate_transition - skipped for genesis
        # (seq 1), which invariant 4 above has already forced to from_state None,
        # to_state "queued". The to_state type guard is unconditional but, at n == 1,
        # defensive only and unreachable in practice: invariant 4 already forces
        # to_state == "queued" (a str) for any event that gets this far. It remains
        # load-bearing for n > 1, where an unhashable to_state would otherwise raise
        # TypeError from validate_transition's `to_state not in ALL_STATES`
        # membership test.
        if type(ev.get("to_state")) is not str:
            raise StorageError(
                f"invalid event chain {path}:{n}: to_state is not a string"
            )
        if n > 1:
            try:
                validate_transition(
                    ev["from_state"],
                    ev["to_state"],
                    ev.get("waiting_on"),
                    ev.get("resume_event"),
                )
            except InvalidTransitionError as e:
                raise StorageError(f"invalid event chain {path}:{n}: {e}")

        # 6. event_id unique across the whole chain.
        if type(ev.get("event_id")) is not str:
            raise StorageError(
                f"invalid event chain {path}:{n}: event_id is not a string"
            )
        if ev["event_id"] in seen_event_ids:
            raise StorageError(
                f"invalid event chain {path}:{n}: duplicate event_id {ev['event_id']!r}"
            )
        seen_event_ids.add(ev["event_id"])

        # 7. event is a string. REQUIRED_EVENT_KEYS omits "event", and nothing else
        # checks it - cmd_transition's idempotent-replay scan dereferences it with a
        # bare subscript (`ev["event"] == args.event`), which would otherwise raise an
        # uncaught KeyError on a log entry missing the key entirely.
        if type(ev.get("event")) is not str:
            raise StorageError(f"invalid event chain {path}:{n}: event is not a string")

        # 8. shipped requires a real sha. cmd_transition enforces --sha (matching
        # SHA_RE) only on the write path; validate_transition (invariant 5) knows
        # nothing about sha, so a hand-written log ending in a shipped event with
        # sha None or garbage would otherwise validate clean. to_state is already
        # confirmed to be a str by the guard above, so a bare subscript is safe here.
        if ev["to_state"] == "shipped":
            sha = ev.get("sha")
            if type(sha) is not str or not SHA_RE.match(sha):
                raise StorageError(
                    f"invalid event chain {path}:{n}: shipped requires sha matching "
                    f"a git SHA (7-40 hex chars), got {sha!r}"
                )

        # 9. Optional runtime diagnosis metadata is an all-or-nothing sanitized
        # pair. A forged `enforced` projection must not pass chain validation.
        metadata = ev.get("metadata", {})
        if not isinstance(metadata, dict):
            raise StorageError(
                f"invalid event chain {path}:{n}: metadata is not an object"
            )
        runtime_mode = metadata.get("runtime_mode")
        runtime_evidence_id = metadata.get("runtime_evidence_id")
        try:
            runtime_metadata(runtime_mode, runtime_evidence_id)
        except RunStateError as e:
            raise StorageError(f"invalid event chain {path}:{n}: {e}")

        prev = ev


# --- Locked durable-state snapshot (GitHub issue #175, Task 1.1) -------------

# The closed vocabulary snapshot_run_state classifies a slug's on-disk storage into
# (design section 5.1). Kept as a named set so both consumers - cmd_status here and
# resume_decision in a later task - branch on the same six values, not scattered
# string literals.
SNAPSHOT_STATUSES = frozenset(
    {
        "untracked",  # neither RUN.json nor events.jsonl exists
        "projection-only",  # RUN.json exists, the canonical log does not
        "events-only",  # a valid log exists, its projection does not
        "drift",  # both exist, but RUN.json differs from a validated fold
        "invalid",  # unreadable storage or an illegal event chain (StorageError)
        "consistent",  # validated events plus a matching projection
    }
)


@dataclass
class RunSnapshot:
    """Neutral, read-only result of snapshot_run_state.

    - status:     one of SNAPSHOT_STATUSES (storage topology).
    - events:     the validated event list when a legal log was read
                  (events-only / drift / consistent), else None.
    - projection: the RUN.json-shaped dict where one is available - the fold of the
                  log for events-only / drift / consistent, or the raw RUN.json for
                  projection-only. None for untracked / invalid.
    - error:      the StorageError message when status == "invalid", else None.
    """

    status: object
    events: object = None
    projection: object = None
    error: object = None


def snapshot_run_state(slug):
    """Classify a slug's durable storage topology under the shared read lock and
    return the validated data, without printing or mutating any canonical evidence.

    This is the single locked primitive both cmd_status and (in a later task)
    resume_decision consume; each keeps its own policy on top of the neutral result.
    All reads happen inside locked_run_readonly, so a transition holding the exclusive
    locked_run across its append -> projection-write cannot interleave and make the
    fold read here newer than the RUN.json it is compared against - i.e. no false
    `drift` verdict on storage that was always consistent.

    Read-only by construction: it never writes, rebuilds, or creates a spec directory
    or lock file beyond what locked_run_readonly already does when the spec dir
    already exists (nothing at all for an uninitialized/typo slug). read_events uses
    the default validate=True, so all issue #174 chain validation fires here and an
    illegal chain is reported as `invalid`, never folded.
    """
    with locked_run_readonly(slug):
        run_exists = os.path.exists(run_json_path(slug))
        events_exist = os.path.exists(events_path(slug))
        if not run_exists and not events_exist:
            return RunSnapshot(status="untracked")
        try:
            if events_exist:
                # A legal history only; an illegal chain raises StorageError and is
                # caught below as `invalid`, so project() only ever folds a valid log.
                events = read_events(slug)
                projected = project(events)
                if not run_exists:
                    return RunSnapshot(
                        status="events-only", events=events, projection=projected
                    )
                data = read_json(run_json_path(slug))
                if projected != data:
                    return RunSnapshot(
                        status="drift", events=events, projection=projected
                    )
                return RunSnapshot(
                    status="consistent", events=events, projection=projected
                )
            # RUN.json exists, events.jsonl does not: a projection with no canonical
            # log behind it. read_json still raises (caught as `invalid`) if RUN.json
            # is itself unreadable/corrupt.
            data = read_json(run_json_path(slug))
            return RunSnapshot(status="projection-only", projection=data)
        except StorageError as e:
            return RunSnapshot(status="invalid", error=str(e))


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
            "metadata": runtime_metadata(
                args.runtime_mode, args.runtime_evidence_id
            ),
        }
        with open(ev_path, "w") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        atomic_write_json(run_json_path(slug), project(read_events(slug)))
    print(f"initialized {slug} run_id={run_id} state=queued")
    return 0


# Metadata sentinel stamped on every event `_close_run_over_invalid_chain` writes,
# so a LATER call can recognize "the last event is our own prior close" and not
# confuse it with a forged/corrupt chain whose fabricated last line merely looks
# terminal (see the already-closed check in _close_run_over_invalid_chain).
_CLOSED_OVER_INVALID_CHAIN_KEY = "_closed_over_invalid_chain"


def _closing_seq_over_invalid_chain(events):
    """The closing event's own seq must not perpetuate whatever is broken about the
    chain's numbering — the issue's own forged log reuses seq=1 twice, so a naive
    `events[-1]["seq"] + 1` would land right back on a duplicate. Take the max of
    every syntactically valid int seq seen anywhere in the raw log and add 1; with
    no int seq anywhere, fall back to the event count. Either way this is a
    best-effort placement for an honest audit trail, not a claim that the resulting
    number continues a legal sequence — the chain it's appended to already isn't
    one."""
    int_seqs = [ev["seq"] for ev in events if type(ev.get("seq")) is int]
    return (max(int_seqs) + 1) if int_seqs else len(events) + 1


def _close_run_over_invalid_chain(slug, args, events, chain_error):
    """Append a closing event (`--to` already checked by the caller to be in
    CLOSEABLE_OVER_INVALID_CHAIN) to a log whose chain does not validate. This is
    the one deliberate bypass of the write path's normal refusal to extend an
    illegal history (E002-C / GitHub issue #174 follow-up) — narrow on purpose:
    abandoning a run is not extending its history, so it doesn't hand back the
    guarantee that refusal buys for every other target, which the caller still
    hard-blocks with no bypass.

    `from_state` cannot come from project(events): that fold over an illegal chain
    is exactly the fabricated value this feature exists to distrust. Instead this
    records the LAST event's raw `to_state` field, taken literally with no
    replay/fold logic applied — an honest "this is what the log's last line said",
    not a claim that reaching it was a legal transition. `seq` is handled by
    _closing_seq_over_invalid_chain for the same reason.

    Round-16 review added two more guards, both load-bearing before anything is
    written:

    - Already-closed check (Fix 3): the caller has already confirmed `args.to` is
      in CLOSEABLE_OVER_INVALID_CHAIN, which is itself a set of TERMINAL states -
      so the run is always terminal after the first successful close. Any further
      close call - same --to, a different --to, matching --event-id or not - must
      therefore be an idempotent no-op that reports what's already on disk, never
      a fresh append. Without this: a second `--to cancelled` appended a
      `cancelled -> cancelled` self-loop; a second call with a DIFFERENT --to (e.g.
      `superseded`) appended a `cancelled -> superseded` hop validate_transition
      forbids out of a terminal state; and two calls sharing one --event-id
      appended two events with that event_id, violating validate_chain's own
      invariant 6 (Fix 2) - all three are the same root cause and this one check
      closes all of them, since every repeat call hits it before reaching the
      append below.

      The detector cannot be "the raw last to_state is a terminal string" alone -
      a FORGED chain's fabricated last line can itself already claim "shipped"
      (the issue's own repro fixture does exactly this), and that must still be
      closeable on the FIRST call, not mistaken for "already closed by us". So
      the marker is narrower: `events[-1]["metadata"]` carries the
      `_CLOSED_OVER_INVALID_CHAIN_KEY` sentinel this function itself stamps on
      (below) - only an event THIS function previously wrote can carry it, so a
      merely terminal-looking but foreign last event does not trip the check.
    - run_id honesty (Fix 5): project() takes run_id from events[0], which
      invariant 3 is exactly what an invalid chain may have corrupted. slug is
      handled by overriding it with the caller's REQUESTED slug after the fold
      below (always honest - it's a function argument, not log data); run_id has
      no equivalent external source of truth, so if events[0]'s run_id is not a
      string this function cannot manufacture one — it refuses to close rather
      than write a RUN.json with fabricated content (the observed symptom was
      `list` printing a raw dict where a run_id belongs).
    """
    last_event = events[-1]
    last_to_state = last_event.get("to_state")
    last_metadata = last_event.get("metadata")
    already_closed_by_us = (
        type(last_to_state) is str
        and last_to_state in TERMINAL_STATES
        and isinstance(last_metadata, dict)
        and last_metadata.get(_CLOSED_OVER_INVALID_CHAIN_KEY) is True
    )
    if already_closed_by_us:
        print(
            f"{slug} is already closed at {last_to_state!r} over an invalid event "
            f"chain ({chain_error}); no new event appended (idempotent no-op)",
            file=sys.stderr,
        )
        print(f"{slug}: {last_to_state} (already closed)")
        return 0

    run_id = events[0].get("run_id")
    if type(run_id) is not str:
        raise StorageError(
            f"cannot close {slug} over an invalid chain: events[0].run_id is "
            f"{run_id!r}, not a string — closing would have to invent a run_id "
            "rather than record an honest one"
        )

    event = {
        "event_id": args.event_id or str(uuid.uuid4()),
        "seq": _closing_seq_over_invalid_chain(events),
        "ts": now_iso(),
        "slug": slug,
        "run_id": run_id,
        "from_state": last_to_state,
        "to_state": args.to,
        "event": args.event,
        "waiting_on": args.waiting_on,
        "resume_event": args.resume_event,
        "sha": args.sha,
        # The sentinel is what lets a LATER call to this same function recognize
        # its own prior work (see already_closed_by_us above) without confusing it
        # with a forged chain whose fabricated last line merely looks terminal.
        # It rides in metadata rather than replacing --event/--to so the caller's
        # own audit intent (e.g. "operator.abandon") is still recorded honestly.
        "metadata": {
            **args.meta,
            **runtime_metadata(args.runtime_mode, args.runtime_evidence_id),
            _CLOSED_OVER_INVALID_CHAIN_KEY: True,
        },
    }
    with open(events_path(slug), "a") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    # Deliberately NOT project(read_events(slug)): that re-reads with the default
    # validate=True and would immediately raise on the very corruption this path
    # exists to close over. Fold the raw events plus the new closing event directly
    # instead — the same "unvalidated fold" project() already performs for
    # `rebuild --allow-invalid-chain` — so RUN.json here never claims the preceding
    # history was legal.
    projected = project(events + [event])
    # project() takes slug from events[0] too, and invariant 3 (chain slug must
    # match the requested slug) is exactly what an invalid chain may have broken -
    # override with the REQUESTED slug, which is always honest (a function
    # argument, never log data).
    projected["slug"] = slug
    atomic_write_json(run_json_path(slug), projected)
    print(
        f"warning: {slug} closed to {args.to!r} over an INVALID event chain "
        f"({chain_error}); RUN.json is an unvalidated fold, not a verified history",
        file=sys.stderr,
    )
    print(f"{slug}: {last_to_state} -> {args.to} (closed over invalid chain)")
    return 0


def cmd_transition(args):
    slug = args.slug
    with locked_run(slug):
        events = read_events(slug, validate=False)
        try:
            validate_chain(events, slug, events_path(slug))
        except StorageError as chain_error:
            if args.to not in CLOSEABLE_OVER_INVALID_CHAIN:
                raise
            return _close_run_over_invalid_chain(slug, args, events, chain_error)

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
                        and ev.get("metadata", {}).get("runtime_mode")
                        == args.meta.get("runtime_mode")
                        and ev.get("metadata", {}).get("runtime_evidence_id")
                        == args.meta.get("runtime_evidence_id")
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
            "metadata": {
                **args.meta,
                **runtime_metadata(args.runtime_mode, args.runtime_evidence_id),
            },
        }
        with open(events_path(slug), "a") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        atomic_write_json(run_json_path(slug), project(read_events(slug)))
    print(f"{slug}: {from_state} -> {args.to}")
    return 0


def cmd_status(args):
    slug = args.slug
    # cmd_status now consumes the one shared locked snapshot (snapshot_run_state,
    # issue #175 Task 1.1) so it and resume see the exact same locked, validated
    # topology. Its own policy - exit codes, messages, and output format - is applied
    # here and is byte-for-byte unchanged from the pre-snapshot implementation, pinned
    # by the status tests. The snapshot performs both reads (RUN.json + a validated
    # fold of events.jsonl) under the shared lock, which is what closes the torn-read
    # race a transition's exclusive lock could otherwise open. See locked_run_readonly
    # for why no storage is created for a slug whose spec directory does not exist.
    snap = snapshot_run_state(slug)
    if snap.status in ("untracked", "events-only"):
        # RUN.json is the artifact `status` reads first, so its absence is the exit-3
        # "missing" the CLI has always reported for both these topologies - a bare
        # projection-less slug and a valid log whose projection was removed alike.
        raise StorageError(f"missing: {run_json_path(slug)}")
    if snap.status == "invalid":
        # Illegal event chain (issue #174's third repro line: a forged/hand-edited log
        # that `status` used to never look at) or unreadable storage - re-raise with
        # the engine's own StorageError message, exit 3, exactly as read_events /
        # read_json produced it before this refactor.
        raise StorageError(snap.error)
    if snap.status == "drift":
        # A legal chain that disagrees with RUN.json (a hand-edited RUN.json, or an
        # interrupted transition) is a second, distinct failure - named separately
        # from "invalid event chain" so the two causes are never confused.
        raise StorageError(
            f"RUN.json does not match events.jsonl for {slug}: projection "
            "drift (run `rebuild --slug " + slug + " --check` for details, "
            "then `rebuild --slug " + slug + "` to repair)"
        )
    # projection-only or consistent: print whatever the projection says, exit 0. The
    # projection-only branch is deliberately unchanged - Step -1 source 2's Branch B
    # (RUN.json exists, the log does not) must NOT be "improved" into a stop here;
    # resume applies that stricter policy. For `consistent`, snap.projection is the
    # validated fold, equal to RUN.json by definition, so the output is identical.
    data = snap.projection
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
    invalid = []
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
            # When a log exists, its chain must be a legal history or the RUN.json
            # projection cannot be trusted. Surface the invalid run and drop it from
            # the listing instead of advertising a possibly-fabricated state (issue
            # #196: `list` must stop visibly on an impossible chain, like status /
            # rebuild --check / resume). read_events is non-mutating and validates by
            # default. A run with RUN.json and no log is unaffected (the status
            # Branch-B case), so this only fires on a log that exists and is illegal.
            if os.path.isfile(events_path(slug)):
                try:
                    read_events(slug)
                except StorageError as e:
                    print(f"error: {slug}: {e}", file=sys.stderr)
                    invalid.append(slug)
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
    # Exit 3 (storage-error contract) if any listed run has an invalid chain — the
    # valid entries are still printed, but the command fails visibly so a caller
    # (or `set -e`) cannot read a clean exit as "all runs healthy".
    return 3 if invalid else 0


def cmd_rebuild(args):
    slug = args.slug
    with locked_run(slug):
        if args.allow_invalid_chain:
            print(
                "warning: chain validation skipped (--allow-invalid-chain); "
                "RUN.json is a fold of a possibly-illegal history, and a "
                '"matches" verdict only means RUN.json agrees with that fold',
                file=sys.stderr,
            )
        rebuilt = project(read_events(slug, validate=not args.allow_invalid_chain))
        if args.check:
            current = read_json(run_json_path(slug))
            if current != rebuilt:
                print("DRIFT: RUN.json does not match events.jsonl", file=sys.stderr)
                return 3
            if args.allow_invalid_chain:
                # Distinct from the plain-match message below: chain legality was
                # never checked, so this proves only that RUN.json agrees with an
                # unvalidated fold - not that the log is a legal history. A consumer
                # capturing stdout alone (the `2>/dev/null` idiom) must not be able to
                # mistake this for a fully validated pass.
                print(
                    f"{slug}: RUN.json matches an UNVALIDATED fold (seq={rebuilt['seq']})"
                )
            else:
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
    p_init.add_argument("--runtime-mode", choices=sorted(RUNTIME_MODES))
    p_init.add_argument("--runtime-evidence-id")

    p_tr = sub.add_parser("transition")
    p_tr.add_argument("--slug", required=True)
    p_tr.add_argument("--to", required=True, choices=sorted(ALL_STATES))
    p_tr.add_argument("--event", required=True)
    p_tr.add_argument("--event-id")
    p_tr.add_argument("--waiting-on")
    p_tr.add_argument("--resume-event")
    p_tr.add_argument("--sha")
    p_tr.add_argument("--meta", action="append", default=[])
    p_tr.add_argument("--runtime-mode", choices=sorted(RUNTIME_MODES))
    p_tr.add_argument("--runtime-evidence-id")

    p_st = sub.add_parser("status")
    p_st.add_argument("--slug", required=True)
    p_st.add_argument("--json", action="store_true")

    p_ls = sub.add_parser("list")
    p_ls.add_argument("--active", action="store_true")
    p_ls.add_argument("--json", action="store_true")

    p_rb = sub.add_parser("rebuild")
    p_rb.add_argument("--slug", required=True)
    p_rb.add_argument("--check", action="store_true")
    p_rb.add_argument("--allow-invalid-chain", action="store_true")

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
            args.meta.update(
                runtime_metadata(args.runtime_mode, args.runtime_evidence_id)
            )
        return handlers[args.command](args)
    except RunStateError as e:
        print(str(e), file=sys.stderr)
        return e.exit_code


if __name__ == "__main__":
    sys.exit(main())
