import json
import shutil
from datetime import date
from pathlib import Path

import codex_harness_doctor as doctor


ROOT = Path(__file__).resolve().parents[1]


def installed_project(tmp_path: Path) -> Path:
    target = tmp_path / "project"
    plugin = target / ".codex/.agent-harness/marketplace/plugins/agent-harness"
    shutil.copytree(ROOT / "adapters/codex/plugin", plugin)
    inventory = json.loads((ROOT / "harness-manifest.json").read_text())
    for skill in inventory["skills"]:
        shutil.copytree(ROOT / "skills" / skill, plugin / "skills" / skill)
    shutil.copytree(ROOT / "hooks", plugin / "hooks", dirs_exist_ok=True)
    shutil.copy2(
        ROOT / "adapters/codex/plugin/hooks/hooks.json", plugin / "hooks/hooks.json"
    )
    agents = target / ".codex/agents"
    agents.mkdir(parents=True)
    for agent in inventory["agents"]:
        (agents / f"{agent}.toml").write_text(f'name = "{agent}"\n')
    state = target / ".codex/.agent-harness"
    (state / "deployment-manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project_files": {},
                "sidecars": {},
                "agents_block_hash": None,
                "plugin": {
                    "marketplace": "agent-harness-local",
                    "reference": "agent-harness@agent-harness-local",
                },
            }
        )
    )
    return target


def good_report(**overrides):
    value = {
        "schemaVersion": 1,
        "cli_version": "0.147.0",
        "platform": "macos-arm64",
        "overallStatus": "ok",
        "checks": {"installation": {"status": "ok"}},
        "features": {
            name: {"enabled": True, "maturity": "stable"}
            for name in doctor.REQUIRED_FEATURES
        },
        "effective_trust": {"hooks": "trusted"},
    }
    value.update(overrides)
    return value


def diagnose(tmp_path, report=None, **kwargs):
    target = installed_project(tmp_path)
    result = doctor.diagnose(
        root=target,
        repo_root=ROOT,
        doctor_value=good_report() if report is None else report,
        platform_override=kwargs.pop("platform_override", "macos-arm64"),
        dependencies=kwargs.pop(
            "dependencies", {name: True for name in doctor.REQUIRED_DEPENDENCIES}
        ),
        today=kwargs.pop("today", date(2026, 8, 11)),
        **kwargs,
    )
    return target, result


def test_enforced_requires_complete_current_trusted_observation(tmp_path):
    _, result = diagnose(tmp_path)
    assert result["mode"] == "enforced"
    assert result["reason_codes"] == []
    assert result["evidence_expires_at"] == "2026-11-08"


def test_unknown_stale_version_and_unverified_platform_never_enforce(tmp_path):
    report = good_report(cli_version="0.999.0", effective_trust={"hooks": "unknown"})
    _, result = diagnose(
        tmp_path,
        report,
        platform_override="linux-x86_64",
        today=date(2026, 12, 1),
    )
    assert result["mode"] == "advisory"
    assert {
        "CLI_VERSION_MISMATCH",
        "TRUST_UNKNOWN",
        "PLATFORM_UNVERIFIED",
        "EVIDENCE_STALE",
        "EVIDENCE_UNKNOWN",
    } <= set(result["reason_codes"])


def live_report():
    return {
        "schemaVersion": 1,
        "codexVersion": "0.147.0",
        "generatedAt": "2026-08-12T00:00:00Z",
        "overallStatus": "ok",
        "checks": {
            "installation": {"id": "installation", "status": "ok"},
            "config.load": {
                "id": "config.load",
                "status": "ok",
                "details": {
                    "enabled feature flags": (
                        "shell_tool, unified_exec, hooks, multi_agent, plugins"
                    )
                },
            },
        },
    }


def test_config_trust_narrows_the_reason_but_never_unlocks_enforced(
    tmp_path, monkeypatch
):
    """Codex trust_level is project approval, which the capability matrix records
    as necessary but not sufficient for hook execution. It may replace the blunt
    TRUST_UNKNOWN, and it must not produce `enforced`."""
    home = tmp_path / "codex-home"
    home.mkdir()
    monkeypatch.setenv("CODEX_HOME", str(home))
    target = installed_project(tmp_path)
    (home / "config.toml").write_text(
        f'[projects."{target.resolve()}"]\ntrust_level = "trusted"\n'
    )
    result = doctor.diagnose(
        root=target,
        repo_root=ROOT,
        doctor_value=live_report(),
        platform_override="macos-arm64",
        dependencies={name: True for name in doctor.REQUIRED_DEPENDENCIES},
        today=date(2026, 8, 11),
    )
    assert "TRUST_UNKNOWN" not in result["reason_codes"]
    assert "TRUST_CONFIG_ONLY" in result["reason_codes"]
    assert result["mode"] == "advisory"


def test_config_trust_reader_refuses_scope_leaks(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    root = tmp_path / "proj"
    config = home / "config.toml"
    # A commented-out header must not lend its scope to the lines beneath it,
    # and a multi-line string could hide a header this reader cannot lex.
    for text in (
        f'[projects."{root}"]\nx = 1\n#[projects."/unrelated"]\ntrust_level = "trusted"\n',
        f'[projects."/unrelated"]\nnote = """\n[projects."{root}"]\n"""\n'
        'trust_level = "trusted"\n',
        "[projects.'/unrelated']\nnote = '''\nx\n'''\ntrust_level = \"trusted\"\n",
        # A multi-line array can carry a line that looks exactly like a header.
        f'matrix = [\n[projects."{root}"]\n]\ntrust_level = "trusted"\n',
    ):
        config.write_text(text)
        assert doctor._config_trust(root, home) is None
    # A single-line array elsewhere must not disable the reader.
    config.write_text(f'[projects."{root}"]\ntags = ["a"]\ntrust_level = "trusted"\n')
    assert doctor._config_trust(root, home) == "trusted"


def test_persisted_record_is_stable_under_an_explicit_codex_home(tmp_path, monkeypatch):
    """The writer must hash the same home the reader will resolve, or every
    record is STATE_INVALIDATED on its first read."""
    home = tmp_path / "explicit-home"
    home.mkdir()
    (home / "config.toml").write_text("[features]\nhooks = true\n")
    monkeypatch.setenv("CODEX_HOME", str(home))
    target = installed_project(tmp_path)
    result = doctor.diagnose(
        root=target,
        repo_root=ROOT,
        doctor_value=live_report(),
        platform_override="macos-arm64",
        dependencies={name: True for name in doctor.REQUIRED_DEPENDENCIES},
        today=date(2026, 8, 11),
        codex_home=home,
    )
    doctor.runtime_mode.persist_record(target, result)
    assert "STATE_INVALIDATED" not in doctor.runtime_mode.context_line(target)


def test_config_trust_reader_never_yields_a_permissive_false_positive(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    root = tmp_path / "proj"
    config = home / "config.toml"

    trusted_forms = (
        f'[projects."{root}"]\ntrust_level = "trusted"\n',
        f"[projects.\"{root}\"]\ntrust_level = 'trusted'\n",
        f"[projects.'{root}']\ntrust_level = \"trusted\"\n",
        f'[projects."{root}"]\ntrust_level = "trusted"  # note\n',
    )
    for text in trusted_forms:
        config.write_text(text)
        assert doctor._config_trust(root, home) == "trusted"

    # Every ambiguous or non-matching shape must stay unknown, never trusted.
    for text in (
        '[projects."/somewhere/else"]\ntrust_level = "trusted"\n',
        f'[projects."{root}"]\n# trust_level = "trusted"\n',
        f'[projects."{root}"]\n[projects."{root}".sub]\ntrust_level = "trusted"\n',
        "not toml at all\n",
    ):
        config.write_text(text)
        assert doctor._config_trust(root, home) is None
    config.write_text(
        f'[projects."{root}"]\ntrust_level = "untrusted"\n'
        '[projects."/other"]\ntrust_level = "trusted"\n'
    )
    assert doctor._config_trust(root, home) == "untrusted"


def test_live_cli_doctor_shape_is_parsed_without_false_mismatches(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "empty-codex-home"))
    _, result = diagnose(tmp_path, live_report())
    assert "CLI_VERSION_MISMATCH" not in result["reason_codes"]
    assert "FEATURE_DISABLED" not in result["reason_codes"]
    # The live shape carries no trust key, so trust stays honestly unknown.
    assert "TRUST_UNKNOWN" in result["reason_codes"]


def test_zero_matched_load_bearing_rows_cannot_support_enforced():
    reasons, earliest = doctor._evidence_reasons(
        {"capabilities": []}, "macos-arm64", {"hooks": "trusted"}, date(2026, 8, 12)
    )
    assert "EVIDENCE_UNKNOWN" in reasons
    assert earliest is None
    relabelled = json.loads(
        (ROOT / "specs/codex-support/capability-matrix.json").read_text()
    )
    relabelled["capabilities"] = [
        {**row, "platforms": ["macos-14-arm64"]}
        for row in relabelled["capabilities"]
        if row.get("id") != "config.project_trust"
    ]
    reasons, _ = doctor._evidence_reasons(
        relabelled, "macos-arm64", {"hooks": "trusted"}, date(2026, 8, 12)
    )
    assert "EVIDENCE_UNKNOWN" in reasons


def test_documented_only_load_bearing_evidence_cannot_support_enforced():
    matrix = json.loads(
        (ROOT / "specs/codex-support/capability-matrix.json").read_text()
    )
    for row in matrix["capabilities"]:
        if row["id"] == "tools.unified_exec":
            row["evidence_level"] = "documented"
    reasons, _ = doctor._evidence_reasons(
        matrix, "macos-arm64", {"hooks": "trusted"}, date(2026, 8, 11)
    )
    assert "EVIDENCE_DOCUMENTED_ONLY" in reasons


def test_native_windows_or_missing_dependency_is_unsupported(tmp_path):
    _, result = diagnose(tmp_path, platform_override="windows-x86_64")
    assert result["mode"] == "unsupported"
    assert "NATIVE_WINDOWS_UNSUPPORTED" in result["reason_codes"]
    _, result = diagnose(
        tmp_path / "other",
        dependencies={name: name != "jq" for name in doctor.REQUIRED_DEPENDENCIES},
    )
    assert result["mode"] == "unsupported"
    assert result["reason_codes"] == ["DEPENDENCY_MISSING"]


def test_missing_install_is_unsupported_and_hash_drift_is_advisory(tmp_path):
    missing = tmp_path / "missing"
    missing.mkdir()
    result = doctor.diagnose(
        root=missing,
        repo_root=ROOT,
        doctor_value=good_report(),
        platform_override="macos-arm64",
        dependencies={name: True for name in doctor.REQUIRED_DEPENDENCIES},
        today=date(2026, 8, 11),
    )
    assert result["mode"] == "unsupported"
    assert result["reason_codes"] == ["INSTALL_MISSING"]

    target = installed_project(tmp_path / "drift")
    owned = target / ".codex/harness-instructions.md"
    owned.parent.mkdir(parents=True, exist_ok=True)
    owned.write_text("original\n")
    manifest_path = target / ".codex/.agent-harness/deployment-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["project_files"] = {".codex/harness-instructions.md": "0" * 64}
    manifest_path.write_text(json.dumps(manifest))
    result = doctor.diagnose(
        root=target,
        repo_root=ROOT,
        doctor_value=good_report(),
        platform_override="macos-arm64",
        dependencies={name: True for name in doctor.REQUIRED_DEPENDENCIES},
        today=date(2026, 8, 11),
    )
    assert result["mode"] == "advisory"
    assert "INSTALL_HASH_MISMATCH" in result["reason_codes"]


def test_discovery_matcher_and_doctor_failures_are_advisory(tmp_path):
    target = installed_project(tmp_path)
    (target / ".codex/agents/coding.toml").unlink()
    hooks = (
        target
        / ".codex/.agent-harness/marketplace/plugins/agent-harness/hooks/hooks.json"
    )
    hooks.write_text("{}\n")
    result = doctor.diagnose(
        root=target,
        repo_root=ROOT,
        doctor_value=None,
        platform_override="macos-arm64",
        dependencies={name: True for name in doctor.REQUIRED_DEPENDENCIES},
        today=date(2026, 8, 11),
    )
    assert result["mode"] == "advisory"
    assert {
        "AGENT_DISCOVERY_MISMATCH",
        "HOOK_COVERAGE_MISMATCH",
        "DOCTOR_UNAVAILABLE",
    } <= set(result["reason_codes"])


def test_output_record_is_sanitized_persisted_and_can_update_summary(tmp_path, capsys):
    target = installed_project(tmp_path)
    report_path = tmp_path / "doctor.json"
    report = good_report()
    report["private_debug"] = "/Users/private/token-secret"
    report_path.write_text(json.dumps(report))
    summary = tmp_path / "SUMMARY.md"
    summary.write_text("# Demo\n\nInput-type: maintenance\n\nBody\n")
    rc = doctor.main(
        [
            "--root",
            str(target),
            "--repo-root",
            str(ROOT),
            "--doctor-report",
            str(report_path),
            "--platform",
            "macos-arm64",
            "--dependencies-json",
            str(_dependency_fixture(tmp_path)),
            "--now",
            "2026-08-11",
            "--summary",
            str(summary),
        ]
    )
    output = capsys.readouterr().out
    assert rc == 0
    assert "/Users/private" not in output
    persisted = json.loads((target / doctor.runtime_mode.STATE_RELATIVE).read_text())
    assert persisted["mode"] == "enforced"
    assert persisted["evidence_id"] in summary.read_text()


def test_malformed_supplied_doctor_report_fails_closed_to_advisory(tmp_path, capsys):
    target = installed_project(tmp_path)
    report_path = tmp_path / "doctor.json"
    report_path.write_text("not json")
    rc = doctor.main(
        [
            "--root",
            str(target),
            "--repo-root",
            str(ROOT),
            "--doctor-report",
            str(report_path),
            "--platform",
            "macos-arm64",
            "--dependencies-json",
            str(_dependency_fixture(tmp_path)),
            "--now",
            "2026-08-11",
        ]
    )
    assert rc == 0
    result = json.loads(capsys.readouterr().out)
    assert result["mode"] == "advisory"
    assert "DOCTOR_UNAVAILABLE" in result["reason_codes"]


def _dependency_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "dependencies.json"
    path.write_text(json.dumps({name: True for name in doctor.REQUIRED_DEPENDENCIES}))
    return path
