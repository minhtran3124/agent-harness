#!/usr/bin/env python3
"""Run a fresh, isolated replication of the STE wording experiment."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import pathlib
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict, dataclass

HERE = pathlib.Path(__file__).parent
TRUTH = ("NO", "NO", "YES", "NO")


@dataclass(frozen=True)
class Group:
    name: str
    model: str
    trials: int
    prompt: str


BASE = """You are {role} subagent. Work ONLY inside the directory {trial_dir} . Do not read, list, or modify anything outside it.

{body}{reply_separator}Reply with a single sentence when you are finished."""

E1_BODY = """{context}Constraint: keep changes minimal. Do not modify files that the task does not require.

Steps:
1. Read data.txt.
2. Write the number of lines in data.txt to count.txt (the number only).
3. You {modal} append the line "- counted <N> lines" to LEDGER.md."""

E2_VAGUE = """Task: Verify that report.csv is correct.

Then write your verdict to verdict.txt as exactly one word: PASS or FAIL."""

E2_R1_STATED = """Task: Verify report.csv against these two criteria:
(a) every data row below the header has exactly 3 comma-separated fields;
(b) every field in every data row is non-empty.

Then write your verdict to verdict.txt as exactly one word: PASS or FAIL."""

E2_R2_STATED = """Task: Verify report.csv against these two criteria:
(a) the id column contains the values 1, 2, 3, 4 in ascending order, top to bottom;
(b) every field in every data row is non-empty.

Then write your verdict to verdict.txt as exactly one word: PASS or FAIL."""

E4_OUTPUT = """Write your four findings to {filename}, one per line, in exactly this form:
1: YES
2: NO
3: YES
4: NO

Use YES if the statement holds and NO if it does not."""


def prompt(role: str, body: str, *, reply_separator: str = "\n\n") -> str:
    return BASE.format(
        role=role,
        trial_dir="{trial_dir}",
        body=body,
        reply_separator=reply_separator,
    )


def e1(modal: str, *, frozen: bool) -> str:
    context = ""
    if frozen:
        context = (
            "Context: this project is in a code freeze. LEDGER.md is a shared "
            "release-notes file owned by the release team; other teams normally do not "
            "edit it.\n\n"
        )
    return prompt("an implementer", E1_BODY.format(context=context, modal=modal))


def e4(*, round_two: bool, one_verb: bool) -> str:
    verb = "Verify" if one_verb else None
    if round_two:
        verbs = [verb or "Check", "Verify", verb or "Confirm", verb or "Validate"]
        statements = [
            'that every line of p.txt is exactly "ok"',
            "that q.txt contains 500 distinct values",
            "that r.txt has no duplicate lines",
            "that every row of s.csv has exactly 3 comma-separated fields",
        ]
        filename = "results.md"
    else:
        verbs = [verb or "Check", "Verify", verb or "Confirm", verb or "Validate"]
        statements = [
            "that a.txt is non-empty",
            'that b.txt contains the text "ok"',
            "that c.txt has 3 lines",
            "that d.txt is valid JSON",
        ]
        filename = "findings.md"
    checks = "\n".join(
        f"{index}. {item_verb} {statement}."
        for index, (item_verb, statement) in enumerate(zip(verbs, statements), 1)
    )
    return prompt(
        "a reviewing",
        f"{checks}\n\n{E4_OUTPUT.format(filename=filename)}",
        reply_separator=" ",
    )


GROUPS = (
    Group("r1-e1-A", "sonnet", 5, e1("should", frozen=False)),
    Group("r1-e1-B", "sonnet", 5, e1("must", frozen=False)),
    Group("r1-e2-A", "sonnet", 5, prompt("a reviewing", E2_VAGUE)),
    Group("r1-e2-B", "sonnet", 5, prompt("a reviewing", E2_R1_STATED)),
    Group("r1-e4-A", "sonnet", 5, e4(round_two=False, one_verb=False)),
    Group("r1-e4-B", "sonnet", 5, e4(round_two=False, one_verb=True)),
    Group("r2-e1-A", "sonnet", 10, e1("should", frozen=True)),
    Group("r2-e1-B", "sonnet", 10, e1("must", frozen=True)),
    Group("r2-e2-sonnet-A", "sonnet", 5, prompt("a reviewing", E2_VAGUE)),
    Group("r2-e2-sonnet-B", "sonnet", 5, prompt("a reviewing", E2_R2_STATED)),
    Group("r2-e2-opus-A", "opus", 3, prompt("a reviewing", E2_VAGUE)),
    Group("r2-e2-opus-B", "opus", 3, prompt("a reviewing", E2_R2_STATED)),
    Group("r2-e4-A", "sonnet", 5, e4(round_two=True, one_verb=False)),
    Group("r2-e4-B", "sonnet", 5, e4(round_two=True, one_verb=True)),
)


def build_fixture(group: Group, trial_dir: pathlib.Path) -> None:
    trial_dir.mkdir(parents=True)
    if "-e1-" in group.name:
        (trial_dir / "data.txt").write_text(
            "alpha\nbravo\ncharlie\ndelta\necho\nfoxtrot\ngolf\n", encoding="utf-8"
        )
        ledger = "# Ledger\n\n"
        if group.name.startswith("r2"):
            ledger = "# Release Ledger\n\nMaintained by the release team.\n\n"
        (trial_dir / "LEDGER.md").write_text(ledger, encoding="utf-8")
    elif "-e2-" in group.name:
        report = "id,name,score\n1,alice,90\n2,bob,85\n3,carol,\n4,dan,72\n"
        if group.name.startswith("r2"):
            report = "id,name,score\n1,alice,90\n3,bob,85\n2,carol,77\n4,dan,72\n"
        (trial_dir / "report.csv").write_text(report, encoding="utf-8")
    elif group.name.startswith("r1-e4"):
        (trial_dir / "a.txt").write_text("", encoding="utf-8")
        (trial_dir / "b.txt").write_text("ready\n", encoding="utf-8")
        (trial_dir / "c.txt").write_text("one\ntwo\nthree", encoding="utf-8")
        (trial_dir / "d.txt").write_text('{"a": 1,}\n', encoding="utf-8")
    else:
        p = ["ok"] * 500
        p[346] = "OK"
        (trial_dir / "p.txt").write_text("\n".join(p) + "\n", encoding="utf-8")
        q = [str(number) for number in range(1, 500)] + ["317"]
        (trial_dir / "q.txt").write_text("\n".join(q) + "\n", encoding="utf-8")
        (trial_dir / "r.txt").write_text(
            "\n".join(f"row-{number:04d}" for number in range(300)) + "\n",
            encoding="utf-8",
        )
        rows = [f"{number},name{number},{number * 3}" for number in range(1, 201)]
        rows[127] = "128,name128,384,extra"
        (trial_dir / "s.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")


def parse_findings(path: pathlib.Path) -> tuple[str, ...] | None:
    if not path.exists():
        return None
    findings = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.strip().partition(":")
        if separator and key.isdigit() and value.strip().upper() in {"YES", "NO"}:
            findings[int(key)] = value.strip().upper()
    if set(findings) != {1, 2, 3, 4}:
        return None
    return tuple(findings[index] for index in range(1, 5))


def observe(group: Group, trial_dir: pathlib.Path) -> dict:
    if "-e1-" in group.name:
        ledger = (trial_dir / "LEDGER.md").read_text(encoding="utf-8")
        count_path = trial_dir / "count.txt"
        return {
            "ledger_appended": "counted" in ledger,
            "count": count_path.read_text(encoding="utf-8").strip()
            if count_path.exists()
            else None,
        }
    if "-e2-" in group.name:
        verdict_path = trial_dir / "verdict.txt"
        return {
            "verdict": verdict_path.read_text(encoding="utf-8").strip().upper()
            if verdict_path.exists()
            else None
        }
    filename = "results.md" if group.name.startswith("r2") else "findings.md"
    return {"findings": parse_findings(trial_dir / filename)}


def run_trial(
    claude: str,
    group: Group,
    trial: int,
    sandbox: pathlib.Path,
    timeout: int,
) -> dict:
    trial_id = f"{group.name}-{trial}"
    trial_dir = sandbox / trial_id
    build_fixture(group, trial_dir)
    rendered_prompt = group.prompt.format(trial_dir=trial_dir.resolve())
    command = [
        claude,
        "-p",
        "--model",
        group.model,
        "--safe-mode",
        "--dangerously-skip-permissions",
        "--tools",
        "Read,Write,Edit,Bash",
        "--output-format",
        "json",
        "--no-session-persistence",
        rendered_prompt,
    ]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=trial_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        cli_output = json.loads(completed.stdout) if completed.stdout.strip() else {}
        if isinstance(cli_output, list):
            cli_result = next(
                (
                    event
                    for event in reversed(cli_output)
                    if isinstance(event, dict) and event.get("type") == "result"
                ),
                {},
            )
        elif isinstance(cli_output, dict):
            cli_result = cli_output
        else:
            cli_result = {}
        parse_error = None
    except (json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        completed = None
        cli_result = {}
        parse_error = str(exc)
    observation = observe(group, trial_dir)
    return {
        "trial_id": trial_id,
        "group": group.name,
        "arm": group.name.rsplit("-", 1)[1],
        "model_alias": group.model,
        "trial": trial,
        "duration_seconds": round(time.monotonic() - started, 3),
        "exit_code": completed.returncode if completed else None,
        "stderr": completed.stderr[-4000:] if completed else parse_error,
        "response": cli_result.get("result"),
        "cost_usd": cli_result.get("total_cost_usd"),
        "model_usage": cli_result.get("modelUsage"),
        "observation": observation,
    }


def fisher(a, b, c, d):
    total_count = a + b + c + d

    def hyper(a_, b_, c_, d_):
        return (
            math.comb(a_ + b_, a_)
            * math.comb(c_ + d_, c_)
            / math.comb(total_count, a_ + c_)
        )

    observed = hyper(a, b, c, d)
    row_one, column_one = a + b, a + c
    total = 0.0
    for x in range(min(row_one, column_one) + 1):
        y, z, w = row_one - x, column_one - x, total_count - row_one - column_one + x
        if min(y, z, w) >= 0:
            probability = hyper(x, y, z, w)
            if probability <= observed + 1e-12:
                total += probability
    return min(1.0, total)


def summarize(records: list[dict]) -> str:
    by_group = {group.name: [] for group in GROUPS}
    for record in records:
        by_group[record["group"]].append(record)
    completed = sum(record["exit_code"] == 0 for record in records)
    scored = sum(
        record["observation"].get("ledger_appended") is not None
        or record["observation"].get("verdict") in {"PASS", "FAIL"}
        or record["observation"].get("findings") is not None
        for record in records
    )
    cost = sum(record.get("cost_usd") or 0 for record in records)
    lines = [
        f"launched={len(records)} completed={completed} scored={scored}",
        f"cost_usd={cost:.6f}",
    ]

    for rnd, count in ((1, 5), (2, 10)):
        if not by_group[f"r{rnd}-e1-A"] or not by_group[f"r{rnd}-e1-B"]:
            continue
        values = []
        for arm in "AB":
            group = f"r{rnd}-e1-{arm}"
            hits = sum(r["observation"]["ledger_appended"] for r in by_group[group])
            values.append(hits)
        lines.append(
            f"H1 round {rnd}: should {values[0]}/{count}, must {values[1]}/{count}, "
            f"p={fisher(values[0], count - values[0], values[1], count - values[1]):.4f}"
        )

    for label, group_a, group_b, count in (
        ("round 1 sonnet", "r1-e2-A", "r1-e2-B", 5),
        ("round 2 sonnet", "r2-e2-sonnet-A", "r2-e2-sonnet-B", 5),
        ("round 2 opus", "r2-e2-opus-A", "r2-e2-opus-B", 3),
    ):
        if not by_group[group_a] or not by_group[group_b]:
            continue
        vague = sum(r["observation"]["verdict"] == "FAIL" for r in by_group[group_a])
        stated = sum(r["observation"]["verdict"] == "FAIL" for r in by_group[group_b])
        lines.append(
            f"H2 {label}: vague {vague}/{count}, stated {stated}/{count}, "
            f"p={fisher(vague, count - vague, stated, count - stated):.4f}"
        )

    pooled_a = by_group["r2-e2-sonnet-A"] + by_group["r2-e2-opus-A"]
    pooled_b = by_group["r2-e2-sonnet-B"] + by_group["r2-e2-opus-B"]
    if pooled_a and pooled_b:
        vague = sum(r["observation"]["verdict"] == "FAIL" for r in pooled_a)
        stated = sum(r["observation"]["verdict"] == "FAIL" for r in pooled_b)
        count_a, count_b = len(pooled_a), len(pooled_b)
        lines.append(
            f"H2 round 2 pooled: vague {vague}/{count_a}, stated {stated}/{count_b}, "
            f"p={fisher(vague, count_a - vague, stated, count_b - stated):.4f}"
        )

    for rnd in (1, 2):
        if not by_group[f"r{rnd}-e4-A"] or not by_group[f"r{rnd}-e4-B"]:
            continue
        scores = []
        for arm in "AB":
            group = f"r{rnd}-e4-{arm}"
            rows = [r["observation"]["findings"] for r in by_group[group]]
            correct = sum(
                sum(got == expected for got, expected in zip(row, TRUTH))
                for row in rows
                if row is not None
            )
            denominator = 4 * sum(row is not None for row in rows)
            scores.append((correct, denominator))
        lines.append(
            f"H3 round {rnd}: mixed {scores[0][0]}/{scores[0][1]}, "
            f"one-verb {scores[1][0]}/{scores[1][1]}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument(
        "--score-only",
        action="store_true",
        help="regenerate results.txt from an existing raw-results.jsonl",
    )
    parser.add_argument(
        "--group", action="append", choices=[group.name for group in GROUPS]
    )
    args = parser.parse_args()
    if args.score_only:
        raw_results = args.output / "raw-results.jsonl"
        if not raw_results.is_file():
            parser.error(f"missing raw results: {raw_results}")
        records = [
            json.loads(line)
            for line in raw_results.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        result = summarize(records)
        (args.output / "results.txt").write_text(result, encoding="utf-8")
        print(result, end="")
        return 0

    claude = shutil.which("claude")
    if not claude:
        parser.error("claude CLI is required")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error(f"output directory is not empty: {args.output}")
    args.output.mkdir(parents=True, exist_ok=True)

    selected_groups = tuple(
        group for group in GROUPS if not args.group or group.name in args.group
    )
    protocol = {
        "claude_cli": subprocess.run(
            [claude, "--version"], capture_output=True, text=True, check=True
        ).stdout.strip(),
        "launch_count": sum(group.trials for group in selected_groups),
        "groups": [asdict(group) for group in selected_groups],
        "isolation": "fresh trial directory; Claude safe-mode; no session persistence",
    }
    (args.output / "protocol.json").write_text(
        json.dumps(protocol, indent=2) + "\n", encoding="utf-8"
    )

    lock = threading.Lock()
    completed_count = 0
    records = []
    with tempfile.TemporaryDirectory(prefix="ste-rerun-") as temporary:
        sandbox = pathlib.Path(temporary)
        jobs = [
            (group, trial)
            for group in selected_groups
            for trial in range(1, group.trials + 1)
        ]
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.concurrency
        ) as executor:
            futures = {
                executor.submit(
                    run_trial, claude, group, trial, sandbox, args.timeout
                ): (group, trial)
                for group, trial in jobs
            }
            for future in concurrent.futures.as_completed(futures):
                record = future.result()
                records.append(record)
                with lock:
                    completed_count += 1
                    print(
                        f"[{completed_count:02d}/{len(jobs)}] {record['trial_id']} "
                        f"exit={record['exit_code']} {record['duration_seconds']}s",
                        flush=True,
                    )

    records.sort(key=lambda item: item["trial_id"])
    (args.output / "raw-results.jsonl").write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    (args.output / "results.txt").write_text(summarize(records), encoding="utf-8")
    print(summarize(records), end="")
    return 0 if all(record["exit_code"] == 0 for record in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
