"""Mutation gate for runtime/run_state.py::validate_chain (GitHub issue #174/#177
follow-up, wave 4). Green tests are not evidence a guard does work — a fixture can
raise identically whether the guard is present or removed (see
docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md, and this
repo's own round-1 review, which found three such vacuous fixtures in
runtime/test_run_state.py). This file automates the check instead of asserting it in
prose: for each of the 15 mutations below, it copies run_state.py + test_run_state.py
into a fresh temp dir, applies exactly one targeted mutation to the copy, runs the
copied suite as a subprocess, and asserts the named victim test failed. It never
mutates the real runtime/run_state.py.

The copy mechanism is load-bearing: runtime/test_run_state.py does
`sys.path.insert(0, os.path.dirname(__file__))` before `import run_state as rs`, so
it always imports the module sitting NEXT TO ITSELF. Copying only run_state.py and
running the real test_run_state.py against it would import the real module and every
mutation would report SURVIVED regardless of what was mutated — both files must be
copied together.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RUN_STATE_SRC = REPO_ROOT / "runtime" / "run_state.py"
TEST_RUN_STATE_SRC = REPO_ROOT / "runtime" / "test_run_state.py"

# (id, old, new, expected_failing_test) — one targeted string mutation per entry,
# applied to a temp copy of run_state.py. `old` must match runtime/run_state.py
# verbatim, including its exact line wrapping; if it doesn't, the mutation is a
# no-op and must fail distinctly from a killed/survived mutation (see
# _apply_mutation below).
MUTATIONS = [
    (
        "drop-to_state-type-guard",
        'if type(ev.get("to_state")) is not str:',
        'if False and type(ev.get("to_state")) is not str:',
        "test_chain_unhashable_to_state_raises_storage_error_not_typeerror",
    ),
    (
        "drop-event_id-type-guard",
        'if type(ev.get("event_id")) is not str:',
        'if False and type(ev.get("event_id")) is not str:',
        "test_chain_unhashable_event_id_raises_storage_error_not_typeerror",
    ),
    (
        "drop-seq-type-guard",
        'if type(ev.get("seq")) is not int:',
        'if False and type(ev.get("seq")) is not int:',
        "test_chain_seq_must_be_int_not_bool",
    ),
    (
        "invariant5-bare-raise-instead-of-wrap",
        "            except InvalidTransitionError as e:\n"
        '                raise StorageError(f"invalid event chain {path}:{n}: {e}")',
        "            except InvalidTransitionError as e:\n                raise",
        "test_chain_legality_wraps_as_storage_error",
    ),
    (
        "neuter-genesis-carve-out-entirely",
        "if n == 1 and (",
        "if False and n == 1 and (",
        "test_chain_genesis_accepted_and_each_bad_variant_rejected",
    ),
    (
        "skip-event_id-uniqueness-check",
        'if ev["event_id"] in seen_event_ids:',
        'if False and ev["event_id"] in seen_event_ids:',
        "test_chain_event_id_unique",
    ),
    (
        "neuter-invariant2-from_state-chaining",
        'if prev is not None and ev.get("from_state") != prev["to_state"]:',
        'if False and prev is not None and ev.get("from_state") != prev["to_state"]:',
        "test_chain_from_state_must_chain_to_previous_to_state",
    ),
    (
        "genesis-disjunction-drop-from_state-clause",
        'ev.get("from_state") is not None or ev.get("to_state") != "queued"',
        'False or ev.get("to_state") != "queued"',
        "test_chain_genesis_accepted_and_each_bad_variant_rejected",
    ),
    (
        "genesis-disjunction-drop-to_state-clause",
        'ev.get("from_state") is not None or ev.get("to_state") != "queued"',
        'ev.get("from_state") is not None or False',
        "test_chain_genesis_accepted_and_each_bad_variant_rejected",
    ),
    (
        "skip-slug-constancy",
        'if ev.get("slug") != first.get("slug"):',
        'if False and ev.get("slug") != first.get("slug"):',
        "test_chain_slug_and_run_id_constant",
    ),
    (
        "skip-seq-contiguity",
        'if ev["seq"] != n:',
        'if False and ev["seq"] != n:',
        "test_chain_seq_must_be_contiguous_from_one",
    ),
    (
        "skip-run_id-constancy",
        'if ev.get("run_id") != first.get("run_id"):',
        'if False and ev.get("run_id") != first.get("run_id"):',
        "test_chain_slug_and_run_id_constant",
    ),
    (
        "skip-requested-slug-match",
        'if n == 1 and first.get("slug") != slug:',
        'if False and n == 1 and first.get("slug") != slug:',
        "test_chain_slug_and_run_id_constant",
    ),
    (
        "drop-event-type-guard",
        'if type(ev.get("event")) is not str:',
        'if False and type(ev.get("event")) is not str:',
        "test_chain_event_field_must_be_a_string",
    ),
    (
        "drop-shipped-requires-sha",
        'if ev["to_state"] == "shipped":',
        'if False and ev["to_state"] == "shipped":',
        "test_chain_shipped_requires_sha",
    ),
]


SANDBOX_TIMEOUT = 120


def _fresh_sandbox():
    """Copy BOTH run_state.py and test_run_state.py into a fresh temp dir. Never
    touches the real files."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="chain-mutation-"))
    shutil.copy2(RUN_STATE_SRC, tmp / "run_state.py")
    shutil.copy2(TEST_RUN_STATE_SRC, tmp / "test_run_state.py")
    return tmp


def _run_sandbox_suite(tmp):
    """Runs `pytest -k chain -q` against the sandbox copy as a subprocess. Bounded by
    SANDBOX_TIMEOUT: a mutation can make the copy hang rather than fail - concretely,
    test_transition_on_invalid_chain_* and test_allow_invalid_chain_* both match `-k
    chain` and go through locked_run -> fcntl.flock(..., LOCK_EX), which blocks
    unboundedly by design - and an unbounded subprocess.run would hang CI on both
    matrix legs with no diagnostic."""
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(tmp / "test_run_state.py"),
            "-k",
            "chain",
            "-q",
        ],
        capture_output=True,
        text=True,
        timeout=SANDBOX_TIMEOUT,
    )


@pytest.fixture(scope="module", autouse=True)
def sandbox_baseline():
    """Runs the sandbox suite once, UNMUTATED, and asserts it passes cleanly, before
    any mutation test runs. Without this, test_mutation_is_killed only ever proves a
    `FAILED ...::<victim>` line appears somewhere in the mutated run's output - it
    never establishes the counterfactual that the victim test PASSES without the
    mutation. That gap is not hypothetical: test_run_state.py already contains tests
    that are green in-repo but red in a temp-dir sandbox because they resolve paths
    from __file__; only the `-k chain` name filter keeps them out of this file's
    parametrization, a naming coincidence rather than a mechanism. If the sandbox
    baseline itself is not green, no "killed" verdict in this file is trustworthy -
    that must fail loudly and distinctly from a per-mutation result."""
    tmp = _fresh_sandbox()
    try:
        try:
            result = _run_sandbox_suite(tmp)
        except subprocess.TimeoutExpired as e:
            pytest.fail(
                f"sandbox baseline: the unmutated suite timed out after "
                f"{SANDBOX_TIMEOUT}s - the sandbox hung rather than ran.\n"
                f"--- stdout so far ---\n{e.stdout}\n--- stderr so far ---\n{e.stderr}"
            )

        if "passed" not in result.stdout and "failed" not in result.stdout:
            pytest.fail(
                "sandbox baseline: the unmutated suite did not run tests at all "
                "(missing pytest, a collection error, or '-k' matched nothing) - "
                "this is not a green baseline.\n"
                f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
            )
        if result.returncode != 0 or "failed" in result.stdout:
            pytest.fail(
                "sandbox baseline is NOT GREEN: the unmutated suite already fails "
                "under `-k chain` in a temp-dir sandbox. No mutation result in this "
                "file is trustworthy until this is fixed.\n"
                f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _apply_mutation(tmp, mutation_id, old, new):
    """Apply one targeted string mutation to the temp copy of run_state.py. A
    missing pattern is a distinct failure from a survived mutation — it means this
    gate has drifted from the real source, not that the guard is untested."""
    run_state_copy = tmp / "run_state.py"
    src = run_state_copy.read_text()
    if old not in src:
        pytest.fail(f"mutation {mutation_id}: pattern not found")
    run_state_copy.write_text(src.replace(old, new, 1))


@pytest.mark.parametrize(
    "mutation_id,old,new,expected_failing_test",
    MUTATIONS,
    ids=[m[0] for m in MUTATIONS],
)
def test_mutation_is_killed(mutation_id, old, new, expected_failing_test):
    tmp = _fresh_sandbox()
    try:
        _apply_mutation(tmp, mutation_id, old, new)

        try:
            result = _run_sandbox_suite(tmp)
        except subprocess.TimeoutExpired as e:
            # Distinct from both SURVIVED (the suite ran and passed anyway) and "did
            # not run tests at all" below (the suite never started) — this is the
            # third outcome: the suite started and hung. A mutated `if False and ...`
            # guard can make locked_run's fcntl.flock(..., LOCK_EX) block unboundedly
            # instead of raising, and an unbounded subprocess.run would hang CI on
            # both matrix legs with no diagnostic.
            pytest.fail(
                f"mutation {mutation_id!r}: the mutation subprocess timed out after "
                f"{SANDBOX_TIMEOUT}s — this is not SURVIVED, the sandbox hung.\n"
                f"--- stdout so far ---\n{e.stdout}\n--- stderr so far ---\n{e.stderr}"
            )

        # Sanity check BEFORE the kill check: missing pytest, an unparseable
        # mutated source (collection error), and "-k" matching nothing all fail
        # loudly, but headlining them as "SURVIVED" misattributes the cause — the
        # mutation subprocess never ran the test suite at all. A real pytest -q
        # summary line always contains "passed" or "failed"; if neither appears,
        # this is environmental breakage, not a survived mutation.
        if "passed" not in result.stdout and "failed" not in result.stdout:
            pytest.fail(
                f"mutation {mutation_id!r}: the mutation subprocess did not run "
                f"tests at all (missing pytest, a collection error, or '-k' "
                f"matched nothing) — this is not a SURVIVED mutation.\n"
                f"--- stdout ---\n{result.stdout}\n"
                f"--- stderr ---\n{result.stderr}"
            )

        # Assert the NAMED victim FAILED — not merely rc != 0. A non-zero rc alone
        # is ambiguous (see the sanity check above); the named FAILED line is not.
        needle = f"::{expected_failing_test}"
        killed = any(
            line.startswith("FAILED") and needle in line
            for line in result.stdout.splitlines()
        )
        assert killed, (
            f"mutation {mutation_id!r} SURVIVED: expected a "
            f"'FAILED ...{needle}' line in pytest output.\n"
            f"--- stdout ---\n{result.stdout}\n"
            f"--- stderr ---\n{result.stderr}"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
