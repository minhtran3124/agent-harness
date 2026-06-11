---
name: feature-intake
description: The routing entry point for any change request. Classifies a prompt by input type, runs a 10-flag risk checklist + hard gates to assign a lane (tiny / normal / high-risk), scores confidence to decide whether a human is needed, writes the result to specs/<slug>/SUMMARY.md, and routes to the matching workflow path. Use FIRST, before xia2 / writing-plans / any edit, to decide how much ceremony and how much human oversight a task needs.
allowed-tools: Read, Write, Grep, Glob, Bash(git log *), Bash(git diff *), Bash(ls *)
---

# Feature Intake — Risk Lane Classifier & Router

Every implementation prompt passes through this gate before code changes. The output is a
**lane** (how much proof/ceremony) and a **confidence** (whether a human is asked), recorded
in `specs/<slug>/SUMMARY.md` and used to route the rest of the workflow.

> **The human does not classify risk. The harness does.**
> Two independent axes:
> - **Lane** scales with **RISK** → how much proof and ceremony.
> - **Confidence/ambiguity** scales with **UNCERTAINTY** → whether to pause for a human.
>
> A high-risk-but-unambiguous task runs autonomously through heavy proof.
> A low-risk-but-ambiguous task still pauses. Never ask a human "is this risky?" — answer
> that mechanically. Ask a human only "did I understand you?" and "may I cross this boundary?"

<HARD-GATE>
Do NOT edit files, scaffold, or dispatch implementation work until intake is complete:
the lane is assigned, the intake statement is emitted, and `Lane:`/`Confidence:` are written
to `specs/<slug>/SUMMARY.md` (shape: `templates/SUMMARY.template.md`).

A hard gate (see below) forces `high-risk` and cannot be self-downgraded — only a human
narrowing scope may lower it. The orchestrator MUST write a `Lane:` line: `.claude/hooks/risk-corroboration.sh`
blocks a commit whose diff trips a hard gate while the declared lane is below `high-risk`.
(A *missing* lane only warns — fail-open — unless `RISK_CORROBORATION_STRICT=1` is set, so
write the lane rather than rely on the hook.)
</HARD-GATE>

---

## Step 1 — Classify the input type

Decide *where the work lands* before scoring risk. Use the type to pick the artifact, not to
add ceremony — most types collapse onto an existing workflow path.

| Input type | Use when | Lands as |
|---|---|---|
| New spec | A user-provided project spec must become docs + work | design.md + initiative notes |
| Spec slice | A selected behavior from an accepted spec | one story/PLAN |
| Change request | Change, fix, or refine accepted behavior | story/PLAN or direct patch |
| New initiative | A larger area needing multiple stories | initiative notes + PLANs |
| Maintenance | Dependency / perf / security / ops work | story/PLAN or decision |
| Harness improvement | Change to .claude/skills/rules/hooks/docs themselves | direct docs/skill update or `/compound` |

## Step 2 — Run the risk checklist (10 flags)

Mark each flag that the work touches. Cross-check the expected diff against High-Blast Files +
Shared Contracts in PROJECT.md to name the affected contract (used to populate the `Affects:`
field in SUMMARY.md).

| # | Risk flag | Fires when the work touches |
|---|---|---|
| 1 | Auth | login, logout, sessions, JWT, password, refresh token |
| 2 | Authorization | roles, permissions, tenant/company scope |
| 3 | Data model | schema, migrations, uniqueness, deletion, retention |
| 4 | Audit/security | audit logs, privacy, sensitive data, access logs |
| 5 | External systems | email, payments, cloud, provider SDKs, queues, webhooks |
| 6 | Public contracts | API shape, response envelope, client-visible behavior |
| 7 | Cross-platform | desktop/mobile/browser split, native shell, deep links |
| 8 | Existing behavior | already-implemented or test-covered behavior changes |
| 9 | Weak proof | unclear or missing tests around the affected area |
| 10 | Multi-domain | more than one product domain changes at once |

## Step 3 — Assign the lane

```text
0–1 flags        -> tiny (if ≤1 file & no new public callable) or normal
2–3 flags        -> normal (stronger validation)
4+ flags         -> high-risk
any hard gate    -> high-risk (only a human narrowing scope may lower it)
```

**Hard gates** (force high-risk regardless of flag count):

- Auth.
- Authorization.
- Data loss or migration.
- Audit/security.
- External provider behavior.
- Removing or weakening validation requirements.
- Touching a high-blast-radius file: `.claude/settings.json`, any `.claude/hooks/*`, or a core skill engine.

These mirror `.claude/rules/auto-correct-scope.md` Rule 4 and are corroborated mechanically by
`.claude/hooks/risk-corroboration.sh` against the staged diff.

## Step 4 — Score confidence (the interruption axis)

Assess how well the *direction* is understood — separately from risk.

| Confidence | When | Effect |
|---|---|---|
| **high** | One plausible interpretation; scope is clear | proceed autonomously in lane |
| **medium** | Minor open questions; a reasonable default exists | proceed; note assumptions; escalate if also high-risk |
| **low** | >1 materially different interpretation, or vague intent | **escalate** before work, regardless of lane |

**Ambiguity rubric (conservative default):** if you cannot state the single thing the user
wants in one sentence, or two competent engineers would build materially different things,
confidence is **low** → escalate. When unsure, treat as ambiguous.

## Step 5 — Escalation decision

```text
hard gate hit            -> ESCALATE: have a human narrow scope or confirm high-risk
confidence == low        -> ESCALATE: confirm intent (even for a tiny task)
ambiguous direction      -> ESCALATE: confirm intent
else                     -> PROCEED autonomously in the assigned lane
```

Escalations are recorded in `specs/<slug>/ESCALATIONS.md` (shape: `templates/ESCALATIONS.template.md`),
which defaults to deny-on-no-response. See `.claude/rules/orchestration.md` for the runtime decision step.

## Step 6 — Emit the intake statement + write SUMMARY.md

Emit, and write the header fields to `specs/<slug>/SUMMARY.md`:

```text
Lane: <tiny | normal | high-risk>
Confidence: <high | medium | low>
Reason: <one sentence — which flags / hard gates fired, or none>
Flags: <comma-separated flags, or none>
Affects: <affected contract/module from PROJECT.md High-Blast/Shared-Contracts, or 'none'>
Input-type: <one of the six>
Route: <see Step 7>
Escalate: <yes (reason) | no>
```

## Step 7 — Route to the workflow path

**Artifacts scale by signal, not by lane alone.** `SUMMARY.md` is written for **every** lane —
it is the always-on audit record (its `Rationale` / `Alternatives` fields make an autonomous
decision reconstructable). The forward-looking artifacts are signal-triggered: `PLAN.md` at
>3 steps or >2 files (`rules/plan-format.md`); `research-brief.md` for unfamiliar code or a
high-risk lane; `design.md` only on a genuine design fork (≥2 viable approaches) or high-risk.
For autonomous (no-human) work the `### Verify` evidence + independent review **substitute for
the human gate — not extra documents.** Set `FULL_ARTIFACTS=1` to force the full set regardless
of lane (audit-heavy work / calibrating trust). See `rules/orchestration.md` → Artifact policy.

| Lane | Route | Human checkpoint |
|---|---|---|
| **tiny** | Direct `Edit` (no plan). Proof = quick-check hooks (`ruff-on-edit`, `auto-test-on-change`, `commit-quality-gate`). | none (unless confidence low / ambiguous) |
| **normal** | `/subagent-driven-development` (+ `wave-parallelism` for independent tasks). Two-stage agent review per task. | only if confidence low / ambiguous |
| **high-risk** | Full chain: `/brainstorming` → `/xia2` → `/writing-plans` → `/subagent-driven-development`; record a decision via `/compound` when architecture/behavior changes. | only on ambiguity or a hard gate |

After routing, hand off. The downstream skills already enforce their own gates and proof.

---

## Guardrails

- **Never edit before intake.** The lane and SUMMARY come first, always (HARD-GATE).
- **Never self-downgrade a hard gate.** Only a human narrowing scope may lower it.
- **Decouple the axes.** Lane is about risk; the human gate is about ambiguity. Do not pause
  a human merely because work is risky if the direction is clear — apply more proof instead.
- **Write a `Lane:` line.** The corroboration hook and the trust-metrics ledger depend on it.
- **Append to the ledger.** At the DONE disclosure, record the task in
  `docs/harness-experimental/trust-metrics.md`.

## Arguments

- `$ARGUMENTS` — the change request to classify. If omitted, ask the user what they want to do.
- `<slug>` — the spec directory (e.g. `specs/<slug>/`). If absent, derive a kebab-case slug.

## See also

- `templates/SUMMARY.template.md` — the SUMMARY shape this skill writes.
- `templates/ESCALATIONS.template.md` — the escalation channel.
- `.claude/rules/orchestration.md` — the orchestrator loop + escalation-decision step.
- `.claude/rules/auto-correct-scope.md` — Rule 4 hard gates (the autonomy boundary).
- `.claude/hooks/risk-corroboration.sh` — mechanical corroboration of the declared lane.
- `docs/harness-experimental/trust-metrics.md` — the per-task trust ledger this skill appends to.
- [hoangnb24/harness-experimental](https://github.com/hoangnb24/harness-experimental) — the upstream research this skill implements.
