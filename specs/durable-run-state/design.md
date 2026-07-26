# Durable Run State — Design (canonical, GitHub issue #129)

Consolidated design account for the whole Durable Run State Contract (Phases A–D). Real design
decisions were made and recorded in each phase's own `design.md`
(`specs/gh-129-durable-run-state-phase-{b,c}/design.md` — Phase A predates a `design.md`
requirement for its lane). This file cross-references them rather than re-deciding anything.

## 1. Architecture overview

```mermaid
flowchart LR
    subgraph "Phase A — Engine"
        E["runtime/run_state.py<br/>16-state FSM, stdlib-only CLI"]
    end
    subgraph "Phase B — Portable deployment"
        D["deploy-harness.sh / install-harness.sh<br/>ships runtime/ to every consumer"]
    end
    subgraph "Phase C — Workflow checkpoints"
        FI["feature-intake"] --> SDD["subagent-driven-development"]
        SDD --> FDB["finishing-a-development-branch"]
        SK["session-knowledge.sh"]
        HS["harness-status.sh (meta-repo-only)"]
        PMM["post-merge-maintenance.yml (meta-repo-only)"]
    end
    E --> D --> FI
    FI --> SK
    FDB --> PMM
```

## 2. Ownership boundary with `specs/STATE.md`

See `specs/STATE.md` → `## RUN/Event State vs. This File` (Phase D, Task 1.1) for the full
table. Summary: `STATE.md` is session-scoped and human-focused; `RUN.json`/`events.jsonl` is
per-spec-slug and durable across sessions. Neither reads nor writes the other's files.

## 3. Portability boundary

Checkpoints 1–6 (per `specs/gh-129-durable-run-state-phase-c/design.md` §3) are portable —
shipped to every consuming repo via Phase B's deploy/install registration. Checkpoints 7–8
(`harness-status.sh`, `post-merge-maintenance.yml`) are meta-repo-only tooling: the whole
`scripts/` directory is never synced as a unit — `SYNCED_DIRS_RE` in `deploy-harness.sh`
(`^(skills|agents|hooks|rules|templates|runtime)/[^/]+$`) has no `scripts` alternation, and
`.github/` is referenced nowhere in either distribution script as a real path (the only
`.github` substring hits are inside `githubusercontent.com` URLs). `install-harness.sh`'s
`PAYLOAD` array does ship two individually-named files out of `scripts/`
(`scripts/deploy-harness.sh`, `scripts/init-structure.sh`), but `scripts/harness-status.sh` is
not among them — confirmed absent via `grep -c "harness-status" scripts/install-harness.sh`
returning `0`.

## 4. Known, disclosed limitations

See the "Known, disclosed limitations" section in `research-brief.md`. Both are Phase C findings, both
explicitly deferred (one advisory/scored-below-fix-threshold, one by direct user decision) —
not re-opened here.

## 5. Non-goals

See `specs/gh-129-durable-run-state-phase-d/PLAN.md` §2 (issue #129's Phase D Non-goals, quoted
verbatim) — not restated here to avoid a third copy.
