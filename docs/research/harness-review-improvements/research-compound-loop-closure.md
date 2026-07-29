# Research — Is the `/compound` loop closed?

> Question: After running `/compound` and generating a file in `docs/solutions/`, do later new sessions **read it back automatically**, and does the harness **learn** from it?
> Scope: `harness-skills` repo
> Research date: 2026-06-08
> Method: trace the actual wiring (SKILL.md, settings.json, hooks/, CLAUDE.md) — not relying on README descriptions.

---

## Verdict

**The loop is OPEN (semi-closed).** `/compound` successfully **writes** durable knowledge, but the harness has **no mechanism to automatically pull** that knowledge into a new session's context. The knowledge only comes back when **a person/skill actively pulls** it.

---

## Evidence

### 1. What `/compound` writes (CONFIRMED)
`skills/compound/SKILL.md` writes to exactly 3 paths:
- `docs/solutions/<category>/<slug>.md` — entry by track (bug/knowledge/decision/failure) — *line ~90*
- `docs/solutions/critical-patterns.md` — when `severity = critical` — *line ~309*
- `docs/solutions/INDEX.md` — fully rebuilt after each run — *line ~343*

### 2. Automatic read at session start (NOT FOUND)
- ❌ No **SessionStart hook**: grep `"SessionStart"` across the repo → 0 results.
- ❌ `settings.json` / `settings.local.json` only register SessionEnd (`state-breadcrumb.sh`), no SessionStart.
- ❌ No hook in `hooks/` reads/`cat`s `docs/solutions/`.

### 3. Read by skill (pull, not push) — CONFIRMED
- **`/xia2`** (`skills/xia2/SKILL.md:93-99`): reads INDEX first → reads `critical-patterns.md` **regardless of domain** → reads at most **3** solution files by recency. Falls back to grep if the Index is not declared in `PROJECT.md`.
- **`/brainstorming`** (`skills/brainstorming/SKILL.md:79-83`): `grep "problem_type: decision" docs/solutions/` → reads the decision files to avoid re-proposing an already-rejected approach.

### 4. The real gap
```
Session 1: work → find a bug → /compound → write docs/solutions/foo/bar.md
   ↓ [session 1 ends]
Session 2 (new): context does NOT contain bar.md
   ↓
   ├─ Call /xia2 or /brainstorming?  → YES: the skill pulls from docs/solutions/
   └─ Don't call?                     → the knowledge is INVISIBLE in this session
```
There is no path for `critical-patterns.md` (or any entry) to load itself into a new session's context without an active action.

### 5. Nuance: why "semi-closed" rather than fully open
`CLAUDE.md` **is auto-loaded** every session and contains the line:
> "Critical learnings (read at planning time): `docs/solutions/critical-patterns.md`"

→ This is a **self-surfacing pointer**, but **the content does not load itself**. It only *reminds* the model to read at planning time — dependent on whether the model complies. Pointer auto, content on-demand.

### 6. Current data state
`docs/solutions/` **does not exist yet** (scaffold-only) — `/compound` and `/bootstrap-xia2` have never been run. The loop currently has no data to verify end-to-end.

---

## Summary table

| Component | Status | Evidence |
|---|---|---|
| Compound writes files | ✅ | `compound/SKILL.md` line ~90, ~309, ~343 |
| Auto-load at SessionStart | ❌ None | 0 SessionStart hooks; grep 0 matches |
| Hook reads docs/solutions | ❌ None | only SessionEnd `state-breadcrumb.sh` |
| `/xia2` pull | ✅ | `xia2/SKILL.md:93-99` (INDEX → critical-patterns → ≤3 files) |
| `/brainstorming` pull | ✅ | `brainstorming/SKILL.md:79-83` (grep decision) |
| critical-patterns self-loads | ❌ | only read when `/xia2` is called |
| docs/solutions/ today | EMPTY | directory does not exist yet |
| **Loop status** | **OPEN / semi-closed** | resurfaces only on pull |

---

## Options for closing the loop (not implemented — recorded only)

| Level | Approach | Trade-off |
|---|---|---|
| **Light** | Change the pointer in `CLAUDE.md` to an imperative ("ALWAYS read `critical-patterns.md` before planning/implementation") | Still depends on model compliance; 0 baseline tokens |
| **Medium (recommended)** | Add a **SessionStart hook** that prints the contents of `INDEX.md` + `critical-patterns.md` (or their titles) into context | Costs a few tokens/session; genuinely closes the loop, no skill dependency |
| **Heavy** | SessionStart hook + relevance-filter (surface only entries matching the open file/branch) | Complex, needs a filtering script |

> ⚠️ The SessionStart hook + `settings.json` are a **high-blast file** (Rule 4, `auto-correct-scope.md`) → user confirmation is required before modifying them.

---

## Practical consequence
Until the loop is closed, reusing `/compound` knowledge in a new session requires **actively** doing one of the following:
1. Call `/xia2` (reads INDEX + critical-patterns + ≤3 solutions).
2. Call `/brainstorming` (reads the relevant decisions).
3. Read `docs/solutions/INDEX.md` or `critical-patterns.md` yourself and feed it into the prompt.
