#!/usr/bin/env python3
"""Phase 2 pilot: compare original and rewritten harness prose with headless Claude Code."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import pathlib
import re
import shlex
import shutil
import subprocess
import tempfile
import time

HERE = pathlib.Path(__file__).parent
REPO = HERE.parents[2]
PROBES = json.loads((HERE / "probes.json").read_text(encoding="utf-8"))
FIXTURES = json.loads((HERE / "intake-fixtures.json").read_text(encoding="utf-8"))
PILOT_FILES = tuple(PROBES)
INTAKE = "skills/feature-intake/SKILL.md"
WORKFLOW_FILES = (INTAKE, "harness-manifest.json", "rules/orchestration.md")
ARMS = ("original", "rewritten")
MODEL = "sonnet"
TRIALS = 10  # budget: trials per arm per method per file
TRIAL_CAP_USD = 0.50
PILOT_CAP_USD = 25.0
AGGREGATE_SLACK = 2  # budget: rewritten may score this many fewer correct answers
MEANING_DROP = 3  # budget: 10/10 original -> 7/10 or fewer rewritten is a meaning change
FIELDS = ("Lane", "Confidence", "Escalate")

HEADER = """You are a subagent. Work ONLY inside the directory {trial_dir} . Do not read, list, or modify anything outside it.

"""

PROBE_PROMPT = HEADER + """Read the file {path} . Answer each question below from that file only. Start each answer with the answer itself: a word, a number, a name, or yes/no. Keep each answer short. Do not explain.

Questions:
{questions}

Write your answers to answers.json as one JSON object that maps each question id to its answer string, for example {{"{first}": "..."}}. Write nothing else to the file. Reply with a single sentence when you are finished."""

WORKFLOW_PROMPT = HEADER + """Read skills/feature-intake/SKILL.md, harness-manifest.json, and rules/orchestration.md. For each change request below, follow only Steps 2-4 of the Procedure in SKILL.md: mark the risk flags, assign the lane, and assign the confidence. Then decide Escalate (yes or no) from the escalation decision in rules/orchestration.md. Each request is for an application repository whose code is under app/. Do not create SUMMARY.md, a branch, or any file other than classification.json.

Requests:
{requests}

Write classification.json as one JSON object that maps each request id to an object with the keys "Lane" (tiny, normal, or high-risk), "Confidence" (high, medium, or low), and "Escalate" (yes or no). Write nothing else to the file. Reply with a single sentence when you are finished."""


def _json_object(text):
    try:
        data = json.loads(text) if text is not None else None
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def parse_answers(text):
    data = _json_object(text)
    return None if data is None else {str(key): str(value) for key, value in data.items()}


def parse_classification(text):
    data = _json_object(text)
    if data is None:
        return None
    rows = {}
    for key, row in data.items():
        if not isinstance(row, dict) or not all(isinstance(row.get(f), str) for f in FIELDS):
            return None
        words = [row[f].strip().lower().split() or [""] for f in FIELDS]
        rows[key] = tuple(w[0].strip("().,;:") for w in words)
    return rows


def score_record(record):
    """Map each question or fixture id to True/False. A bad output file scores all False.

    A probe answer is right when an `accept` pattern matches and no `reject` pattern matches.
    """
    if record["method"] == "probes":
        answers = parse_answers(record["output_text"]) or {}

        def hit(patterns, answer):
            return any(re.search(p, answer, re.IGNORECASE | re.DOTALL) for p in patterns)

        return {
            p["id"]: hit(p["accept"], answers.get(p["id"], ""))
            and not hit(p.get("reject", []), answers.get(p["id"], ""))
            for p in PROBES[record["file"]]
        }
    rows = parse_classification(record["output_text"]) or {}
    return {
        f["id"]: rows.get(f["id"]) == tuple(f[k].lower() for k in FIELDS) for f in FIXTURES
    }


def _method_failures(records, method, path):
    """Return failed rule names for one method on one file."""
    by_arm = {arm: [score_record(r) for r in records
                    if r["method"] == method and r["file"] == path and r["arm"] == arm]
              for arm in ARMS}
    if not all(by_arm.values()):
        missing = [arm for arm in ARMS if not by_arm[arm]]
        return [f"missing {method} {'/'.join(missing)} arm"]
    # The thresholds hold only for TRIALS trials per arm. Do not apply them to other counts.
    if any(len(by_arm[arm]) != TRIALS for arm in ARMS):
        return ["unequal trials"]
    correct = {arm: sum(sum(s.values()) for s in by_arm[arm]) for arm in ARMS}
    failures = []
    if correct["rewritten"] < correct["original"] - AGGREGATE_SLACK:
        failures.append(f"aggregate-{method}")
    if method == "probes":
        for probe in PROBES[path]:
            hits = {arm: sum(s[probe["id"]] for s in by_arm[arm]) for arm in ARMS}
            if hits["original"] == TRIALS and hits["rewritten"] <= TRIALS - MEANING_DROP:
                failures.append(f"meaning-change {probe['id']}")
    return failures


def verdicts(records):
    lines = []
    for path in PILOT_FILES:
        failures = _method_failures(records, "probes", path)
        if path == INTAKE:
            failures += _method_failures(records, "workflow", path)
        lines.append(f"{path}: FAIL ({', '.join(failures)})" if failures else f"{path}: PASS")
    return lines


def parse_failures(records):
    if not records:
        return ["<no trials>"]
    parse = {"probes": parse_answers, "workflow": parse_classification}
    return [r.get("trial_id", "?") for r in records if parse[r["method"]](r["output_text"]) is None]


def decision_matches(decision_text, lines):
    """True when DECISION.md has exactly the scorer's verdict line for every pilot file."""
    found = {line.strip().lstrip("-* ").strip("`").strip() for line in decision_text.splitlines()}
    for path, expected in zip(PILOT_FILES, lines):
        if {line for line in found if line.startswith(f"{path}: ")} != {expected}:
            return False
    return True


def summarize(records):
    out = [f"trials={len(records)} cost_usd={sum(r.get('cost_usd') or 0 for r in records):.4f}"]
    for path in PILOT_FILES:
        methods = ("probes", "workflow") if path == INTAKE else ("probes",)
        for method in methods:
            for arm in ARMS:
                scores = [score_record(r) for r in records
                          if r["method"] == method and r["file"] == path and r["arm"] == arm]
                total = sum(len(s) for s in scores)
                out.append(f"{path} {method} {arm}: {sum(sum(s.values()) for s in scores)}/{total}")
    return "\n".join(out + verdicts(records)) + "\n"


def arm_text(arm, path, base):
    """Original arm: `git show <base>:<path>`. Rewritten arm: the working tree."""
    if arm == "original":
        return subprocess.run(["git", "show", f"{base}:{path}"], cwd=REPO, capture_output=True,
                              text=True, check=True).stdout
    return (REPO / path).read_text(encoding="utf-8")


def jobs(smoke):
    """Each job is (method, pilot file, arm, trial number)."""
    if smoke:
        return [("probes", INTAKE, "original", 1), ("workflow", INTAKE, "original", 1)]
    return [(method, path, arm, trial)
            for method, paths in (("probes", PILOT_FILES), ("workflow", (INTAKE,)))
            for path in paths for arm in ARMS for trial in range(1, TRIALS + 1)]


def build_fixture(job, trial_dir, base, smoke):
    method, path, arm, _ = job
    # In smoke mode both arms read the base, so the run does not depend on parallel edits.
    source_arm = "original" if smoke else arm
    for name in ((path,) if method == "probes" else WORKFLOW_FILES):
        target = trial_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(arm_text(source_arm, name, base), encoding="utf-8")
    if method == "probes":
        questions = "\n".join(f"{p['id']}. {p['question']}" for p in PROBES[path])
        return PROBE_PROMPT.format(trial_dir=trial_dir, path=path, questions=questions,
                                   first=PROBES[path][0]["id"])
    requests = "\n".join(f"{f['id']}. {f['request']}" for f in FIXTURES)
    return WORKFLOW_PROMPT.format(trial_dir=trial_dir, requests=requests)


def command(claude, prompt):
    return [claude, "-p", "--model", MODEL, "--safe-mode", "--tools", "Read,Write",
            "--permission-mode", "acceptEdits", "--output-format", "json",
            "--max-budget-usd", f"{TRIAL_CAP_USD:.2f}", "--no-session-persistence", prompt]


def trial_id(job):
    method, path, arm, trial = job
    name = pathlib.Path(path)
    return f"{method}-{name.parent.name if name.name == 'SKILL.md' else name.stem}-{arm}-{trial}"


def run_trial(claude, job, sandbox, base, smoke, output, timeout):
    tid = trial_id(job)
    trial_dir = (sandbox / tid).resolve()
    trial_dir.mkdir(parents=True)
    prompt = build_fixture(job, trial_dir, base, smoke)
    started = time.monotonic()
    try:
        done = subprocess.run(command(claude, prompt), cwd=trial_dir, capture_output=True,
                              text=True, timeout=timeout, check=False)
        cli = json.loads(done.stdout) if done.stdout.strip() else {}
        if isinstance(cli, list):
            cli = next((e for e in reversed(cli) if isinstance(e, dict) and e.get("type") == "result"), {})
        error = done.stderr[-4000:]
    except (json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        done, cli, error = None, {}, str(exc)
    # Score from the file on disk only, never from the reply text.
    out_name = "answers.json" if job[0] == "probes" else "classification.json"
    out_file = trial_dir / out_name
    text = out_file.read_text(encoding="utf-8") if out_file.is_file() else None
    if text is not None:
        (output / "trials" / tid).mkdir(parents=True, exist_ok=True)
        (output / "trials" / tid / out_name).write_text(text, encoding="utf-8")
    return {
        "trial_id": tid, "method": job[0], "file": job[1], "arm": job[2], "trial": job[3],
        "model_alias": MODEL, "duration_seconds": round(time.monotonic() - started, 3),
        "exit_code": done.returncode if done else None, "stderr": error,
        "response": cli.get("result") if isinstance(cli, dict) else None,
        "cost_usd": cli.get("total_cost_usd") if isinstance(cli, dict) else None,
        "model_usage": cli.get("modelUsage") if isinstance(cli, dict) else None,
        "output_text": text,
    }


def load_records(output):
    raw = output / "raw-results.jsonl"
    if not raw.is_file():
        raise SystemExit(f"missing raw results: {raw}")
    return [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines() if line.strip()]


def prior_spend(output):
    """Spend of every smoke run (runs/smoke*/) counts toward the pilot cap."""
    total = 0.0
    for raw in (HERE / "runs").glob("smoke*/raw-results.jsonl"):
        if raw.parent.resolve() != output.resolve():
            total += sum(json.loads(line).get("cost_usd") or 0
                         for line in raw.read_text(encoding="utf-8").splitlines() if line.strip())
    return total


def _probe_record(path, arm, answers):
    text = None if answers is None else json.dumps(answers)
    return {"method": "probes", "file": path, "arm": arm, "output_text": text}


def _workflow_record(arm, rows):
    text = None if rows is None else json.dumps(rows)
    return {"method": "workflow", "file": INTAKE, "arm": arm, "output_text": text}


def _gold_answers(path):
    return {probe["id"]: probe["gold"] for probe in PROBES[path]}


def _gold_rows():
    return {f["id"]: {k: f[k] for k in ("Lane", "Confidence", "Escalate")} for f in FIXTURES}


def _full_pilot(orig, rew, wf_orig=None, wf_rew=None):
    """Build 10 trials per arm per file. orig/rew map path -> list of 10 answer dicts."""
    records = []
    for path in PILOT_FILES:
        for arm, table in (("original", orig), ("rewritten", rew)):
            for answers in table.get(path, [_gold_answers(path)] * 10):
                records.append(_probe_record(path, arm, answers))
    for arm, rows in (("original", wf_orig), ("rewritten", wf_rew)):
        for row in rows or [_gold_rows()] * 10:
            records.append(_workflow_record(arm, row))
    return records


def selftest() -> int:
    checks = []

    def check(name, condition):
        checks.append((name, bool(condition)))

    # Data files have the agreed shape and each gold answer passes its own accept pattern.
    for path, probes in PROBES.items():
        check(f"8 probes for {path}", len(probes) == 8)
        check(f">=4 hard probes for {path}", sum(p["hard"] for p in probes) >= 4)
        for probe in probes:
            check(f"gold matches accept {probe['id']}", score_record(
                _probe_record(path, "original", {probe["id"]: probe["gold"]})
            )[probe["id"]])
            for answer in probe.get("accept_examples", []):
                check(f"accept example {probe['id']}: {answer}", score_record(
                    _probe_record(path, "original", {probe["id"]: answer})
                )[probe["id"]])
            for answer in probe.get("reject_examples", []):
                check(f"reject example {probe['id']}: {answer}", not score_record(
                    _probe_record(path, "original", {probe["id"]: answer})
                )[probe["id"]])
    rejects = {p["id"]: p.get("reject_examples", []) for ps in PROBES.values() for p in ps}
    check("reject examples cover S8 S2 F6 F7 S4",
          all(rejects[i] for i in ("S8", "S2", "F6", "F7", "S4")))
    check("S8 'any commit' listed", "any commit" in rejects["S8"])
    check("S2 negatives listed", {"when runtime/resume_decision.py is missing or exits non-zero",
                                  "when .claude/runtime is missing"} <= set(rejects["S2"]))
    check("F6 negative listed", "notify the user and proceed" in rejects["F6"])
    check("S4 don't stop listed", "don't stop" in rejects["S4"])
    accepts = {p["id"]: p.get("accept_examples", []) for ps in PROBES.values() for p in ps}
    check("S2 positives listed", {"only when the source file is absent, never on a non-zero exit",
                                  "when runtime/resume_decision.py is not found"} <= set(accepts["S2"]))
    check("S8 positive listed", "any code commit after the review" in accepts["S8"])
    check("8 fixtures", len(FIXTURES) == 8)
    cases = {f["Lane"] for f in FIXTURES} | {f["Confidence"] for f in FIXTURES}
    check("fixtures cover lanes and low", {"tiny", "normal", "high-risk", "low"} <= cases)
    check("fixtures cover a hard gate", any("hard gate" in f["case"] for f in FIXTURES))

    # Parsing.
    check("answers parse", parse_answers('{"O1": "x"}') == {"O1": "x"})
    check("answers not object", parse_answers("[1]") is None)
    check("answers bad json", parse_answers("{nope") is None)
    check("answers missing", parse_answers(None) is None)
    check("classification parse", parse_classification(
        '{"R1": {"Lane": " Tiny", "Confidence": "HIGH", "Escalate": "Yes (hard gate)"}}'
    ) == {"R1": ("tiny", "high", "yes")})
    check("classification bad", parse_classification('{"R1": "tiny"}') is None)

    # Probe scoring: pattern match, wrong answer, and a missing file scores all wrong.
    orch = "rules/orchestration.md"
    scored = score_record(_probe_record(orch, "original", {"O2": "Only warns", "O5": "proceed"}))
    check("probe right", scored["O2"] is True)
    check("probe wrong", scored["O5"] is False)
    check("probe absent key wrong", scored["O1"] is False)
    missing = score_record(_probe_record(orch, "original", None))
    check("missing file all wrong", len(missing) == 8 and not any(missing.values()))
    bad = score_record({**_probe_record(orch, "original", None), "output_text": "{oops"})
    check("unparsable file all wrong", len(bad) == 8 and not any(bad.values()))

    # Workflow scoring: an answer is right only when all three fields match.
    rows = _gold_rows()
    rows["R1"] = {**rows["R1"], "Escalate": "yes"}
    wf = score_record(_workflow_record("original", rows))
    check("workflow one field off is wrong", wf["R1"] is False and wf["R2"] is True)
    check("workflow missing all wrong", not any(score_record(_workflow_record("original", None)).values()))

    # Pass rule.
    all_pass = verdicts(_full_pilot({}, {}))
    check("all pass", all_pass == [f"{p}: PASS" for p in PILOT_FILES])

    def wrong(path, ids, count):
        """10 trials, the first `count` of which answer `ids` wrong."""
        out = []
        for trial in range(10):
            answers = _gold_answers(path)
            if trial < count:
                for probe_id in ids:
                    answers[probe_id] = "zzz"
            out.append(answers)
        return out

    sdd = "skills/subagent-driven-development/SKILL.md"
    # Rewritten loses 2 answers on two probes: aggregate 80 vs 78 passes, no 10/10 -> <=7/10.
    check("minus 2 passes", verdicts(_full_pilot({}, {sdd: wrong(sdd, ["S1", "S2"], 1)}))[2] == f"{sdd}: PASS")
    # Rewritten loses 3 answers spread over 3 probes: aggregate fails.
    check("minus 3 fails aggregate", verdicts(_full_pilot({}, {sdd: wrong(sdd, ["S1", "S2", "S3"], 1)}))[2]
          == f"{sdd}: FAIL (aggregate-probes)")
    # Original loses 3 elsewhere, so the aggregate holds, but S4 drops 10/10 -> 7/10.
    lines = verdicts(_full_pilot({sdd: wrong(sdd, ["S1"], 3)}, {sdd: wrong(sdd, ["S4"], 3)}))
    check("meaning change fails", lines[2] == f"{sdd}: FAIL (meaning-change S4)")
    # 10/10 -> 8/10 is not a meaning change.
    lines = verdicts(_full_pilot({sdd: wrong(sdd, ["S1"], 2)}, {sdd: wrong(sdd, ["S4"], 2)}))
    check("8/10 is not a meaning change", lines[2] == f"{sdd}: PASS")
    # A single miss at ceiling fails neither rule.
    check("single miss passes", verdicts(_full_pilot({}, {orch: wrong(orch, ["O1"], 1)}))[0] == f"{orch}: PASS")
    # feature-intake: probes pass, workflow fails -> FAIL (mixed result is a fail).
    bad_rows = [_gold_rows() for _ in range(10)]
    for trial in range(3):
        bad_rows[trial]["R1"] = {**bad_rows[trial]["R1"], "Lane": "normal"}
    lines = verdicts(_full_pilot({}, {}, wf_rew=bad_rows))
    check("intake mixed fails", lines[1] == f"{INTAKE}: FAIL (aggregate-workflow)")
    check("workflow does not affect others", lines[0] == f"{orch}: PASS")
    # A missing rewritten output file costs all 8 answers for that trial.
    rew = [_gold_answers(orch)] * 9 + [None]
    check("missing trial counts wrong", verdicts(_full_pilot({}, {orch: rew}))[0] == f"{orch}: FAIL (aggregate-probes)")
    # No trials for an arm cannot pass.
    only_orig = [r for r in _full_pilot({}, {}) if r["arm"] == "original"]
    check("missing arm fails", verdicts(only_orig)[0].startswith(f"{orch}: FAIL (missing"))
    # Trial counts other than TRIALS per arm fail with a named rule, not a generalized threshold.
    short = [_gold_answers(orch)] * 9
    check("unequal trials fails", verdicts(_full_pilot({}, {orch: short}))[0]
          == f"{orch}: FAIL (unequal trials)")
    check("unequal trials both arms", verdicts(_full_pilot({orch: short}, {orch: short}))[0]
          == f"{orch}: FAIL (unequal trials)")

    # --check-parse.
    check("check-parse clean", parse_failures(_full_pilot({}, {})) == [])
    broken = _full_pilot({}, {}) + [{**_probe_record(orch, "rewritten", None), "trial_id": "x"}]
    check("check-parse finds missing", parse_failures(broken) == ["x"])
    check("check-parse empty fails", parse_failures([]) == ["<no trials>"])

    # --check-decision.
    good = ["rules/orchestration.md: PASS", f"{INTAKE}: FAIL (aggregate-workflow)", f"{sdd}: PASS"]
    doc = "# Decision\n\n- rules/orchestration.md: PASS\n" + f"`{INTAKE}: FAIL (aggregate-workflow)`\n{sdd}: PASS\n"
    check("decision matches", decision_matches(doc, good))
    check("decision mismatch", not decision_matches(doc.replace("FAIL (aggregate-workflow)", "PASS"), good))
    check("decision missing line", not decision_matches("# Decision\n", good))

    failed = [name for name, ok in checks if not ok]
    for name in failed:
        print(f"FAIL {name}")
    print(f"selftest: {len(checks) - len(failed)}/{len(checks)} passed")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="run the scorer self-test")
    parser.add_argument("--dry-run", action="store_true",
                        help="build one fixture directory and print the command; no CLI call")
    parser.add_argument("--smoke", action="store_true",
                        help="one real trial per method, both reading --base")
    parser.add_argument("--score-only", action="store_true",
                        help="re-derive results.txt from <output>/raw-results.jsonl")
    parser.add_argument("--check-parse", action="store_true",
                        help="exit 1 when any stored trial output is missing or does not parse")
    parser.add_argument("--check-decision", type=pathlib.Path, metavar="DECISION.md",
                        help="exit 1 unless the file has the scorer's verdict line per pilot file")
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--base", help="git sha for the original arm")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if args.output is None:
        parser.error("--output is required")
    if args.check_parse:
        bad = parse_failures(load_records(args.output))
        for tid in bad:
            print(f"unparsable or missing output: {tid}")
        print(f"check-parse: {'FAIL' if bad else 'OK'}")
        return 1 if bad else 0
    if args.check_decision:
        lines = verdicts(load_records(args.output))
        ok = decision_matches(args.check_decision.read_text(encoding="utf-8"), lines)
        print("\n".join(lines))
        print(f"check-decision: {'OK' if ok else 'FAIL'}")
        return 0 if ok else 1
    if args.score_only:
        result = summarize(load_records(args.output))
        (args.output / "results.txt").write_text(result, encoding="utf-8")
        print(result, end="")
        return 0
    if not args.base:
        parser.error("--base is required to run trials")
    base = subprocess.run(["git", "rev-parse", "--verify", f"{args.base}^{{commit}}"], cwd=REPO,
                          capture_output=True, text=True, check=True).stdout.strip()
    if args.dry_run:
        job = jobs(smoke=False)[0]
        trial_dir = (args.output / trial_id(job)).resolve()
        if trial_dir.exists():
            shutil.rmtree(trial_dir)
        trial_dir.mkdir(parents=True)
        print(f"fixture: {trial_dir}")
        print(shlex.join(command("claude", build_fixture(job, trial_dir, base, False))))
        return 0

    claude = shutil.which("claude")
    if not claude:
        parser.error("claude CLI is required")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error(f"output directory is not empty: {args.output}")
    args.output.mkdir(parents=True, exist_ok=True)
    selected = jobs(args.smoke)
    spent = prior_spend(args.output)
    protocol = {
        "claude_cli": subprocess.run([claude, "--version"], capture_output=True, text=True,
                                     check=True).stdout.strip(),
        "base": base, "model": MODEL, "smoke": args.smoke, "launch_count": len(selected),
        "trial_cap_usd": TRIAL_CAP_USD, "pilot_cap_usd": PILOT_CAP_USD, "prior_spend_usd": spent,
        "command": command("claude", "<prompt>"),
        "isolation": "fresh temp directory per trial; safe-mode; no session persistence",
    }
    (args.output / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")

    records = []
    with tempfile.TemporaryDirectory(prefix="ste-pilot-") as temporary, \
            concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        # Launch in batches. Stop before a batch whose worst case passes the pilot cap.
        for start in range(0, len(selected), args.concurrency):
            batch = selected[start:start + args.concurrency]
            cost = spent + sum(r.get("cost_usd") or 0 for r in records)
            if cost + len(batch) * TRIAL_CAP_USD > PILOT_CAP_USD:
                print(f"budget stop: spent ${cost:.2f}; {len(selected) - start} trials not launched")
                break
            futures = [pool.submit(run_trial, claude, job, pathlib.Path(temporary), base,
                                   args.smoke, args.output, args.timeout) for job in batch]
            for future in concurrent.futures.as_completed(futures):
                record = future.result()
                records.append(record)
                print(f"[{len(records):02d}/{len(selected)}] {record['trial_id']} "
                      f"exit={record['exit_code']} cost={record['cost_usd']}", flush=True)
    records.sort(key=lambda r: r["trial_id"])
    (args.output / "raw-results.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8")
    result = summarize(records)
    (args.output / "results.txt").write_text(result, encoding="utf-8")
    print(result, end="")
    return 0 if records and all(r["exit_code"] == 0 for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
