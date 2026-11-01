import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("run_report", Path(__file__).parent.parent / "plugins" / "harness" / "scripts" / "run_report.py")
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)


def agent_file(path, stamps, outs, model="claude-sonnet-5-5"):
    lines = []
    for i, (t, o) in enumerate(zip(stamps, outs)):
        lines.append({"type": "assistant", "timestamp": t, "uuid": f"u{i}",
                      "message": {"id": f"m{i // 2}", "model": model, "usage": {"output_tokens": o}}})
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n")


def make_run(tmp_path):
    j = [
        {"type": "launched"},
        {"type": "started", "agentId": "a1", "key": "k1", "label": "#7 implement · Add the thing", "phase": "Tickets"},
        {"type": "result", "agentId": "a1", "key": "k1", "result": {"status": "ok"}},
        {"type": "started", "agentId": "a2", "key": "k2", "label": "#7 implement retry · Add the thing", "phase": "Tickets"},
        {"type": "result", "agentId": "a2", "key": "k2", "result": {"status": "blocked"}},
        {"type": "started", "agentId": "a3", "key": "k3", "label": "code-review · round 0", "phase": "Review"},
        {"type": "result", "agentId": "a3", "key": "k3", "result": {"status": "ok"}},
        {"type": "started", "agentId": "a4", "key": "k4", "label": "#7 verify · Add the thing", "phase": "Tickets"},
    ]
    (tmp_path / "journal.jsonl").write_text("\n".join(json.dumps(x) for x in j) + "\n")
    agent_file(tmp_path / "agent-a1.jsonl", ["2026-11-01T00:00:00Z", "2026-11-01T00:01:00Z"], [100, 50])
    agent_file(tmp_path / "agent-a2.jsonl", ["2026-11-01T00:01:00Z", "2026-11-01T00:03:00Z"], [10, 10])
    agent_file(tmp_path / "agent-a3.jsonl", ["2026-11-01T00:00:00Z", "2026-11-01T00:00:10Z"], [5, 5], model="claude-haiku-5-5")
    # a4 has no transcript file


def test_stage_of():
    assert rr.stage_of("#516 implement · feat(x)") == ("516", "implement")
    assert rr.stage_of("#516 advisor plan-review · t") == ("516", "advisor plan-review")
    assert rr.stage_of("#3 implement retry") == ("3", "implement")
    assert rr.stage_of("code-review · round 0") == ("run", "code-review")
    assert rr.stage_of(None) == ("run", "?")


def test_groups_retry_into_the_stage_and_sorts_slowest_first(tmp_path):
    make_run(tmp_path)
    rows, missing = rr.build(tmp_path)
    assert missing == ["a4"]
    assert [(r["ticket"], r["stage"]) for r in rows] == [("7", "implement"), ("run", "code-review")]
    impl = rows[0]
    assert impl["agents"] == 2 and impl["agent_seconds"] == 180.0 and impl["wall_seconds"] == 180.0
    assert impl["blocked_agents"] == 1


def test_tokens_count_a_streamed_message_once(tmp_path):
    make_run(tmp_path)
    rows, _ = rr.build(tmp_path)
    # a1: two lines share message id m0, so only the larger count (100) is kept; a2: same, 10
    assert rows[0]["output_tokens"] == 100 + 10
    assert rows[1]["models"] == ["claude-haiku-5-5"]


def test_journal_join_adds_status_and_retries(tmp_path):
    make_run(tmp_path)
    rows, _ = rr.build(tmp_path, [{"ticket": 7, "stage": "implement", "status": "ok", "retries": 1}])
    assert rows[0]["status"] == "ok" and rows[0]["retries"] == 1
    assert "status" not in rows[1]


def test_missing_journal_file_is_an_error_not_a_guess(tmp_path):
    try:
        rr.build(tmp_path)
    except SystemExit as e:
        assert "no journal.jsonl" in str(e)
    else:
        raise AssertionError("expected SystemExit")


def test_cli_prints_a_table_and_json(tmp_path, capsys):
    make_run(tmp_path)
    assert rr.main([str(tmp_path)]) == 0
    out = capsys.readouterr()
    assert "implement" in out.out and "1 agent(s) had no readable transcript" in out.err
    assert rr.main([str(tmp_path), "--json"]) == 0
    first = json.loads(capsys.readouterr().out.splitlines()[0])
    assert first["stage"] == "implement"


def test_every_journaled_stage_joins_the_label_ship_js_gives_it():
    # label stage (as stage_of reads the display label) -> the name ship.js journals it under
    pairs = [
        ("code-review · round 0", "run", "review"), ("#5 gate code-review · round 0", "5", "gate-review"),
        ("#5 gate CI checks", "5", "ci"), ("#5 UAT · t", "5", "uat"), ("#5 UAT rerun · t", "5", "uat-rerun"),
        ("merge ticket branches · group 2", "run", "merge-g2"), ("test · run full suite", "run", "suite"),
        ("#5 implement · t", "5", "implement"), ("#5 verify-retry · t", "5", "verify-retry"),
    ]
    for label, ticket, journaled in pairs:
        t, st = rr.stage_of(label)
        assert t == ticket and rr.journal_stage(st) == rr.journal_stage(journaled), (label, t, st)


def test_join_keeps_the_worst_status_and_sums_retries_over_merge_groups(tmp_path):
    j = [{"type": "started", "agentId": "a1", "label": "merge ticket branches · group 1", "phase": "Merge"},
         {"type": "started", "agentId": "a2", "label": "merge ticket branches · group 2", "phase": "Merge"}]
    (tmp_path / "journal.jsonl").write_text("\n".join(json.dumps(x) for x in j) + "\n")
    for a in ("a1", "a2"):
        agent_file(tmp_path / f"agent-{a}.jsonl", ["2026-11-01T00:00:00Z", "2026-11-01T00:00:30Z"], [1, 1])
    rows, _ = rr.build(tmp_path, [{"ticket": "run", "stage": "merge-g1", "status": "ok", "retries": 0},
                                  {"ticket": "run", "stage": "merge-g2", "status": "failed", "retries": 1}])
    assert rows[0]["status"] == "failed" and rows[0]["retries"] == 1


def test_journal_input_can_be_the_run_log():
    text = "log line\njournal row: {\"ticket\": 1, \"stage\": \"suite\", \"status\": \"ok\", \"retries\": 0}\nnoise\n"
    assert rr.read_journal_rows(text) == [{"ticket": 1, "stage": "suite", "status": "ok", "retries": 0}]
    assert rr.read_journal_rows("[{\"stage\": \"ci\"}]") == [{"stage": "ci"}]
    assert rr.read_journal_rows("nothing here") is None


def test_a_run_id_is_found_under_home(tmp_path, monkeypatch):
    run = tmp_path / ".claude" / "projects" / "proj" / "sess" / "subagents" / "workflows" / "wf_abc-123"
    run.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert rr.resolve_run_dir("wf_abc-123") == run
    for bad in ("wf_missing", "../etc", "wf_*"):
        try:
            rr.resolve_run_dir(bad)
        except SystemExit:
            continue
        raise AssertionError(bad)


def test_a_naive_timestamp_does_not_crash_the_report(tmp_path):
    (tmp_path / "journal.jsonl").write_text(json.dumps({"type": "started", "agentId": "a1", "label": "#1 plan", "phase": "T"}) + "\n")
    agent_file(tmp_path / "agent-a1.jsonl", ["2026-11-01T00:00:00", "2026-11-01T00:00:30Z"], [1, 1])
    rows, missing = rr.build(tmp_path)
    assert not missing and rows[0]["agent_seconds"] == 30.0
