# Design — Slim the skill surface (review items 1→6)

> Slug: `slim-skill-surface` · Date: 2026-07-23 · Lane: high-risk
> Scope: items 1–6 of the post-read cut list. Item 7 (xia2 depth classifier ↔ feature-intake
> lane) and item 8 (`compound` Step 5.75 → script) are **out of scope**; `visual-planner` is
> explicitly retained at the user's instruction.

## 1. What the reading found

All 14 non-`visual-planner` skills were read in full (2.817 lines of `SKILL.md` plus ~2.500
lines of sidecar prompts and scripts). Two prior hypotheses were **falsified** by that reading
and are recorded here so they are not re-proposed:

| Hypothesis (from the sampled review) | Verdict after reading | Evidence |
|---|---|---|
| The 3–4 review skills duplicate native `/code-review` | **False** | They are three mutually-blind oracles (plan / runtime / intent / delivery). `correctness-review` measured the swap: recall matched 3/3, but **3 false positives vs a baseline of 0**, at 10–15× tokens → swap rejected, FIND-B stage built then deleted |
| `evals/` is maintenance overhead measuring a moving target | **False** | 7 result files under `evals/skills/review-chain/results/` drove real deletions and the threshold-75 decision |

What the reading **did** confirm, and one thing it surfaced that sampling missed:

**Boilerplate is real and extremely unevenly distributed.** Counting the sections that exist to
persuade or hand-hold a model (`Advantages`, `Example Workflow`, `Red Flags`, `Common Mistakes`,
`Quick Reference`, `Key Principles`, `Remember`, `Process Flow`) plus fenced DOT graphs:

| Skill | Lines | Boilerplate + DOT | % |
|---|---:|---:|---:|
| `subagent-driven-development` | 484 | 260 | **54%** |
| `brainstorming` | 172 | 82 | **48%** |
| `using-git-worktrees` | 315 | 67 | 21% |
| `executing-plans` | 126 | 26 | 21% |
| `finishing-a-development-branch` | 194 | 28 | 14% |
| **8 other skills** | 1.526 | **0** | **0%** |

The eight skills at 0% are the newer ones (`feature-intake`, `correctness-review`,
`intent-review`, `context-propagation-audit`, `compound`, `xia2`, `writing-plans`, `create-pr`).
**Skill age predicts bloat better than skill purpose does** — this is not a design flaw to
redesign around, it is unmigrated legacy.

**The thing sampling missed: `skills/brainstorming/scripts/` is 1.084 lines.** It contains
`server.js` (338 lines implementing the RFC 6455 WebSocket handshake and frame encoding **by
hand**), `frame-template.html`, `helper.js`, start/stop scripts, and a 276-line
`visual-companion.md` operating manual. Its purpose is to show mockups and diagrams in a
browser during brainstorming — which Artifacts now do natively, with no server, no port, no
30-minute inactivity timeout, and no `.server-info` liveness dance. Nothing outside
`skills/brainstorming/` references any of it.

## 2. The principle applied

> A prompt that **teaches the model how to work** loses value as models improve.
> A mechanism that **constrains what the model cannot constrain in itself** does not.

Every cut below is on the first side of that line. Nothing on the second side is touched:
`branch-isolation-guard`, the commit gates, `ci-strict-gate`, `verify_summary --check`, the
review receipt, and all three review oracles survive unchanged.

Two corollaries that shape the specific edits:

- **Deleting the fallback is the point.** `using-git-worktrees` opens with "prefer the native
  worktree tool" and then spends 250 lines on the manual `git worktree` path. Saying "prefer
  the native tool" while carrying the fallback is how the fallback survives forever. The native
  tool (`EnterWorktree`) exists in this harness; the manual path becomes a two-line escape
  hatch, not a procedure.
- **A skill whose only distinguishing feature is *where it is invoked* is not a skill.**
  `executing-plans` differs from `subagent-driven-development` in exactly one respect: it runs
  in a separate session. That is a property of the invocation, not of the workflow — both
  validate the plan, both branch, both run tasks, both run `/correctness-review` →
  `/intent-review`, both hand off to `finishing-a-development-branch`.

## 3. The six changes

| # | Change | Removes | What is deliberately kept |
|---|---|---:|---|
| 1 | Delete `skills/brainstorming/scripts/` + `visual-companion.md`; drop the Visual Companion section from `SKILL.md` | 1.084 | The HARD-GATE (no implementation before an approved design) and the offer-visuals judgment, rewritten as one line pointing at Artifacts |
| 2 | `using-git-worktrees` → ~60 lines | ~255 | Step 0 isolation detection incl. the **submodule guard**; the native-tool-first rule; branch naming `<type>/<slug>`; and `deploy-harness.sh --target` (without it a worktree has no `.claude/`) |
| 3 | `subagent-driven-development`: drop `Advantages`, `Example Workflow`, `Red Flags`, both DOT graphs | ~260 | Every gate: branch isolation, `status: active`, wave policy, implementer statuses, correctness → intent chain, **review receipt + the conjunction ship gate**, deviation logging |
| 4 | Fold `executing-plans` into `subagent-driven-development` as a "parallel session" subsection | 126 | The Step-0 four guardrail checks — they are a real pre-flight validation, moved not deleted |
| 5 | `brainstorming`: drop the DOT graph and `Key Principles` | ~82 | The checklist, the spec-review loop, the user-review gate, the xia2 → writing-plans handoff |
| 6 | Fold `create-pr`'s template into `finishing-a-development-branch` Step 3; delete `review-diff` | 135 | The PR body shape (title/summary/tasks/notes + conditional diagram) survives inline, ~15 lines |

### Why `review-diff` is a deletion and not a trim

It is the only skill with **no consumer**: nothing invokes it, it gates nothing, and its output
(`.review/review.md`) is read by no other step. Its content is 40 lines of hardcoded dark-theme
Mermaid hex colors (`fill:#0d3320,stroke:#238636,…`) that render wrong on a light background. A
diff walkthrough with diagrams is something the model produces on request; a stale palette
committed to the repo is not an asset.

### Why `create-pr` is a merge and not a deletion

It has exactly one consumer — `finishing-a-development-branch` Step 3.3 — and its useful core
is the PR-body shape plus one genuinely non-obvious rule: *include a diagram only when the
change is flow-shaped; omit the section otherwise*. That is worth keeping. A separate skill
file, a registry entry, and a cross-skill dispatch for ~15 lines of template are not.

## 4. Registry and reference consequences

Deleting three skills is not a `rm -rf`; four mechanisms key on the skill inventory:

1. **`harness-manifest.json` → `skills[]`** — `scripts/check_manifest.py` checks it
   bidirectionally against `skills/*/SKILL.md` on disk. A deletion without a manifest edit
   fails CI, and vice versa.
2. **`scripts/lint-doc-truth.sh`** — lints `CLAUDE.md`, `README.md`, `HARNESS.md`,
   `skills/README.md`, `agents/*.md`, `rules/*.md` for dangling paths. Every reference to a
   deleted skill in those files must go, or CI fails.
3. **`scripts/deploy-harness.sh`** — prunes deleted-skill orphans from `.claude/` via its
   per-deploy manifest, so the deletion propagates on the next sync without manual cleanup.
4. **Live cross-skill references** — `executing-plans` is named in `rules/plan-format.md`,
   `rules/wave-parallelism.md`, `skills/writing-plans/SKILL.md`,
   `skills/using-git-worktrees/SKILL.md`, `skills/subagent-driven-development/SKILL.md`,
   `templates/structure/specs-README.md`, and `CLAUDE.md`; `review-diff` in
   `skills/correctness-review/SKILL.md`; `create-pr` in
   `skills/finishing-a-development-branch/SKILL.md`.

**`specs/**` and `docs/research/**` are NOT scrubbed.** Roughly 30 shipped specs mention
`executing-plans`. Those are the historical record of what was true when they shipped; rewriting
history to match the present is how an audit trail stops being one. `lint-doc-truth.sh` already
excludes both paths, so leaving them is also CI-clean.

## 5. Risk of over-cutting, and the guard against it

The real hazard is not deleting too much text — it is deleting a *gate* hidden inside a
boilerplate-looking section. `subagent-driven-development`'s `Red Flags` list, for example,
contains two rules that exist nowhere else in the file: *"never hand off with a stale review
receipt"* and *"never ship with an SC lacking a passing Criterion row"*.

The guard is mechanical, not editorial: **Success Criteria SC-5, SC-6 and SC-7 grep for a
load-bearing string in each trimmed file** (`check_review_receipt`, `deploy-harness.sh --target`,
the parallel-session path). Before deleting any section, the rule for the executing agent is:
if a line states a *constraint* rather than an *explanation*, it moves — it does not disappear.

## 6. Expected effect

- Skill surface: 2.817 → ~1.900 lines of `SKILL.md` (−33%), plus 1.084 lines of scripts deleted.
- Registered skills: 15 → 12.
- Skills carrying >20% boilerplate: 4 → 0.
- No change to: any review oracle, `feature-intake`, `evals/`, `visual-planner`, every hook, and
  every CI gate.
