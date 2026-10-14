"""Tests for run_review_prompt_eval.py. No model call: every call goes to a stub `claude`."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
TOOL = str(SCRIPTS / "run_review_prompt_eval.py")
SENTINEL = "ANSWER-KEY-SENTINEL"
HEAD_ONLY = "HEAD-ONLY-SENTINEL"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]

# The stub appends one JSON line per call (argv, cwd, every file in cwd with its text), then emits stream-json:
# one assistant Read of stub.json's `read` path and a final result event with the configured reply/cost/denials.
STUB = """#!{python}
import json, os, sys
from pathlib import Path
here = Path({here!r})
cfg = json.loads((here / "stub.json").read_text())
files = {{str(p): p.read_text() for p in Path(".").rglob("*") if p.is_file()}}
with open(here / "calls.jsonl", "a") as log:
    log.write(json.dumps({{"argv": sys.argv[1:], "cwd": os.getcwd(), "files": files}}) + "\\n")
prompt = sys.argv[sys.argv.index("-p") + 1]
if any(all(s in prompt for s in group) for group in cfg.get("fail_when", [])):
    sys.exit(1)  # failed to run: non-zero exit, no output
if cfg.get("bad_utf8"):
    sys.stdout.buffer.write(b"\\xff\\xfe not utf-8\\n")
    sys.stdout.flush()
if cfg.get("fail_first") and not (here / "failed-once").exists():  # tests using it run with --workers 1
    (here / "failed-once").write_text("")
    sys.exit(1)  # non-zero exit, no result event
if cfg.get("sleep"):
    import time
    time.sleep(cfg["sleep"])
if cfg.get("error_result"):  # it ran and was billed, then stopped (for example its budget was exceeded)
    print(json.dumps({{"type": "result", "result": "", "is_error": True, "total_cost_usd": cfg["error_result"]}}))
    sys.exit(1)
print(json.dumps({{"type": "system"}}))
print(json.dumps({{"type": "assistant", "message": {{"content": [
    {{"type": "tool_use", "name": "Read", "input": {{"file_path": os.path.join(os.getcwd(), cfg["read"])}}}}]}}}}))
print(json.dumps({{"type": "result", "result": cfg["reply"], "total_cost_usd": cfg["cost"], "num_turns": 2,
    "is_error": False, "usage": {{"input_tokens": 10, "output_tokens": 7}},
    "permission_denials": cfg.get("raw_denials") or [{{"tool_input": {{"file_path": p}}}} for p in cfg.get("deny", [])]}}))
"""

REPLY = ("Review done.\n```json\n" + json.dumps([{"oracle": "correctness", "class": "bug", "file": "app/stats.py",
         "line": 3, "confidence": 90, "summary": "count_active does not filter deleted rows"}]) + "\n```\nspec_verdict: pass\n")


def make_stub(tmp_path: Path, reply=REPLY, cost=0.01, read="rules/review-policy.md", deny=(), **extra):
    here = tmp_path / "stub"
    here.mkdir()
    (here / "stub.json").write_text(json.dumps({"reply": reply, "cost": cost, "read": read, "deny": list(deny), **extra}))
    stub = here / "claude"
    stub.write_text(STUB.format(python=sys.executable, here=str(here)))
    stub.chmod(0o755)
    return stub, here / "calls.jsonl"


def calls(log: Path):
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def prompt_of(call):
    argv = call["argv"]
    return argv[argv.index("-p") + 1]


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def git(repo: Path, *args):
    return subprocess.run(GIT + ["-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def make_repo(tmp_path: Path):
    """A git repo with the prompt files in the shapes the tool expects; commit 2 changes one finder angle."""
    repo = tmp_path / "repo"
    write(repo / "rules/review-policy.md", "policy\n")
    write(repo / "rules/arm-marker.md", "base\n")
    write(repo / "agents/reviewer.md", "agent\n")
    write(repo / "scripts/render_skill_prompt.py", (SCRIPTS / "render_skill_prompt.py").read_text())
    write(repo / "skills/correctness-review/review-config.json", json.dumps({"finder_angles": ["enclosing-function", "prior-art"]}))
    write(repo / "skills/correctness-review/prompts/shared.md",
          "# Finder\n\n- BASE_SHA: [commit before the first task]\n- HEAD_SHA: [current commit after all tasks]\n"
          "- Files touched: [list of paths]\n- REVIEW_PACKAGE_PATH: [the SDD-generated mechanical review package, or \"none\"]\n")
    write(repo / "skills/correctness-review/prompts/angles/enclosing-function.md", "Angle: enclosing function.\n")
    write(repo / "skills/correctness-review/prompts/angles/prior-art.md", "Angle: prior art.\n")
    write(repo / "skills/intent-review/intent-reviewer-prompt.md",
          "# Intent\n\n```\nTask(\n  prompt: |\n    You are an intent reviewer.\n\n    ## Inputs\n\n    - INTENT: [paste]\n\n"
          "    When `REVIEW_PACKAGE_PATH` is provided, read it first.\n```\n")
    write(repo / "skills/subagent-driven-development/task-reviewer-prompt.md",
          "# Task reviewer\n\n```\nTask(\n  prompt: |\n    Review the task.\n    - TASK_BRIEF_PATH: <path>\n"
          "    - IMPLEMENTER_REPORT_PATH: <path>\n    - REVIEW_PACKAGE_PATH: <path>\n```\n")
    write(repo / "skills/context-propagation-audit/SKILL.md", "---\nname: context-propagation-audit\n---\n# Audit body\n")
    git(tmp_path, "init", "-q", str(repo))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    base = git(repo, "rev-parse", "HEAD")
    write(repo / "skills/correctness-review/prompts/angles/enclosing-function.md", f"Angle: enclosing function. {HEAD_ONLY}\n")
    write(repo / "rules/arm-marker.md", "head\n")
    git(repo, "commit", "-q", "-am", "head")
    return repo, base, git(repo, "rev-parse", "HEAD")


DIFF = ("diff --git a/app/stats.py b/app/stats.py\n--- a/app/stats.py\n+++ b/app/stats.py\n@@ -1,1 +1,2 @@\n"
        " def count_active(rows):\n+    return len(rows)\n")


def make_fixtures(tmp_path: Path):
    review, task = tmp_path / "review-fixtures", tmp_path / "task-fixtures"
    for name, oracle in (("fx", "correctness"), ("au", "context-propagation-audit")):
        write(review / name / "intent.md", f"Count active rows ({name}).\n")
        write(review / name / "diff.patch", DIFF)
        write(review / name / "truth.md", f"The planted defect: {SENTINEL}.\n")
        write(review / name / "truth.json", json.dumps({
            "schema_version": 1, "expected_oracle": oracle, "core": oracle == "correctness", "correctness_clean": False,
            "planted": {"file": "app/stats.py", "match_any": ["count_active"], "and_any": ["filter"]},
            "false_positives": [{"file": "", "match_any": [SENTINEL], "and_any": []}]}))
    write(task / "tk" / "input.md", "# Task\nAdd x.\n\n# Implementation\nAdded x.\n")
    write(task / "tk" / "truth.json", json.dumps({"required": ["spec_pass"], "forbidden": [SENTINEL]}))
    return review, task


def run(tmp_path, stub, *args, repo=None, base=None, head=None, out=None):
    review, task = tmp_path / "review-fixtures", tmp_path / "task-fixtures"
    cmd = [sys.executable, TOOL, "run", "--repo", str(repo), "--base-rev", base, "--head-rev", head,
           "--out", str(out or tmp_path / "out"), "--review-fixtures", str(review), "--task-fixtures", str(task),
           "--claude", str(stub), *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=tmp_path)


def report(tmp_path, out=None):
    cmd = [sys.executable, TOOL, "report", "--out", str(out or tmp_path / "out"),
           "--review-fixtures", str(tmp_path / "review-fixtures"), "--task-fixtures", str(tmp_path / "task-fixtures")]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=tmp_path)


def setup(tmp_path, **stub_kw):
    repo, base, head = make_repo(tmp_path)
    make_fixtures(tmp_path)
    stub, log = make_stub(tmp_path, **stub_kw)
    return dict(repo=repo, base=base, head=head), stub, log


def test_arms_are_isolated(tmp_path):
    revs, stub, log = setup(tmp_path)
    proc = run(tmp_path, stub, "--kinds", "finder", "--only-fixture", "fx", **revs)
    assert proc.returncode == 0, proc.stderr
    by_arm = {"base": [], "head": []}
    for call in calls(log):
        by_arm[call["files"]["rules/arm-marker.md"].strip()].append(call)
    assert len(by_arm["base"]) == 2 and len(by_arm["head"]) == 2
    assert all(HEAD_ONLY not in prompt_of(c) for c in by_arm["base"])
    head_enclosing = [c for c in by_arm["head"] if "enclosing function" in prompt_of(c)]
    assert len(head_enclosing) == 1 and HEAD_ONLY in prompt_of(head_enclosing[0])


def test_call_flags_and_clean_cwd_without_answer_key(tmp_path):
    revs, stub, log = setup(tmp_path)
    proc = run(tmp_path, stub, "--model", "m1", "--effort", "low", "--max-call-usd", "0.5", **revs)
    assert proc.returncode == 0, proc.stderr
    seen = calls(log)
    # per arm: 2 finder angles x 2 fixtures, intent x 2, audit x 1 (au only), task x 1
    assert len(seen) == 2 * (4 + 2 + 1 + 1)
    for call in seen:
        argv = call["argv"]
        flags = argv[:argv.index("-p")] + argv[argv.index("-p") + 2:]
        assert flags == ["--safe-mode", "--tools", "Read", "--allowedTools", "Read", "--model", "m1", "--effort", "low",
                         "--max-budget-usd", "0.5", "--output-format", "stream-json", "--verbose",
                         "--no-session-persistence"]
        assert not call["cwd"].startswith(str(tmp_path / "repo")) and not call["cwd"].startswith(str(tmp_path / "out"))
        assert not any(Path(name).name.startswith("truth.") for name in call["files"])
        assert SENTINEL not in prompt_of(call) and all(SENTINEL not in text for text in call["files"].values())
    assert len({c["cwd"] for c in seen}) == len(seen)
    runs = sorted(p.name for p in (tmp_path / "out" / "runs").iterdir())
    assert "base__finder__fx__enclosing-function__a1.json" in runs and "head__task__tk__-__a1.json" in runs
    record = json.loads((tmp_path / "out" / "runs" / "head__intent__fx__-__a1.json").read_text())
    for key in ("job", "rc", "elapsed", "cost", "usage", "reads", "denials", "prompt_words", "text"):
        assert key in record
    assert record["text"] == REPLY and record["prompt_words"] > 0


def test_never_overwrites_a_recorded_call(tmp_path):
    revs, stub, log = setup(tmp_path)
    assert run(tmp_path, stub, "--kinds", "intent", **revs).returncode == 0
    first = len(calls(log))
    record = tmp_path / "out" / "runs" / "base__intent__fx__-__a1.json"
    before = record.read_bytes()
    proc = run(tmp_path, stub, "--kinds", "intent", **revs)
    assert proc.returncode == 0, proc.stderr
    assert len(calls(log)) == first and record.read_bytes() == before
    assert "already recorded; not rerun" in proc.stdout


def test_budget_cap_stops_new_calls(tmp_path):
    revs, stub, log = setup(tmp_path, cost=5.0)
    proc = run(tmp_path, stub, "--kinds", "intent", "--workers", "1", "--max-total-usd", "1", **revs)
    assert proc.returncode == 0, proc.stderr
    assert len(calls(log)) == 1
    assert len(list((tmp_path / "out" / "runs").iterdir())) == 1
    assert "budget cap reached" in proc.stdout
    # a resumed run shares the cap: the recorded call's cost already exceeds it, so nothing new runs
    proc = run(tmp_path, stub, "--kinds", "intent", "--workers", "1", "--max-total-usd", "1", **revs)
    assert proc.returncode == 0, proc.stderr
    assert len(calls(log)) == 1 and "budget cap reached" in proc.stdout


def test_meta_mismatch_is_refused(tmp_path):
    revs, stub, log = setup(tmp_path)
    assert run(tmp_path, stub, "--kinds", "task", "--model", "m1", **revs).returncode == 0
    first = len(calls(log))
    proc = run(tmp_path, stub, "--kinds", "task", "--model", "m2", **revs)
    assert proc.returncode == 1 and proc.stderr.startswith("review-prompt-eval: ") and "meta.json" in proc.stderr
    assert len(calls(log)) == first


def test_unknown_only_fixture_is_an_error(tmp_path):
    revs, stub, log = setup(tmp_path)
    proc = run(tmp_path, stub, "--kinds", "task", "--only-fixture", "fx", **revs)
    assert proc.returncode == 1 and proc.stderr.startswith("review-prompt-eval: ") and not calls(log)


def test_report_counts_watch_path_reads_and_writes_scorer_files(tmp_path):
    revs, stub, _ = setup(tmp_path)
    assert run(tmp_path, stub, **revs).returncode == 0
    proc = report(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "finder: 4/4" in proc.stdout and "task: 1/1" in proc.stdout
    assert "parseable JSON block (finished calls): 7/7" in proc.stdout
    assert "fx [core]: CAUGHT" in proc.stdout
    assert "tk" in proc.stdout and "spec_pass" in proc.stdout and "requirements hold: yes" in proc.stdout
    for arm in ("base", "head"):
        data = json.loads((tmp_path / "out" / f"result-{arm}.json").read_text())
        assert sorted(data["cases"]) == ["au", "fx"]
        text = data["cases"]["fx"]["result"]
        findings = json.loads(text.split("```json\n", 1)[1].rsplit("\n```", 1)[0])
        assert {f["oracle"] for f in findings} == {"correctness", "intent"}
        audit = json.loads(data["cases"]["au"]["result"].split("```json\n", 1)[1].rsplit("\n```", 1)[0])
        assert "context-propagation-audit" in {f["oracle"] for f in audit}
    scored = subprocess.run([sys.executable, str(SCRIPTS / "score_review_chain_eval.py"), "--score",
                             str(tmp_path / "out" / "result-head.json"), "--fixtures", str(tmp_path / "review-fixtures")],
                            capture_output=True, text=True)
    assert scored.returncode == 0, scored.stderr


def test_unparseable_reply_does_not_stop_the_run(tmp_path):
    revs, stub, log = setup(tmp_path, reply="I found nothing worth reporting.")
    proc = run(tmp_path, stub, "--kinds", "finder,intent", **revs)
    assert proc.returncode == 0, proc.stderr
    assert len(calls(log)) == 2 * (4 + 2)
    rep = report(tmp_path)
    assert rep.returncode == 0, rep.stderr
    assert "parseable JSON block (finished calls): 0/6" in rep.stdout and "UNPARSEABLE" in rep.stdout


def test_permission_denial_is_reported(tmp_path):
    # malformed entries (not an object, or a tool_input that is not an object) are tolerated
    revs, stub, _ = setup(tmp_path, raw_denials=["junk", {"tool_input": "junk"}, {"tool_input": {"file_path": "/etc/passwd"}}])
    proc = run(tmp_path, stub, "--kinds", "task", **revs)
    assert proc.returncode == 0, proc.stderr
    rep = report(tmp_path)
    assert rep.returncode == 0, rep.stderr
    assert "permission denials: 1 call(s)" in rep.stdout and "/etc/passwd" in rep.stdout
    assert "core catches" not in rep.stdout  # a task-only directory has no review-chain section


class Crash(BaseException):
    """Stands in for the process dying: not an Exception, so nothing in the tool converts it."""


def test_crash_mid_write_leaves_no_partial_record(tmp_path, monkeypatch):
    import run_review_prompt_eval as tool
    revs, stub, log = setup(tmp_path)
    real_link = tool.os.link

    def crashing_link(src, dst):
        if Path(dst).name.startswith("head__intent__fx"):
            raise Crash()
        return real_link(src, dst)

    monkeypatch.setattr(tool.os, "link", crashing_link)
    monkeypatch.setattr(sys, "argv", [TOOL, "run", "--repo", str(revs["repo"]), "--base-rev", revs["base"],
                                      "--head-rev", revs["head"], "--out", str(tmp_path / "out"),
                                      "--review-fixtures", str(tmp_path / "review-fixtures"), "--task-fixtures",
                                      str(tmp_path / "task-fixtures"), "--claude", str(stub), "--kinds", "intent",
                                      "--only-fixture", "fx", "--workers", "1"])
    try:
        tool.main()
    except Crash:
        pass
    else:
        raise AssertionError("the simulated crash did not happen")
    monkeypatch.setattr(tool.os, "link", real_link)
    runs = tmp_path / "out" / "runs"
    assert sorted(p.name for p in runs.iterdir()) == ["base__intent__fx__-__a1.json"]
    before = len(calls(log))
    proc = run(tmp_path, stub, "--kinds", "intent", "--only-fixture", "fx", "--workers", "1", **revs)
    assert proc.returncode == 0, proc.stderr
    assert len(calls(log)) == before + 1
    assert json.loads((runs / "head__intent__fx__-__a1.json").read_text())["rc"] == 0


def main_in_process(monkeypatch, tmp_path, revs, stub, *extra):
    import run_review_prompt_eval as tool
    monkeypatch.setattr(sys, "argv", [TOOL, "run", "--repo", str(revs["repo"]), "--base-rev", revs["base"],
                                      "--head-rev", revs["head"], "--out", str(tmp_path / "out"),
                                      "--review-fixtures", str(tmp_path / "review-fixtures"), "--task-fixtures",
                                      str(tmp_path / "task-fixtures"), "--claude", str(stub), *extra])
    return tool.main()


def test_job_exception_becomes_a_recorded_failed_call(tmp_path, monkeypatch, capsys):
    import run_review_prompt_eval as tool
    revs, stub, log = setup(tmp_path)

    def broken_copytree(*_args, **_kw):
        raise OSError("disk full")

    monkeypatch.setattr(tool.shutil, "copytree", broken_copytree)
    assert main_in_process(monkeypatch, tmp_path, revs, stub, "--kinds", "task") == 1
    err = capsys.readouterr().err
    assert err.startswith("review-prompt-eval: 2 call(s) failed") and "Traceback" not in err
    assert not calls(log)
    for arm in ("base", "head"):
        record = json.loads((tmp_path / "out" / "runs" / f"{arm}__task__tk__-__a1.json").read_text())
        assert record["rc"] == "error" and "disk full" in record["reason"] and len(record["attempts"]) == 1


def test_invalid_utf8_output_keeps_the_parsed_cost(tmp_path):
    revs, stub, log = setup(tmp_path, bad_utf8=True, cost=0.07)
    proc = run(tmp_path, stub, "--kinds", "task", **revs)
    assert proc.returncode == 0, proc.stderr
    assert len(calls(log)) == 2
    record = json.loads((tmp_path / "out" / "runs" / "base__task__tk__-__a1.json").read_text())
    assert record["rc"] == 0 and record["cost"] == 0.07 and record["text"] == REPLY


def test_exception_during_retry_keeps_the_paid_first_attempt(tmp_path, monkeypatch, capsys):
    import run_review_prompt_eval as tool
    revs, stub, log = setup(tmp_path, fail_first=True)
    real_call = tool.call_claude
    seen = []

    def call_then_break(*args, **kw):
        seen.append(1)
        if len(seen) == 2:
            raise RuntimeError("retry broke")
        return real_call(*args, **kw)

    monkeypatch.setattr(tool, "call_claude", call_then_break)
    assert main_in_process(monkeypatch, tmp_path, revs, stub, "--kinds", "task", "--workers", "1",
                           "--max-call-usd", "0.02", "--only-fixture", "tk") == 1
    capsys.readouterr()
    base = json.loads((tmp_path / "out" / "runs" / "base__task__tk__-__a1.json").read_text())
    assert base["rc"] == "error" and "retry broke" in base["reason"]
    assert [a["rc"] for a in base["attempts"]] == [1, "error"] and abs(base["cost"] - 0.02) < 1e-9


def test_report_separates_failed_calls(tmp_path):
    # the intent call on fixture fx and the task call fail to run (both attempts) in both arms
    revs, stub, _ = setup(tmp_path, fail_when=[["You are an intent reviewer", "Count active rows (fx)"],
                                               ["Review the task."]])
    assert run(tmp_path, stub, **revs).returncode == 0
    rep = report(tmp_path)
    assert rep.returncode == 0, rep.stderr
    for arm in ("base", "head"):
        assert f"== {arm}: calls 8; failed calls 2; parseable JSON block (finished calls): 6/6" in rep.stdout
        assert f"tk {arm} a1: labels []; requirements hold: error (rc=1)" in rep.stdout
    assert rep.stdout.count("excluded because a call failed: fx\n") == 2
    assert "au [bonus]: CAUGHT" in rep.stdout


def test_a_call_that_failed_to_run_is_retried_once(tmp_path):
    revs, stub, log = setup(tmp_path, fail_first=True)
    proc = run(tmp_path, stub, "--kinds", "task", "--workers", "1", "--max-call-usd", "0.02", **revs)
    assert proc.returncode == 0, proc.stderr
    assert len(calls(log)) == 3  # base: failed + one retry; head: first-call success, never retried
    runs = tmp_path / "out" / "runs"
    base = json.loads((runs / "base__task__tk__-__a1.json").read_text())
    head = json.loads((runs / "head__task__tk__-__a1.json").read_text())
    assert [a["rc"] for a in base["attempts"]] == [1, 0] and base["rc"] == 0 and base["text"] == REPLY
    assert abs(base["cost"] - 0.03) < 1e-9
    assert len(head["attempts"]) == 1 and head["cost"] == 0.01


def test_retry_respects_the_total_cap(tmp_path):
    revs, stub, log = setup(tmp_path, fail_first=True)
    proc = run(tmp_path, stub, "--kinds", "task", "--workers", "1", "--max-call-usd", "0.02",
               "--max-total-usd", "0.02", **revs)
    assert proc.returncode == 0, proc.stderr
    assert len(calls(log)) == 1
    base = json.loads((tmp_path / "out" / "runs" / "base__task__tk__-__a1.json").read_text())
    assert len(base["attempts"]) == 1 and base["rc"] == 1


def test_timeout_is_charged_the_call_cap_and_not_retried(tmp_path, monkeypatch, capsys):
    import functools
    import run_review_prompt_eval as tool
    revs, stub, log = setup(tmp_path, sleep=5)
    monkeypatch.setattr(tool, "call_claude", functools.partial(tool.call_claude, timeout=0.5))
    assert main_in_process(monkeypatch, tmp_path, revs, stub, "--kinds", "task", "--workers", "1",
                           "--max-call-usd", "0.4", "--max-total-usd", "0.4") == 0
    assert "budget cap reached" in capsys.readouterr().out
    assert len(calls(log)) == 1  # not retried, and the estimated cost stops the head call
    record = json.loads((tmp_path / "out" / "runs" / "base__task__tk__-__a1.json").read_text())
    assert record["rc"] == "timeout" and record["cost"] == 0.4 and record["cost_estimated"] is True
    assert [a["cost_estimated"] for a in record["attempts"]] == [True]
    rep = report(tmp_path)
    assert "cost $0.40 (estimated)" in rep.stdout, rep.stderr


def test_a_billed_error_result_is_not_retried(tmp_path):
    revs, stub, log = setup(tmp_path, error_result=0.3)
    assert run(tmp_path, stub, "--kinds", "task", "--workers", "1", **revs).returncode == 0
    assert len(calls(log)) == 2  # one per arm, no retry
    record = json.loads((tmp_path / "out" / "runs" / "base__task__tk__-__a1.json").read_text())
    assert record["rc"] == 1 and record["cost"] == 0.3 and len(record["attempts"]) == 1
    assert record["cost_estimated"] is False


def test_missing_claude_binary_fails_before_any_record(tmp_path):
    revs, stub, log = setup(tmp_path)
    proc = run(tmp_path, stub, "--claude", str(tmp_path / "no-such-claude"), **revs)
    assert proc.returncode == 1 and proc.stderr.startswith("review-prompt-eval: --claude")
    assert not (tmp_path / "out").exists() and not calls(log)


def test_relative_claude_path_is_resolved(tmp_path):
    revs, stub, log = setup(tmp_path)
    proc = run(tmp_path, stub, "--kinds", "task", "--claude", "stub/claude", **revs)  # relative to cwd=tmp_path
    assert proc.returncode == 0, proc.stderr
    assert len(calls(log)) == 2


def test_a_call_that_did_not_start_leaves_no_record_and_reruns(tmp_path):
    revs, stub, log = setup(tmp_path)
    good = stub.read_text()
    stub.write_text("#!/nonexistent/interpreter\n")  # executable, but exec fails: the call does not start
    proc = run(tmp_path, stub, "--kinds", "task", **revs)
    assert proc.returncode == 1 and "2 call(s) failed" in proc.stderr
    assert not list((tmp_path / "out" / "runs").iterdir())
    stub.write_text(good)
    proc = run(tmp_path, stub, "--kinds", "task", **revs)
    assert proc.returncode == 0, proc.stderr
    assert len(calls(log)) == 2 and len(list((tmp_path / "out" / "runs").iterdir())) == 2


def test_watch_path_is_stored_in_meta(tmp_path):
    revs, stub, _ = setup(tmp_path)
    assert run(tmp_path, stub, "--kinds", "task", "--watch-path", "rules/other.md", **revs).returncode == 0
    assert json.loads((tmp_path / "out" / "meta.json").read_text())["watch_path"] == "rules/other.md"
    assert run(tmp_path, stub, "--kinds", "task", "--watch-path", "rules/other.md", **revs).returncode == 0
    refused = run(tmp_path, stub, "--kinds", "task", **revs)
    assert refused.returncode == 1 and "watch_path" in refused.stderr
    assert "read rules/other.md - task: 0/1" in report(tmp_path).stdout
    override = subprocess.run([sys.executable, TOOL, "report", "--out", str(tmp_path / "out"), "--task-fixtures",
                               str(tmp_path / "task-fixtures"), "--watch-path", "rules/review-policy.md"],
                              capture_output=True, text=True, cwd=tmp_path)
    assert "read rules/review-policy.md - task: 1/1" in override.stdout, override.stderr


def test_real_prompts_build_from_this_repo(tmp_path):
    """The repo's own prompt files still have the shapes the tool fills in (fails loudly otherwise)."""
    stub, log = make_stub(tmp_path)
    repo = SCRIPTS.parent
    cmd = [sys.executable, TOOL, "run", "--repo", str(repo), "--base-rev", "HEAD", "--head-rev", "HEAD",
           "--out", str(tmp_path / "out"), "--claude", str(stub), "--only-fixture", "missing-await",
           "--only-fixture", "context-rule-unread", "--only-fixture", "spec-only"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=repo)
    assert proc.returncode == 0, proc.stderr
    seen = calls(log)
    assert len(seen) == 2 * (6 + 1 + 6 + 1 + 1 + 1)
    for call in seen:
        prompt = prompt_of(call)
        assert "[commit before the first task]" not in prompt and ": <path>" not in prompt
        assert not any(Path(name).name.startswith("truth.") for name in call["files"])


def test_help_exits_zero():
    assert subprocess.run([sys.executable, TOOL, "--help"], capture_output=True).returncode == 0
