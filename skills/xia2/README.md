# xia2 — Research-First Feature Discovery (Portable)

A portable version of `xia`. All logic — including the risk-classification signals — is built into `SKILL.md` as common cross-project vocabulary. The same skill works across projects with no per-project config file.

`xia2` enforces *research before code* via a HARD-GATE and classifies each feature into **Quick / Standard / Deep** depth modes based on concrete signals (not gut feel).

> **Difference from `xia`:** `xia` is project-specific (Edgeful API only). `xia2` is portable and zero-config — copy the folder and it classifies from its built-in Common signals.

---

## When to invoke

| Trigger | Should you use `xia2`? |
|---|---|
| Adding a new feature, capability, or integration | **Yes** |
| Modifying behaviour with possible local precedent | **Yes** |
| Bumping a dependency, changing schema, touching shared infrastructure | **Yes** |
| One-line typo fix, doc-only edit, comment cleanup | No — overkill |
| Bug fix where root cause is already known | No — use `/systematic-debugging` |

When in doubt, invoke. The HARD-GATE prevents code being written, so the cost of a false positive is low (one research brief).

---

## How to invoke

```
/xia2 <feature description>                 # default: Standard depth
/xia2 <feature> --depth=quick|standard|deep # explicit override
```

Skill auto-classifies depth from the built-in **Common signals** in `SKILL.md` (no config file). Override with `--depth=` if you have stronger context than the prompt conveys.

To bypass the research step entirely (rare): start the prompt with *"skip research"* or *"just implement it"*. The skill notes the waiver but still surfaces any Deep-signal risks per the HARD-GATE rule.

**First time in a project?** Run `bash scripts/init-structure.sh` once to scaffold `specs/` and `docs/solutions/`. xia2 itself needs no per-project setup.

---

## File layout

| Path | Purpose | Loaded at runtime? |
|---|---|---|
| `SKILL.md` | Universal skill definition: HARD-GATE, Decision Procedure, Depth Modes, workflow steps | **Yes** — entry point |
| `references/research-brief-template.md` | Output template the skill renders in Step 7 | **Yes** — Step 7 |
| `tests/structural/depth-modes-test-cases.md` | Decision Procedure regression tests (against the common signals) | No — validation only |
| `tests/behavioural/pressure-scenarios.md` | RED/GREEN scenarios verifying HARD-GATE adherence | No — validation only |
| `README.md` | This file | No |

**Runtime vs validation:** anything under `references/` may be loaded by the skill mid-execution. Anything under `tests/` exists only for humans (or future agents) maintaining the skill.

**Two test artifacts, two purposes:**
- `tests/structural/` — **classification correctness.** 30 prompts walked through the Decision Procedure to verify the rule outputs the right depth.
- `tests/behavioural/` — **HARD-GATE adherence.** 7 RED/GREEN scenarios verifying the agent holds the gate under pressure (doesn't skip research, doesn't guess stack from folder names).

Use both when validating major skill changes.

---

## Forking for another project

To use `xia2` in a different project:

1. **Copy the entire `.claude/skills/xia2/` folder** to `<new-project>/.claude/skills/xia2/`. No auto-scan skill needed — xia2 is zero-config.
2. **Scaffold structure** — run `bash scripts/init-structure.sh` in the new repo to create `specs/` and `docs/solutions/`.
3. **Keep `tests/structural/depth-modes-test-cases.md`** — it is a portable regression set against the common signals; extend it with project-specific prompts if useful.
4. **Keep `tests/behavioural/pressure-scenarios.md`** — most scenarios are universal (project-specific examples are easy to swap).

What's universal (don't customize):
- `SKILL.md` — Decision Procedure, Tiebreakers, Workflow steps, Guardrails
- `references/research-brief-template.md` — output format
- `tests/behavioural/pressure-scenarios.md` — most scenarios

What's project-specific (optional to extend):
- `tests/structural/depth-modes-test-cases.md` — add concrete prompts for your repo's signals
- `README.md` — file layout if you add/remove files

---

## Maintenance workflow

### When you change `SKILL.md`

If you edit any of these surfaces, you **must** re-run the structural test suite:

- HARD-GATE wording or rules
- Decision Procedure (the Quick/Standard/Deep classifier)
- Depth Modes table (signals, conditions, examples)
- Tiebreakers
- Re-evaluation gate (the upgrade rules triggered after reading knowledge base docs)
- Step 1 waiver clause

Edits that **do not** require a re-run: `Tool Routing` table, `Guardrails` list (unless they change classification), wording polish in non-classifier sections, Sub-step 2b knowledge base lookup mechanism (INDEX-first vs grep — changes *how* files are found, not *when depth upgrades trigger*).

### Re-run procedure

1. Open `tests/structural/depth-modes-test-cases.md`.
2. For each test case, mentally walk the prompt through the **updated** `SKILL.md` Decision Procedure against the Common signals.
3. Record the result in a new column (e.g., `Run 4 result`).
4. Compare to the most recent passing run.
5. Fill the Δ column:
   - **stable** — same result as prior run
   - **<change> by F<N>** — flipped intentionally because of a fix
   - **regression** — flipped unintentionally; you must either fix `SKILL.md` or update the test's `Expected` (with justification)
6. Add a `Re-run Delta` subsection summarising what changed and why.
7. Update the `Summary` table totals.

### Critical regression checks

These are the canary tests — if any one flips when it shouldn't, you've broken the procedure or the project mapping:

| Check | Triggered when |
|---|---|
| TC-01 to TC-04 must remain Quick | Any time you tighten Quick conditions |
| TC-19, TC-21 must remain Deep | Any time you loosen Deep signals or narrow the high-blast definition in the Common signals |
| TC-20 must remain Standard *(initial)* | Any time you change Tiebreaker #1 or the Re-evaluation gate |
| TC-29 must surface a risk warning | Any time you edit the HARD-GATE waiver clause |

### When you add new test cases

1. Decide: **structural** (signal coverage / boundary case) or **behavioural** (HARD-GATE pressure)?
2. Pick `TC-NN` above the current max (structural) or `S-NN` (behavioural).
3. Define: *Prompt*, *Expected*, *Triggering signal/rule*. For pressure cases also add *Pressure type*.
4. Walk the prompt through the Decision Procedure to fill *Result*.
5. Update the `Summary` table totals.
6. If a new gap surfaces, document as a new `F`-numbered Finding with priority and proposed fix.

### When a Finding is resolved

1. Apply the fix to `SKILL.md` (use `Edit`, not `Write` — preserve untouched sections).
2. Re-run the structural test suite (above).
3. Mark the Finding as `✅ RESOLVED` with the run number, date, and a one-line summary of the applied fix.
4. Verify the case that originally surfaced the Finding now passes.

---

## Open findings (current)

| ID | Status | Note |
|---|---|---|
| F1, F7, F8 | ✅ Resolved (Run 2 in `xia`, ported into `xia2`) | Quick condition tightened; implicit signals named; HARD-GATE waiver extended |
| F2 – F5 | Informational | No action; observations only |
| F6 — bundled scope | Open *(cosmetic)* | OR-logic handles it; explicit naming optional |
| F9 — familiarity bias | Open *(cosmetic)* | Deep signals fire correctly; explicit naming optional |

See `tests/structural/depth-modes-test-cases.md#findings` for full descriptions.

---

## Why this validation matters

Without the test suite, every change to `SKILL.md` is blind — there's no way to know if a tweak fixes a real bug, breaks correct cases, or both. The test files convert `SKILL.md` from prose into a **verifiable contract**:

- *Decision Procedure* defines the rule, keyed off the built-in Common signals.
- *Test cases* exercise the rule across realistic prompts and pressure patterns.
- *Run-by-Run columns* prove the combined behaviour didn't drift across edits.
- *Findings* convert "this feels off" into "TC-NN flipped because rule X is too literal".

Treat the test suites as the canonical regression check. If a future maintainer can't reproduce the most recent Run results, the skill has drifted.

---

## See also

- `xia` — the original Edgeful-specific version. Kept for backwards compatibility; `xia2` is the recommended portable replacement.
- `scripts/init-structure.sh` — scaffolds the structural dirs (`specs/`, `docs/solutions/`) in a bare repo.
