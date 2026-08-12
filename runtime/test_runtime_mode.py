import json

import pytest

import runtime_mode as mode


def fingerprint(**overrides):
    value = {
        "install_hash": "i" * 64,
        "config_hash": "c" * 64,
        "cli_version": "0.147.0",
        "trust_hash": "t" * 64,
    }
    value.update(overrides)
    return value


def record(**overrides):
    values = {
        "mode": "enforced",
        "reason_codes": [],
        "fingerprint": fingerprint(),
        "observed_at": "2026-08-11",
        "evidence_expires_at": "2026-11-08",
        "diagnostic_summary": {"platform": "macos-arm64"},
    }
    values.update(overrides)
    return mode.make_record(**values)


def test_record_is_deterministic_sanitized_and_strict():
    first = record()
    second = record()
    assert first == second
    assert mode.EVIDENCE_ID_RE.fullmatch(first["evidence_id"])
    assert "/Users/" not in json.dumps(first)
    with pytest.raises(mode.RuntimeModeError):
        mode.make_record(
            mode="peer",
            reason_codes=[],
            fingerprint=fingerprint(),
            observed_at="2026-08-11",
            evidence_expires_at=None,
            diagnostic_summary={},
        )


def test_persist_load_and_malformed_legacy_state_fail_closed(tmp_path):
    expected = record(mode="advisory", reason_codes=["TRUST_UNKNOWN"])
    path = mode.persist_record(tmp_path, expected)
    assert path == tmp_path / mode.STATE_RELATIVE
    assert mode.load_record(tmp_path) == expected
    path.write_text("not json")
    assert mode.load_record(tmp_path) is None
    path.write_text(json.dumps({"schema_version": 0}))
    assert mode.load_record(tmp_path) is None


@pytest.mark.parametrize("key", mode.FINGERPRINT_KEYS)
def test_install_config_cli_and_trust_changes_invalidate_enforcement(key):
    original = record()
    current = fingerprint(**{key: "changed"})
    invalidated = mode.invalidate_if_changed(original, current)
    assert invalidated["mode"] == "advisory"
    assert invalidated["valid"] is False
    assert invalidated["invalidated_by"] == [key]
    assert "STATE_INVALIDATED" in invalidated["reason_codes"]


def test_expired_evidence_cannot_keep_advertising_enforced(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))
    stale = record(
        evidence_expires_at="2026-01-01",
        fingerprint=mode.make_fingerprint(
            tmp_path, cli_version="0.147.0", trust={"hooks": "trusted"}
        ),
    )
    mode.persist_record(tmp_path, stale)
    line = mode.context_line(tmp_path)
    assert "mode=advisory" in line
    assert "EVIDENCE_STALE" in line


def test_user_level_config_change_invalidates_cached_diagnosis(tmp_path, monkeypatch):
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "config.toml").write_text("[features]\nhooks = true\n")
    monkeypatch.setenv("CODEX_HOME", str(home))
    current = record(
        fingerprint=mode.make_fingerprint(
            tmp_path, cli_version="0.147.0", trust={"hooks": "trusted"}
        ),
        evidence_expires_at="2099-01-01",
    )
    mode.persist_record(tmp_path, current)
    assert "mode=enforced" in mode.context_line(tmp_path)
    (home / "config.toml").write_text("[features]\nhooks = false\n")
    line = mode.context_line(tmp_path)
    assert "mode=advisory" in line
    assert "STATE_INVALIDATED" in line


def test_unchanged_fingerprint_preserves_record_identity():
    original = record()
    assert mode.invalidate_if_changed(original, fingerprint()) is original


def test_context_is_bounded_and_rejects_locally_stale_file_hashes(tmp_path):
    root = tmp_path
    (root / ".codex/.agent-harness").mkdir(parents=True)
    expected = record(
        mode="advisory",
        reason_codes=["TRUST_UNKNOWN"],
        fingerprint=mode.make_fingerprint(
            root, cli_version="0.147.0", trust={"hooks": "unknown"}
        ),
    )
    mode.persist_record(root, expected)
    line = mode.context_line(root, limit=220)
    assert "mode=advisory" in line
    assert len(line) <= 220
    (root / ".codex/config.toml").parent.mkdir(exist_ok=True)
    (root / ".codex/config.toml").write_text("changed = true\n")
    assert "STATE_INVALIDATED" in mode.context_line(root)


def test_summary_metadata_is_optional_and_update_preserves_body(tmp_path):
    summary = tmp_path / "SUMMARY.md"
    summary.write_text(
        "# Demo\n\nInput-type: maintenance\n\n## What changed\n\nBody.\n"
    )
    expected = record(mode="advisory", reason_codes=["TRUST_UNKNOWN"])
    mode.update_summary_metadata(summary, expected["mode"], expected["evidence_id"])
    text = summary.read_text()
    assert "Runtime-mode: advisory" in text
    assert f"Runtime-evidence-id: {expected['evidence_id']}" in text
    assert "Body." in text
    mode.update_summary_metadata(summary, "unsupported", expected["evidence_id"])
    assert summary.read_text().count("Runtime-mode:") == 1
