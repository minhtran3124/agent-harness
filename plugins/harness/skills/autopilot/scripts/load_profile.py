#!/usr/bin/env python3
"""Load the autopilot profile: the plugin default, then the project override on top.

Default:  ../profile.json, next to this script's directory.
Override: <repo-dir>/.claude/autopilot-profile.json, if it exists. A top-level key replaces the
          default one; `stages` is merged per stage.
Output JSON (stdout): the merged profile.
Exit 2 names the problem: a file that does not parse, an unknown key or a value that is not allowed.
ship.js checks `stages` again (stage names) when it starts.
"""
import argparse
import json
import sys
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent.parent / "profile.json"
OVERRIDE = Path(".claude") / "autopilot-profile.json"

ROLE_MODELS = {
    "orchestrator": {"sonnet", "opus"},
    "researcher": {"haiku", "sonnet", "opus"},
    "intake": {"haiku", "sonnet", "opus"},
    "advisor": {"opus", "fable"},
}
STAGE_MODELS = {"haiku", "sonnet", "opus"}
EFFORTS = {"low", "medium", "high", "xhigh", "max"}


def read(path):
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise ValueError(f"{path}: {e}")
    if not isinstance(data, dict):
        raise ValueError(f"{path}: must be a JSON object")
    return data


def check(profile, source):
    for key, value in profile.items():
        if key == "stages":
            if not isinstance(value, dict):
                raise ValueError(f"{source}: stages must be an object")
            for stage, cfg in value.items():
                if not isinstance(cfg, dict) or set(cfg) - {"model", "effort"}:
                    raise ValueError(f"{source}: stages.{stage} must be an object with model and/or effort")
                if "model" in cfg and cfg["model"] not in STAGE_MODELS:
                    raise ValueError(f"{source}: stages.{stage}.model must be one of {sorted(STAGE_MODELS)}")
                if "effort" in cfg and cfg["effort"] not in EFFORTS:
                    raise ValueError(f"{source}: stages.{stage}.effort must be one of {sorted(EFFORTS)}")
        elif key in ROLE_MODELS:
            if value not in ROLE_MODELS[key]:
                raise ValueError(f"{source}: {key} must be one of {sorted(ROLE_MODELS[key])}")
        else:
            raise ValueError(f"{source}: unknown key '{key}'")


def load(repo_dir, default=DEFAULT):
    profile = read(default)
    check(profile, default)
    override_path = Path(repo_dir) / OVERRIDE
    if override_path.exists():
        override = read(override_path)
        check(override, override_path)
        stages = {**profile.get("stages", {}), **override.get("stages", {})}
        profile = {**profile, **override, "stages": stages}
    return profile


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-dir", required=True, help="the owner's checkout")
    ap.add_argument("--default", default=str(DEFAULT), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    try:
        out = load(args.repo_dir, Path(args.default))
    except ValueError as e:
        print(f"load_profile: {e}", file=sys.stderr)
        return 2
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
