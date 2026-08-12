#!/usr/bin/env python3
"""Diagnose an installed Codex harness without running inside a hook."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform as host_platform
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "runtime"))
import runtime_mode  # noqa: E402

REQUIRED_DEPENDENCIES = ("bash", "git", "jq", "python3")
REQUIRED_FEATURES = ("hooks", "multi_agent", "plugins", "unified_exec")
SUPPORTED_PLATFORMS = {"macos-arm64"}
EXPECTED_PLUGIN_REFERENCE = "agent-harness@agent-harness-local"


class DoctorInputError(ValueError):
    """Raised for an invalid deterministic input fixture."""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DoctorInputError(f"cannot read JSON input: {path.name}") from exc


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_inventory(root: Path) -> dict[str, str]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in root.rglob("*")
        if path.is_file()
        and not path.is_symlink()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
        and path.name != ".DS_Store"
    }


def _safe_relative(value: Any) -> str | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return value


def detect_platform() -> str:
    system = host_platform.system().lower()
    machine = host_platform.machine().lower()
    arch = "arm64" if machine in {"arm64", "aarch64"} else "x86_64"
    if system == "darwin":
        return f"macos-{arch}"
    if system == "linux":
        try:
            release = Path("/proc/sys/kernel/osrelease").read_text().lower()
        except OSError:
            release = ""
        return f"{'wsl' if 'microsoft' in release else 'linux'}-{arch}"
    if system == "windows":
        return f"windows-{arch}"
    return f"{system or 'unknown'}-{arch}"


def dependency_status() -> dict[str, bool]:
    return {name: shutil.which(name) is not None for name in REQUIRED_DEPENDENCIES}


def _front_matter(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return values
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip('"')
    return {}


def _live_features(report: dict[str, Any]) -> dict[str, Any] | None:
    """Derive a features map from the live `codex doctor --json` shape (0.147.0),
    where enabled flags live in checks['config.load'].details as one string."""
    checks = report.get("checks")
    if not isinstance(checks, dict):
        return None
    config_load = checks.get("config.load")
    if not isinstance(config_load, dict):
        return None
    details = config_load.get("details")
    if not isinstance(details, dict):
        return None
    flags = details.get("enabled feature flags")
    if not isinstance(flags, str):
        return None
    enabled = {name.strip() for name in flags.split(",") if name.strip()}
    return {name: {"enabled": True} for name in enabled}


def _doctor_payload(value: Any) -> tuple[dict[str, Any] | None, str, str, Any]:
    if not isinstance(value, dict):
        return None, "unknown", "unknown", {"hooks": "unknown"}
    report = value.get("result") if isinstance(value.get("result"), dict) else value
    if not isinstance(report.get("features"), dict):
        live_features = _live_features(report)
        if live_features is not None:
            report = {**report, "features": live_features}
    cli_version = (
        value.get("cli_version")
        or report.get("cli_version")
        or value.get("codexVersion")
        or report.get("codexVersion")
        or "unknown"
    )
    platform_id = value.get("platform") or report.get("platform") or "unknown"
    trust: Any = report.get("effective_trust", report.get("trust"))
    if trust is None:
        trust = report.get("hook_trust")
    if isinstance(trust, str):
        trust = {"hooks": trust}
    if not isinstance(trust, dict):
        trust = {"hooks": "unknown"}
    return report, str(cli_version), str(platform_id), trust


def _run_doctor(codex_bin: str, codex_home: Path | None, root: Path) -> Any | None:
    env = None
    if codex_home is not None:
        import os

        env = dict(os.environ)
        env["CODEX_HOME"] = str(codex_home)
    try:
        result = subprocess.run(
            [codex_bin, "doctor", "--json"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def _config_trust(root: Path, codex_home: Path | None) -> str | None:
    """Project trust from the effective user-level Codex config — the only
    deterministic local trust source at alpha. Hook-definition trust freshness
    is not derivable here and stays outside this signal."""
    home = codex_home if codex_home is not None else runtime_mode.default_codex_home()
    try:
        text = (Path(home) / "config.toml").read_text()
    except (OSError, UnicodeDecodeError):
        return None
    # Minimal reader for the one table shape that carries trust; tomllib is 3.11+
    # and the harness must stay stdlib-only on the supported baseline.
    wanted = str(root)
    in_table = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            match = re.fullmatch(r'\[projects\."(.*)"\]', line)
            in_table = bool(match) and match.group(1) == wanted
            continue
        if not in_table:
            continue
        match = re.fullmatch(r'trust_level\s*=\s*"([^"]*)"', line)
        if match:
            return match.group(1)
    return None


def _doctor_reasons(report: dict[str, Any] | None, trust: Any) -> list[str]:
    if report is None:
        return ["DOCTOR_UNAVAILABLE", "TRUST_UNKNOWN"]
    reasons: list[str] = []
    overall = report.get("doctor_overall_status", report.get("overallStatus"))
    if overall != "ok":
        reasons.append("DOCTOR_NOT_OK")
    checks = report.get("checks")
    if not isinstance(checks, (list, dict)) or not checks:
        reasons.append("DOCTOR_MALFORMED")
    else:
        rows = checks.values() if isinstance(checks, dict) else checks
        if any(
            not (
                value is True
                or (isinstance(value, dict) and value.get("status") == "ok")
            )
            for value in rows
        ):
            reasons.append("DOCTOR_CHECK_FAILED")
    features = report.get("features")
    if not isinstance(features, dict) or any(
        not isinstance(features.get(name), dict)
        or features[name].get("enabled") is not True
        for name in REQUIRED_FEATURES
    ):
        reasons.append("FEATURE_DISABLED")
    hook_trust = trust.get("hooks") if isinstance(trust, dict) else None
    if hook_trust in {"trusted", "enabled", True}:
        pass
    elif hook_trust in {"untrusted", "disabled", False}:
        reasons.append("HOOKS_UNTRUSTED")
    else:
        reasons.append("TRUST_UNKNOWN")
    return reasons


def _install_reasons(root: Path, repo_root: Path) -> list[str]:
    state = root / ".codex/.agent-harness"
    manifest_path = state / "deployment-manifest.json"
    if not manifest_path.is_file():
        return ["INSTALL_MISSING"]
    try:
        manifest = _load_json(manifest_path)
    except DoctorInputError:
        return ["MANIFEST_INVALID"]
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return ["MANIFEST_INVALID"]
    plugin = manifest.get("plugin")
    if (
        not isinstance(plugin, dict)
        or plugin.get("reference") != EXPECTED_PLUGIN_REFERENCE
    ):
        return ["PACKAGE_EVIDENCE_MISMATCH"]
    reasons: list[str] = []
    project_files = manifest.get("project_files")
    if not isinstance(project_files, dict):
        return ["MANIFEST_INVALID"]
    for relative, expected in project_files.items():
        safe = _safe_relative(relative)
        if safe is None or not isinstance(expected, str):
            return ["MANIFEST_INVALID"]
        path = root / safe
        if not path.is_file() or _sha256(path) != expected:
            reasons.append("INSTALL_HASH_MISMATCH")
            break

    marketplace = state / "marketplace/plugins/agent-harness"
    try:
        source_hooks = _load_json(repo_root / "adapters/codex/plugin/hooks/hooks.json")
        installed_hooks = _load_json(marketplace / "hooks/hooks.json")
    except DoctorInputError:
        reasons.append("HOOK_COVERAGE_MISMATCH")
    else:
        if source_hooks != installed_hooks:
            reasons.append("HOOK_COVERAGE_MISMATCH")
    expected_hook_files = _tree_inventory(repo_root / "hooks")
    expected_hook_files["hooks.json"] = _sha256(
        repo_root / "adapters/codex/plugin/hooks/hooks.json"
    )
    if _tree_inventory(marketplace / "hooks") != expected_hook_files:
        reasons.append("INSTALL_HASH_MISMATCH")
    source_plugin_manifest = (
        repo_root / "adapters/codex/plugin/.codex-plugin/plugin.json"
    )
    installed_plugin_manifest = marketplace / ".codex-plugin/plugin.json"
    if not installed_plugin_manifest.is_file() or _sha256(
        installed_plugin_manifest
    ) != _sha256(source_plugin_manifest):
        reasons.append("INSTALL_HASH_MISMATCH")
    try:
        inventory = _load_json(repo_root / "harness-manifest.json")
    except DoctorInputError:
        return reasons + ["MANIFEST_INVALID"]
    expected_skills = set(inventory.get("skills", []))
    expected_skill_files: dict[str, str] = {}
    for skill in expected_skills:
        expected_skill_files.update(
            {
                f"{skill}/{relative}": digest
                for relative, digest in _tree_inventory(
                    repo_root / "skills" / skill
                ).items()
            }
        )
    if _tree_inventory(marketplace / "skills") != expected_skill_files:
        reasons.append("INSTALL_HASH_MISMATCH")
    installed_skills = (
        {path.name for path in (marketplace / "skills").iterdir() if path.is_dir()}
        if (marketplace / "skills").is_dir()
        else set()
    )
    if expected_skills != installed_skills:
        reasons.append("SKILL_DISCOVERY_MISMATCH")
    expected_agents = {f"{name}.toml" for name in inventory.get("agents", [])}
    installed_agents = {path.name for path in (root / ".codex/agents").glob("*.toml")}
    if expected_agents != installed_agents:
        reasons.append("AGENT_DISCOVERY_MISMATCH")
    return reasons


def _evidence_reasons(
    matrix: dict[str, Any], platform_id: str, trust: Any, today: date
) -> tuple[list[str], str | None]:
    reasons: list[str] = []
    expiry_dates: list[date] = []
    capabilities = matrix.get("capabilities")
    if not isinstance(capabilities, list):
        return ["EVIDENCE_UNKNOWN"], None
    hook_trust = trust.get("hooks") if isinstance(trust, dict) else None
    matched_load_bearing = 0
    for row in capabilities:
        if not isinstance(row, dict) or row.get("load_bearing") is not True:
            continue
        row_id = row.get("id", "")
        platforms = row.get("platforms", [])
        if row_id.startswith("platform.") and platform_id not in platforms:
            continue
        if platform_id not in platforms and not row_id.startswith(
            "config.project_trust"
        ):
            continue
        matched_load_bearing += 1
        source = row.get("source")
        expires = source.get("expires_at") if isinstance(source, dict) else None
        try:
            expiry = date.fromisoformat(expires)
            expiry_dates.append(expiry)
            if expiry < today:
                reasons.append("EVIDENCE_STALE")
        except (TypeError, ValueError):
            reasons.append("EVIDENCE_UNKNOWN")
        if row_id == "config.project_trust" and hook_trust in {
            "trusted",
            "enabled",
            True,
        }:
            continue
        if row.get("status") != "supported" or row.get("evidence_level") not in {
            "observed",
            "documented",
        }:
            reasons.append("EVIDENCE_UNKNOWN")
        elif row.get("evidence_level") == "documented":
            # Documentation is traceability, not truth: a load-bearing surface
            # that was never observed cannot silently support `enforced`.
            reasons.append("EVIDENCE_DOCUMENTED_ONLY")
    if matched_load_bearing == 0:
        # Zero matched load-bearing rows means no evidence, not clean evidence:
        # an emptied or re-labelled matrix must not compute to `enforced`.
        reasons.append("EVIDENCE_UNKNOWN")
    earliest = min(expiry_dates).isoformat() if expiry_dates else None
    return reasons, earliest


def diagnose(
    *,
    root: Path,
    repo_root: Path,
    doctor_value: Any | None,
    platform_override: str | None = None,
    dependencies: dict[str, bool] | None = None,
    today: date | None = None,
    codex_home: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    repo_root = repo_root.resolve()
    report, cli_version, reported_platform, trust = _doctor_payload(doctor_value)
    if isinstance(trust, dict) and trust.get("hooks") not in {
        "trusted",
        "enabled",
        True,
        "untrusted",
        "disabled",
        False,
    }:
        config_level = _config_trust(root, codex_home)
        if config_level == "trusted":
            trust = {**trust, "hooks": "trusted", "trust_source": "codex-home-config"}
        elif config_level is not None:
            trust = {**trust, "hooks": "untrusted", "trust_source": "codex-home-config"}
    platform_id = platform_override or (
        reported_platform if reported_platform != "unknown" else detect_platform()
    )
    deps = dependencies if dependencies is not None else dependency_status()
    unsupported: list[str] = []
    advisory: list[str] = []
    if platform_id.startswith("windows-"):
        unsupported.append("NATIVE_WINDOWS_UNSUPPORTED")
    if any(deps.get(name) is not True for name in REQUIRED_DEPENDENCIES):
        unsupported.append("DEPENDENCY_MISSING")
    install = _install_reasons(root, repo_root)
    for reason in install:
        (
            unsupported
            if reason in {"INSTALL_MISSING", "MANIFEST_INVALID"}
            else advisory
        ).append(reason)
    decision = _front_matter(repo_root / "specs/codex-support/packaging-decision.md")
    if (
        decision.get("decision") != "hybrid"
        or decision.get("runtime_execution") != "observed"
    ):
        unsupported.append("PACKAGE_UNSELECTED")
    expected_version = "unknown"
    try:
        matrix = _load_json(repo_root / "specs/codex-support/capability-matrix.json")
        expected_version = str(matrix.get("cli_version", "unknown"))
    except DoctorInputError:
        matrix = {}
        advisory.append("EVIDENCE_UNKNOWN")
    if cli_version != expected_version:
        advisory.append("CLI_VERSION_MISMATCH")
    if platform_id not in SUPPORTED_PLATFORMS:
        advisory.append("PLATFORM_UNVERIFIED")
    if (
        platform_override is not None
        and reported_platform != "unknown"
        and reported_platform != platform_override
    ):
        advisory.append("PLATFORM_REPORT_MISMATCH")
    advisory.extend(_doctor_reasons(report, trust))
    evidence, expires_at = _evidence_reasons(
        matrix, platform_id, trust, today or date.today()
    )
    advisory.extend(evidence)
    reasons = sorted(set(unsupported + advisory))
    mode = "unsupported" if unsupported else ("advisory" if reasons else "enforced")
    fingerprint = runtime_mode.make_fingerprint(
        root, cli_version=cli_version, trust=trust, codex_home=codex_home
    )
    return runtime_mode.make_record(
        mode=mode,
        reason_codes=reasons,
        fingerprint=fingerprint,
        observed_at=(today or date.today()).isoformat(),
        evidence_expires_at=expires_at,
        diagnostic_summary={
            "doctor": "ok"
            if not any(r.startswith("DOCTOR_") for r in reasons)
            else "degraded",
            "package": decision.get("decision", "unknown"),
            "platform": platform_id,
            "trust": str(trust.get("hooks", "unknown"))
            if isinstance(trust, dict)
            else "unknown",
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--doctor-report", type=Path)
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--platform")
    parser.add_argument("--dependencies-json", type=Path)
    parser.add_argument("--now", type=date.fromisoformat)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.doctor_report:
            try:
                doctor_value = _load_json(args.doctor_report)
            except DoctorInputError:
                doctor_value = None
        else:
            doctor_value = _run_doctor(
                args.codex_bin, args.codex_home, args.root.resolve()
            )
        dependencies = (
            _load_json(args.dependencies_json) if args.dependencies_json else None
        )
        if dependencies is not None and not isinstance(dependencies, dict):
            raise DoctorInputError("dependencies fixture must be an object")
        record = diagnose(
            root=args.root,
            repo_root=args.repo_root,
            doctor_value=doctor_value,
            platform_override=args.platform,
            dependencies=dependencies,
            today=args.now,
            codex_home=args.codex_home,
        )
        if not args.no_persist:
            runtime_mode.persist_record(args.root, record)
        if args.summary:
            runtime_mode.update_summary_metadata(
                args.summary, record["mode"], record["evidence_id"]
            )
    except (
        DoctorInputError,
        runtime_mode.RuntimeModeError,
        OSError,
        ValueError,
    ) as exc:
        print(f"codex-harness-doctor: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
