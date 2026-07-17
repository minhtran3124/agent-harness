"""Unit tests for the intake-classifier scorer (deterministic comparison logic)."""

import score_intake_eval as s


# ── parse_classification ────────────────────────────────────────────────────
def test_parse_classification_basic():
    text = "Lane: high-risk\nConfidence: high\nFlags: auth, data-model\nEscalate: yes (auth gate)\n"
    p = s.parse_classification(text)
    assert p["lane"] == "high-risk"
    assert p["confidence"] == "high"
    assert p["flags"] == {"auth", "data-model"}
    assert p["escalate"] == "yes"  # 'yes (reason)' normalizes to 'yes'


def test_parse_classification_none_flags_and_no_escalate():
    p = s.parse_classification(
        "Lane: tiny\nConfidence: high\nFlags: none\nEscalate: no\n"
    )
    assert p["flags"] == set()
    assert p["escalate"] == "no"


# ── parse_kv_header ─────────────────────────────────────────────────────────
def test_parse_kv_header_stops_at_separator():
    text = "expected_lane: high-risk\nexpected_hard_gate: auth\n---\nprose: ignored\n"
    h = s.parse_kv_header(text)
    assert h == {"expected_lane": "high-risk", "expected_hard_gate": "auth"}


def test_parse_kv_header_stops_at_heading():
    h = s.parse_kv_header("expected_lane: tiny\n\n## Rationale\nexpected_lane: nope\n")
    assert h["expected_lane"] == "tiny"


# ── score_one ───────────────────────────────────────────────────────────────
def test_lane_match_all_correct():
    truth = {
        "expected_lane": "normal",
        "expected_confidence": "high",
        "expected_escalate": "no",
    }
    produced = {
        "lane": "normal",
        "confidence": "high",
        "flags": set(),
        "escalate": "no",
    }
    r = s.score_one(truth, produced)
    assert r["lane_match"] is True
    assert r["overall"] is True
    assert r["reasons"] == []


def test_lane_mismatch_is_incorrect():
    truth = {"expected_lane": "high-risk"}
    r = s.score_one(
        truth,
        {"lane": "normal", "confidence": "high", "flags": set(), "escalate": "no"},
    )
    assert r["lane_match"] is False
    assert r["overall"] is False


def test_hard_gate_downgrade_is_caught():
    # an auth hard-gate fixture that intake wrongly classified as normal
    truth = {
        "expected_lane": "high-risk",
        "expected_hard_gate": "auth",
        "must_not_downgrade": "true",
    }
    r = s.score_one(
        truth,
        {"lane": "normal", "confidence": "high", "flags": {"auth"}, "escalate": "yes"},
    )
    assert r["is_gate"] is True
    assert r["gate_ok"] is False
    assert r["overall"] is False
    assert any("HARD-GATE" in x for x in r["reasons"])


def test_hard_gate_respected():
    truth = {"expected_lane": "high-risk", "expected_hard_gate": "auth"}
    r = s.score_one(
        truth,
        {
            "lane": "high-risk",
            "confidence": "high",
            "flags": {"auth"},
            "escalate": "yes",
        },
    )
    assert r["gate_ok"] is True
    assert r["overall"] is True


def test_lane_any_is_not_scored():
    # ambiguous fixture: lane unasserted, only confidence/escalate matter
    truth = {
        "expected_lane": "any",
        "expected_confidence": "low",
        "expected_escalate": "yes",
    }
    r = s.score_one(
        truth,
        {"lane": "normal", "confidence": "low", "flags": set(), "escalate": "yes"},
    )
    assert r["lane_match"] is None
    assert r["overall"] is True


def test_confidence_mismatch_fails():
    truth = {
        "expected_lane": "any",
        "expected_confidence": "low",
        "expected_escalate": "yes",
    }
    r = s.score_one(
        truth,
        {"lane": "normal", "confidence": "high", "flags": set(), "escalate": "no"},
    )
    assert r["conf_match"] is False
    assert r["esc_match"] is False
    assert r["overall"] is False


def test_flags_subset_missing_fails():
    truth = {"expected_lane": "high-risk", "expected_flags_include": "auth, data-model"}
    r = s.score_one(
        truth,
        {
            "lane": "high-risk",
            "confidence": "high",
            "flags": {"auth"},
            "escalate": "yes",
        },
    )
    assert r["flags_ok"] is False
    assert any("flags missing" in x for x in r["reasons"])


def test_flags_subset_present_ok():
    truth = {"expected_lane": "high-risk", "expected_flags_include": "auth"}
    r = s.score_one(
        truth,
        {
            "lane": "high-risk",
            "confidence": "high",
            "flags": {"auth", "data-model"},
            "escalate": "yes",
        },
    )
    assert r["flags_ok"] is True


def test_flags_match_is_substring_tolerant():
    # the skill emits flags with parenthetical numbers: 'Auth (1)', 'data-model (#3)'
    truth = {"expected_lane": "high-risk", "expected_flags_include": "auth"}
    produced = s.parse_classification(
        "Lane: high-risk\nFlags: Auth (1), Existing behavior (8)\n"
    )
    r = s.score_one(truth, produced)
    assert r["flags_ok"] is True  # 'auth' is a substring of 'auth (1)'


def test_flags_match_normalizes_separators():
    # skill emits the flag-table spelling 'Data model' (space); truth uses 'data-model' (hyphen)
    truth = {"expected_lane": "high-risk", "expected_flags_include": "data-model"}
    produced = s.parse_classification(
        "Lane: high-risk\nFlags: Data model (3), Weak proof (9)\n"
    )
    r = s.score_one(truth, produced)
    assert r["flags_ok"] is True  # 'data-model' == 'data model' after normalization
