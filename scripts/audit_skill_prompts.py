#!/usr/bin/env python3
"""Inventory the registered skill prompt surface and guard its baseline.

The audit deliberately measures repository artifacts, not model output.  It discovers every
registered SKILL.md and every Markdown companion file whose name contains ``prompt`` beneath
that skill directory.  The resulting JSON is stable enough to commit as a pre/post prompt
surface baseline.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path


DESCRIPTION_CHARACTER_CEILING = 1024
SKILL_WORD_CEILING = 600


def count_text(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8")
    return {
        "lines": len(text.splitlines()),
        "words": len(re.findall(r"\S+", text)),
        "characters": len(text),
    }


def description_length(text: str) -> int:
    """Return a conservative frontmatter-description length without a YAML dependency."""
    if not text.startswith("---\n"):
        return 0
    frontmatter = text.split("\n---\n", 1)[0]
    match = re.search(r"^description:\s*[>|]?\s*(.*)$", frontmatter, re.MULTILINE)
    return len(match.group(1).strip()) if match else 0


def git_sha(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def prompt_paths(skill_dir: Path) -> Iterable[Path]:
    for path in sorted(skill_dir.rglob("*.md")):
        if path.name != "SKILL.md" and "prompt" in path.name.lower():
            yield path


def inventory(root: Path) -> dict[str, object]:
    manifest_path = root / "harness-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    registered = manifest.get("skills", [])
    if not isinstance(registered, list) or not all(isinstance(name, str) for name in registered):
        raise ValueError("harness-manifest.json skills must be a list of strings")

    problems: list[str] = []
    skills: list[dict[str, object]] = []
    totals = {"skills": 0, "companion_prompts": 0, "lines": 0, "words": 0, "characters": 0}
    discovered_prompt_paths: set[str] = set()

    for name in sorted(registered):
        skill_path = root / "skills" / name / "SKILL.md"
        if not skill_path.is_file():
            problems.append(f"registered skill missing SKILL.md: skills/{name}/SKILL.md")
            continue
        stats = count_text(skill_path)
        text = skill_path.read_text(encoding="utf-8")
        desc_len = description_length(text)
        if desc_len > DESCRIPTION_CHARACTER_CEILING:
            problems.append(
                f"skill description exceeds {DESCRIPTION_CHARACTER_CEILING} characters: "
                f"skills/{name}/SKILL.md ({desc_len})"
            )
        if stats["words"] > SKILL_WORD_CEILING:
            problems.append(
                f"skill exceeds {SKILL_WORD_CEILING}-word progressive-disclosure ceiling: "
                f"skills/{name}/SKILL.md ({stats['words']})"
            )
        companions = []
        for prompt in prompt_paths(skill_path.parent):
            prompt_stats = count_text(prompt)
            rel = prompt.relative_to(root).as_posix()
            discovered_prompt_paths.add(rel)
            companions.append({"path": rel, **prompt_stats})
            totals["companion_prompts"] += 1
            for key in ("lines", "words", "characters"):
                totals[key] += prompt_stats[key]
        skills.append(
            {
                "name": name,
                "skill": {"path": skill_path.relative_to(root).as_posix(), **stats},
                "description_characters": desc_len,
                "companion_prompts": companions,
            }
        )
        totals["skills"] += 1
        for key in ("lines", "words", "characters"):
            totals[key] += stats[key]

    for prompt in sorted((root / "skills").rglob("*prompt*.md")):
        rel = prompt.relative_to(root).as_posix()
        if rel not in discovered_prompt_paths:
            problems.append(f"unowned companion prompt: {rel}")

    return {
        "schema_version": 1,
        "git_sha": git_sha(root),
        "measurement": "whitespace words; lines exclude a trailing empty line",
        "inventory": skills,
        "totals": totals,
        "problems": problems,
    }


def comparable(data: dict[str, object]) -> dict[str, object]:
    """Drop volatile metadata before comparing a committed baseline."""
    return {key: data[key] for key in ("schema_version", "measurement", "inventory", "totals", "problems")}


def inventory_errors(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["inventory must be an object"]
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if not isinstance(data.get("git_sha"), str) or not data["git_sha"]:
        errors.append("git_sha is required")
    rows = data.get("inventory")
    if not isinstance(rows, list) or not rows:
        errors.append("inventory must be a non-empty list")
    totals = data.get("totals")
    if not isinstance(totals, dict) or any(not isinstance(totals.get(key), int) for key in ("skills", "companion_prompts", "lines", "words", "characters")):
        errors.append("totals must contain integer surface counts")
    if data.get("problems"):
        errors.append("inventory records unresolved problems")
    return errors


def markdown(data: dict[str, object]) -> str:
    totals = data["totals"]
    assert isinstance(totals, dict)
    lines = [
        "# Skill prompt inventory baseline",
        "",
        f"Git SHA: `{data['git_sha']}`",
        "",
        "| Surface | Files | Lines | Words | Characters |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| Registered SKILL.md | {totals['skills']} | "
        f"{sum(item['skill']['lines'] for item in data['inventory'])} | "
        f"{sum(item['skill']['words'] for item in data['inventory'])} | "
        f"{sum(item['skill']['characters'] for item in data['inventory'])} |",
        f"| Companion prompts | {totals['companion_prompts']} | "
        f"{totals['lines'] - sum(item['skill']['lines'] for item in data['inventory'])} | "
        f"{totals['words'] - sum(item['skill']['words'] for item in data['inventory'])} | "
        f"{totals['characters'] - sum(item['skill']['characters'] for item in data['inventory'])} |",
        f"| **Total** | **{totals['skills'] + totals['companion_prompts']}** | "
        f"**{totals['lines']}** | **{totals['words']}** | **{totals['characters']}** |",
        "",
        "Measurement uses whitespace-delimited words. Model/client token and latency metrics are "
        "recorded by the behavioral eval runner, not inferred from repository text.",
    ]
    return "\n".join(lines) + "\n"


def comparison(before: dict[str, object], after: dict[str, object]) -> tuple[bool, str]:
    """Return whether the candidate meets the configured surface-reduction floor."""
    for label, data in (("baseline", before), ("candidate", after)):
        if not isinstance(data.get("totals"), dict):
            raise ValueError(f"{label}: missing totals")
    old = before["totals"]
    new = after["totals"]
    assert isinstance(old, dict) and isinstance(new, dict)
    old_words, new_words = int(old["words"]), int(new["words"])
    reduction = 0 if old_words == 0 else (old_words - new_words) / old_words * 100
    ok = new_words <= old_words and reduction >= 25
    report = (
        f"prompt-audit: words {old_words} -> {new_words} "
        f"({reduction:.1f}% reduction; required >=25.0%)"
    )
    return ok, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--json", action="store_true", help="print JSON inventory")
    parser.add_argument("--markdown", action="store_true", help="print Markdown summary")
    parser.add_argument("--write-json", type=Path, help="write JSON inventory to this path")
    parser.add_argument("--write-markdown", type=Path, help="write Markdown summary to this path")
    parser.add_argument("--check-baseline", type=Path, help="compare current inventory to JSON")
    parser.add_argument("--validate-inventory", type=Path, help="validate a pinned inventory without comparing it to current source")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("BASELINE", "CANDIDATE"),
                        help="verify a candidate inventory reduces total words by at least 25%")
    args = parser.parse_args()

    try:
        data = inventory(args.root.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"prompt-audit: {exc}", file=sys.stderr)
        return 1

    if data["problems"]:
        for problem in data["problems"]:
            print(f"prompt-audit: {problem}", file=sys.stderr)
        return 1

    if args.validate_inventory:
        try:
            errors = inventory_errors(json.loads(args.validate_inventory.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"prompt-audit: cannot read inventory: {exc}", file=sys.stderr)
            return 1
        if errors:
            for error in errors:
                print(f"prompt-audit: inventory: {error}", file=sys.stderr)
            return 1
        print("prompt-audit: inventory is valid")

    if args.check_baseline:
        try:
            baseline = json.loads(args.check_baseline.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"prompt-audit: cannot read baseline: {exc}", file=sys.stderr)
            return 1
        if comparable(data) != comparable(baseline):
            print("prompt-audit: current inventory differs from baseline", file=sys.stderr)
            return 1
        print("prompt-audit: baseline matches")

    if args.compare:
        try:
            before = json.loads(args.compare[0].read_text(encoding="utf-8"))
            after = json.loads(args.compare[1].read_text(encoding="utf-8"))
            ok, report = comparison(before, after)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"prompt-audit: cannot compare inventories: {exc}", file=sys.stderr)
            return 1
        print(report)
        if not ok:
            return 1

    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_markdown:
        args.write_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.write_markdown.write_text(markdown(data), encoding="utf-8")

    if args.markdown:
        print(markdown(data), end="")
    elif args.json or (not args.check_baseline and not args.validate_inventory and not args.compare and not args.write_json and not args.write_markdown):
        print(json.dumps(data, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
