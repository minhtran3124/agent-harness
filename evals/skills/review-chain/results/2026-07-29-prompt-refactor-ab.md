# Review-Chain Results — skill prompt refactor A/B (2026-07-29)

**Run date:** 2026-07-29
**`claude --version`:** `2.1.220 (Claude Code)`
**Arms:**
- **baseline** — worktree `/private/tmp/harness-skills-baseline-ab` @ `924af147e9721c0e09fb5d3f25a71e4465ea9b10` (pre-refactor prompt surface), harness deployed.
- **candidate** — worktree `/tmp/harness-skills-candidate-ab` @ `dbdd2b70afd5d76637f0a87d6014c8dff9ae4763` (`refactor/skill-prompt-surface`), harness deployed.

**Fixtures:** all **7**, at their current committed revision.
**Scorer threshold referenced:** **75** (unchanged by this refactor).

## ⚠️ Harness caveat — read before trusting any number

Same **condensed harness** as `2026-07-22-threshold-75.md`, not the full `/correctness-review` +
`/intent-review` pipeline: one blind reviewer per fixture (`sonnet`, `--effort low`) doing a
combined correctness + intent pass and self-reporting confidence 0–100 per finding. That
confidence is a **proxy** for the SCORE stage, not a run of the 6-angle FIND → independent-scorer
pipeline.

Two protocol differences from the 2026-07-22 run, both deliberate:

1. **Blindness is enforced by construction.** Each reviewer ran with **no tools** and the
   fixture's `intent.md` + `diff.patch` inlined, so `truth.md` was unreachable rather than merely
   off-limits by instruction.
2. **This is an A/B, not a single arm.** The identical prompt ran in both worktrees; the only
   variable is the deployed harness surface each session loads.

Consequence: **do not trend these numbers against `2026-07-22-threshold-75.md`.** That run used a
different client version (2.1.217), a different HEAD, and a reviewer that could Read the repo.
The valid comparison here is baseline-arm vs candidate-arm, both from this sitting.
`not_observed != absent`. **n = 1 run per cell.**

## Scoring (blind review vs `truth.md`)

| fixture | expected oracle | baseline | conf | candidate | conf | delta |
|---|---|---|---|---|---|---|
| none-deref | correctness | **caught** (unguarded `Optional[User]` → `user.email`) | 90 | **caught** (same line, same class) | 90 | none |
| missing-await | correctness | **caught** (coroutine never awaited) | 95 | **caught** (same) | 97 | none |
| soft-delete-filter | correctness | **missed** (reported "no defects found") | — | **missed** (reported unverifiable premises only) | — | none — see Fixture staleness |
| excess-scope | intent | **caught** (unrequested `get_profile` rewrite + service layer) | 85 | **caught** (same) | 85 | none |
| intent-gap | intent | **caught** (empty-name check on create, absent on update) | 95 | **caught** (same) | 97 | none |
| context-rule-unread | context-propagation-audit | **caught** by correctness (reference relied on but never Read) — exceeds the answer key | 80 | **missed** — matches the answer key, which expects both oracles to miss | — | candidate matches key; baseline exceeds it |
| stale-inline-policy | context-propagation-audit | **caught** by correctness (hand-copied Rule-4 subset may diverge from source of truth) | 55 | **caught** (same, better articulated) | 65 | none |

## Headline numbers

- **On the 5 fixtures whose expected oracle IS correctness or intent: baseline 4/5, candidate
  4/5 — identical, with the identical miss (`soft-delete-filter`).** This is the load-bearing
  number for SC-6: the refactored prompts show **no recall regression** on the defect classes
  these two oracles are contracted to catch.
- On the 2 fixtures whose expected oracle is `/context-propagation-audit` (answer key: both
  oracles *should* miss), baseline incidentally caught both and candidate caught one. Neither is a
  contract these two oracles owe; see "context-rule-unread" below.
- **False positives: 2 soft per arm — equal count.** Both arms flagged the pre-declared
  `none-deref` `require_admin` "drift" FP and the pre-declared `soft-delete-filter` `order_by`
  excess FP. No new false-positive *class* appeared in the candidate.

## The one real difference worth acting on — FP confidence crossed the threshold

The `none-deref` `require_admin` finding is the false positive `truth.md` pre-declares for that
fixture (the route is an intentional admin-gated cross-user lookup). Both arms produced it. The
confidences differ across the fix-loop line:

| arm | pre-declared FP | confidence | admitted at threshold 75? |
|---|---|---|---|
| baseline | `require_admin` is intent drift | 65 | **no** — held advisory |
| candidate | `require_admin` is intent drift | 75 | **yes** — enters the fix loop |

Using self-reported confidence as the SCORE proxy, the candidate arm would have pushed a known
false positive into the fix loop where the baseline arm held it back. This is **n = 1, one model,
one run, and a proxy for the real independent scorer** — it is a signal to watch, not a
demonstrated regression, and it is not a recall or safety failure. It is recorded here rather than
smoothed over, and it is the reason SC-6 is reported as "no recall regression" rather than "no
regression".

## context-rule-unread — the candidate matches the answer key

`truth.md` for this fixture states plainly that `/correctness-review` and `/intent-review` are
**expected to record `missed`**: the defect is instruction *delivery* across isolated contexts,
which neither oracle structurally models, and the fixture exists to prove a class only
`/context-propagation-audit` can own.

- The **candidate** arm missed it — i.e. produced the answer key's expected verdict. Its findings
  were about deploy-path resolution (`.claude/rules/` vs `rules/`) and return-contract
  completeness, not about the reference-never-Read defect.
- The **baseline** arm caught it (confidence 80), repeating the 2026-07-22 run's "surprising
  finding" that a capable blind reviewer can see this defect when the whole thing is compressed
  into one self-contained prompt-file diff.

So the arm-to-arm difference here is the **loss of an incidental over-performance**, not the loss
of a contracted catch. The contracted guard for this class is deterministic and still green:
`bash tests/scripts/context-propagation-regression.test.sh` (SC-8) asserts both known escapes stay
blocked, and the candidate's context-boundary probes are recorded in
`evals/context-boundaries/results/2026-07-29-prompt-refactor.md`.

## Fixture staleness — `soft-delete-filter` is no longer answerable from this repo

Both arms missed `soft-delete-filter`, and the cause is the fixture, not the prompts. Its
`truth.md` grounds the soft-delete convention in `templates/stacks/fastapi/architecture.md` and
`templates/stacks/fastapi/guidelines.md`. **Neither file exists in either arm** — the bundled stack
profile was removed from the harness core before the baseline commit (`techstacks/` is now
project-owned and empty in this meta-repo). Verified:

```bash
ls /private/tmp/harness-skills-baseline-ab/templates   # no stacks/
ls /tmp/harness-skills-candidate-ab/templates          # no stacks/
```

A reviewer cannot infer "this model soft-deletes" from the diff alone — the diff shows only
`user_id` and `created_at`. The 2026-07-22 run's catch at confidence 60 came from a reviewer with
Read access to a tree that still carried the profile. This fixture therefore needs re-grounding
(state the soft-delete convention in `intent.md`, or restore a stack-profile reference that exists)
before its verdict means anything again. Recorded as a follow-up, not as a prompt regression.

## Limitations

- Condensed harness, one blind `sonnet` reviewer per cell; confidences are self-reported proxies
  for the independent SCORE stage.
- **n = 1 per cell**, one model, one client version (2.1.220). No variance estimate. The
  `require_admin` confidence delta (65 → 75) sits exactly on the threshold and is within the range
  a second run could move either way.
- Both arms share the same user-level `~/.claude` profile (user memories and global instructions),
  so that context is present in both. It is identical across arms, so it does not confound the
  differential — but it means these are not clean-room numbers.
- Measures only whether these two oracles catch these planted classes on these seven fixtures.
  Unseeded defect classes are unmeasured, not handled.
- `soft-delete-filter` is currently unanswerable from repo context (see above); treat its row as
  uninformative rather than as evidence about either arm.

## Follow-up

- Re-ground `soft-delete-filter` so its answer key does not depend on the removed
  `templates/stacks/fastapi/` profile.
- Re-run `none-deref` a few times per arm to see whether the candidate's `require_admin` FP
  confidence sits above 75 reliably or was a single-run artifact.
