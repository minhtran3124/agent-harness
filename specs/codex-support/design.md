# Codex Support — High-Level Design

> Vietnamese version: [`design.vi.md`](./design.vi.md)

**Status:** design only. No implementation, no file layout committed, no code.
**Goal:** a user driving **OpenAI Codex CLI** gets the same harness — same lanes, same
artifacts, same gates — as a user driving Claude Code, from **one set of sources**.

---

## 1. The finding that makes this tractable

The harness was built against Claude Code's extensibility model. During 2026 Codex CLI
converged on that same model. The three surfaces the harness depends on now exist on both:

| Harness dependency | Claude Code | Codex CLI | Verdict |
|---|---|---|---|
| Prompt programs | `skills/<n>/SKILL.md`, YAML frontmatter `name`/`description` | Skills — **same file name, same two required frontmatter fields**, model-selected *or* explicit | near-identical |
| Enforcement | hooks: stdin JSON → exit 2 / `permissionDecision:"deny"` / `hookSpecificOutput.additionalContext`, `matcher` regex, `type:"command"` | hooks: **the same contract, field for field** | near-identical |
| Isolated contexts | `agents/*.md` + Task tool + tool whitelist | `.codex/agents/*.toml` + spawn tools + **`sandbox_mode`** | same semantics, different encoding |

So the question is no longer *"can the harness run on Codex"* but *"what is the smallest seam
that keeps one source of truth serving two runtimes."*

**Corollary that shapes everything below:** the work is ~70% *neutralising the existing core*
and ~30% *writing a Codex adapter*. The neutralisation half improves the Claude side too — it
removes silent single-runtime dependencies the harness currently has no oracle for.

---

## 2. Architecture — one source, two adapters

Today the repo already separates **source** (repo root) from **derived install** (`.claude/`,
gitignored, built by `deploy-harness.sh`). The design keeps that shape and adds a second target.
It does **not** add a second copy of the sources.

```
        RUNTIME-NEUTRAL SOURCE                 ADAPTER              DERIVED INSTALL
  ┌──────────────────────────────────┐
  │ skills/    agents/    rules/     │──┬──► claude adapter  ──►  .claude/
  │ hooks/     templates/ runtime/   │  │                          (settings.json, skills/, …)
  │ scripts/   harness-manifest.json │  │
  └──────────────────────────────────┘  └──► codex adapter   ──►  .agents/skills/  +  .codex/
                                                                   (hooks.json, agents/*.toml,
                                                                    AGENTS.md)
```

Three rules govern the seam:

1. **Sources never name a runtime.** No `.claude/` path, no `/skill-name` invocation syntax, no
   Claude-only tool name in any `skills/`, `agents/`, or `rules/` file.
2. **Adapters are mechanical.** An adapter re-encodes and re-locates; it must not carry policy.
   Any adapter that needs to *decide* something has found a leak in the neutral core.
3. **Divergence is declared, never discovered.** What an adapter cannot deliver is recorded in a
   machine-checked ledger (§5), not left for a user to find at runtime.

### 2.1 The four layers, by portability

| Layer | Examples | Portability | Work needed |
|---|---|---|---|
| **Logic core** | `runtime/run_state.py`, `scripts/*.py`, `specs/` schema, templates, manifest | 100% — plain Python and files, zero runtime coupling | none |
| **Enforcement** | `hooks/*.sh` | ~85% — same contract, different vocabulary and payload shapes | input-normalisation shim (§3) |
| **Instruction surface** | `skills/`, `agents/`, `rules/` | ~70% — same concepts, different delivery and encoding | neutralisation (§4) |
| **Entry point** | `CLAUDE.md`, `settings.json`, install script | ~0% — runtime-specific by definition | adapter-generated |

The logic core being 100% portable is the load-bearing fact: lanes, evidence rules, run-state
FSM, plan contract, verify-row linting and the review receipt are **already** runtime-agnostic.
Codex support does not touch the harness's actual thinking — only how it is delivered and
enforced.

---

## 3. Enforcement — the hook seam

### 3.1 What ports for free

Event names (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`,
`SessionEnd`), the `matcher` + `type:"command"` config shape, exit-2 blocking, `deny`
decisions, and `additionalContext` injection are the same on both runtimes. The nine hook
scripts do not need to be rewritten.

### 3.2 What breaks — and how it breaks

Three divergences matter, and two of them **fail open**, which is the dangerous kind:

| Divergence | Effect on the harness |
|---|---|
| **Tool vocabulary.** Codex's canonical `tool_name` for every file edit is `apply_patch` (with `Write`/`Edit` exposed only as matcher aliases); shell is `shell`/`unified_exec`. | Matchers mostly survive via aliasing — needs empirical confirmation. |
| **Payload shape.** `apply_patch` carries a **patch envelope**, not `{file_path}`. Four hooks (`branch-isolation-guard`, `blast-radius-check`, `ruff-on-edit`, `render-plan-on-write`) read `.tool_input.file_path` with a `// empty` fallback. | **Silent fail-open.** They exit 0 and enforce nothing. For `branch-isolation-guard` that means implementation edits on a shared branch stop being blocked — with no error, no warning. |
| **Event coverage.** Codex hook emission is opt-in per tool handler and has open upstream coverage gaps. | A gate can be *configured* and still never fire. |

### 3.3 Design response: one normalisation seam

Hooks stop parsing raw stdin. A single shared shim (sourced by all hooks, sitting beside the
existing `hooks/lib/`) reads stdin once, detects the runtime, and exports a normalised view:
the invoking tool, the **set** of files touched, the shell command, the prompt text.

Why this shape:

- It is **one testable seam**, not nine. The existing `tests/hooks/*.test.sh` contract-test
  pattern extends to it directly.
- A patch envelope naturally yields *many* files, so the neutral contract is a file **set**.
  That is strictly more correct than today's single `file_path` — `blast-radius-check` and
  `branch-isolation-guard` are both semantically set-valued already.
- It converts the fail-open into an **explicit policy decision per hook**. A hook that cannot
  determine its inputs must choose: warn loudly, or refuse. Silence stops being an option.

### 3.4 Two hard constraints from the Codex side

- **`SessionEnd` has a ~1s timeout (3s max)**, against ~600s for other events.
  `state-breadcrumb.sh` does git work plus a file append. It must be measured, and if it does
  not fit, moved to `Stop`. This is a real behavioural constraint, not a tuning note.
- **Hooks are experimental, feature-flagged (`[features] hooks = true`), Windows-disabled, and
  project-level hooks require the `.codex/` directory to be trusted.** A Codex install can
  therefore be fully deployed and have **zero enforcement**. See §6.

---

## 4. Instruction surface — neutralising the core

Four concrete couplings, each with a design answer. All four are *simplifications* of the
current source, not additions.

### 4.1 Path-scoped rule auto-loading — the biggest risk

Claude Code injects `rules/plan-format.md`, `wave-parallelism.md`, and `auto-correct-scope.md`
automatically via `paths:` frontmatter when a matching `specs/**` file is read. **Codex has no
equivalent.** The harness's most safety-relevant rule — `auto-correct-scope.md`, which carries
the Rule-4 STOP criteria — reaches isolated reviewer and implementer contexts partly through
this channel.

This is also a latent defect *today*: PR #141 shipped a rule that was referenced but never read
in an isolated subagent context, which is why `/context-propagation-audit` exists.

**Design answer:** demote `paths:` from *mechanism* to *accelerant*.

- Explicit `Read` steps in the consuming skill become the **only** delivery guarantee. Several
  skills already do this (`writing-plans`, `correctness-review`, `intent-review`,
  `subagent-driven-development`, `implementer-prompt.md`) — the design makes it universal and
  the audit makes it provable.
- `/context-propagation-audit` becomes the oracle: for every rule, every consuming context has a
  Read. It already exists and already runs on workflow-engine diffs.
- **Rejected:** inlining rule content into `AGENTS.md`. That reproduces the exact
  `stale-inline-policy` defect this repo has already been bitten by.

**This is the item most likely to make Codex support quietly wrong, and it is fixed on the
Claude side by the same change.**

### 4.2 Hard-coded `.claude/` paths in skill prose

26 occurrences instruct agents to read `.claude/rules/...`. Under Codex there is no `.claude/`.

**Design answer:** reference rules at their **repo-root** path (`rules/…`) — where they already
live in source, and where both runtimes can read them. The `.claude/rules/` copy stays as
Claude's auto-load fixture, not as the address anyone is told to use. Deploy-time prose
rewriting is explicitly rejected as opaque and untestable.

### 4.3 Subagents

The *semantic* contract is already runtime-neutral and already written down in
`rules/orchestration.md`: read-only reviewers, separate spec/quality verdicts, 150–300 word
structured summaries, no raw file dumps. Only the **encoding** differs (Markdown+frontmatter vs
TOML), so `agents/*.md` stays the source and the Codex adapter emits TOML.

Two notes worth carrying into implementation:

- Codex's `sandbox_mode = "read-only"` is a **stronger** independence guarantee than a tool
  whitelist — it is enforced by the sandbox rather than by the tool list. Reviewer independence
  gets better under Codex, not worse.
- Codex "does not spawn subagents automatically" — delegation must be explicit in the prompt.
  `subagent-driven-development`'s wave dispatch is already explicit; this needs verification,
  not redesign.

### 4.4 Invocation syntax and entry file

`/skill-name` (Claude) vs `$skill`/model-selected (Codex); `CLAUDE.md` vs `AGENTS.md`. Sources
should name skills, not invocation syntax ("invoke the feature-intake skill"). `AGENTS.md`
already exists in this repo and is adapter-generated from the same content that produces
`CLAUDE.md`.

---

## 5. Parity as a release gate — two tiers

**Decision D2 makes Codex a peer runtime**, so parity is a release gate, not a ledger of
excuses. But Codex CLI is a paid, non-deterministic, network-dependent process — gating every
PR on live Codex execution would make CI slow, expensive and flaky. The design therefore splits
the gate along the axis the repo already uses for evidence tiers:

| Tier | What it proves | Cost | When it runs |
|---|---|---|---|
| **Static parity** (traceability) | Every skill, agent, rule and hook the harness ships is *emitted* for both runtimes; the manifest's runtime block is internally consistent; no adapter drift. | Free, deterministic | **Every PR**, blocking |
| **Behavioural parity** (truth) | A small golden set of harness behaviours — a lane classification, a plan execution, a blocked commit, a review receipt — produces equivalent artifacts when *driven* by each runtime. | Paid, non-deterministic | Scheduled + pre-release, blocking on release only |

`harness-manifest.json` — already the single source of truth for hard-gate vocabulary and
modes — gains a **runtime block**: for each gate, which runtimes enforce it, at what strength
(block / warn / unavailable), and why. Static parity is checked against that block by a drift
guard shaped like the existing `check_manifest.py` and embedded-gate-modes parity check.

**Under peer status the ledger changes role.** It is no longer "here are the gaps"; it is a
short, owned, expiring exception list. Every `unavailable` entry carries an owner and an exit
condition — otherwise "peer" degrades into a word and the ledger becomes the thing that *hides*
the gap instead of exposing it.

---

## 6. Advisory mode — transitional, not the steady state

**Decisions D2 and D3 are in tension, and the design must not paper over it.** Peer runtime means
parity is a release gate. Advisory mode means Codex ships with weaker or absent mechanical
enforcement. A runtime shipping advisory is, on the enforcement layer, *by definition not at
parity*.

The resolution is to be precise about **which layers reach peer status when**:

| Layer | Peer at ship? | Basis |
|---|---|---|
| Instruction surface (skills, agents, rules) | **Yes** | Same sources, adapter-emitted, statically checkable |
| Artifacts + workflow (lanes, `specs/` schema, run-state FSM, review receipt) | **Yes** | Runtime-agnostic logic core, already portable |
| Enforcement (hooks) | **No — advisory, tracked to closure** | Codex hooks experimental, flag/trust/OS-gated, upstream coverage gaps |

So: **ship advisory, declare peer on two of three layers, and carry the third as a named,
owned, expiring exception in the parity ledger.** Advisory is a transitional state with an exit
criterion, not a permanent tier.

Mechanically that means:

- The installer **probes** for hook capability and reports the result rather than assuming it.
- With hooks unavailable, the harness runs in advisory mode: skills, artifacts, lanes, evidence
  rules and the review chain all still work — only the mechanical corroboration is absent.
- Advisory mode is **visible and recorded** — surfaced at session start and written into the
  artifact — so a `SUMMARY.md` produced without corroboration is never mistaken for one that
  survived it.

The alternative (silently shipping a harness whose gates do nothing, under a "peer" label) is
exactly the traceability-read-as-truth failure the repo's gate-verifiability rule exists to
prevent.

---

## 6a. Ensemble diversity becomes runtime-aware

**Decision D1 has a consequence that must be designed for, not absorbed.** Today the external
heterogeneous PR reviewer *is* Codex, and its value comes from being a different model family
than the Claude chain that built the work — 16 rounds of independent findings on PR #173 alone.
Once Codex also **drives** the harness, a Codex-built PR reviewed by a Codex oracle shares both
the model family and the harness's own prompts. The diversity that made that review valuable
collapses, silently, with no signal that it happened.

**Design answer:** make the oracle a function of the builder, not a constant.

- The **review receipt gains a `runtime` field** per recorded review — which runtime produced it.
  The receipt is already the provenance artifact pinned to a HEAD sha; recording the runtime is
  the natural place, and it makes the property checkable rather than assumed.
- The independence rule becomes **cross-runtime**: the external oracle must differ from the
  runtime that built the change. A Claude-built branch gets a Codex external review (today's
  behaviour, unchanged); a Codex-built branch gets a Claude external review.
- The external PR review stays **harness-blind** either way — it must not run the harness's own
  review prompts, or it re-inherits the inside oracle's blind spots regardless of model family.

This turns an implicit property the repo currently relies on into an explicit, verifiable one —
and it only becomes necessary *because* Codex is being promoted from oracle to peer driver.

---

## 7. Phasing

Ordered so that value and risk-reduction land before any Codex-specific file exists.

| Phase | Deliverable | Why this order |
|---|---|---|
| **0 — Spike** | Empirically confirm Codex hook payloads, tool-name aliasing, event coverage, `SessionEnd` budget, the skills discovery directory, **and that a subagent wave actually dispatches and returns under Codex**. | Docs disagree in places and upstream coverage bugs are open. **Blocking** — everything downstream is built on these facts. D1 adds the subagent probe: peer-driver status is unattainable if wave dispatch doesn't work. |
| **1 — Neutralise** | Rule-path neutralisation, universal explicit rule Reads, hook input shim, neutral invocation prose. **No Codex files.** | Pure refactor of the existing harness, provable by the existing test suite. Ships value (closes a real Claude-side gap) even if Codex support is later dropped. |
| **2 — Adapter** | Codex deploy target: skills, `agents/*.toml`, `hooks.json`, `AGENTS.md`. | **On the critical path under D1** — Codex driving the agents means the TOML emitter and `sandbox_mode` reviewer isolation are load-bearing, not optional. |
| **3 — Parity + honesty** | Manifest runtime block, static-parity drift guard (per-PR), capability probe, advisory-mode reporting, **review-receipt `runtime` field + cross-runtime independence rule**. | Makes the divergence checkable rather than folkloric, and makes ensemble diversity verifiable (§6a). |
| **4 — Entry** | `install-harness.sh --runtime claude\|codex\|both`, docs, `HARNESS.md` update. | Last: nothing to install until 2–3 are real. |
| **5 — Behavioural parity** | Golden-set harness behaviours executed on both runtimes; scheduled + pre-release gate. | **Added by D2.** This is what converts "peer" from a claim into truth-tier evidence. Deferred to last because it is the only phase that costs money per run. |

**Phase 1 is independently valuable and independently shippable.** That is deliberate — it means
the Codex decision can be reversed after Phase 1 at no loss.

**D2 moves the finish line, not the start.** Peer status is only real once Phase 5 exists;
Phases 0–4 are the same work either way. Declaring peer before Phase 5 means declaring it on
static evidence alone — acceptable if said plainly (§6), not if left implied.

---

## 8. Non-goals

- **Forking skills per runtime.** One source or the design has failed.
- **A Codex-specific workflow.** Same lanes, same artifacts, same gates — or the harness's
  claims stop being comparable across runtimes.
- **Cursor / OpenCode support now.** The adapter seam makes it possible later; adding it now
  would design against unknowns.
- **Mirroring Codex's cloud manager-worker sandbox model.** Out of scope; local CLI only.
- **Replacing the `.claude/` build.** Claude Code remains a first-class target, unchanged in
  behaviour.

---

## 9. Decisions

Recorded 2026-08-08. These were the design's three open questions; all are now settled.

| # | Decision | Consequence in this design |
|---|---|---|
| **D1** | **Codex drives the agents too** — a full peer driver, not only the external reviewer. | Subagent TOML emitter and `sandbox_mode` reviewer isolation move onto the critical path (§4.3, Phase 2). Subagent wave dispatch joins the Phase-0 blocking spike. Ensemble diversity must become runtime-aware (§6a). |
| **D2** | **Codex is a peer runtime**, not best-effort. | Parity becomes a release gate, split into static (per-PR, free) and behavioural (scheduled/pre-release, paid) tiers (§5). New Phase 5. The parity ledger becomes an owned, expiring exception list rather than a gap inventory. |
| **D3** | **Ship advisory** — do not wait on upstream hook coverage. | Advisory is defined as a transitional state with an exit criterion, and peer status is declared per-layer rather than wholesale (§6). |

### The one tension that survives

**D2 and D3 pull against each other**, and the design resolves it rather than hiding it: peer
status is claimed on the instruction and artifact/workflow layers at ship, while the enforcement
layer ships advisory and is carried as a named, owned exception until Codex's hook coverage
lands upstream. Anything else would either delay the ship (violating D3) or let "peer" mean less
than it says (violating the repo's own gate-verifiability rule).

**The residual risk to watch:** an exception list with no expiry is how "advisory" quietly
becomes permanent. The exit condition and owner on that ledger entry are the control — not the
intention to fix it later.

---

## 10. Sources

Codex CLI capability claims in this document were read from OpenAI's Codex documentation
(hooks contract, skills discovery, subagent TOML schema) and cross-checked against
third-party references and two open upstream coverage issues. They are **traceability-tier**
evidence — read, not executed — which is why Phase 0 exists.

- [Codex — Hooks](https://developers.openai.com/codex/hooks) ([current URL](https://learn.chatgpt.com/docs/hooks))
- [Codex — Build skills](https://developers.openai.com/codex/skills)
- [Codex — Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex — Custom prompts](https://developers.openai.com/codex/custom-prompts) (deprecated in favour of skills)
- [Codex — Configuration reference](https://developers.openai.com/codex/config-reference)
- [hookshot — Codex hook payload reference](https://github.com/CorridorSecurity/hookshot/blob/main/docs/reference-codex.md)
- [openai/codex#16732 — apply_patch does not emit PreToolUse/PostToolUse](https://github.com/openai/codex/issues/16732)
- [openai/codex#20204 — inconsistent PreToolUse hook coverage across tool handlers](https://github.com/openai/codex/issues/20204)
