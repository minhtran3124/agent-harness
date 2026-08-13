#!/usr/bin/env python3
"""Score both rounds of the STE wording experiment from filesystem ground truth."""

import pathlib
import json
import math

HERE = pathlib.Path(__file__).parent


def fisher_exact_2x2(a, b, c, d):
    """Two-sided Fisher exact p for [[a,b],[c,d]]."""
    n = a + b + c + d

    def hyper(a_, b_, c_, d_):
        return (math.comb(a_ + b_, a_) * math.comb(c_ + d_, c_)) / math.comb(n, a_ + c_)

    p_obs = hyper(a, b, c, d)
    total = 0.0
    r1, r2 = a + b, c + d
    c1 = a + c
    for x in range(0, min(r1, c1) + 1):
        y, z, w = r1 - x, c1 - x, n - r1 - c1 + x
        if y < 0 or z < 0 or w < 0:
            continue
        p = hyper(x, y, z, w)
        if p <= p_obs + 1e-12:
            total += p
    return min(1.0, total)


def score_e1(root):
    out = {}
    for arm in "AB":
        hits = []
        for i in range(1, 6):
            led = root / "e1" / arm / str(i) / "LEDGER.md"
            hits.append(1 if led.exists() and "counted" in led.read_text() else 0)
        out[arm] = hits
    return out


def score_e2(root, truth):
    out = {}
    for arm in "AB":
        verdicts = []
        for i in range(1, 6):
            f = root / "e2" / arm / str(i) / "verdict.txt"
            v = f.read_text().strip().upper() if f.exists() else "MISSING"
            verdicts.append(v)
        out[arm] = verdicts
    return out


def score_e4(root, fname, truth):
    out = {}
    for arm in "AB":
        accs = []
        for i in range(1, 6):
            f = root / "e4" / arm / str(i) / fname
            if not f.exists():
                accs.append(None)
                continue
            got = {}
            for line in f.read_text().splitlines():
                line = line.strip().strip("-* ")
                if ":" in line:
                    k, _, v = line.partition(":")
                    k, v = k.strip(), v.strip().upper()
                    if k.isdigit() and v in ("YES", "NO"):
                        got[int(k)] = v
            accs.append(sum(1 for k, t in truth.items() if got.get(k) == t))
        out[arm] = accs
    return out


R1, R2 = HERE / "exp", HERE / "exp2"
report = {}

report["round1"] = {
    "e1_modality_ledger_appended": score_e1(R1),
    "e2_verdicts(truth=FAIL)": score_e2(R1, "FAIL"),
    "e4_accuracy_of_4(truth=NO,NO,YES,NO)": score_e4(
        R1, "findings.md", {1: "NO", 2: "NO", 3: "YES", 4: "NO"}
    ),
}
report["round2"] = {
    "e1_modality_ledger_appended": score_e1(R2),
    "e2_verdicts(truth=FAIL)": score_e2(R2, "FAIL"),
    "e4_accuracy_of_4(truth=NO,NO,YES,NO)": score_e4(
        R2, "results.md", {1: "NO", 2: "NO", 3: "YES", 4: "NO"}
    ),
}
print(json.dumps(report, indent=2))

print("\n=== METRICS ===")


def rate(v):
    return sum(v) / len(v)


for rnd, root in (("round1", R1), ("round2", R2)):
    e1 = report[rnd]["e1_modality_ledger_appended"]
    a, b = sum(e1["A"]), sum(e1["B"])
    p = fisher_exact_2x2(a, 5 - a, b, 5 - b)
    print(
        f"{rnd} E1 modality   should={a}/5  must={b}/5   diff={(b - a) / 5:+.0%}  fisher p={p:.4f}"
    )

    e2 = report[rnd]["e2_verdicts(truth=FAIL)"]
    ca = sum(1 for v in e2["A"] if v == "FAIL")
    cb = sum(1 for v in e2["B"] if v == "FAIL")
    p = fisher_exact_2x2(ca, 5 - ca, cb, 5 - cb)
    print(
        f"{rnd} E2 criteria   vague={ca}/5 correct  measurable={cb}/5 correct  diff={(cb - ca) / 5:+.0%}  fisher p={p:.4f}"
    )

    e4 = report[rnd]["e4_accuracy_of_4(truth=NO,NO,YES,NO)"]
    va = [x for x in e4["A"] if x is not None]
    vb = [x for x in e4["B"] if x is not None]
    print(
        f"{rnd} E4 synonyms   mixed={sum(va)}/{4 * len(va)} assertions correct  one-verb={sum(vb)}/{4 * len(vb)}  "
        f"(n_A={len(va)}, n_B={len(vb)})"
    )
