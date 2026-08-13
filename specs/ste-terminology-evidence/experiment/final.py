#!/usr/bin/env python3
"""Final metrics across both rounds + extensions."""

import pathlib
import math

HERE = pathlib.Path(__file__).parent
R1, R2 = HERE / "exp", HERE / "exp2"


def fisher(a, b, c, d):
    n = a + b + c + d

    def h(a_, b_, c_, d_):
        return math.comb(a_ + b_, a_) * math.comb(c_ + d_, c_) / math.comb(n, a_ + c_)

    obs = h(a, b, c, d)
    r1, c1 = a + b, a + c
    tot = 0.0
    for x in range(min(r1, c1) + 1):
        y, z, w = r1 - x, c1 - x, n - r1 - c1 + x
        if min(y, z, w) < 0:
            continue
        p = h(x, y, z, w)
        if p <= obs + 1e-12:
            tot += p
    return min(1.0, tot)


def ledger(root, arm, n):
    return sum(
        1
        for i in range(1, n + 1)
        if (f := root / "e1" / arm / str(i) / "LEDGER.md").exists()
        and "counted" in f.read_text()
    )


def verdicts(root, sub, arm, n):
    out = []
    for i in range(1, n + 1):
        f = root / sub / arm / str(i) / "verdict.txt"
        out.append(f.read_text().strip().upper() if f.exists() else "MISSING")
    return out


def acc(root, arm, fname):
    truth = {1: "NO", 2: "NO", 3: "YES", 4: "NO"}
    tot = ok = 0
    for i in range(1, 6):
        f = root / "e4" / arm / str(i) / fname
        if not f.exists():
            continue
        got = {}
        for line in f.read_text().splitlines():
            k, _, v = line.strip().strip("-* ").partition(":")
            if k.strip().isdigit() and v.strip().upper() in ("YES", "NO"):
                got[int(k.strip())] = v.strip().upper()
        tot += 4
        ok += sum(1 for k, t in truth.items() if got.get(k) == t)
    return ok, tot


print("=" * 74)
print("H1  §2 modality: does 'must' beat 'should' when a constraint competes?")
r1a, r1b = ledger(R1, "A", 5), ledger(R1, "B", 5)
print(
    f"  round 1 (no competing constraint)  should {r1a}/5   must {r1b}/5   p={fisher(r1a, 5 - r1a, r1b, 5 - r1b):.4f}"
)
r2a, r2b = ledger(R2, "A", 10), ledger(R2, "B", 10)
print(
    f"  round 2 (code freeze + foreign file) should {r2a}/10  must {r2b}/10  p={fisher(r2a, 10 - r2a, r2b, 10 - r2b):.4f}"
)

print("=" * 74)
print("H2  §3 vague acceptance: does a measurable criterion beat 'is it correct?'")
for label, root, sub, n in (
    ("round 1 (obvious defect)", R1, "e2", 5),
    ("round 2 sonnet (debatable)", R2, "e2", 5),
    ("round 2 opus  (debatable)", R2, "e2opus", 3),
):
    va, vb = verdicts(root, sub, "A", n), verdicts(root, sub, "B", n)
    ca, cb = va.count("FAIL"), vb.count("FAIL")
    print(
        f"  {label:28} vague {ca}/{n}   measurable {cb}/{n}   p={fisher(ca, n - ca, cb, n - cb):.4f}"
    )
pa, pb = 0 + 1, 5 + 3  # round-2 sonnet+opus pooled: vague 1/8 correct, measurable 8/8
print(
    f"  {'round 2 POOLED (n=8/arm)':28} vague {pa}/8   measurable {pb}/8   p={fisher(pa, 8 - pa, pb, 8 - pb):.4f}"
)

print("=" * 74)
print("H3  §1 one concept = one word: does mixed check/verify/confirm/validate hurt?")
for label, root, fn in (
    ("round 1 (easy traps)", R1, "findings.md"),
    ("round 2 (read-proof traps)", R2, "results.md"),
):
    oa, ta = acc(root, "A", fn)
    ob, tb = acc(root, "B", fn)
    print(
        f"  {label:28} mixed {oa}/{ta}   one-verb {ob}/{tb}   diff={oa / ta - ob / tb:+.0%}"
    )
print("=" * 74)
