import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("run_report", Path(__file__).with_name("run-report.py"))
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
