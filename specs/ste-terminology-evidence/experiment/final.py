#!/usr/bin/env python3
"""Re-derive the STE experiment metrics from archived per-trial outcomes."""

from __future__ import annotations

import math
import pathlib
import re
import sys
from dataclasses import dataclass, field

HERE = pathlib.Path(__file__).parent
RAW_TRIALS = HERE / "raw-trials.txt"
TRUTH = ("NO", "NO", "YES", "NO")

MODALITY_RE = re.compile(r"^r([12])-e1-([AB])(\d+) (APPENDED|SKIPPED)$")
VERDICT_RE = re.compile(r"^r([12])-e2(?:-(sonnet|opus))?-([AB])(\d+) (PASS|FAIL)$")
FINDINGS_RE = re.compile(
    r"^r([12])-e4-([AB])(\d+) "
    r"1: (YES|NO) 2: (YES|NO) 3: (YES|NO) 4: (YES|NO)$"
)


class TrialDataError(ValueError):
    """The archived trial ledger is incomplete, duplicated, or malformed."""


@dataclass
class TrialData:
    modality: dict[tuple[int, str], dict[int, str]] = field(default_factory=dict)
    verdicts: dict[tuple[int, str, str], dict[int, str]] = field(default_factory=dict)
    findings: dict[tuple[int, str], dict[int, tuple[str, ...]]] = field(
        default_factory=dict
    )


def _record(mapping, key, trial, value, line_number):
    trials = mapping.setdefault(key, {})
    if trial in trials:
        raise TrialDataError(f"line {line_number}: duplicate trial for {key} #{trial}")
    trials[trial] = value


def parse_trials(text: str) -> TrialData:
    data = TrialData()
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if match := MODALITY_RE.fullmatch(line):
            rnd, arm, trial, outcome = match.groups()
            _record(data.modality, (int(rnd), arm), int(trial), outcome, line_number)
        elif match := VERDICT_RE.fullmatch(line):
            rnd, model, arm, trial, verdict = match.groups()
            model = model or "sonnet"
            _record(
                data.verdicts,
                (int(rnd), model, arm),
                int(trial),
                verdict,
                line_number,
            )
        elif match := FINDINGS_RE.fullmatch(line):
            rnd, arm, trial, *answers = match.groups()
            _record(
                data.findings,
                (int(rnd), arm),
                int(trial),
                tuple(answers),
                line_number,
            )
        else:
            raise TrialDataError(
                f"line {line_number}: unrecognized trial record: {line}"
            )
    return data


def _require_trials(mapping, key, count):
    expected = set(range(1, count + 1))
    actual = set(mapping.get(key, {}))
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise TrialDataError(
            f"{key}: missing trials {missing}; unexpected trials {extra}"
        )


def validate(data: TrialData) -> None:
    for rnd, count in ((1, 5), (2, 10)):
        for arm in "AB":
            _require_trials(data.modality, (rnd, arm), count)

    for rnd, model, count in ((1, "sonnet", 5), (2, "sonnet", 5), (2, "opus", 3)):
        for arm in "AB":
            _require_trials(data.verdicts, (rnd, model, arm), count)

    for rnd, arm, count in ((1, "A", 5), (1, "B", 4), (2, "A", 5), (2, "B", 5)):
        _require_trials(data.findings, (rnd, arm), count)

    unexpected_verdicts = set(data.verdicts) - {
        (1, "sonnet", "A"),
        (1, "sonnet", "B"),
        (2, "sonnet", "A"),
        (2, "sonnet", "B"),
        (2, "opus", "A"),
        (2, "opus", "B"),
    }
    if unexpected_verdicts:
        raise TrialDataError(
            f"unexpected verdict groups: {sorted(unexpected_verdicts)}"
        )


def fisher(a, b, c, d):
    n = a + b + c + d

    def hyper(a_, b_, c_, d_):
        return math.comb(a_ + b_, a_) * math.comb(c_ + d_, c_) / math.comb(n, a_ + c_)

    observed = hyper(a, b, c, d)
    row_one, column_one = a + b, a + c
    total = 0.0
    for x in range(min(row_one, column_one) + 1):
        y, z, w = row_one - x, column_one - x, n - row_one - column_one + x
        if min(y, z, w) < 0:
            continue
        probability = hyper(x, y, z, w)
        if probability <= observed + 1e-12:
            total += probability
    return min(1.0, total)


def _count(mapping, key, outcome):
    return sum(value == outcome for value in mapping[key].values())


def render(data: TrialData) -> str:
    validate(data)
    lines = ["=" * 74]
    lines.append(
        "H1  §2 modality: does 'must' beat 'should' when a constraint competes?"
    )
    for rnd, label, count in (
        (1, "round 1 (no competing constraint)", 5),
        (2, "round 2 (code freeze + foreign file)", 10),
    ):
        arm_a = _count(data.modality, (rnd, "A"), "APPENDED")
        arm_b = _count(data.modality, (rnd, "B"), "APPENDED")
        lines.append(
            f"  {label:39} should {arm_a}/{count}   must {arm_b}/{count}   "
            f"p={fisher(arm_a, count - arm_a, arm_b, count - arm_b):.4f}"
        )

    lines.append("=" * 74)
    lines.append(
        "H2  §3 vague acceptance: does a measurable criterion beat 'is it correct?'"
    )
    pooled = {"A": 0, "B": 0}
    for rnd, model, label, count in (
        (1, "sonnet", "round 1 (obvious defect)", 5),
        (2, "sonnet", "round 2 sonnet (debatable)", 5),
        (2, "opus", "round 2 opus  (debatable)", 3),
    ):
        arm_a = _count(data.verdicts, (rnd, model, "A"), "FAIL")
        arm_b = _count(data.verdicts, (rnd, model, "B"), "FAIL")
        if rnd == 2:
            pooled["A"] += arm_a
            pooled["B"] += arm_b
        lines.append(
            f"  {label:28} vague {arm_a}/{count}   measurable {arm_b}/{count}   "
            f"p={fisher(arm_a, count - arm_a, arm_b, count - arm_b):.4f}"
        )
    lines.append(
        f"  {'round 2 POOLED (n=8/arm)':28} vague {pooled['A']}/8   "
        f"measurable {pooled['B']}/8   "
        f"p={fisher(pooled['A'], 8 - pooled['A'], pooled['B'], 8 - pooled['B']):.4f}"
    )

    lines.append("=" * 74)
    lines.append(
        "H3  §1 one concept = one word: does mixed check/verify/confirm/validate hurt?"
    )
    for rnd, label in (
        (1, "round 1 (easy traps)"),
        (2, "round 2 (read-proof traps)"),
    ):
        scores = {}
        for arm in "AB":
            answers = data.findings[(rnd, arm)].values()
            correct = sum(
                sum(got == want for got, want in zip(row, TRUTH)) for row in answers
            )
            scores[arm] = (correct, 4 * len(answers))
        difference = scores["A"][0] / scores["A"][1] - scores["B"][0] / scores["B"][1]
        lines.append(
            f"  {label:28} mixed {scores['A'][0]}/{scores['A'][1]}   "
            f"one-verb {scores['B'][0]}/{scores['B'][1]}   diff={difference:+.0%}"
        )
    lines.append("=" * 74)
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        data = parse_trials(RAW_TRIALS.read_text(encoding="utf-8"))
        print(render(data), end="")
    except (OSError, TrialDataError) as exc:
        print(f"experiment data error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
