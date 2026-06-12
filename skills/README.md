# Claude Skills — Reference & Workflow

Skills are reusable prompt programs invoked with `/skill-name`. Each skill has a defined scope, hard gates, and a handoff to the next skill.

This file is the single source of truth for overview, workflow, and cross-skill concerns — consult the `SKILL.md` of each skill for runtime behavior. Two skills keep deeper standalone docs: `skills/compound/README.md` and `skills/xia2/README.md`; the other per-skill `README.md` files have been removed (their rationale notes live at the bottom of this file).

---

## Development Workflows

### Full Cycle (3+ layers, migration, or spans multiple services)

```
/bootstrap-xia2  (first-time repo setup only)
  → scaffolds specs/, docs/solutions/, agent-memory/
  → generates xia2/PROJECT.md from repo scan
      ↓
/feature-intake  (routing entry point — run first on every change request)
  → classifies input type + 10-flag risk checklist + hard gates
  → output: lane (tiny|normal|high-risk) + confidence → specs/<slug>/SUMMARY.md
  → routes: tiny → direct edit · normal → subagent-driven · high-risk → full chain below
      ↓
/brainstorming
  → reads: CLAUDE.md, docs/solutions/ (decision track only), recent commits
  → output: specs/<slug>/design.md
      ↓
/xia2
  → reads: PROJECT.md, CLAUDE.md, .claude/rules/, docs/, docs/solutions/, specs/
  → depth re-evaluated after reading docs
  → output: specs/<slug>/research-brief.md (no code)
      ↓
/writing-plans
  → input: design.md + research-brief.md
  → output: specs/<slug>/PLAN.md
  → auto-handoff: /visual-planner renders PLAN.html (deterministic script), then opens it
      ↓
/using-git-worktrees
  → creates isolated worktree + branch
      ↓
/subagent-driven-development        ← same session
  OR /executing-plans               ← parallel session
  → implements plan task-by-task
  → two-stage review per task (spec compliance → code quality)
  → final adversarial correctness review (/correctness-review) over the whole diff before shipping
  → final intent review (/intent-review) — diff vs the original request, blind to PLAN
      ↓
/compound  (if non-obvious pattern found)
  → output: docs/solutions/<category>/<slug>.md
      ↓
/finishing-a-development-branch
  → PR description, review checklist, merge
```

### Minimum Viable Path (intent clear, in-place edit, <1 day)

```
/feature-intake → /xia2 → /writing-plans → implement → /compound (if pattern found)

/feature-intake confirms the lane; a tiny lane drops straight to a direct edit.
Skip /brainstorming when intent is clear.
Skip /using-git-worktrees for in-place edits.
/writing-plans still auto-renders PLAN.html via /visual-planner.
```

### Bug Fix Path

```
/systematic-debugging  (external — see below)
  → root cause analysis before any fix
      ↓
fix (implement directly or via /subagent-driven-development)
      ↓
/compound  (always — root cause is worth preserving)
```

---

## Skills Reference (in this repo)

### Intake & Routing

| Skill | Trigger | Output |
|---|---|---|
| `/feature-intake` | First, on every change request — classify risk lane + confidence and route | `specs/<slug>/SUMMARY.md` (Lane/Confidence/Reason/Flags) + a route decision |

### Setup

| Skill | Trigger | Output |
|---|---|---|
| `/bootstrap-xia2` | First-time repo setup or major architectural change | Scaffolded dirs + `xia2/PROJECT.md` draft |

### Discovery & Design

| Skill | Trigger | Output |
|---|---|---|
| `/brainstorming` | Before any new feature, component, or behavior change | `specs/<slug>/design.md` |
| `/xia2` | Before implementing anything — research what already exists (portable; reads `PROJECT.md`) | `specs/<slug>/research-brief.md` |

### Planning

| Skill | Trigger | Output |
|---|---|---|
| `/writing-plans` | After design is approved and xia2 brief is ready | `specs/<slug>/PLAN.md` (+ auto-renders `PLAN.html`) |
| `/visual-planner` | Render a `PLAN.md` for visual review (auto-invoked by `/writing-plans`; also standalone) | `specs/<slug>/PLAN.html` (untracked, local-only) |

### Execution

| Skill | Trigger | Output |
|---|---|---|
| `/using-git-worktrees` | Before starting feature work needing isolation | Isolated worktree + branch |
| `/subagent-driven-development` | Executing a plan in the current session (fresh subagent per task) | Implemented tasks, two-stage reviewed per task + final adversarial correctness review (delegates to `/correctness-review`) |
| `/executing-plans` | Executing a plan in a separate parallel session (checkpoint-based) | Same as above |

### Review & Shipping

| Skill | Trigger | Output |
|---|---|---|
| `/correctness-review` | After implementation — adversarial runtime-bug hunt over a diff. **Standalone** (any diff, no workflow gate) or called by `/subagent-driven-development` as its final pass | Findings scored (0–100, threshold 80) + classified (Severity + Rule class) → fixes or escalations |
| `/intent-review` | After correctness-review — checks the diff against the original request verbatim, blind to PLAN (the third oracle). **Standalone** on any diff that has an intent statement, or called by `/subagent-driven-development` as its last pass | Findings classified `gap` / `excess` / `drift` → fix-loop · escalate · report-only |
| `/review-diff` | After implementation — visualize what changed | Markdown review with C4 diagrams |
| `/compound` | After session with non-obvious bug fix, pattern, or architectural decision | `docs/solutions/<category>/<slug>.md` |
| `/create-pr` | When only a PR description is needed | `PR_TEMPLATE.md` |
| `/finishing-a-development-branch` | Implementation complete, tests pass | Runs tests, pushes, opens a PR (never merges) |

---

## External Skills (referenced but live elsewhere)

These skills appear in workflows above but are provided by the global `superpowers` plugin or `~/.claude/skills/`, not by this repo:

| Skill | Role |
|---|---|
| `/systematic-debugging` | Root-cause analysis before a bug fix |
| `/test-driven-development` | Tests-first protocol used by implementer subagents |
| `/requesting-code-review` | Structured review template |
| `/session-tracker` | Session resumption across conversations |
| `/skill-creator` | Authoring new skills |

If one of these isn't available in your environment, the workflows degrade gracefully — treat them as optional.

---

## Skill Handoff Map

```
/bootstrap-xia2             ──► (repo setup — terminal; user now invokes workflow)
/feature-intake             ──► tiny: direct edit · normal: /subagent-driven-development
                                high-risk: /brainstorming (full chain) · low confidence: escalate
/brainstorming              ──► /xia2 → /writing-plans (the only valid next skills)
/xia2                       ──► research brief → user/skill decides next step
/writing-plans              ──► /visual-planner (auto: render PLAN.html) → /using-git-worktrees
                                → /subagent-driven-development
                                OR /executing-plans (parallel session)
/visual-planner             ──► PLAN.html (terminal — visual artifact; back to writing-plans handoff)
/subagent-driven-development ──► /correctness-review → /intent-review (final passes) → /compound → /finishing-a-development-branch
/correctness-review         ──► (standalone — runs the same pipeline ad-hoc on any diff; no gate)
/intent-review              ──► (standalone — same pipeline; needs ### Intent in SUMMARY or intent provided by the user)
/systematic-debugging       ──► fix → /compound
/compound                   ──► nothing (terminal — crystallization is end state)
/finishing-a-development-branch ──► nothing (terminal — shipped)
```

---

## Knowledge Base Integration

Skills read from and write to `docs/solutions/`:

```
writes ──► /compound
           docs/solutions/<category>/<slug>.md
           front-matter: problem_type (bug | knowledge | decision | failure),
                         module, tags, severity, applicable_when,
                         affects, supersedes, confidence, confirmed_at

reads  ◄── /brainstorming  (decision track only — avoid re-proposing rejected approaches)
       ◄── /xia2           (all tracks — module, affects, confidence filtering)
```

Schema reference: `docs/solutions/README.md` (scaffolded by `/bootstrap-xia2`).

---

## Agent Memory

Per-agent persistent memory with confidence decay: `agent-memory/`

Each entry carries:
```
<!-- confirmed: YYYY-MM-DD | confidence: high|medium|low | review-by: YYYY-MM-DD -->
```

- `high` — verified this session
- `medium` — 1+ month old, or inferred
- `low` — >3 months old or uncertain; treat as hypothesis, verify before acting

**Write protocol:** when re-verifying an entry, update `confirmed` to today and adjust `confidence`. Expired `review-by`: downgrade confidence one tier on next read.

---

## Commit Hook

`hooks/commit-quality-gate.sh` gates every commit:
1. Secrets scan
2. Debug artifact check (`breakpoint()`, bare `print()`)
3. Targeted pytest for changed `app/` files

When ≥5 `app/` files are staged, the hook hints: `★ Consider running /compound`.

---

## Per-skill Design Rationales

Notes preserved from the former per-skill READMEs. For full runtime behavior read each skill's `SKILL.md`.
The diagrams below render natively in the GitHub README — no clone needed.

### `/compound`

> **One-liner:** an orchestrator fans out read-only subagents to mine the session transcript, then writes every knowledge doc itself.

```mermaid
graph LR
    subgraph W1["① Parallel — read transcript, return text only"]
        CA["Context Analyzer"]
        SE["Solution Extractor"]
        DE["Decision Extractor"]
    end
    CA -->|"module + tags"| RDF["② Related Docs Finder<br/>(exact module + tags)"]
    SE --> ORCH
    DE --> ORCH
    RDF --> ORCH["③ Orchestrator<br/>writes ALL files + rebuilds INDEX"]
```

- **Orchestrator + 4 subagents.** `SKILL.md` orchestrates; subagents read the session transcript and return **text only** — the orchestrator writes all files.
- **Dispatch order (Option A, recommended):** the 3 extractors run in parallel; wait for Context Analyzer → extract `module`+`tags`; then Related Docs Finder with those exact values. Option B (all 4 in parallel with best-guess tags) is faster but slightly less accurate.
- **`applicable_when` is the primary discovery field.** Knowledge: "Use this pattern when…". Decision: "Make this decision when…". Bug: inherited from `CONTEXT_ANALYSIS`. Appears as an INDEX.md column so future agents scan one sentence per doc.
- **Four track types: `bug`, `knowledge`, `decision`, `failure`.** The `failure` track records a tried-and-abandoned approach to prevent recurrence: sections are Symptom → Wrong Approach → Why It Failed → Correct Approach → Guardrail (the check/hook/rule that now prevents a repeat). Emitted only when all four required sections (Symptom, Wrong_Approach, Why_It_Failed, Correct_Approach) are non-empty. `Harness-Delta: backlog` friction signals from subagent summaries are also mined into failure records.
- **Every `bug` doc requires `## Regression Test`.** Names the pinned test that catches a recurrence, or `[none] — <reason>` if none exists. This field is not optional.
- **Multi-decision consolidation.** ≥2 decisions in one session → single `[slug]-decisions.md` with `## Decision 1` / `## Decision 2` sections. Rationale: decisions from the same session are causally related; reading one without the other loses the constraints that drove it.
- **INDEX full rebuild (not append-only).** After every run. Prevents orphaned rows when files are renamed/moved/deleted. `docs/solutions/` grows to tens of files, not thousands — full scan is negligible.
- **Never auto-write to `CLAUDE.md`.** At end of run, if `CLAUDE.md` does not reference `docs/solutions/`, propose an addition — wait for developer approval.

**Severity triage** — `critical` requires **all three**; anything else is `standard`:

| Tier | Conditions | Effect |
|---|---|---|
| `critical` | (1) affects multiple features/layers **and** (2) ≥30 min wasted if unknown **and** (3) generalizable beyond this PR | Summary promoted to `critical-patterns.md` |
| `standard` | anything missing one of the above | Normal doc only |

**Collision handling** — how a new finding merges with existing docs:

| Overlap | Detected when | Action |
|---|---|---|
| **High** | same module **+** ≥2 matching tags | Update the existing file |
| **Moderate** | partial match | Write `[slug]-2.md` |
| **Low** | no real match | Write `[slug].md` |

### `/visual-planner`

> **One-liner:** a deterministic script (not the LLM) renders `PLAN.md` → a self-contained, untracked `PLAN.html`; a second script serves and opens it.

```mermaid
graph LR
    MD["PLAN.md"] --> RP["render_plan.py<br/>+ template.html"]
    RP --> HTML["PLAN.html<br/>(untracked, beside PLAN.md)"]
    HTML --> VP["view_plan.py<br/>serve + auto-render if stale"]
    VP --> B["Chrome @ localhost<br/>(secure context → clipboard works)"]
```

| Script | Role |
|---|---|
| `render_plan.py` | **Builds** `PLAN.html` by filling `{{PLACEHOLDER}}` slots in `template.html` — byte-for-byte reproducible. |
| `view_plan.py` | **Shows** it — serves on localhost + opens Chrome, auto-rendering first if `PLAN.html` is missing/stale. |

- **Deterministic script, not LLM transcription.** The skill only runs the script and relays its report — never emits HTML token-by-token. Transcribing a ~340-line template every run is expensive and the least reproducible part of the pipeline; a script makes the fill free and stable.
- **Local-only output.** `PLAN.html` is untracked — it lives beside `PLAN.md` in `specs/` (which is tracked), but `PLAN.html` itself is gitignored as a derived artifact.
- **Auto-invoked by `/writing-plans`.** After a plan is approved and before the execution handoff, `writing-plans` dispatches a `visual-planner` sub-agent to render `PLAN.html`, then opens it. Also runs standalone as `/visual-planner <slug>`.
- **Why serve instead of `file://`?** Localhost is a browser *secure context*, so per-task "copy `<verify>`" buttons use `navigator.clipboard`; `--file` (`file://`) is faster but falls back to `execCommand`. Auto-view is environment-dependent (no display on headless/remote), so it stays an explicit step.
- **Self-check before claiming success.** The script asserts non-empty output, no surviving `{{PLACEHOLDER}}`, the `slug` present, and one `<section data-wave>` per distinct wave. On non-zero exit, surface the `SELF-CHECK FAILED:` lines verbatim — do not claim success.

**`--review` mode is a 3-step dance** (the offline renderer can't call MCP itself):

```mermaid
graph LR
    A["1 · render_plan.py --emit-files"] --> B["2 · agent queries code-review-graph<br/>blast-radius + risk per file"]
    B --> C["3 · write .plan-review.json sidecar"]
    C --> D["render_plan.py --review<br/>→ impact dashboard + blast-radius table + risk cards"]
```

### `/xia2`

> **One-liner:** one portable skill; project-specific knowledge lives in a swappable `PROJECT.md` sibling.

```mermaid
graph LR
    SKILL["SKILL.md<br/>universal classifier logic"]
    PROJ["PROJECT.md<br/>project-specific signals"]
    SKILL --- PROJ
    PROJ -.->|"swap per repo"| NEW["Reusable in any project"]
```

- **Portable by design.** Universal logic in `SKILL.md`; project-specific signal mappings in `PROJECT.md`. Same skill works across projects by swapping `PROJECT.md`.
- **PROJECT-CONFIG-GATE halts** when `PROJECT.md` is missing/incomplete. Run `/bootstrap-xia2` first.
- **Fork to another project:**
  1. Copy `skills/xia2/` (and `skills/bootstrap-xia2/` for auto-scan).
  2. Run `/bootstrap-xia2` in the new repo to draft `PROJECT.md` → human-review.
  3. Discard `tests/structural/depth-modes-test-cases.md` (tests this project's `PROJECT.md`) — author your own.
  4. Keep `tests/behavioural/pressure-scenarios.md` — most scenarios are universal.
- **Maintenance discipline:**
  - Editing HARD-GATE, PROJECT-CONFIG-GATE, Decision Procedure, Depth Modes, Tiebreakers, Re-evaluation gate, or Step 1 waiver → **must** re-run `tests/structural/` suite.
  - Editing `PROJECT.md` → re-run structural tests (adding a high-blast file flips any prompt touching it to Deep).
  - Wording polish in non-classifier sections does not require a re-run.

**Critical regression canaries** (see `tests/structural/depth-modes-test-cases.md`):

| Test case | Must classify as |
|---|---|
| TC-01 → TC-04 | **Quick** |
| TC-19, TC-21 | **Deep** |
| TC-20 | **Standard** (initial classification) |
| TC-29 | Surface a **risk warning** when HARD-GATE is waived |
