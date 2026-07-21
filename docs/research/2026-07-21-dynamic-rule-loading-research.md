# Dynamic (On-Demand) Rule Loading — Deep Research

> Date: 2026-07-21 · Status: research only, no implementation
> Question: all 7 rules in `.claude/rules/` auto-load every session (~27.6 KB ≈ 7k tokens).
> Can we load them on demand — e.g. `plan-format` only when writing a plan,
> `wave-parallelism` only when executing waves — and should we?

---

## 1. Ground truth: what loads today, and who needs it

Measured on disk (2026-07-21):

| Rule | Size | Actually needed when | Always-on justified? |
|---|---:|---|---|
| `behavior.md` | 2.4 KB | every turn (behavioral SoT) | ✅ yes |
| `architecture.md` | 0.6 KB | pointer → `techstacks/` | ✅ negligible |
| `guidelines.md` | 0.5 KB | pointer → `techstacks/` | ✅ negligible |
| `orchestration.md` | 9.0 KB | multi-step work, active PLAN, subagent dispatch | ⚠️ partially — decision table + budget rows are broadly useful; escalation/wave detail is contextual |
| `auto-correct-scope.md` | 6.8 KB | executing a `specs/<slug>/PLAN.md` task | ❌ contextual |
| `plan-format.md` | 5.8 KB | writing/validating a `PLAN.md` | ❌ contextual |
| `wave-parallelism.md` | 2.4 KB | executing a multi-wave plan | ❌ contextual |

≈ **15 KB (~55%) of the always-on payload is contextual** — it states its own applicability
("Applies when executing a `specs/<slug>/PLAN.md` task", "Applies when writing `specs/<slug>/PLAN.md`").

Two structural facts that make on-demand loading cheap here:

1. **Skills already treat rules as canonical, path-addressed references.**
   `writing-plans` says "canonical: `.claude/rules/plan-format.md` — do not restate";
   `executing-plans` Step 0 validates against `plan-format.md` + `wave-parallelism.md` by path;
   `subagent-driven-development` hands `auto-correct-scope.md` to subagents by path.
   The invocation of the skill *is* a natural, deterministic load trigger — the only missing
   piece is an explicit "Read this file now" step if the rule stops being pre-loaded.
2. **The deploy pipeline syncs `rules/` wholesale** (`deploy-harness.sh` SYNCED_DIRS, with
   `architecture/guidelines/behavior` as protected files). Any restructure propagates to every
   consumer repo automatically — but also means consumers must be on a Claude Code version
   that supports whatever mechanism we choose.

## 2. Mechanisms available (documented, verified 2026-07-21)

### A. Path-scoped rules — `paths:` frontmatter ✅ official, deterministic

Claude Code (v2.1.198+) supports YAML frontmatter on `.claude/rules/*.md`:

```yaml
---
paths:
  - "specs/**/PLAN.md"
---
```

Rules **without** `paths` load fully at session start (current behavior). Rules **with** `paths`
load only when Claude touches a matching file. Docs: <https://code.claude.com/docs/en/memory.md>.

- Trigger class: **deterministic** (glob match) — the reliable class (see §3).
- Zero new infrastructure: same files, same deploy pipeline, one frontmatter block.
- Caveat A1: exact trigger semantics ("loads when a matching file is read" vs "…written") need
  one empirical test before relying on it for write-flows like plan authoring.
- Caveat A2: consumer repos below v2.1.198 would silently treat the frontmatter as body text —
  the rule would still always-load (fail-safe, not fail-dangerous, but verify).
- Caveat A3 (**unconfirmed**): whether path-scoped rules also trigger inside subagents was not
  confirmed in docs. Subagents DO inherit CLAUDE.md + rules (except built-in Explore/Plan,
  which skip both — <https://code.claude.com/docs/en/sub-agents.md>).

### B. Skill-step loading — "Read the rule as Step 0" ✅ no version dependency

Since skills already name the rules by path, add an explicit load instruction:
`executing-plans` Step 0 becomes "Read `.claude/rules/plan-format.md` and
`.claude/rules/wave-parallelism.md` now, then validate…". Remove the rule from auto-load.

- Trigger class: **deterministic once the skill runs**; the residual judgment risk is whether
  the skill itself gets invoked (mitigated here because `feature-intake` routes lanes explicitly
  and the lane chain names each skill).
- Works on any Claude Code version; survives in subagents (the dispatching skill puts the rule
  path into the subagent prompt — `subagent-driven-development` already does exactly this for
  `auto-correct-scope.md`).

### C. Hook-injected context — `hookSpecificOutput.additionalContext` ✅ official, deterministic

Eleven hook events (incl. `UserPromptSubmit`, `PreToolUse`, `SessionStart`, `SubagentStart`)
can inject up to 10,000 chars of context mid-session
(<https://code.claude.com/docs/en/hooks.md>). E.g. a `PreToolUse` hook on Write/Edit matching
`specs/*/PLAN.md` could inject `plan-format.md` verbatim — the same trigger style
`render-plan-on-write.sh` and `blast-radius-check.sh` already use.

- Strongest guarantee (cannot be "forgotten" by the model), but: 10k-char limit
  (`orchestration.md` at 9.0 KB is near it), repeated firing needs dedup logic, and it adds a
  hook to the high-blast `settings.json` surface (Rule 4 territory). Best held in reserve for
  a rule that MUST be present and has a clean tool-event trigger.

### D. What does NOT work

- `@import` in CLAUDE.md is **eager** — expanded at launch, zero savings
  (<https://code.claude.com/docs/en/memory.md>).
- Repackaging rules as standalone skills gets progressive disclosure (name+description ~100
  tokens at start, body on invoke) but moves the trigger into the **model-judgment** class —
  the unreliable one (§3) — and breaks the "rules are governance, skills are workflows" split.

## 3. Evidence: why bother, and what's the failure mode

**For trimming always-on context (context rot):**
- "Lost in the middle" (Liu et al. 2023/24): >30% accuracy drop for information placed
  mid-context vs edges. Controlled context-rot studies show reasoning accuracy degrading
  (0.92 → 0.68 in one study) well before the window fills
  (<https://redis.io/blog/context-rot/>).
- Anthropic's own Skills architecture is an explicit bet on progressive disclosure — long
  reference material should cost "almost nothing until you need it"
  (<https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills>).

**Against naive lazy loading (the counter-risk):** content the model doesn't know exists never
gets fetched. Cursor's ecosystem documents this concretely:

- Cursor's four rule types map exactly onto our options: **Always** (≈ current state),
  **Auto Attached** via globs (≈ mechanism A), **Agent Requested** via description
  (≈ mechanism D), **Manual**.
- Documented failure modes: Agent-Requested rules silently skipped when the description is
  vague (<https://forum.cursor.com/t/allow-rules-to-auto-attach-and-be-agent-requested-at-the-same-time/64319>);
  one community test found 0/9 compliance with legacy `.cursorrules` vs 9/9 with explicit
  `.mdc` + alwaysApply (<https://forum.cursor.com/t/cursorrules-isnt-loaded-in-agent-mode-i-tested-it-heres-what-actually-works/152045>).
- GitHub Copilot's path-scoped `.github/instructions/*.instructions.md` with `applyTo:` globs
  (stacking union semantics) independently converged on the same design
  (<https://github.blog/changelog/2025-09-03-copilot-code-review-path-scoped-custom-instruction-file-support/>).

**Synthesis:** two trigger classes exist — **deterministic** (glob / tool-event / skill-step:
near-100% reliable) and **model-judgment** (description-based: documented misses). Every
mechanism we adopt should be in the deterministic class, ideally doubled up
("belt and braces": `paths:` frontmatter **and** a skill-step Read).

## 4. Recommendation (per rule)

| Rule | Strategy | Trigger |
|---|---|---|
| `behavior.md` | keep always-on | — (it's the SoT; 2.4 KB is cheap) |
| `architecture.md`, `guidelines.md` | keep always-on | — (pointers, ~0.5 KB each) |
| `plan-format.md` | **A + B** | `paths: ["specs/**/PLAN.md"]` + explicit Read in `writing-plans` / `executing-plans` Step 0 |
| `wave-parallelism.md` | **A + B** | `paths: ["specs/**/PLAN.md"]` + Read in `executing-plans` / `subagent-driven-development` |
| `auto-correct-scope.md` | **B** (primary) | dispatching skill injects the path into every task-subagent prompt (already the pattern); optional `paths: ["specs/**"]` |
| `orchestration.md` | **split** | extract a ~1.5 KB always-on core (decision table + context-budget rows + "escalation exists, see full rule"); move escalation detail / wave protocol / examples to the on-demand remainder loaded via B |

Estimated always-on payload after: **~5 KB (~1.3k tokens) vs ~27.6 KB (~7k tokens) today — a
~75–80% reduction**, with every load trigger deterministic.

Explicitly rejected: hook-injection (C) as the default mechanism (reserve for a future
must-not-miss rule), rules-as-skills (D), description-only lazy loading (D).

## 5. Risks & open verifications before implementing

1. **Empirical test of `paths:` semantics** (Caveat A1) — does a rule with
   `paths: ["specs/**/PLAN.md"]` load *before* the first Write to a new PLAN.md? If it only
   fires on Read, the `writing-plans` Step-0 Read (mechanism B) is the real trigger and
   `paths:` is the backstop — acceptable, but we should know which is load-bearing.
2. **Subagent behavior of path-scoped rules** (Caveat A3) — unconfirmed in docs;
   `not_observed != absent`. Test with a `reviewer`-type subagent.
3. **Consumer version floor** — deployed repos need Claude Code ≥ v2.1.198 for `paths:`;
   below that the rule silently stays always-on (safe fallback, but savings don't materialize).
4. **Doc-truth lint / cross-references** — `CLAUDE.md`, `skills/README.md`, and several skills
   describe rules as auto-loaded ("deployed to `.claude/rules/`, which auto-loads"); the split
   of `orchestration.md` touches the most-referenced rule (7 skill/agent files reference the
   rule set; `feature-intake` alone 7 times). Run `bash scripts/run-tests.sh` after any change.
5. **`orchestration.md` split is the only risky edit** — the other changes are additive
   frontmatter + one skill line each. The split should be its own normal-lane change with an
   eval that the always-on core still routes correctly (cf. `skill-eval-blind-run-scoring`).
6. **High-blast surface** — none of the recommended changes touch `settings.json` or `hooks/`
   (that's precisely why C was rejected as default).

## 6. Suggested phasing (when/if implemented)

1. **Phase 0 — verify**: empirical tests for A1/A3 on this repo (tiny lane, throwaway rule).
2. **Phase 1 — low-risk wins**: add `paths:` to `plan-format.md` + `wave-parallelism.md`;
   add the Step-0 Read lines to the three consuming skills. (~8.2 KB off the floor.)
3. **Phase 2 — auto-correct-scope**: confirm every dispatch path injects the rule path into
   subagent prompts, then scope it. (~6.8 KB.)
4. **Phase 3 — orchestration split**: core + remainder, with blind-run eval. (~7 KB.)
5. Update `CLAUDE.md`/`skills/README.md` wording ("auto-loads" → "core auto-loads; contextual
   rules load by path/skill trigger") and `deploy-harness.sh` docs; bump VERSION/CHANGELOG.

---

### Sources

- Claude Code docs: [memory](https://code.claude.com/docs/en/memory.md) ·
  [skills](https://code.claude.com/docs/en/skills.md) ·
  [hooks](https://code.claude.com/docs/en/hooks.md) ·
  [sub-agents](https://code.claude.com/docs/en/sub-agents.md) ·
  [context-window](https://code.claude.com/docs/en/context-window.md)
- Cursor rules: [trigger.dev guide](https://trigger.dev/blog/cursor-rules) ·
  [forum: .cursorrules not loaded in agent mode](https://forum.cursor.com/t/cursorrules-isnt-loaded-in-agent-mode-i-tested-it-heres-what-actually-works/152045) ·
  [forum: auto-attach + agent-requested](https://forum.cursor.com/t/allow-rules-to-auto-attach-and-be-agent-requested-at-the-same-time/64319)
- [Anthropic: Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Copilot path-scoped instructions](https://github.blog/changelog/2025-09-03-copilot-code-review-path-scoped-custom-instruction-file-support/) ·
  [VS Code custom instructions](https://code.visualstudio.com/docs/agent-customization/custom-instructions)
- Context rot: [Redis](https://redis.io/blog/context-rot/) ·
  [Salesforce](https://www.salesforce.com/artificial-intelligence/ai-context/context-rot/) ·
  Liu et al., "Lost in the Middle" (2023/24)
- [alexop.dev: Stop Bloating Your CLAUDE.md — Progressive Disclosure](https://alexop.dev/posts/stop-bloating-your-claude-md-progressive-disclosure-ai-coding-tools/)
