#!/usr/bin/env python3
"""Per-stage time and token report for one Workflow run (#529).

The ship.js sandbox has no clock, but the runtime keeps, for every run:
  <run dir>/journal.jsonl        one `started` and one `result` line per agent (agentId, label, phase, result)
  <run dir>/agent-<id>.jsonl     the transcript of that agent, with a timestamp and token usage per message
This script joins them: it groups the agents by the stage named in their label ("#516 implement · title" ->
ticket 516, stage implement), and reports wall time, summed agent time and output tokens per stage, slowest first.
With --journal it also adds the status and retries ship.js recorded (the `out.journal` array saved as JSON).

Read-only. The run dir is under ~/.claude/projects/<project>/<session>/subagents/workflows/<run id>/ ; that layout
belongs to Claude Code and can change, so a missing file is reported, never guessed.

  python3 scripts/run-report.py <run dir> [--journal out-journal.json] [--json]
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

LABEL = re.compile(r"^#(?P<n>\d+)\s+(?P<rest>.+)$")


def stage_of(label):
    """('516', 'implement') for '#516 implement · title'; ('run', 'code-review') for 'code-review · round 0'."""
    m = LABEL.match(label or "")
    ticket, rest = (m.group("n"), m.group("rest")) if m else ("run", label or "?")
    rest = re.sub(r"\s+retry$", "", rest.split(" · ")[0].strip())   # a retry is the same stage
    return ticket, rest or "?"


def when(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def read_jsonl(path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue   # a torn last line of a live run
    return out


def agent_facts(path):
    """first/last timestamp, output tokens (once per message id) and model of one agent transcript."""
    stamps, tokens, model = [], {}, None
    for d in read_jsonl(path):
        if d.get("timestamp"):
            try:
                stamps.append(when(d["timestamp"]))
            except ValueError:
                pass
        msg = d.get("message") or {}
        if d.get("type") == "assistant":
            model = model or msg.get("model")
            usage = msg.get("usage") or {}
            # A message can be written on several lines while it streams: keep the largest count per message id.
            key = msg.get("id") or d.get("uuid")
            tokens[key] = max(tokens.get(key, 0), usage.get("output_tokens") or 0)
    return (min(stamps), max(stamps)) if stamps else None, sum(tokens.values()), model


def build(run_dir, journal_rows=None):
    jpath = run_dir / "journal.jsonl"
    if not jpath.is_file():
        raise SystemExit(f"run-report: no journal.jsonl in {run_dir}")
    agents = {}
    for d in read_jsonl(jpath):
        if d.get("type") == "started" and d.get("agentId"):
            agents[d["agentId"]] = {"label": d.get("label"), "phase": d.get("phase"), "status": None}
        elif d.get("type") == "result" and d.get("agentId") in agents:
            r = d.get("result")
            agents[d["agentId"]]["status"] = r.get("status") if isinstance(r, dict) else None
    stages, missing = {}, []
    for aid, a in agents.items():
        f = run_dir / f"agent-{aid}.jsonl"
        if not f.is_file():
            missing.append(aid)
            continue
        span, tok, model = agent_facts(f)
        if span is None:
            missing.append(aid)
            continue
        key = stage_of(a["label"])
        s = stages.setdefault(key, {"ticket": key[0], "stage": key[1], "agents": 0, "agent_seconds": 0.0,
                                    "start": span[0], "end": span[1], "output_tokens": 0, "models": set(), "blocked": 0})
        s["agents"] += 1
        s["agent_seconds"] += (span[1] - span[0]).total_seconds()
        s["start"], s["end"] = min(s["start"], span[0]), max(s["end"], span[1])
        s["output_tokens"] += tok
        if model:
            s["models"].add(model)
        if a["status"] == "blocked":
            s["blocked"] += 1
    joined = {}
    for r in journal_rows or []:
        if isinstance(r, dict) and r.get("stage") is not None:
            joined[(str(r.get("ticket")), r["stage"])] = r
    rows = []
    for key, s in stages.items():
        row = {"ticket": s["ticket"], "stage": s["stage"], "agents": s["agents"],
               "wall_seconds": round((s["end"] - s["start"]).total_seconds(), 1),
               "agent_seconds": round(s["agent_seconds"], 1), "output_tokens": s["output_tokens"],
               "models": sorted(s["models"]), "blocked_agents": s["blocked"]}
        j = joined.get(key)
        if j:
            row["status"], row["retries"] = j.get("status"), j.get("retries")
        rows.append(row)
    rows.sort(key=lambda r: r["agent_seconds"], reverse=True)
    return rows, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--journal", type=Path, help="out.journal of the run, saved as a JSON array")
    ap.add_argument("--json", action="store_true", help="one JSON object per stage instead of a table")
    a = ap.parse_args(argv)
    if not a.run_dir.is_dir():
        raise SystemExit(f"run-report: {a.run_dir} is not a directory")
    jr = None
    if a.journal:
        try:
            jr = json.loads(a.journal.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise SystemExit(f"run-report: cannot read {a.journal}: {e}")
        if not isinstance(jr, list):
            raise SystemExit(f"run-report: {a.journal} must hold a JSON array")
    rows, missing = build(a.run_dir, jr)
    if a.json:
        for r in rows:
            print(json.dumps(r))
    else:
        print(f"{'ticket':>6} {'stage':<22} {'agents':>6} {'agent s':>8} {'wall s':>8} {'out tok':>9}  status retries  models")
        for r in rows:
            print(f"{r['ticket']:>6} {r['stage'][:22]:<22} {r['agents']:>6} {r['agent_seconds']:>8.0f} {r['wall_seconds']:>8.0f} "
                  f"{r['output_tokens']:>9}  {str(r.get('status', '-')):<6} {str(r.get('retries', '-')):<7} {','.join(r['models'])}")
    if missing:
        print(f"run-report: {len(missing)} agent(s) had no readable transcript and are not counted", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
