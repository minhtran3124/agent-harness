# Codex Support — High-Level Design

> Vietnamese version: [`design.vi.md`](./design.vi.md)

**Status:** revised design only. No runtime adapter or enforcement change is implemented here.
**Evidence refreshed:** 2026-08-10 against Codex CLI 0.147.0, current OpenAI documentation,
and the `simplify` branch.
**Goal:** a user driving OpenAI Codex gets the same harness lanes, artifacts, workflow, and
release gates as a Claude Code user, from one semantic source of truth.

---

## 1. Feasibility and current capability baseline

Codex now exposes the three extension surfaces the harness needs: skills, lifecycle hooks, and
custom subagents. That makes a peer adapter feasible, but the two runtimes are not field-for-field
equivalent. The design therefore shares **semantics** and makes runtime policy mappings explicit.

| Harness dependency | Claude Code | Codex | Design conclusion |
|---|---|---|---|
| Prompt programs | `skills/<name>/SKILL.md` | `SKILL.md` skills, discovered from supported skill roots or plugins | share skill sources; validate discovery in each package |
| Enforcement | lifecycle hooks receiving JSON on stdin | lifecycle hooks enabled by default, with project trust and handler-coverage constraints | share hook logic behind a payload normaliser; detect effective coverage outside hooks |
| Isolated contexts | Markdown agents, model/tool allowlists | `.codex/agents/*.toml`, developer instructions, sandbox/config policies | share an agent contract; emit tested runtime bindings rather than transliterating fields |
| Repository instructions | `CLAUDE.md` and rules | hierarchical root-to-CWD `AGENTS.md` files | preserve existing `AGENTS.md`; manage only a bounded harness section or pointer |

The previous draft treated Codex hooks as experimental, opt-in, and broadly missing
`apply_patch` coverage. That is stale. On the evidence date:

- hooks are enabled by default in Codex and `codex features list` reports `hooks` as stable;
- an isolated live probe observed `PreToolUse` and `PostToolUse` for both shell execution and
  `apply_patch`;
- the `apply_patch` payload contains the raw patch in `tool_input.command`, not a single
  `tool_input.file_path`;
- project hook execution still depends on project trust/configuration; hosted tools have no
  lifecycle coverage, and specialised tool paths may opt out.

The risk is therefore **payload and effective-coverage mismatch**, not an assumption that Codex
never emits edit hooks.

### 1.1 Supported platform baseline

The existing hooks depend on Bash, `jq`, Git, and Python. The first supported Codex platform set
is therefore macOS, Linux, and WSL with those dependencies present. Native Windows is not claimed
until either every hook has a `commandWindows` implementation or a native adapter exists. The
runtime doctor (§5) must report unsupported platforms as advisory, never silently label them peer.

---

## 2. Architecture — one semantic core, explicit runtime bindings

The repository already separates editable sources from Claude's generated `.claude/` install.
Codex support keeps one editable semantic core and adds runtime bindings plus generated/installable
surfaces.

```
              SEMANTIC SOURCE                         RUNTIME BINDINGS
  ┌──────────────────────────────────────┐      ┌─────────────────────────┐
  │ skills/  agents/  rules/  hooks/     │─────►│ Claude policy mapping   │──► .claude/
  │ templates/  runtime/  scripts/       │      └─────────────────────────┘
  │ harness-manifest.json                │      ┌─────────────────────────┐
  └──────────────────────────────────────┘─────►│ Codex policy + packaging│──► plugin/project config
                                                └─────────────────────────┘
```

Four rules govern this seam:

1. **Workflow policy has one owner.** Lanes, artifacts, STOP conditions, review responsibilities,
   and evidence rules remain in shared sources.
2. **Runtime capabilities are explicit bindings.** Model names, tool permissions, sandbox policy,
   context-fork policy, matcher aliases, and package locations may differ and must be mapped and
   tested. Calling these transformations “mechanical” would hide real policy.
3. **Generated files are reproducible and validated.** The same source revision and adapter
   inputs must produce byte-stable output; generated TOML/JSON must pass the runtime's strict
   configuration parser.
4. **Divergence is declared.** Any missing capability is an owned, expiring exception with an exit
   condition in the runtime manifest, not a silent best-effort gap.

### 2.1 Packaging decision: hybrid by default

OpenAI recommends plugins for reusable distributions, and a Codex plugin can bundle skills and
hooks. Custom project agents and repository-level `AGENTS.md` integration have different ownership
and conflict semantics. The preferred package is therefore hybrid:

- **plugin-owned:** reusable skills and hook registration/assets;
- **project-adapter-owned:** generated `.codex/agents/*.toml`, runtime state, and the bounded
  `AGENTS.md` integration described in §6;
- **fallback:** direct project sync for all Codex assets only if the packaging spike proves that
  plugin discovery, trust, or local-development installation cannot satisfy the harness contract.

Phase 2 records that decision with an executable discovery probe. The semantic sources and parity
tests do not change if the fallback is selected.

### 2.2 Portability by layer

| Layer | Examples | Expected portability | Adapter responsibility |
|---|---|---|---|
| Logic core | run-state FSM, schemas, templates, manifest | complete | none beyond executable paths |
| Instruction surface | skills and rules | high | discovery, invocation-neutral prose, explicit rule delivery |
| Enforcement | hook shell logic | high after normalisation | config, matcher aliases, payload normalisation, coverage diagnosis |
| Agent policy | reviewer/implementer roles | semantic only | model, tools, sandbox, MCP, nesting, and context-fork bindings |
| Entry/config | `CLAUDE.md`, `AGENTS.md`, settings | runtime-specific | generated or bounded managed integration |

---

## 3. Enforcement contract — exact event matrix and one normalisation seam

The implementation must pin a tested event/tool matrix instead of relying on “hook support” as a
single boolean.

| Harness need | Codex event/tool path | Observed or documented baseline | Required control |
|---|---|---|---|
| Git command gates | `PreToolUse` on shell/unified execution | live probe observed pre/post shell events | matcher fixture + command normalisation |
| Edit isolation | `PreToolUse` on `apply_patch` | live probe observed event | parse every path in the patch; unknown input follows each gate's explicit fail policy |
| Post-edit checks | `PostToolUse` on `apply_patch` | live probe observed event | path-set normalisation; never assume one file |
| Prompt scope guidance | `UserPromptSubmit` | documented lifecycle event | golden payload fixture |
| Knowledge injection | `SessionStart` | documented lifecycle event | supplementary only; cannot prove hooks are active |
| Durable breadcrumb | `SessionEnd` | documented event with a short timeout | benchmark below the timeout and keep work bounded |
| Hosted/specialised tools | handler-dependent | hosted tools are outside lifecycle coverage; specialised paths may opt out | doctor reports coverage; unsupported edit paths cannot be called blocking parity |

### 3.1 Existing failure mode

Four current edit hooks read `.tool_input.file_path` and use an empty fallback. A Codex
`apply_patch` event instead carries a patch envelope in `tool_input.command`. Without an adapter,
those hooks can silently observe no path and allow the operation. This is a real fail-open, even
though the event itself fires.

### 3.2 Normalised hook input

Every hook consumes a single normaliser that reads stdin once and exposes:

- runtime and event identity;
- canonical tool class (`shell`, `edit`, `mcp`, or `other`);
- the complete, deduplicated set of touched repository paths;
- shell command, prompt text, and tool outcome when applicable;
- parse status: `known`, `partial`, or `unknown`.

A patch touching multiple files is set-valued by definition. `branch-isolation-guard`,
`blast-radius-check`, `ruff-on-edit`, and `render-plan-on-write` must evaluate every applicable
path. A parse failure must be visible. Each gate declares whether `partial`/`unknown` blocks,
warns, or is unavailable; the default is never silent success.

Golden fixtures cover Claude and Codex payloads, multi-file patches, rename/delete operations,
malformed input, paths with spaces, and paths outside the repository. Matcher tests separately
prove which tool handlers actually reach the normaliser.

### 3.3 Session-end work stays at SessionEnd

`state-breadcrumb.sh` currently belongs to `SessionEnd`. Codex gives that event a much smaller
budget than ordinary hooks, so the script must be timed and reduced if needed. It must **not** be
moved directly to `Stop`: Stop may repeat before the session ends, and the current per-session
idempotency could preserve the first, stale snapshot. Moving would require a replaceable snapshot
design plus repetition tests; that is a separate change, not the default adapter plan.

---

## 4. Agent contract — shared roles, runtime-specific security policy

The current `agents/*.md` files contain Claude model identifiers and Claude tool allowlists.
Codex `sandbox_mode` is not equivalent to those allowlists: read-only filesystem policy does not
by itself disable nested agents, shell access, MCP calls, or every non-filesystem side effect.
Therefore a direct Markdown-to-TOML field conversion cannot preserve the role contract.

The shared agent schema must express capabilities, not vendor fields:

- role instructions and output contract;
- filesystem access (`none`, `read-only`, or `workspace-write`);
- shell policy and network policy;
- allowed MCP servers/tools;
- whether nested delegation is allowed;
- context policy (`fresh`, `bounded`, or inherited);
- model-class requirement and runtime-specific model binding.

Each adapter owns a checked mapping from those capabilities to its runtime. An unmapped capability
is an adapter error, not an implicit default.

### 4.1 Reviewer profile

Review agents require, at minimum:

- read-only filesystem access;
- nested-agent delegation disabled;
- no uncontrolled side-effecting MCP tools;
- fresh or explicitly bounded context, preserving plan-blind/intent-blind boundaries;
- the structured verdict contract already defined by the harness.

A live Codex probe confirmed another important constraint: a custom agent profile can be selected
with a fresh/bounded fork, while a full-history fork inherits the parent's agent type and rejects
that override. Generated dispatch instructions and behavioural tests must use the supported
fresh/bounded path. If a runtime cannot enforce one capability, the parity ledger records the exact
exception rather than describing `sandbox_mode` as stronger than a tool allowlist.

---

## 5. Effective enforcement and advisory mode

Hook self-reporting is circular: when hooks are disabled, untrusted, misconfigured, or skipped,
`SessionStart` cannot announce that fact. Capability detection must therefore live **outside** the
hook system.

The adapter provides `harness doctor --runtime codex` (name illustrative at design stage). It is
invoked during installation and from the top-level entry/skill flow, not only from a hook. It
records and evaluates:

- Codex CLI version and declared hook feature state;
- supported OS and required executables;
- effective project trust and the hash of the trusted hook configuration;
- installed/package configuration hash versus generated expectation;
- required event/tool matcher coverage from the pinned capability matrix;
- skill and custom-agent discovery;
- last successful live or deterministic probe and its freshness.

Any unknown or stale load-bearing result yields advisory mode. A `SessionStart` message may echo
the result when hooks do run, but it is not the source of truth.

### 5.1 Mode semantics

| Mode | Meaning | Allowed claim |
|---|---|---|
| `enforced` | all required blocking paths are trusted, current, supported, and covered | peer enforcement for the declared matrix |
| `advisory` | workflow is usable but one or more mechanical controls are missing, stale, or unknown | no claim that blocking gates corroborated the run |
| `unsupported` | required runtime/platform capability is absent | no Codex peer claim |

The active mode and doctor evidence identifier are written into the run artifact/SUMMARY metadata.
Unknown must never collapse to `enforced`. Re-installation, config edits, CLI upgrades, or trust-hash
changes invalidate the cached diagnosis.

D3 (“ship advisory”) means alpha users may run with weaker enforcement while gaps are visible. It
does not justify a GA peer label before the behavioural and effective-enforcement gates pass.

---

## 6. Instruction delivery and `AGENTS.md` ownership

### 6.1 Rules and paths

Claude path-scoped `paths:` loading has no equivalent guarantee in Codex and is already unsafe for
isolated contexts. It becomes an optimisation only:

- every consuming skill/agent explicitly reads each load-bearing rule;
- prose references the repository source path (`rules/...`), never `.claude/rules/...`;
- `context-propagation-audit` proves delivery to each isolated context;
- adapter-time prose rewriting and duplicated inline policy are rejected.

### 6.2 Existing root `AGENTS.md` is user-owned

Codex discovers hierarchical `AGENTS.md` files from the repository root toward the working
directory. It does **not** use `.codex/AGENTS.md` as the repository instruction entry point. This
repository already tracks a root `AGENTS.md` whose content intentionally differs from `CLAUDE.md`.

The installer must never replace that file wholesale. It may use one of two non-clobbering
strategies, selected and tested during the packaging phase:

1. a sentinel-delimited managed section that points to the shared harness entry instructions; or
2. an explicit one-line pointer that the user chooses to add, leaving generated harness content in
   a separate file.

Fresh install, existing-custom-content install, reinstall, local edits inside/outside the sentinel,
and incoming conflict cases are contract tests. Conflicts preserve the local file and write a
reviewable incoming copy, consistent with the repository's current protected-file behaviour.

### 6.3 Invocation-neutral prose

Shared sources name the skill (“invoke the `feature-intake` skill”), not `/feature-intake` or
`$feature-intake`. Entry documents may teach runtime-specific invocation syntax.

---

## 7. Parity and provenance are release gates

Peer status has two evidence tiers.

| Tier | What it proves | When it runs |
|---|---|---|
| Deterministic adapter contract | byte-stable generated TOML/JSON, strict config parsing, skill/agent discovery, hook matcher/payload coverage, manifest parity, and non-clobber install behaviour | every PR, blocking |
| Behavioural parity | equivalent lane choice, artifacts, blocked operations, resumption, subagent review boundaries, and review receipt under Claude and Codex | scheduled and pre-release; blocking for GA |

Model-driven tests are behavioural evidence, not deterministic config tests. Their fixtures pin
inputs, expected invariant outputs, CLI/runtime versions, and allowed nondeterministic fields.

### 7.1 Runtime-aware review receipt

Recording only the reviewer runtime is insufficient: independence cannot be evaluated without the
builder provenance. The receipt evolves conceptually to:

```json
{
  "builder": {
    "runtime": "claude|codex|mixed",
    "client_version": "...",
    "model_family": "..."
  },
  "reviews": [
    {
      "runtime": "...",
      "model_family": "...",
      "origin": "internal|external",
      "harness_blind": true
    }
  ]
}
```

The final schema also retains the receipt's existing reviewed-SHA, review types, findings, and
verdict fields.

- `builder.runtime = mixed` means more than one runtime contributed implementation changes since
  the last accepted review boundary; the artifact records the contributing runtime/model set.
- The external oracle must be harness-blind and, where available, use a runtime/model family not in
  the builder set.
- If no disjoint oracle is available, the run requires an explicit owned exception or human review;
  it must not silently claim heterogeneous corroboration.

The checker enforces provenance shape and cross-runtime/model independence separately from review
truth. It must not claim that different labels guarantee independent reasoning.

---

## 8. Implementation phases and gates

| Phase | Deliverable | Exit gate |
|---|---|---|
| **1 — Capability baseline** | versioned event/tool/platform matrix; live fixtures for shell, `apply_patch`, trust/config, agent dispatch, and SessionEnd timing | every load-bearing claim is observed or marked unknown |
| **2 — Packaging decision** | plugin/hybrid spike versus direct sync; discovery and upgrade/conflict behaviour | one package path selected with a recorded fallback criterion |
| **3 — Semantic neutralisation** | repo-root rule references, universal explicit reads, invocation-neutral prose, runtime-neutral agent capabilities and binding maps | Claude behaviour unchanged; context-delivery audit passes |
| **4 — Hook seam** | payload normaliser, per-gate unknown policy, exact matcher/event fixtures | no silent fail-open for supported tool paths |
| **5 — Codex alpha adapter** | generated agents/config, non-clobber `AGENTS.md` integration, runtime doctor, mode recording | deterministic adapter suite passes on macOS/Linux/WSL baseline |
| **6 — Per-PR parity gate** | manifest runtime block, strict config/discovery/install checks, review provenance schema | deterministic checks block drift on every PR |
| **7 — Behavioural parity** | cross-runtime golden workflows and subagent boundary tests | required goldens pass on pinned supported versions |
| **8 — GA** | installer/docs expose Codex as peer; remaining exceptions reviewed | no unowned/expired exception; enforced or explicitly scoped advisory claim |

Phases 1–4 are prerequisites to wiring the Codex alpha adapter, not optional cleanup after it.
Phase 5 is an **alpha**, not GA. D2's peer claim becomes truthful only after Phases 6–7; D3 permits
an earlier advisory alpha but does not move that finish line.

---

## 9. Decisions

| # | Decision | Consequence |
|---|---|---|
| **D1** | Codex drives agents as a full workflow runtime. | agent capability mappings, fresh/bounded dispatch, and subagent behavioural tests are critical-path work |
| **D2** | Codex targets peer status. | deterministic parity is per-PR; behavioural parity blocks GA |
| **D3** | ship an advisory alpha before every mechanical path is enforceable. | doctor-derived mode is visible and recorded; advisory is not silently called enforced |
| **D4** | share semantic sources, not runtime configuration fields. | adapters contain explicit, reviewed policy bindings |
| **D5** | prefer hybrid plugin/project packaging. | plugin owns reusable skills/hooks; project adapter owns agents and bounded repository integration, subject to Phase-2 proof |
| **D6** | preserve root `AGENTS.md`. | no wholesale generation or overwrite; managed integration is conflict-tested |

---

## 10. Non-goals

- Forking skills or workflow policy per runtime.
- Claiming native Windows support before a Windows hook adapter exists.
- Mirroring Codex cloud orchestration; this design targets the local CLI/runtime.
- Replacing Claude's current install path or changing its workflow semantics.
- Treating a runtime label alone as proof of review independence.

---

## 11. Sources and evidence level

Capability claims were refreshed from official OpenAI documentation and checked with an isolated
local Codex CLI 0.147.0 probe. Documentation is traceability evidence; captured deterministic/live
fixtures in Phase 1 become provenance/behavioural evidence. Historical upstream hook gaps are not
used as the current architecture premise.

- [Codex hooks](https://developers.openai.com/codex/hooks)
- [Codex skills](https://developers.openai.com/codex/skills)
- [Codex subagents](https://developers.openai.com/codex/subagents)
- [Codex configuration reference](https://developers.openai.com/codex/config-reference)
- [Codex plugins](https://developers.openai.com/plugins/build/plugins)
- [Repository instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [openai/codex#16732](https://github.com/openai/codex/issues/16732) — historical
  `apply_patch` coverage issue, now closed; retained only to explain why older designs may be stale
