#!/usr/bin/env python3
"""A/B the real review prompts of two git revisions on the review-chain and task-review fixtures.

`run` extracts each revision's rules/skills/agents and its own prompt renderer, builds the finder (one call per
angle), intent, audit and task-reviewer prompts from that revision's files, and runs each one as an isolated
`claude -p` call (Read only, safe mode, a fresh temporary working directory holding the arm's rules/ and the
fixture's package). Every call is recorded once under OUT/runs/ and never overwritten or rerun.
`report` summarizes the records and scores them with the existing scorers.
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_review_chain_eval as scorer  # noqa: E402
import score_task_review_eval as task_scorer  # noqa: E402

ARMS = ("base", "head")
KINDS = ("finder", "intent", "audit", "task")
ORACLE = {"finder": "correctness", "intent": "intent", "audit": "context-propagation-audit"}
ARM_PATHS = ("rules", "skills", "agents", "scripts/render_skill_prompt.py")
OUTPUT_REQUEST = (
    "\n\n## Machine-readable output for this evaluation\n\n"
    "End your reply with your findings as a JSON array inside one fenced ```json block. Each finding is "
    '{"oracle": "%s", "class": str, "file": str, "line": int|null, "confidence": int, "summary": str}, '
    "with confidence from 0 to 100. Use class `unknown` for anything you cannot confirm from the diff alone "
    "(for example a symbol defined outside it). Return an empty array if you find nothing. Your usual report "
    "format may precede the block.\n")
TASK_ADAPTER = (
    "\n\nThe fixture statements are the complete provided evidence: do not demand files that the fixture does "
    "not claim to provide. Use `cannot_verify` only when the fixture explicitly says an external contract is "
    "unavailable.\n")
TASK_PACKAGE = "# Review package\n\nNo diff exists for this fixture. The implementer report is the only evidence.\n"


class EvalError(Exception):
    """A one-line, user-facing problem; main() prints it and exits 1."""


def git(repo: Path, *args: str, binary: bool = False):
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=not binary)
    if proc.returncode != 0:
        err = proc.stderr if not binary else proc.stderr.decode(errors="replace")
        raise EvalError(f"git {' '.join(args[:2])} failed: {err.strip().splitlines()[-1] if err.strip() else proc.returncode}")
    return proc.stdout


def toplevel() -> Path:
    return Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip())


def extract_arm(repo: Path, rev: str, dest: Path) -> None:
    data = git(repo, "archive", "--format=tar", rev, *ARM_PATHS, binary=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(dest, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))


# ---- prompt building (placeholders copied verbatim from the reference driver) ----

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EvalError(f"cannot read {path}: {exc.strerror}") from None


def render(tree: Path, fragments: list[str]) -> str:
    """Run the arm's own renderer from the arm's own tree (its --root does not select fragments)."""
    cmd = [sys.executable, "scripts/render_skill_prompt.py"]
    for fragment in fragments:
        cmd += ["--fragment", fragment]
    proc = subprocess.run(cmd, cwd=tree, capture_output=True, text=True)
    if proc.returncode != 0:
        raise EvalError(f"{tree.name} arm: render_skill_prompt.py failed: {proc.stderr.strip()}")
    return proc.stdout


def dispatch_block(tree: Path, rel: str) -> str:
    match = re.search(r"\n  prompt: \|\n(.*?)\n```", read(tree / rel), re.S)
    if not match:
        raise EvalError(f"{tree.name} arm: {rel} has no `  prompt: |` dispatch block ending at a closing fence")
    return textwrap.dedent(match.group(1))


def replace_once(text: str, old: str, new: str, where: str) -> str:
    if text.count(old) != 1:
        raise EvalError(f"{where}: expected exactly one {old!r}")
    return text.replace(old, new)


def package_text(diff: str) -> tuple[list[str], str]:
    paths = sorted(scorer.diff_paths(diff))
    return paths, ("# Review package (fixture)\n\nRange: fixture-base..fixture-head\n\nFiles changed:\n"
                   + "".join(f"- {p}\n" for p in paths) + "\n## Diff\n\n" + diff)


def build(tree: Path, kind: str, fixture_dir: Path, angle: str) -> tuple[str, dict[str, str]]:
    """Return (prompt, files to place in the call's cwd). Reads only the fixture's input files, never truth.*."""
    if kind == "task":
        body = read(fixture_dir / "input.md")
        parts = re.split(r"\n(?=# Implementation)", body.strip(), maxsplit=1)
        rel = "skills/subagent-driven-development/task-reviewer-prompt.md"
        block = dispatch_block(tree, rel)
        for key, name in (("TASK_BRIEF_PATH", "brief.md"), ("IMPLEMENTER_REPORT_PATH", "report.md"),
                          ("REVIEW_PACKAGE_PATH", "package.md")):
            block = replace_once(block, f"- {key}: <path>", f"- {key}: {name}", f"{tree.name} arm: {rel}")
        files = {"brief.md": parts[0] + "\n", "report.md": (parts[1] if len(parts) > 1 else "") + "\n",
                 "package.md": TASK_PACKAGE}
        return block + TASK_ADAPTER, files
    diff = read(fixture_dir / "diff.patch")
    intent = read(fixture_dir / "intent.md")
    paths, package = package_text(diff)
    files = {"package.md": package}
    if kind == "finder":
        text = render(tree, ["skills/correctness-review/prompts/shared.md",
                             f"skills/correctness-review/prompts/angles/{angle}.md"])
        for old, new in (("- BASE_SHA: [commit before the first task]", "- BASE_SHA: fixture-base"),
                         ("- HEAD_SHA: [current commit after all tasks]", "- HEAD_SHA: fixture-head"),
                         ("- Files touched: [list of paths]", "- Files touched: " + ", ".join(paths)),
                         ('- REVIEW_PACKAGE_PATH: [the SDD-generated mechanical review package, or "none"]',
                          "- REVIEW_PACKAGE_PATH: package.md")):
            text = replace_once(text, old, new, f"{tree.name} arm: skills/correctness-review/prompts/shared.md")
        return text + OUTPUT_REQUEST % "correctness", files
    if kind == "intent":
        rel = "skills/intent-review/intent-reviewer-prompt.md"
        block = dispatch_block(tree, rel)
        inputs = ("## Inputs\n\n- INTENT (the oracle: the user's original request, VERBATIM):\n"
                  + textwrap.indent(intent.strip(), "  ") + "\n- SUCCESS CRITERIA (secondary oracle): none\n"
                  "- PLAN §3 SC TABLE (secondary oracle): none\n- SUMMARY ### Verify TABLE: none\n"
                  "- BASE_SHA: fixture-base\n- HEAD_SHA: fixture-head\n- Files touched: " + ", ".join(paths)
                  + "\n- REVIEW_PACKAGE_PATH: package.md\n\n")
        block, n = re.subn(r"## Inputs\n\n.*?\n\n(?=When `REVIEW_PACKAGE_PATH`)", lambda _: inputs, block,
                           count=1, flags=re.S)
        if n != 1:
            raise EvalError(f"{tree.name} arm: {rel} has no `## Inputs` block followed by `When \\`REVIEW_PACKAGE_PATH\\``")
        return block + OUTPUT_REQUEST % "intent", files
    # audit
    skill = read(tree / "skills/context-propagation-audit/SKILL.md")
    body = re.sub(r"\A---\n.*?\n---\n", "", skill, count=1, flags=re.S)
    prompt = (body + "\n\n## Change under audit\n\nThe change is the diff in package.md (range fixture-base..fixture-head). "
              "Its stated purpose:\n\n" + textwrap.indent(intent.strip(), "  ") + "\n\nRun the audit on this change and report "
              "every failed delivery row.\n")
    return prompt + OUTPUT_REQUEST % "context-propagation-audit", files


# ---- the call ----

def claude_flags(args) -> list[str]:
    return ["--safe-mode", "--tools", "Read", "--allowedTools", "Read", "--model", args.model, "--effort", args.effort,
            "--max-budget-usd", str(args.max_call_usd), "--output-format", "stream-json", "--verbose",
            "--no-session-persistence"]


def call_claude(claude: str, flags: list[str], prompt: str, cwd: str, timeout: float = 900.0) -> dict:
    start = time.monotonic()
    try:
        proc = subprocess.run([claude, "-p", prompt, *flags], cwd=cwd, text=True, capture_output=True,
                              timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"rc": "timeout", "elapsed": round(time.monotonic() - start, 1), "text": "", "reads": [],
                "denials": [], "cost": 0.0, "usage": {}}
    except OSError as exc:
        return {"rc": "not-run", "elapsed": 0.0, "text": "", "reads": [], "denials": [], "cost": 0.0, "usage": {},
                "stderr": str(exc)}
    reads, result = [], {}
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "assistant":
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Read":
                    reads.append((block.get("input") or {}).get("file_path", ""))
        elif event.get("type") == "result":
            result = event
    return {"rc": proc.returncode, "elapsed": round(time.monotonic() - start, 1),
            "text": result.get("result") or "", "reads": reads,
            "denials": [(d.get("tool_input") or {}).get("file_path", "") for d in result.get("permission_denials") or []],
            "cost": result.get("total_cost_usd") or 0.0, "usage": result.get("usage") or {},
            "turns": result.get("num_turns"), "error": result.get("is_error"), "stderr": proc.stderr.strip()[-300:]}


# ---- run ----

def fixture_dirs(root: Path, marker: str) -> list[Path]:
    if not root.is_dir():
        raise EvalError(f"fixtures directory not found: {root}")
    return sorted(p for p in root.iterdir() if (p / marker).is_file())


def plan_jobs(args, trees: dict[str, Path]) -> list[tuple]:
    kinds = [k for k in KINDS if k in args.kinds]
    review = fixture_dirs(args.review_fixtures, "diff.patch") if set(kinds) - {"task"} else []
    tasks = fixture_dirs(args.task_fixtures, "input.md") if "task" in kinds else []
    if args.only_fixture:
        known = {p.name for p in review + tasks}
        unknown = [name for name in args.only_fixture if name not in known]
        if unknown:
            raise EvalError(f"--only-fixture {unknown[0]} is not a fixture of the selected kinds ({', '.join(kinds)})")
        review = [p for p in review if p.name in args.only_fixture]
        tasks = [p for p in tasks if p.name in args.only_fixture]
    angles = {}
    for arm, tree in trees.items():
        try:
            angles[arm] = json.loads(read(tree / "skills/correctness-review/review-config.json"))["finder_angles"]
        except (ValueError, KeyError, TypeError):
            raise EvalError(f"{arm} arm: skills/correctness-review/review-config.json has no finder_angles list") from None
    jobs = []
    for fixture in review:
        if "finder" in kinds:
            for i in range(max(len(a) for a in angles.values())):
                jobs += [(arm, "finder", fixture, angles[arm][i]) for arm in ARMS if i < len(angles[arm])]
        if "intent" in kinds:
            jobs += [(arm, "intent", fixture, "-") for arm in ARMS]
        if "audit" in kinds and scorer.load_truth(fixture)["expected_oracle"] == "context-propagation-audit":
            jobs += [(arm, "audit", fixture, "-") for arm in ARMS]
    for fixture in tasks:
        jobs += [(arm, "task", fixture, "-") for arm in ARMS]
    return jobs


def write_meta(out: Path, meta: dict) -> None:
    path = out / "meta.json"
    if path.exists():
        try:
            old = json.loads(path.read_text())
        except ValueError:
            raise EvalError(f"{path} is not valid JSON") from None
        if old != meta:
            diff = sorted(k for k in set(old) | set(meta) if old.get(k) != meta.get(k))
            raise EvalError(f"{path} differs from this run ({', '.join(diff)}); use another --out directory")
        return
    path.write_text(json.dumps(meta, indent=1) + "\n")


def cmd_run(args) -> int:
    repo = (args.repo or toplevel()).resolve()
    args.review_fixtures = args.review_fixtures or repo / "evals/skills/review-chain/fixtures"
    args.task_fixtures = args.task_fixtures or repo / "evals/skills/task-review/fixtures"
    args.kinds = [k.strip() for k in args.kinds.split(",") if k.strip()]
    bad = [k for k in args.kinds if k not in KINDS]
    if bad or not args.kinds:
        raise EvalError(f"--kinds must be a comma-separated subset of {','.join(KINDS)}")
    revs = {"base": git(repo, "rev-parse", "--verify", f"{args.base_rev}^{{commit}}").strip(),
            "head": git(repo, "rev-parse", "--verify", f"{args.head_rev}^{{commit}}").strip()}
    flags = claude_flags(args)
    out = args.out
    runs = out / "runs"
    with tempfile.TemporaryDirectory(prefix="review-prompt-eval-arms-") as arms_dir:
        trees = {}
        for arm in ARMS:
            trees[arm] = Path(arms_dir) / arm
            extract_arm(repo, revs[arm], trees[arm])
        jobs = plan_jobs(args, trees)
        # Build every prompt before the first call, so a prompt-shape error costs nothing.
        built = [(arm, kind, fixture.name, angle, *build(trees[arm], kind, fixture, angle))
                 for arm, kind, fixture, angle in jobs]
        runs.mkdir(parents=True, exist_ok=True)
        write_meta(out, {"base_rev": revs["base"], "head_rev": revs["head"], "model": args.model,
                         "effort": args.effort, "claude_flags": flags})
        lock = threading.Lock()
        state = {"spent": 0.0, "ran": 0, "recorded": 0, "capped": 0}

        def run_job(item):
            arm, kind, fixture, angle, prompt, files = item
            name = f"{arm}__{kind}__{fixture}__{angle}__a{args.attempt}"
            path = runs / f"{name}.json"
            if path.exists():
                with lock:
                    state["recorded"] += 1
                print(f"{name}: already recorded; not rerun", flush=True)
                return
            with lock:
                if state["spent"] >= args.max_total_usd:
                    state["capped"] += 1
                    print(f"{name}: budget cap reached (${state['spent']:.2f} of ${args.max_total_usd:.2f}); not run",
                          flush=True)
                    return
            cwd = tempfile.mkdtemp(prefix="review-prompt-eval-call-")
            try:
                shutil.copytree(trees[arm] / "rules", Path(cwd) / "rules")
                for fname, content in files.items():
                    (Path(cwd) / fname).write_text(content, encoding="utf-8")
                attempts = []
                for _ in range(2):
                    result = call_claude(args.claude, flags, prompt, cwd)
                    attempts.append({k: v for k, v in result.items() if k != "text"} | {"chars": len(result["text"])})
                    with lock:
                        state["spent"] += result["cost"]
                    if result["text"] or result["rc"] == 0:
                        break  # only a call that failed to run at all (rc != 0, no text) is retried, once
            finally:
                shutil.rmtree(cwd, ignore_errors=True)
            record = {"job": {"arm": arm, "kind": kind, "fixture": fixture, "angle": angle, "attempt": args.attempt},
                      "prompt_words": len(prompt.split()), "attempts": attempts,
                      **result, "cost": sum(a["cost"] for a in attempts)}
            try:
                with open(path, "x", encoding="utf-8") as handle:
                    json.dump(record, handle, indent=1)
            except FileExistsError:
                print(f"{name}: recorded concurrently by another run; this result discarded", flush=True)
                return
            with lock:
                state["ran"] += 1
                spent = state["spent"]
            print(f"{name}: rc={result['rc']} {result['elapsed']}s ${record['cost']:.3f} reads={len(result['reads'])} "
                  f"total=${spent:.2f}", flush=True)

        print(f"{len(built)} calls planned, workers={args.workers}, cap=${args.max_total_usd:.2f}", flush=True)
        with ThreadPoolExecutor(args.workers) as pool:
            list(pool.map(run_job, built))
    print(f"done: {state['ran']} run, {state['recorded']} already recorded, {state['capped']} not run (budget cap); "
          f"spent ${state['spent']:.2f}", flush=True)
    return 0


# ---- report ----

def load_records(out: Path) -> list[dict]:
    runs = out / "runs"
    if not runs.is_dir():
        raise EvalError(f"no records: {runs} does not exist")
    records = []
    for path in sorted(runs.glob("*.json")):
        try:
            records.append(json.loads(path.read_text()))
        except ValueError:
            raise EvalError(f"{path} is not valid JSON") from None
    if not records:
        raise EvalError(f"no records under {runs}")
    return records


def parseable(text: str) -> list[dict] | None:
    """The findings of a reply with a JSON block that parses as a list; None when there is no such block."""
    findings, blocks = scorer.parse_findings(text)
    return findings if findings is not None and blocks else None


def watch_hit(record: dict, watch: str) -> bool:
    return any(p == watch or p.endswith("/" + watch) for p in record.get("reads") or [])


def report_calls(by_arm: dict, watch: str) -> None:
    for arm, items in by_arm.items():
        json_calls = [r for r in items if r["job"]["kind"] != "task"]
        ok = sum(1 for r in json_calls if parseable(r.get("text") or "") is not None)
        denied = [r for r in items if r.get("denials")]
        cost = sum(r.get("cost") or 0.0 for r in items)
        tokens = sum(int((r.get("usage") or {}).get("output_tokens") or 0) for r in items)
        print(f"== {arm}: calls {len(items)}; parseable JSON block: {ok}/{len(json_calls)}; cost ${cost:.2f}; "
              f"output tokens {tokens}")
        for kind in KINDS:
            sub = [r for r in items if r["job"]["kind"] == kind]
            if sub:
                print(f"  read {watch} - {kind}: {sum(watch_hit(r, watch) for r in sub)}/{len(sub)}")
        paths = sorted({p for r in denied for p in r["denials"]})
        print(f"  permission denials: {len(denied)} call(s)" + (f" ({', '.join(paths)})" if paths else ""))


def report_review_chain(out: Path, by_arm: dict, fixtures: Path, meta: dict) -> None:
    for arm, items in by_arm.items():
        cases: dict = {}
        for r in items:
            job = r["job"]
            if job["kind"] == "task" or job["attempt"] != 1:
                continue
            case = cases.setdefault(job["fixture"], {"rc": 0, "elapsed": 0.0, "findings": [], "ok": 0, "bad": 0,
                                                     "usage": collections.Counter()})
            case["elapsed"] += r.get("elapsed") or 0.0
            for _, key in scorer.TOKEN_KEYS:
                case["usage"][key] += int((r.get("usage") or {}).get(key) or 0)
            if r.get("rc") != 0 and case["rc"] == 0:
                case["rc"] = r.get("rc")
            findings = parseable(r.get("text") or "")
            if findings is None:
                case["bad"] += 1
                continue
            case["ok"] += 1
            case["findings"] += [dict(f, oracle=ORACLE[job["kind"]]) for f in findings]
        if not cases:
            continue
        result = {"model": meta.get("model"), "effort": meta.get("effort"), "client": "claude-code", "cases": {}}
        for name, case in sorted(cases.items()):
            # A fixture none of whose calls produced a parseable block is written so the scorer reads it as unparseable.
            block = json.dumps(case["findings"]) if case["ok"] else f"(no parseable block in {case['bad']} call(s))"
            result["cases"][name] = {"rc": case["rc"], "elapsed": round(case["elapsed"], 1),
                                     "result": "```json\n" + block + "\n```", "usage": dict(case["usage"])}
        path = out / f"result-{arm}.json"
        path.write_text(json.dumps(result, indent=1) + "\n")
        with tempfile.TemporaryDirectory(prefix="review-prompt-eval-score-") as tmp:
            for name in cases:  # score only the fixtures that have records
                if (fixtures / name).is_dir():
                    os.symlink((fixtures / name).resolve(), Path(tmp) / name)
            warnings: list[str] = []
            try:
                totals, lines = scorer.score(result, Path(tmp), 75, warnings)
            except scorer.EvalError as exc:
                raise EvalError(f"scoring {path.name}: {exc}") from None
        print(f"== {arm}: review-chain score (attempt 1, {path})")
        for line in lines + [f"warning: {w}" for w in warnings]:
            print(f"  {line}")
        print(f"  core catches {totals['core_caught']}/{totals['core']}; bonus catches {totals['bonus_caught']}; "
              f"false positives {totals['fp']} (>=75: {totals['fp_at_threshold']}); other {totals['other']}; "
              f"errored {totals['errored']}; unparseable {totals['unparseable']}")


def report_tasks(by_arm: dict, fixtures: Path) -> None:
    tasks = sorted({r["job"]["fixture"] for items in by_arm.values() for r in items if r["job"]["kind"] == "task"})
    if not tasks:
        return
    print("== task review")
    for name in tasks:
        try:
            truth = json.loads((fixtures / name / "truth.json").read_text())
            required, forbidden = set(truth["required"]), set(truth["forbidden"])
        except (OSError, ValueError, KeyError, TypeError):
            raise EvalError(f"{fixtures / name / 'truth.json'} is missing or has no required/forbidden lists") from None
        for arm, items in by_arm.items():
            for r in sorted((r for r in items if r["job"]["kind"] == "task" and r["job"]["fixture"] == name),
                            key=lambda r: r["job"]["attempt"]):
                seen = task_scorer.labels([r.get("text") or ""])
                holds = required <= seen and not forbidden & seen
                print(f"  {name} {arm} a{r['job']['attempt']}: labels [{', '.join(sorted(seen))}]; "
                      f"requirements hold: {'yes' if holds else 'no'}")


def cmd_report(args) -> int:
    out = args.out
    try:
        meta = json.loads((out / "meta.json").read_text())
    except (OSError, ValueError):
        raise EvalError(f"{out / 'meta.json'} is missing or not valid JSON") from None
    records = load_records(out)
    by_arm = {arm: [r for r in records if r["job"]["arm"] == arm] for arm in ARMS}
    kinds = {r["job"]["kind"] for r in records}
    review_fixtures = args.review_fixtures
    task_fixtures = args.task_fixtures
    if (review_fixtures is None and kinds - {"task"}) or (task_fixtures is None and "task" in kinds):
        root = toplevel()
        review_fixtures = review_fixtures or root / "evals/skills/review-chain/fixtures"
        task_fixtures = task_fixtures or root / "evals/skills/task-review/fixtures"
    report_calls(by_arm, args.watch_path)
    if kinds - {"task"}:
        report_review_chain(out, by_arm, review_fixtures, meta)
    if "task" in kinds:
        report_tasks(by_arm, task_fixtures)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run the A/B calls (each call recorded once, never rerun)")
    run.add_argument("--base-rev", required=True)
    run.add_argument("--head-rev", required=True)
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--repo", type=Path, help="git repository holding both revisions (default: current toplevel)")
    run.add_argument("--kinds", default="finder,intent,audit,task", help="comma-separated subset of %(default)s")
    run.add_argument("--only-fixture", action="append", default=[], metavar="NAME", help="repeatable")
    run.add_argument("--attempt", type=int, default=1, help="attempt number in the record name (default 1)")
    run.add_argument("--model", default="claude-opus-5-5")
    run.add_argument("--effort", default="medium")
    run.add_argument("--claude", default="claude", metavar="CMD", help="claude executable (default: claude)")
    run.add_argument("--workers", type=int, default=4)
    run.add_argument("--max-call-usd", type=float, default=1.5, help="--max-budget-usd passed to each call")
    run.add_argument("--max-total-usd", type=float, default=20.0,
                     help="stop starting new calls once this invocation has spent this much")
    rep = sub.add_parser("report", help="summarize and score the recorded calls")
    rep.add_argument("--out", type=Path, required=True)
    for p in (run, rep):
        p.add_argument("--review-fixtures", type=Path, help="default: evals/skills/review-chain/fixtures")
        p.add_argument("--task-fixtures", type=Path, help="default: evals/skills/task-review/fixtures")
        p.add_argument("--watch-path", default="rules/review-policy.md",
                       help="report the share of calls that Read this path (default: %(default)s)")
    args = parser.parse_args()
    try:
        if args.command == "run":
            if args.workers < 1 or args.attempt < 1:
                raise EvalError("--workers and --attempt must be at least 1")
            return cmd_run(args)
        return cmd_report(args)
    except (EvalError, scorer.EvalError) as exc:
        print(f"review-prompt-eval: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
