"""Tests for scripts/check_verify_rows.py — the Verify-row pipe/timeout lint."""

import check_verify_rows as c

_HEADER = (
    "### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n"
)


def _summary(*rows: str) -> str:
    return _HEADER + "".join(r + "\n" for r in rows)


def test_clean_rows_pass():
    text = _summary(
        "| lint | `bash scripts/lint-doc-truth.sh` | 0 | clean |",
        "| grep guard | `grep -e a -e b file` | 1 | pipe-free alternation |",
        '| combined | `X; a=$?; Y; b=$?; test "$a" = 0 -a "$b" = 0` | 0 | captured $? |',
    )
    assert c.check_summary_text(text) == []


def test_unescaped_pipe_splits_the_row():
    # a real pipe in the command splits the cell → wrong column count
    text = _summary('| bad | `grep -E "a|b" file` | 0 | pipe in regex |')
    v = c.check_summary_text(text)
    assert len(v) == 1 and "unescaped" in v[0]


def test_escaped_pipe_still_flagged():
    text = _summary("| piped | `ls \\| wc -l` | 0 | escaped pipe survives |")
    v = c.check_summary_text(text)
    assert len(v) == 1 and "pipe" in v[0].lower()


def test_full_suite_row_flagged():
    text = _summary("| full suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN |")
    v = c.check_summary_text(text)
    assert len(v) == 1 and "full suite" in v[0].lower()


def test_make_test_flagged():
    text = _summary("| build | `make test` | 0 | |")
    assert c.check_summary_text(text) != []


def test_grep_argument_run_tests_is_not_flagged():
    # command greps FOR the string run-tests.sh — it does not RUN it
    text = _summary(
        "| unwired | `grep -q check_plan_format harness-manifest.json scripts/run-tests.sh` | 1 | grep target |"
    )
    assert c.check_summary_text(text) == []


def test_executed_run_tests_variants_flagged():
    for cmd in (
        "bash scripts/run-tests.sh",
        "sh run-tests.sh",
        "./scripts/run-tests.sh",
    ):
        text = _summary(f"| suite | `{cmd}` | 0 | |")
        assert c.check_summary_text(text) != [], cmd


def test_no_verify_section_is_clean():
    assert c.check_summary_text("# Summary\n\n## What changed\n\nx\n") == []


def test_placeholder_command_ignored():
    # a not-yet-filled row shouldn't trip the lint on content it doesn't have
    text = _summary("| <check> | `<command>` | 0 | placeholder |")
    assert c.check_summary_text(text) == []


# --- check_plan_text: SC-table Check-cell lint ---------------------------------

_SC_HEADER = (
    "## 3. Success Criteria\n\n"
    "| ID | Behavior (observable) | Check (re-runnable) | Expected |\n"
    "| --- | --- | --- | --- |\n"
)


def _plan(*rows: str) -> str:
    return _SC_HEADER + "".join(r + "\n" for r in rows)


def test_sc_table_pipe_rejected():
    # an unescaped pipe in the SC Check command splits the cell → flagged
    text = _plan('| SC-1 | greps two names | `grep -E "a|b" file` | exit 0 |')
    v = c.check_plan_text(text)
    assert len(v) == 1 and "SC-1" in v[0] and "pipe" in v[0].lower()


def test_sc_table_full_suite_rejected():
    text = _plan("| SC-2 | runs everything | `bash scripts/run-tests.sh` | exit 0 |")
    v = c.check_plan_text(text)
    assert len(v) == 1 and "SC-2" in v[0] and "full suite" in v[0].lower()


def test_sc_table_clean_passes():
    text = _plan(
        "| SC-1 | unit passes | `python3 -m pytest scripts/test_x.py -q` | exit 0 |",
        "| SC-2 | grep guard | `grep -e a -e b file` | exit 1 |",
    )
    assert c.check_plan_text(text) == []


def test_plan_without_sc_table_passes():
    # a plan with an ordinary table but no SC-<n> rows is untouched
    text = "# Plan\n\n| Step | Detail |\n| --- | --- |\n| 1 | do the thing |\n"
    assert c.check_plan_text(text) == []


def test_sc_table_in_fence_is_ignored():
    # a fenced illustration table must not trip the lint
    text = (
        "## Example\n\n```\n"
        "| ID | Behavior | Check | Expected |\n"
        "| --- | --- | --- | --- |\n"
        "| SC-1 | demo | `bash scripts/run-tests.sh` | exit 0 |\n"
        "```\n"
    )
    assert c.check_plan_text(text) == []
