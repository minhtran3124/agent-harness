#!/usr/bin/env python3
"""Score feature-intake classifier eval runs against labeled fixtures.

Auto-score / manual-run: the classification itself is produced by a subagent running
`/feature-intake` blind to `truth.md` (integrity — see evals/workflow/intake-classifier/README.md).
This script is the deterministic scorer over those produced classifications.

Usage:
  score_intake_eval.py --list [--fixtures DIR]        # parse + list every fixture's truth header
  score_intake_eval.py --run RUN_DIR [--fixtures DIR] [--strict]

A RUN_DIR holds one produced classification per fixture: `<fixture>.md`, each containing the
`Lane:` / `Confidence:` / `Flags:` / `Escalate:` header that intake emitted. The scorecard is
printed to stdout. Exit is 0 (report tool) unless --strict and a hard-gate fixture was
downgraded below high-risk — the one safety-critical failure.
"""

import argparse
import os
import re
import sys

DEFAULT_FIXTURES = "evals/workflow/intake-classifier/fixtures"
LANES = {"tiny", "normal", "high-risk"}


def _tokens(val):
    """'auth, data-model' / 'none' / '' -> set of lowercase tokens (none/empty -> empty set)."""
    val = (val or "").strip().lower()
    if val in ("", "none", "-"):
        return set()
    return {t.strip() for t in val.split(",") if t.strip()}


def _norm_flag(s):
    """Collapse a flag token to alphanumerics only, so 'Data model', 'data-model',
    'data_model', and 'data-model (#3)' all compare equal."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def parse_kv_header(text):
    """Leading `key: value` lines (stop at first blank line, `---`, or `## `)."""
    header = {}
    for line in text.splitlines():
        s = line.strip()
        if s in ("", "---") or s.startswith("## "):
            if header:
                break
            continue
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", s)
        if m:
            header[m.group(1).strip().lower()] = m.group(2).strip()
    return header


def parse_classification(text):
    """Extract intake's emitted header. Case-insensitive keys; tolerant of `yes (reason)`."""
    out = {"lane": None, "confidence": None, "flags": set(), "escalate": None}
    for line in text.splitlines():
        m = re.match(r"^\s*([A-Za-z]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1).lower(), m.group(2).strip()
        if key == "lane":
            out["lane"] = val.lower()
        elif key == "confidence":
            out["confidence"] = val.lower()
        elif key == "flags":
            out["flags"] = _tokens(val)
        elif key == "escalate":
            out["escalate"] = "yes" if val.lower().startswith("yes") else "no"
    return out


def score_one(truth, produced):
    """Pure comparison. Returns dict of per-dimension bools + overall + reasons."""
    exp_lane = (truth.get("expected_lane") or "").strip().lower()
    exp_conf = (truth.get("expected_confidence") or "").strip().lower()
    exp_gate = (truth.get("expected_hard_gate") or "none").strip().lower()
    exp_esc = (truth.get("expected_escalate") or "").strip().lower()
    exp_flags = _tokens(truth.get("expected_flags_include"))
    is_gate = exp_gate not in ("", "none")

    reasons = []
    # lane ('any' means lane is not asserted for this fixture)
    if exp_lane in ("", "any"):
        lane_match = None
    else:
        lane_match = produced.get("lane") == exp_lane
        if not lane_match:
            reasons.append(f"lane {produced.get('lane')!r} != expected {exp_lane!r}")

    # hard-gate respect: a hard-gate fixture must never land below high-risk
    if is_gate:
        gate_ok = produced.get("lane") == "high-risk"
        if not gate_ok:
            reasons.append(
                f"HARD-GATE {exp_gate!r} downgraded to {produced.get('lane')!r}"
            )
    else:
        gate_ok = None

    # confidence
    if exp_conf:
        conf_match = produced.get("confidence") == exp_conf
        if not conf_match:
            reasons.append(f"confidence {produced.get('confidence')!r} != {exp_conf!r}")
    else:
        conf_match = None

    # escalate
    if exp_esc:
        esc_match = produced.get("escalate") == exp_esc
        if not esc_match:
            reasons.append(f"escalate {produced.get('escalate')!r} != {exp_esc!r}")
    else:
        esc_match = None

    # flags: every expected flag keyword must appear in some produced flag token.
    # Normalized substring match — the skill emits flags with parenthetical numbers
    # ("auth (1)") and varied separators ("Data model" vs "data-model"), so exact
    # token equality would spuriously fail. Compare on alphanumerics only.
    if exp_flags:
        prod = [_norm_flag(pf) for pf in produced.get("flags", set())]
        missing = {
            ef for ef in exp_flags if not any(_norm_flag(ef) in pf for pf in prod)
        }
        flags_ok = not missing
        if missing:
            reasons.append(f"flags missing {sorted(missing)}")
    else:
        flags_ok = None

    checks = [
        c
        for c in (lane_match, gate_ok, conf_match, esc_match, flags_ok)
        if c is not None
    ]
    overall = all(checks) if checks else True
    return {
        "lane_match": lane_match,
        "gate_ok": gate_ok,
        "conf_match": conf_match,
        "esc_match": esc_match,
        "flags_ok": flags_ok,
        "is_gate": is_gate,
        "overall": overall,
        "reasons": reasons,
    }


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _fixture_names(fixtures_dir):
    if not os.path.isdir(fixtures_dir):
        return []
    return sorted(
        d
        for d in os.listdir(fixtures_dir)
        if os.path.isfile(os.path.join(fixtures_dir, d, "truth.md"))
    )


def cmd_list(fixtures_dir):
    names = _fixture_names(fixtures_dir)
    if not names:
        print(f"no fixtures under {fixtures_dir}", file=sys.stderr)
        return 1
    print(f"# {len(names)} fixtures in {fixtures_dir}\n")
    for name in names:
        t = parse_kv_header(_read(os.path.join(fixtures_dir, name, "truth.md")))
        print(
            f"- {name}: lane={t.get('expected_lane', '?')} "
            f"conf={t.get('expected_confidence', '?')} "
            f"gate={t.get('expected_hard_gate', 'none')} "
            f"escalate={t.get('expected_escalate', '?')}"
        )
    return 0


def cmd_run(run_dir, fixtures_dir, strict):
    names = _fixture_names(fixtures_dir)
    if not names:
        print(f"no fixtures under {fixtures_dir}", file=sys.stderr)
        return 1

    rows, scored_lane, correct_lane = [], 0, 0
    gate_total, gate_ok_n, conf_total, conf_ok_n, overall_ok, missing = 0, 0, 0, 0, 0, 0
    for name in names:
        truth = parse_kv_header(_read(os.path.join(fixtures_dir, name, "truth.md")))
        prod_path = os.path.join(run_dir, f"{name}.md")
        if not os.path.isfile(prod_path):
            rows.append((name, "—", "—", "no-run", "no produced classification"))
            missing += 1
            continue
        produced = parse_classification(_read(prod_path))
        r = score_one(truth, produced)
        if r["lane_match"] is not None:
            scored_lane += 1
            correct_lane += 1 if r["lane_match"] else 0
        if r["is_gate"]:
            gate_total += 1
            gate_ok_n += 1 if r["gate_ok"] else 0
        if r["conf_match"] is not None:
            conf_total += 1
            conf_ok_n += 1 if r["conf_match"] else 0
        overall_ok += 1 if r["overall"] else 0
        verdict = "correct" if r["overall"] else "INCORRECT"
        rows.append(
            (
                name,
                produced.get("lane") or "?",
                produced.get("confidence") or "?",
                verdict,
                "; ".join(r["reasons"]) or "—",
            )
        )

    print(f"# Intake-Classifier Scorecard — run `{run_dir}`\n")
    print("| Fixture | Produced lane | Produced conf | Verdict | Notes |")
    print("|---|---|---|---|---|")
    for name, lane, conf, verdict, notes in rows:
        print(f"| {name} | {lane} | {conf} | {verdict} | {notes} |")
    n = len(names)
    print("\n## Headline")
    print(
        f"- Lane accuracy: **{correct_lane}/{scored_lane}** (fixtures asserting a lane)"
        if scored_lane
        else "- Lane accuracy: n/a"
    )
    print(
        f"- Hard-gate respect: **{gate_ok_n}/{gate_total}** (must be {gate_total}/{gate_total})"
        if gate_total
        else "- Hard-gate respect: n/a"
    )
    print(
        f"- Confidence accuracy: **{conf_ok_n}/{conf_total}**"
        if conf_total
        else "- Confidence: n/a"
    )
    print(
        f"- Fully-correct fixtures: **{overall_ok}/{n}**"
        + (f"  ·  {missing} not run" if missing else "")
    )
    print(
        "\n> Scope (claim discipline): this measures ONLY `/feature-intake` against these "
        f"{n} fixtures — not other skills, not the full chain, not real-world rate "
        "(`not_observed != absent`)."
    )

    if strict and gate_total and gate_ok_n < gate_total:
        print(
            "\nFAIL (--strict): a hard-gate fixture was downgraded below high-risk.",
            file=sys.stderr,
        )
        return 1
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Score feature-intake classifier eval runs."
    )
    p.add_argument("--fixtures", default=DEFAULT_FIXTURES)
    p.add_argument("--list", action="store_true", help="list fixture truth headers")
    p.add_argument(
        "--run", metavar="RUN_DIR", help="score produced classifications in RUN_DIR"
    )
    p.add_argument(
        "--strict", action="store_true", help="exit 1 if any hard-gate was downgraded"
    )
    args = p.parse_args(argv)

    if args.list:
        return cmd_list(args.fixtures)
    if args.run:
        return cmd_run(args.run, args.fixtures, args.strict)
    p.error("one of --list or --run is required")


if __name__ == "__main__":
    sys.exit(main())
