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

  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run_report.py <run dir | run id> [--journal FILE] [--json]

A run id (wf_...) is looked up under ~/.claude/projects/*/*/subagents/workflows/; it must match one directory.

FILE is either out.journal saved as a JSON array, or the run log saved as text: lines that contain
`journal row: {...}` (what ship.js logs) are read from it.
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

LABEL = re.compile(r"^#(?P<n>\d+)\s+(?P<rest>.+)$")


# Agent labels name stages for people; ship.js journals them under shorter names. Compare through this table.
LABEL_TO_JOURNAL = {
    "code-review": "review", "gate code-review": "gate-review", "gate ci checks": "ci",
    "uat": "uat", "uat rerun": "uat-rerun", "merge ticket branches": "merge", "test": "suite",
}
STATUS_RANK = {"ok": 0, "blocked": 1, "failed": 2}


def journal_stage(name):
    """Stage name as ship.js journals it, for either side of the join: 'merge-g2' -> 'merge', 'Gate CI checks' -> 'ci'."""
    n = re.sub(r"-g\d+$", "", str(name).strip().lower()) if str(name).lower().startswith("merge-g") else str(name).strip().lower()
    return LABEL_TO_JOURNAL.get(n, n)


def stage_of(label):
    """('516', 'implement') for '#516 implement · title'; ('run', 'code-review') for 'code-review · round 0'."""
    m = LABEL.match(label or "")
    ticket, rest = (m.group("n"), m.group("rest")) if m else ("run", label or "?")
    rest = re.sub(r"\s+retry$", "", rest.split(" · ")[0].strip())   # a retry is the same stage
    rest = re.sub(r"^((?:gate )?fix) r\d+(?:\.\d+)?$", r"\1", rest)    # one stage "fix", not one per round and finding
    return ticket, rest or "?"


def when(s):
    if not isinstance(s, str):
        raise ValueError("timestamp is not a string")
    t = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)   # a naive stamp is read as UTC, never compared raw


def read_jsonl(path):
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue   # a torn last line of a live run
    return [d for d in out if isinstance(d, dict)]


def agent_facts(path):
    """first/last timestamp, output tokens (once per message id) and model of one agent transcript."""
    stamps, tokens, model = [], {}, None
    for d in read_jsonl(path):
        if d.get("timestamp"):
            try:
                stamps.append(when(d["timestamp"]))
            except (ValueError, TypeError):
                pass
        msg = d.get("message") if isinstance(d.get("message"), dict) else {}
        if d.get("type") == "assistant":
            model = model or (msg.get("model") if isinstance(msg.get("model"), str) else None)
            usage = msg.get("usage") if isinstance(msg.get("usage"), dict) else {}
            # A message can be written on several lines while it streams: keep the largest count per message id.
            key = msg.get("id") or d.get("uuid")
            n = usage.get("output_tokens")
            tokens[key] = max(tokens.get(key, 0), n if isinstance(n, int) and not isinstance(n, bool) else 0)
    return (min(stamps), max(stamps)) if stamps else None, sum(tokens.values()), model


def read_journal_rows(text):
    """out.journal as a JSON array, or the run log: every `journal row: {...}` line. None when neither is found."""
    try:
        v = json.loads(text)
        return v if isinstance(v, list) else None
    except ValueError:
        pass
    rows = []
    for line in text.splitlines():
        i = line.find("journal row: ")
        if i < 0:
            continue
        try:
            rows.append(json.loads(line[i + len("journal row: "):]))
        except ValueError:
            continue
    return rows or None


def resolve_run_dir(arg):
    """A directory as given, or a run id (wf_...) found under ~/.claude/projects/*/*/subagents/workflows/."""
    p = Path(arg)
    if p.is_dir():
        return p
    if re.fullmatch(r"[A-Za-z0-9_-]+", str(arg)):   # a bare id only: never a path fragment or a glob
        hits = sorted((Path.home() / ".claude" / "projects").glob(f"*/*/subagents/workflows/{arg}"))
        hits = [h for h in hits if h.is_dir()]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise SystemExit(f"run_report: run id {arg} matches {len(hits)} directories; pass the one you mean:\n" + "\n".join(map(str, hits)))
    raise SystemExit(f"run_report: {arg} is neither a directory nor a known run id")


def build(run_dir, journal_rows=None):
    jpath = run_dir / "journal.jsonl"
    if not jpath.is_file():
        raise SystemExit(f"run_report: no journal.jsonl in {run_dir}")
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
        try:
            span, tok, model = agent_facts(f)
        except OSError:
            span = None
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
            k = (str(r.get("ticket")), journal_stage(r["stage"]))
            j = joined.setdefault(k, {"status": "ok", "retries": 0})
            if STATUS_RANK.get(r.get("status"), 0) > STATUS_RANK[j["status"]]:
                j["status"] = r["status"]   # several rows (merge groups, verify modes) share one stage: keep the worst
            j["retries"] += r.get("retries") or 0
    rows = []
    for key, s in stages.items():
        row = {"ticket": s["ticket"], "stage": s["stage"], "agents": s["agents"],
               "wall_seconds": round((s["end"] - s["start"]).total_seconds(), 1),
               "agent_seconds": round(s["agent_seconds"], 1), "output_tokens": s["output_tokens"],
               "models": sorted(s["models"]), "blocked_agents": s["blocked"]}
        j = joined.get((s["ticket"], journal_stage(s["stage"])))
        if j:
            row["status"], row["retries"] = j["status"], j["retries"]
        rows.append(row)
    rows.sort(key=lambda r: r["agent_seconds"], reverse=True)
    return rows, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dir", help="the run directory, or a run id such as wf_2525c101-225")
    ap.add_argument("--journal", type=Path, help="out.journal of the run, saved as a JSON array")
    ap.add_argument("--json", action="store_true", help="one JSON object per stage instead of a table")
    a = ap.parse_args(argv)
    run_dir = resolve_run_dir(a.run_dir)
    jr = None
    if a.journal:
        try:
            jr = read_journal_rows(a.journal.read_text(encoding="utf-8"))
        except OSError as e:
            raise SystemExit(f"run_report: cannot read {a.journal}: {e}")
        if jr is None:
            raise SystemExit(f"run_report: {a.journal} holds neither a JSON array nor 'journal row: {{...}}' lines")
    rows, missing = build(run_dir, jr)
    if a.json:
        for r in rows:
            print(json.dumps(r))
    else:
        print(f"{'ticket':>6} {'stage':<22} {'agents':>6} {'agent s':>8} {'wall s':>8} {'out tok':>9}  status retries  models")
        for r in rows:
            print(f"{r['ticket']:>6} {r['stage'][:22]:<22} {r['agents']:>6} {r['agent_seconds']:>8.0f} {r['wall_seconds']:>8.0f} "
                  f"{r['output_tokens']:>9}  {str(r.get('status', '-')):<6} {str(r.get('retries', '-')):<7} {','.join(r['models'])}")
    if missing:
        print(f"run_report: {len(missing)} agent(s) had no readable transcript and are not counted", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
