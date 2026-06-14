"""Tests for the lane -> evidence validator.

Run:

    python -m pytest scripts/test_check_lane_evidence.py -q
"""

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_lane_evidence", Path(__file__).resolve().parent / "check_lane_evidence.py"
)
assert _SPEC and _SPEC.loader, "could not load check_lane_evidence.py"
cle = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cle)


def _summary(
    lane="tiny",
    confidence="high",
    reason="obvious one-file edit",
    verify=None,
    rollback=None,
):
    """Build a minimal SUMMARY.md body for a given lane."""
    parts = [
        "# demo — Summary",
        "",
        f"Lane: {lane}",
        f"Confidence: {confidence}",
        f"Reason: {reason}",
        "Flags: none",
        "",
        "## What changed",
        "Did the thing.",
    ]
    if verify is not None:
        parts += [
            "",
            "### Verify",
            "",
            "| Check | Command | Exit | Notes |",
            "| --- | --- | --- | --- |",
            verify,
        ]
    if rollback is not None:
        parts += ["", "### Rollback", "", rollback]
    return "\n".join(parts) + "\n"


REAL_VERIFY = "| unit | `pytest -q` | 0 | all pass |"
PLACEHOLDER_VERIFY = "| <unit / lint> | `<command>` | 0 | <excerpt> |"


# ── tiny ────────────────────────────────────────────────────────────────────
def test_tiny_header_only_passes():
    assert cle.check_summary(_summary(lane="tiny")) == []


def test_tiny_missing_confidence_fails():
    text = _summary(lane="tiny").replace("Confidence: high\n", "")
    errs = cle.check_summary(text)
    assert any("Confidence" in e for e in errs)


def test_placeholder_header_value_fails():
    text = _summary(lane="tiny", reason="<one sentence — why this lane>")
    errs = cle.check_summary(text)
    assert any("Reason" in e and "placeholder" in e for e in errs)


# ── normal ──────────────────────────────────────────────────────────────────
def test_normal_with_real_verify_passes():
    assert cle.check_summary(_summary(lane="normal", verify=REAL_VERIFY)) == []


def test_normal_missing_verify_fails():
    errs = cle.check_summary(_summary(lane="normal"))
    assert any("Verify" in e for e in errs)


def test_normal_placeholder_verify_fails():
    errs = cle.check_summary(_summary(lane="normal", verify=PLACEHOLDER_VERIFY))
    assert any("no real command row" in e for e in errs)


# ── high-risk ───────────────────────────────────────────────────────────────
def test_high_risk_full_passes():
    text = _summary(
        lane="high-risk", verify=REAL_VERIFY, rollback="- `alembic downgrade -1`"
    )
    assert cle.check_summary(text) == []


def test_high_risk_missing_rollback_fails():
    text = _summary(lane="high-risk", verify=REAL_VERIFY)
    errs = cle.check_summary(text)
    assert any("Rollback" in e for e in errs)


def test_high_risk_empty_rollback_fails():
    text = _summary(
        lane="high-risk", verify=REAL_VERIFY, rollback="<!-- only a comment -->"
    )
    errs = cle.check_summary(text)
    assert any("Rollback" in e and "empty" in e for e in errs)


# ── lane resolution ─────────────────────────────────────────────────────────
def test_unresolvable_lane_fails():
    text = _summary().replace("Lane: tiny", "Lane: maybe")
    errs = cle.check_summary(text)
    assert errs and "cannot resolve" in errs[0]


def test_lane_normalizes_from_decorated_value():
    # a Lane line with extra prose still resolves
    text = _summary(
        lane="high-risk (hard gate: hooks/*)",
        verify=REAL_VERIFY,
        rollback="- `git revert <sha>`",
    )
    assert cle.check_summary(text) == []


def test_bold_markdown_header_variant_resolves():
    # some older SUMMARYs bold the header: `**Lane:** normal`
    text = _summary(lane="normal", verify=REAL_VERIFY)
    text = (
        text.replace("Lane: normal", "**Lane:** normal")
        .replace("Confidence: high", "**Confidence:** high")
        .replace("Reason: ", "**Reason:** ")
    )
    assert cle.check_summary(text) == []


def test_reason_prose_with_piped_regex_is_not_placeholder():
    # real prose may contain a `|` inside backticks — not a template option list
    reason = "Risk raised because `(^|/)hooks/` matches the new test paths"
    assert cle.check_summary(_summary(lane="tiny", reason=reason)) == []
