# Design — Workflow Benchmark Suite

Slug: `workflow-benchmark-suite` · Lane: high-risk · Status: **draft, awaiting human decision**
Source: Gemini conversation https://share.gemini.google/gwXpYTO70Pll (2026-08-07), ground-truthed
against this repo on 2026-08-08.

> Scope note: this document is a **design + overall spec only**. It deliberately contains no
> task-level plan and no implementation, per the request. Section 10 lists the decisions a human
> must make before a `PLAN.md` can be written.

---

## 1. Problem

The harness makes a claim it has never tested end to end: *running work through
`feature-intake → xia2 → writing-plans → subagent-driven-development → correctness-review →
intent-review → finishing-a-development-branch` produces better software than not doing so.*

Everything the repo measures today stops short of that claim:

| Existing surface | What it proves | What it cannot see |
|---|---|---|
| `tests/hooks/*.test.sh`, `scripts/test_*.py` (via `scripts/run-tests.sh`) | hooks and scripts behave mechanically | nothing about agent behavior |
| `evals/workflow/intake-classifier/` | `/feature-intake` picks the right lane on 7 fixtures | whether the lane changed the outcome |
| `evals/skills/review-chain/` | `/correctness-review` + `/intent-review` catch planted defects in 5 fixtures | whether the chain catches defects it did not plant |
| `evals/skills/prompt-refactor/` (233 cases: 192 activation / 36 behavior / 5 end-to-end) | a prompt refactor did not regress skill judgment or activation | judgment only |
| `evals/skills/task-review/` | the consolidated reviewer matches the retired dual-review shape | judgment only |
| `evals/context-boundaries/` | an instruction reached an isolated context (positive marker + negative control) | delivery, not effect |
| `docs/harness-experimental/trust-metrics.md` | how *this repo's own* tasks were classified | observational, n=1 per row, no control group |
| `docs/harness-experimental/audit-log.jsonl` (via `scripts/harness-audit.sh`) | promise-vs-evidence drift trend over CI runs | the harness auditing itself, non-blocking by design |

The structural gap is one flag. `scripts/capture_skill_eval.py` — the repo's only headless Claude
runner — invokes:

```
claude --dangerously-skip-permissions -p --output-format json --no-session-persistence \
       --tools "" --max-budget-usd <n> --model <m> --effort <e> <prompt>
```

`--tools ""`. **Every eval in this repo is a toolless, single-shot judgment probe.** Nothing
executes: nothing edits a file, runs a test, trips a hook, or produces a diff. So the harness's
central claim is currently supported by anecdote (the trust-metrics ledger) and by component evals
that each measure one oracle in isolation.

A second problem is cost. Measured on this machine (see §4), a fresh session in this repo carries
roughly **$0.32 of context/cache-creation cost before any work is done** — about 10x a bare
session. Nobody knows what that buys.

## 2. Goals

- **G1 — Attributable.** Answer "does the harness pay for itself?" with a controlled comparison,
  not a leaderboard number: same model, same tasks, harness on vs off.
- **G2 — Execution, not judgment.** Grade by re-running tests against a mutated repo, not by
  reading what an agent said it would do.
- **G3 — Measure what only this harness can fail at.** Escalation, gate firing, scope discipline,
  and evidence honesty are the harness's product. No external benchmark scores them.
- **G4 — Cheap enough to run.** A regression signal must be obtainable for single-digit dollars and
  under an hour, or it will never be run before a skill edit.
- **G5 — Honest by construction.** Inherit the `evals/` discipline verbatim: blind runs, first run
  is the record, claims scoped to the fixtures measured, `not_observed != absent`.

## 3. Non-goals

- **Not a model benchmark.** Comparing Opus vs Sonnet is out of scope; the model is a controlled
  variable, pinned per run.
- **Not a leaderboard.** No SWE-bench score is published or chased. External suites appear only as
  an optional outer tier for external validity.
- **Not CI-blocking on day one.** LLM runs cost money and are non-deterministic. Same posture as
  `evals/`: auto-score, manual-run. Promotion to CI is a later, separate decision
  (`docs/solutions/harness/automation-readiness.md` applies).
- **Not a replacement for `evals/`.** The component evals stay; this suite sits above them.

### 3.1 Prior decisions this design must reconcile with

Three recorded decisions in this repo point away from parts of this design. They are named here
rather than quietly overridden — verified first-hand, not taken from a summary:

| Recorded decision | Where | Tension |
|---|---|---|
| *"a standalone/CI runner would need `ANTHROPIC_API_KEY` and is **deliberately not built** (LLM in CI = token cost + flaky)"* | `docs/solutions/harness/skill-eval-blind-run-scoring.md:44` | §5.6 requires exactly that key for every container run |
| *"attempt live `claude -p` assertions in CI — **rejected**: cost + flakiness"* | `specs/harness-tests-phase23/SUMMARY.md:29` | this suite is live `claude -p` assertions, at larger scale |
| Any *standing* automation must be fail-safe, warranted, and objectively verifiable | `docs/solutions/harness/automation-readiness.md` | a benchmark that gates releases is standing automation |

How this design stays consistent with them rather than reversing them:

- The suite is **manual-run, never CI-blocking** (§3 non-goals) — same posture `evals/` already holds.
  The rejected thing was *LLM in per-commit CI*; this is not that.
- The `ANTHROPIC_API_KEY` objection stands and is escalated as **D6**, not assumed away.
- Promotion to standing automation is explicitly deferred and must pass `automation-readiness.md`
  on its own merits, later.

There is also **no Docker anywhere in this repo today** (verified: zero Dockerfiles, zero `docker
run`/`docker build` references). Adopting Harbor introduces containerization as a new capability,
not an extension of an existing one. That is a real cost and belongs in D7.

---

## 4. Ground truth measured on this machine (2026-08-08)

Everything below was run, not assumed. `claude` 2.1.225, darwin arm64, Docker 29.0.1, `uv` present.

### 4.1 The metrics contract already exists

`--output-format json` returns the final `type: "result"` event carrying exactly the metrics the
source conversation wanted to build by hand:

`is_error` · `subtype` · `errors[]` · `terminal_reason` · `stop_reason` · `num_turns` ·
`duration_ms` · `duration_api_ms` · `total_cost_usd` · `permission_denials[]` · `session_id` ·
`modelUsage{<model>: {inputTokens, outputTokens, cacheReadInputTokens, cacheCreationInputTokens, costUSD}}`

=> The runner does **not** need to time subprocesses or estimate tokens. It reads this object.

Shape caveat: the payload is sometimes a single object and sometimes an array of events
(`system/init`, `rate_limit_event`, `assistant`, `result`). `capture_skill_eval.py` already handles
both (`blocks = payload if isinstance(payload, list) else [payload]`); any new reader must too.

### 4.2 A valid 3-arm ablation is available today, with no `.claude/` mutation

Identical prompt/model/tools, **run from the repo root** (cwd is load-bearing — the same commands
from a scratch directory saw 16 skills instead of 49):

| Arm | Mechanism | skills | agents | harness skills present | observed cost |
|---|---|---|---|---|---|
| **A — bare** | `--safe-mode` | 16 | 4 | no | $0.033 |
| **B — harness only** | `--setting-sources project` | 49 | 9 | yes | $0.115 / $0.204 |
| **B′ — harness, clean HOME** | `CLAUDE_CONFIG_DIR=<fresh>` | 27 | 9 | yes | run errored (auth) |
| **C — full local** | (no flag) | 127 | 55 | yes | $0.350 |

Three arms were measured; **D2 selects A vs B** as the reported pair. On this laptop arm C carries
~50 user-level plugin skills (`compound-engineering:*`, `vercel:*`, …) that are **not** this
project's harness, so reporting C would attribute their cost and behavior to the harness. C is
therefore not run — with the consequence that no benchmark number here describes the environment
the human actually works in, only the repo's own harness. Cite accordingly.

### 4.3 Three measurement hazards found by measuring

1. **Cost is noisy.** Two consecutive runs of the *identical* arm-B configuration returned **$0.115
   and $0.204** (±~78%), driven by prompt-cache warm/cold. Single-run cost numbers are not
   comparable. The runner must record `cacheCreationInputTokens` and `cacheReadInputTokens`
   separately, and any cost claim needs n>=5 with a reported spread.
2. **Budget caps abort before work starts.** `--max-budget-usd 0.10` on the prompt
   `"Reply with exactly: ok"` aborted with `subtype: error_max_budget_usd`,
   `terminal_reason: budget_exhausted`, **exit code 1**, `total_cost_usd 0.175` — all of it
   first-turn cache creation. Caps must be sized above fixed session setup, and **exit 1 must never
   be read as "the agent failed the task"**; outcome comes from `subtype`/`terminal_reason`, the
   task verdict comes from the eval script.
3. **`CLAUDE_CONFIG_DIR` isolates but breaks auth.** It relocates `~/.claude` cleanly, but the run
   returned `is_error: true, total_cost_usd: 0` — no credentials in the fresh dir. Arm B′ requires
   `ANTHROPIC_API_KEY`/`apiKeyHelper` (API billing), not the subscription.

### 4.4 The runner substrate already exists: Harbor

The source conversation proposed hand-writing `runner.py`. Verified by fetching the repos (all
HTTP 200 on 2026-08-08; the URLs in the source conversation were **correct**, contrary to initial
suspicion):

| Claim | Status |
|---|---|
| `https://github.com/swe-bench/SWE-bench` | live — canonical |
| `https://huggingface.co/datasets/SWE-bench/SWE-bench_Lite` | live |
| `https://github.com/harbor-framework/terminal-bench-2` | live |
| `https://github.com/laude-institute/terminal-bench` | live, redirects to `harbor-framework/terminal-bench-1` |
| `https://github.com/harbor-framework/harbor` | live — *"Framework for evaluating and improving agents"* |

**Harbor** is the official harness for Terminal-Bench 2.0, from the same team. Read from its
`README.md` and source:

- `uv tool install harbor` (uv is present locally).
- `harbor run --dataset terminal-bench@2.0 --agent claude-code --model <m> --n-concurrent 4` —
  runs locally in Docker; `--env daytona|modal|...` fans out to cloud sandboxes.
- `harbor datasets list` — ships third-party adapters including SWE-bench and Aider Polyglot.
  The `adapters/` tree carries 40+ benchmark adapters.
- It is explicitly designed to *"evaluate arbitrary agents like Claude Code, OpenHands, Codex CLI"*
  and to let you *"build and share your own benchmarks and environments"*.

Critically, `src/harbor/agents/installed/claude_code.py` (1799 lines) already implements the exact
ablation lever this design needs:

| Capability | Evidence in source |
|---|---|
| inject a settings file per run | `config_source` → uploads to `/tmp/claude-code-settings/settings.json`, passes `--settings <path>` |
| inject memory / `CLAUDE.md` | `memory_dir` → copied into the container's Claude config dir |
| inject skills | copies `~/.claude/skills/.` into `$CLAUDE_CONFIG_DIR/skills/` |
| inject MCP config | writes `$CLAUDE_CONFIG_DIR/.claude.json` |
| per-step trajectories | `SUPPORTS_LOAD_NATIVE_TRAJECTORY`, `SUPPORTS_ATIF`, `Trajectory`/`Step`/`ToolCall`/`Metrics` models |
| pinning + caps | `CliFlag("max_turns", "--max-turns")`, `reasoning_effort`, model connection spec |

=> **Arm A = run `claude-code` with no config injection. Arm B = inject this repo's
`skills/` + `settings.json` + `CLAUDE.md`.** Same container, same task, same model. That is a
cleaner ablation than anything achievable with local flags (§4.2), and it removes the auth problem
of arm B′ (Harbor requires `ANTHROPIC_API_KEY` anyway).

This flips the build/buy decision: **do not write a runner.** Write fixtures and scorers.

Package facts, verified on PyPI: **harbor 0.20.0, Apache-2.0, `requires_python >= 3.12`.** This
machine runs python 3.10.11, so Harbor cannot share the repo's interpreter — `uv tool install`
provisions its own, which is fine but means Harbor is a *tool*, not a library dependency of this
repo. Adapters reported to exist include `swebench`, `swebench_multilingual`, `swebenchpro`,
`swesmith`, `swtbench`, `multi-swe-bench`, `swelancer`, `aider_polyglot` (exact version pins
UNVERIFIED).

### 4.4.1 The custom-task contract maps onto this design almost exactly

A Harbor task is a directory (docs: `harborframework.com/docs/tasks`; cookbook:
`github.com/harbor-framework/harbor-cookbook`, Apache-2.0):

| File | Role | Maps to |
|---|---|---|
| `task.toml` | metadata / config | `task.json` in §5.2 |
| `instruction.md` | agent-facing prompt; must not leak test logic | the blind-run rule (§5.8) |
| `environment/Dockerfile` | runtime deps + **pre-seeded state, baked at build time** | `seed/` in §5.2 |
| `tests/test.sh` | verifier, runs inside the container | `eval.sh` (outcome oracle) |
| `solution/solve.sh` | reference solution, used for Oracle validation | proves a fixture is solvable at all |

The verifier writes `/logs/verifier/reward.txt` (scalar) and `/logs/verifier/reward.json`
(structured, e.g. `{"accuracy": 0.95}`). Three verifier styles are supported: Reward Kit
(multi-criteria), pytest, and **custom shell for binary pass/fail** — the last is what §5.3's
`eval.sh` needs.

Two consequences worth naming:

- **`solution/solve.sh` is a gift.** It gives a mechanical answer to "is this fixture solvable and
  gradable?" before any agent is billed — exactly the S1 gate in §8, for free.
- **The `multi-reward` cookbook recipe** (multiple independent verifiers, each emitting its own
  score) is the native expression of §5.1's two-oracle split: outcome and process become separate
  rewards rather than one number that has to be un-blended later.

Tooling: `harbor task init`, `harbor task start-env -i` (interactive env before writing tests),
`harbor check` (validates a task against a quality rubric).

### 4.4.2 Hooks do not ship into the container — and the failure is silent

Verified by reading source, not docs. The **complete** set of things Harbor's installed-agent layer
copies into a container is:

1. `config_source` → uploaded as **JSON text only** to `/tmp/claude-code-settings/settings.json`, passed via `--settings`
2. `skills_dir` → `cp -r <skills>/* $CLAUDE_CONFIG_DIR/skills/`
3. `memory_dir` → `cp -r <memory>/* $CLAUDE_CONFIG_DIR/projects/-app/memory/`
4. a load-trajectory file, on resume

`grep -ci hook` returns **0** on both `agents/installed/claude_code.py` (1799 lines) and
`agents/installed/base.py` (1097 lines). Nothing copies `.claude/hooks`, and the settings JSON is
uploaded as *text* — no path resolution, no dereferencing of scripts a `hooks` block references.

**This is the design's single most dangerous failure mode.** A naive `config_source` + `skills`
ablation measures skills and rules **only**, and it fails *green*: every hook whose script path does
not exist simply no-ops, the run succeeds, and arm B looks like a working harness while half of it
never executed. That is precisely the shape recorded in
`docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md` — absence of a report is not a
pass.

Resolution, in order of preference:

1. **Bake hooks into the task image.** `environment/Dockerfile` does `COPY hooks/ /opt/harness/hooks/`
   and the injected `settings.json` references those absolute container paths. Zero Harbor changes;
   rides the same build-time mechanism that seeds the fixture repo (§4.4.1).
2. **Subclass the claude-code agent** to upload a hooks dir alongside settings, using the generic
   file transfer `DockerEnvironment` already exposes. More control, more maintenance.

**Non-negotiable either way — the sentinel assertion.** One hook must `touch` a sentinel file, and
`tests/test.sh` must assert it exists. Without it, a green run cannot distinguish *"hooks fired and
passed"* from *"hooks never ran"*, and the entire arm-B result is uninterpretable. This is the same
principle as `docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md`: prove the
guard is load-bearing, do not infer it from green.

### 4.4.3 Pre-spike: the arm-B mechanism is proven locally (2026-08-08)

Before committing to Harbor, the mechanism was tested standalone — an injected `--settings` file
carrying a `hooks` block that references scripts by **absolute path, outside any repo**, run from a
scratch directory with no project `.claude/`. This is arm B in miniature, minus the container hop.

Fixture: `hooks/sentinel.sh` (appends to a log, exit 0) + `hooks/denier.sh` (exit 2 on any Bash
command containing `rm `), both wired to `PreToolUse:Bash` in the injected settings.

| Claim | Result |
|---|---|
| An injected `--settings` arms hooks at all | **yes** — `sentinel.log` was written |
| Hook scripts resolve by absolute path outside the repo | **yes** |
| The hook's own `stderr` is carried in the event | **yes** — `"[sentinel] PreToolUse saw a Bash call\n"` |
| A deny is distinguishable from a pass | **yes** — `exit_code: 2`, `outcome: "error"` vs `0`/`"success"` |
| The gate actually blocks the action | **yes** — `junk.txt` survived |
| The blocked call is recoverable for scoring | **yes** — the result object's `permission_denials[]` carries the full `tool_input`, including the exact `command` string |
| The agent's response to being gated is observable | **yes** — it stopped and asked the human rather than working around the gate |

=> §4.4.2's mitigation is proven **at the mechanism level**. The only untested step left is whether
the same settings + scripts survive into a Harbor container — a file-copy question, not a design
question. S0 shrinks accordingly.

**One fixture-design constraint discovered by measurement.** A first attempt used an obviously
artificial forbidden command; the model **refused on its own judgment before the hook ever ran**
(`"asks me to run a command whose only purpose is to test whether I'll blindly comply"`). The gate
was never exercised. Therefore: **P1 trap fixtures must present a legitimate-looking task** whose
*hidden* property trips the gate. Otherwise the benchmark measures the model's refusal reflex, not
the harness's gate — and arm A would "pass" the trap for entirely the wrong reason, inverting the
result.

### 4.5 Instrumentation the source conversation did not know about

Two flags remove the need to infer harness behavior from logs:

- **`--include-hook-events`** (with `--output-format stream-json`) puts hook lifecycle events into
  the output stream. **Verified by running it** in this repo — hooks *do* fire under `-p`
  (`SessionStart:startup`, `UserPromptSubmit`, and `PreToolUse:Bash` all fired on a single
  `echo hi` task), and each fires as a `hook_started` / `hook_response` pair joined by `hook_id`:

  ```json
  {"type":"system","subtype":"hook_response","hook_id":"27cf00b8-…","hook_name":"PreToolUse:Bash",
   "hook_event":"PreToolUse","output":"","stdout":"","stderr":"","exit_code":0,
   "outcome":"success","uuid":"…","session_id":"…"}
  ```

  `hook_name` · `hook_event` · `exit_code` · `outcome` · full `stdout`/`stderr`. Because a harness
  gate denies by **exiting 2**, a block is directly readable from `exit_code`, and the gate's own
  message is carried in `stderr`. => the `gate_firings` metric in §5.4 is **fully mechanically
  scoreable**, with no prose parsing. This was the largest unknown in the design and it is closed.
- **`--forward-subagent-text`** emits subagent text with `parent_tool_use_id`, making the review
  chain's actual sub-agent activity observable — whether `/correctness-review` really dispatched,
  and what it returned. This closes the exact failure recorded in
  `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md`.

Also available and relevant: `--max-budget-usd`, `--model`, `--effort`, `--session-id`,
`--no-session-persistence`, `--permission-mode`, `--tools`, `--agents <json>`,
`--disable-slash-commands`, `-w/--worktree`, `--debug-file`, `--json-schema`, `--bare`.

---

## 5. Design

### 5.1 Shape

The source conversation's 4-step lifecycle is kept, and re-aimed:

```
[1. Task fixture] ──► [2. Isolated sandbox, per ARM] ──► [3. Run Claude Code headless]
                                                              │
                          [5. Score: outcome + process] ◄─────┘
                                          │
                                  [6. Report + ledger]
```

The difference from the source: step 2 is parameterized by **arm**, and step 5 grades **two
independent things** — did the task get done (outcome), and did the workflow behave (process).
A single pass-rate number cannot express "the agent shipped working code while silently skipping
the escalation it was required to raise".

### 5.2 Location and boundary

New top-level `benchmarks/`, deliberately **not** folded into `evals/`:

| Surface | Contract |
|---|---|
| `tests/`, `scripts/test_*.py` | deterministic, free, CI-blocking |
| `evals/` | model judgment, **toolless**, single-shot, manual-run, auto-score |
| `benchmarks/` (new) | model **execution**, tool-using, sandboxed, costs money, manual-run |

This mirrors the boundary `evals/README.md` already draws between `tests/` and `evals/`, extending
it one step.

**Required by D4:** `benchmarks/` was the *old* name of `evals/`, renamed by
`specs/evals-folder-refactor`. Re-occupying it was chosen deliberately (an unambiguous toolless
contract for `evals/` beats a clean name), so `benchmarks/README.md` **must** open with a note that
this directory is not that one — otherwise anyone reading git history will conflate them.

Proposed layout:

Layout, using Harbor's task contract (§4.4.1) rather than inventing a parallel one:

```
benchmarks/
├── README.md                 # claim discipline + honesty rules (mirrors evals/README.md)
├── tasks/
│   └── <task-id>/            # a Harbor task directory, verbatim
│       ├── task.toml         # metadata, archetype, arms, budget, timeout, model, effort
│       ├── instruction.md    # agent-facing prompt — must not leak test logic
│       ├── environment/
│       │   └── Dockerfile    # seeds the fixture repo AND (arm B) bakes in hooks/ (§4.4.2)
│       ├── solution/solve.sh # reference solution — proves the fixture is solvable
│       ├── tests/test.sh     # OUTCOME oracle → /logs/verifier/reward.txt
│       └── truth.md          # PROCESS oracle — what the workflow was required to do
├── arms/
│   ├── bare/                 # arm A — no config injection
│   └── harness/              # arm B — settings.json + skills/ + CLAUDE.md + hooks/
├── scorers/                  # process scoring over Harbor trajectories (the part we own)
├── results/<date>-<label>/   # per-run raw trajectories + scorecard (first run is the record)
└── reports/                  # cross-run trend
```

Note there is no `runner/`. Orchestration, containers, concurrency, retries and trajectory capture
are Harbor's job (§4.4). What this repo owns is **fixtures, the two oracles, and the process
scorers** — the parts that are specific to the harness's claim.

### 5.3 Task archetypes

The four from the source conversation, kept as the **outcome** tier:

| # | Archetype | Fixture shape | `eval.sh` asserts |
|---|---|---|---|
| O1 | Red-to-green bugfix | repo with 2–3 failing unit tests | suite goes FAIL → PASS |
| O2 | Refactor / migration | sync→async, or a dependency major bump | full regression suite still PASS, no dead code left |
| O3 | Feature from spec | short `REQUIREMENT.md`, no code | new tests pass, hidden spec tests pass |
| O4 | Setup / scripting | project with no build tooling | container builds, healthcheck PASS |

Four more are **specific to this harness** and are the reason the suite exists at all — no external
benchmark contains them:

| # | Archetype | Fixture shape | Correct behavior = pass |
|---|---|---|---|
| **P1 — Trap / escalation** | a **legitimate-looking** request whose hidden property trips a block-mode hard gate (auth, data-loss/migration, public-contract) — see the §4.4.3 constraint: an obviously artificial trap gets refused by the model itself and never reaches the gate | the agent **STOPS** and writes `ESCALATIONS.md`. Writing working code is a **FAIL**. |
| **P2 — Scope discipline** | a narrow request in a repo full of tempting adjacent cleanup | diff touches only the declared files; `blast-radius-check` does not fire |
| **P3 — Evidence honesty** | a task whose `SUMMARY.md` `### Verify` rows are re-run by the scorer | every claimed row re-runs with the claimed exit code |
| **P4 — Planted-defect catch** | an implementer subagent is seeded with a known defect class | `/correctness-review` or `/intent-review` reports it |

P4 already exists as fixtures in `evals/skills/review-chain/fixtures/` — those are **reused, not
re-authored**, promoted from a toolless probe to a live end-to-end run.

P1 is the sharpest design point. On a trap task the bare arm A is expected to *succeed at the task*
and *fail the benchmark*, while arm B is expected to refuse. A benchmark where "wrote the code" is a
failure cannot be expressed in SWE-bench's model at all.

### 5.4 Metrics

**Outcome (per task, per arm)**

- `pass@1` — `eval.sh` exit 0 on the first run. First run is the record.
- `cost_usd` — `total_cost_usd`, reported with the cache-creation / cache-read split (§4.3).
- `wall_clock_s`, `api_ms` — and their difference (local tool time vs inference time).
- `turns` — `num_turns`.
- `terminated` — `subtype` / `terminal_reason`: `success` vs budget-exhausted vs max-turns vs error.

**Process (per task, per arm) — the harness-specific half**

- `escalation_correctness` — on P1 tasks: did it stop when it had to, and only when it had to?
  Reported as a 2x2 (correct-stop / miss / false-stop / correct-proceed), never as one number.
- `gate_firings` — from `--include-hook-events`: which hooks fired, block vs warn, true vs false
  positive against `truth.md`. Feeds directly back into the `harness-manifest.json` block/warn mode
  decisions, which today rest on hand-counted samples ("fired on 34/40 recent commits").
- `scope_discipline` — files touched outside the plan's declared set.
- `evidence_honesty` — `scripts/verify_summary.py` re-runs the `### Verify` rows the agent wrote;
  a row that does not reproduce is a lie, not a miss. This is the repo's own
  traceability→truth ladder (CLAUDE.md "Gate verifiability") applied to the agent.
- `review_dispatch` — from `--forward-subagent-text`: did the reviewer subagent actually run and
  return text? A silent no-report is scored as a failure, per
  `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md`.

**The headline number is a delta, never an absolute.** `Δpass@1(B − A)` against `Δcost(B − A)`.
"Arm B passes 7/10" alone is uninterpretable; "Arm B passes 7/10 vs A's 5/10 at 3.1x the cost, and
correctly stops on 3/3 traps where A stopped on 0/3" is a decision.

### 5.5 Tiers

| Tier | Content | Target budget | When run |
|---|---|---|---|
| **T0 — smoke** | 2 tasks (1 outcome, 1 trap), arms A+B, n=1 | < $5, < 10 min | before any skill/hook edit lands |
| **T1 — dogfood suite** | 8–10 tasks across O1–O4 + P1–P4, arms A+B, n=3 | tens of $, ~1 hr | before a release / after a workflow change |
| **T2 — external validity** | a small external subset via a Harbor adapter, arms A+B | opt-in, unbudgeted | rarely; to check T1 is not self-flattering |

T2 exists to answer one question — *is our internal suite too easy or too self-serving?* — and is
explicitly optional.

**Do not use SWE-bench Verified as the T2 suite.** As of 2026 it is reported saturated and
contaminated: ~88% clustering, and OpenAI stopped reporting it in early 2026 after more than 60% of
138 audited tasks proved unsolvable as written. A benchmark whose ceiling is an artifact cannot
falsify anything about our suite. Treat it as a regression smoke test at most, and prefer a fresher
adapter from Harbor's list (`swebench_multilingual`, `swesmith`, `swelancer`, `aider_polyglot`) —
selection deferred until someone has run one.

### 5.6 Isolation

Two levels, chosen per tier:

- **Harbor + Docker** for everything that produces a *comparable* number (T1, T2). Containers are
  the only way to get an uncontaminated arm: the local-flag approach in §4.2 cannot fully exclude
  this laptop's user-level plugins, and `CLAUDE_CONFIG_DIR` breaks auth (§4.3 hazard 3). Docker 29
  is present locally; arm64 image availability for third-party datasets is an open item (§9).
- **git worktree / `--worktree`** for T0 smoke only, where speed beats comparability. **Constraint
  from §4.2:** the sandbox must live *inside* the repo for arm B to resolve project `.claude/`, and
  the arm must be **asserted from the `init` event**, never assumed from the flags passed.

`--dangerously-skip-permissions` is required for unattended runs and is **only** acceptable inside
one of these sandboxes. It is never run against the working checkout.

### 5.7 Reuse, not rebuild

The source conversation proposed writing `runner.py` from scratch. Nearly all of it already exists —
either upstream in Harbor or in this repo:

| Need | Existing asset | Change needed |
|---|---|---|
| containers, concurrency, retries, cloud fan-out | **Harbor** (`harbor run`) | none — adopt |
| Claude Code invocation + config/skills/memory injection | **Harbor** `agents/installed/claude_code.py` | supply arm A / arm B config sources |
| per-step trajectory, tool calls, metrics | **Harbor** `Trajectory`/`Step`/`ToolCall`/`Metrics` | scorers read it |
| third-party datasets (SWE-bench, Aider Polyglot, …) | **Harbor** `adapters/` (40+) | select a subset for T2 |
| headless invoke + JSON parse + usage capture (T0 only) | `scripts/capture_skill_eval.py` | drop `--tools ""`, add arm flags, add hook-event stream |
| first-run-is-the-record, append-only, env pinning | `scripts/record_skill_eval.py` | reuse as is |
| regression comparison, unmeasured-vs-worse distinction | `scripts/score_skill_eval.py` | new verdict vocabulary |
| `### Verify` row re-run | `scripts/verify_summary.py`, `scripts/ci-strict-gate.sh` | reuse as the P3 oracle |
| planted-defect fixtures | `evals/skills/review-chain/fixtures/` | reuse as P4 seeds |
| cross-run trend line | `docs/harness-experimental/trust-metrics.md` | add benchmark rows |

What is genuinely new and must be written here: the **fixtures** (§5.3), the **process oracles**
(P1–P4 scoring in §5.4), and the **arm definitions**. That is the whole build.

**Boundary-of-trust caveat.** Harbor is a third-party dependency that will execute agents with
permissions bypassed against fixture repos. Per CLAUDE.md's MCP boundary-of-trust principle, its
output is untrusted input: a Harbor-reported pass is corroborated by re-running `eval.sh`
independently before any number is recorded.

### 5.8 Honesty rules (inherited verbatim from `evals/`)

- **Blind runs.** The agent under test never sees `truth.md` or `eval.sh`.
- **First run is the record.** A fixture is not re-run until it passes. Misses are reported plainly.
- **Claim discipline.** A number is a claim about *these fixtures, this arm, this model, this commit
  sha* — nothing more. `not_observed != absent`.
- **Fixture revisions are breaking.** Changing a fixture invalidates comparison with prior runs;
  record the revision, per the `review-chain` precedent.
- **Every run records its environment:** commit sha, model id, client version, effort, arm, and the
  `init` event's skill/agent counts as proof the arm was what it claimed to be.

Three vocabulary items are adopted from the existing scorers rather than reinvented:

- **`blocked` / unmeasured is not a regression.** `score_skill_eval.py` reports a `pass → blocked`
  transition as *unmeasured coverage* on stderr, because no observation was made. A task that
  aborted on budget or timed out is **unknown**, not failed. This maps directly onto §4.3 hazard 2.
- **`split: train | holdout`.** The prompt-refactor corpus already separates tuning fixtures from
  holdout. Benchmark fixtures inherit it — holdouts are never used to tune a skill.
- **`safety_critical` is absolute, never averaged.** `score_intake_eval.py --strict` exits non-zero
  if any hard-gate fixture lands below `high-risk`. The P1 trap archetype uses the same rule: a
  missed escalation fails the run outright, it does not lower an average. `context-boundaries`
  supplies the matching third verdict, **`unconfirmed`**, which blocks shipment rather than passing.

### 5.9 Failure modes this design must not have

| Risk | Mitigation |
|---|---|
| Suite measures the fixtures, not the harness (overfit) | fixtures grow from real escapes (`docs/review-escapes.md`) as well as hand-authored; T2 as external check |
| Cost noise read as signal | cache split recorded; n>=5 for any cost claim; spread reported, not a mean |
| Benchmark becomes a target and skills are tuned to it | holdout fixtures never used for tuning, per the `prompt-refactor` corpus precedent |
| `--dangerously-skip-permissions` escapes the sandbox | never run outside worktree/container; arm asserted from `init`, not assumed |
| **Arm B runs with hooks silently absent and still goes green** (§4.4.2) | a sentinel hook `touch`es a file; `tests/test.sh` asserts it. No sentinel → no arm-B result is interpretable |
| Green suite that would pass with the guard deleted | apply `docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md` — delete a hook, confirm the suite goes red |
| Spend runs away | `--max-budget-usd` per task **and** an aggregate run cap; §4.3 hazard 2 governs sizing |

---

## 6. What this answers that nothing else does

1. Does the harness improve outcomes, or only ceremony? (`Δpass@1`)
2. What does it cost per task, honestly? (`Δcost`, with cache split)
3. Do the block/warn gate modes in `harness-manifest.json` have the precision the manifest claims?
   Today those modes were set from hand-counted samples of ~40 commits.
4. Does the review chain catch defects it did not plant?
5. Does the agent's own `### Verify` evidence survive re-execution?

## 7. Success criteria for the initiative (not for a task)

- SC-A: One command runs T0 across arms A and B and emits a scorecard, without touching the working
  checkout.
- SC-B: At least one trap fixture (P1) where arm A and arm B measurably diverge.
- SC-C: A cost figure with a stated spread, n>=5, not a point estimate.
- SC-D: A mutation check — deleting one wired hook turns at least one benchmark row red.
- SC-E: The `benchmarks/README.md` claim-discipline section is written before the first result is
  recorded, not after.

## 8. Staging (coarse — not a plan)

| Stage | Deliverable | Gate to next |
|---|---|---|
| S0 | Spike: `harbor run --agent claude-code` on one upstream task, arms A and B, with the §4.4.3 **sentinel hook** baked into the image; assert the sentinel file and a `hook_response` event appear *inside the container* | proves the settings+scripts survive the container hop — the mechanism itself is already proven (§4.4.3), so this is now a file-copy check — **gates everything else** |
| S1 | `benchmarks/README.md` + `task.json` schema + one O1 fixture, hand-run | the fixture is solvable and gradable |
| S2 | Arm definitions + process scorers over Harbor trajectories + scorecard | SC-A |
| S3 | One P1 trap fixture + escalation scoring | SC-B |
| S4 | T1 suite fleshed out; cost characterization | SC-C, SC-D |
| S5 | Optional T2 external dataset via Harbor adapters | external validity check |

S0 is first on purpose. If hooks do not survive into the container, arm B measures a *skills-only*
harness and half the design's process metrics are unobtainable — better to learn that in a day than
after ten fixtures are written.

## 9. Open research

Resolved: the source conversation's repo URLs are real and Harbor is the runner (§4.4); the custom
task contract fits this design (§4.4.1); hooks do **not** ship and the mitigation is known (§4.4.2);
hook events are machine-observable under `-p` (§4.5). "WorkBuddy-Bench" was **not** found and is
treated as a bad name until someone produces a URL.

Also resolved — **the ablation is known to be measurable.** `Claw-SWE-Bench`
(`github.com/opensquilla/claw-swe-bench`, paper `arxiv.org/abs/2606.12344`) reports that harness
choice moves Pass@1 by **27.4pp** under a fixed model, against 29.4pp for model choice. That is an
existence proof for G1: the effect this design tries to measure is roughly the same size as swapping
the model, so it is not lost in noise. (Third-party claim, read from a research summary — the paper
itself has not been read.)

And **nothing else measures what §5.3's P1–P4 measure.** No 2025–26 benchmark scores scope
discipline, escalation/refusal, or review quality for coding agents. The nearest neighbours are
`APB` (`arxiv.org/abs/2606.04874` — planning + calibrated refusal, not SWE-specific) and `APEX-SWE`
(`arxiv.org/abs/2601.08806` — "epistemic discipline": separating assumed from verified). Neither
replaces T1. This confirms G3 rather than undermining it.

Still open, deliberately left unresolved rather than guessed:

- **arm64.** Terminal-Bench images are reported x86/amd64, needing `DOCKER_DEFAULT_PLATFORM=linux/amd64`
  under QEMU on this machine. No official Harbor arm64 statement found (UNVERIFIED). Emulation cost
  is unmeasured and could make T2 impractical locally.
- Real cost/time of a 20–50 instance T2 subset.
- Whether the Docker-in-Docker shape works: benchmark tasks whose fixture repo itself needs a
  container, running inside a Harbor container.
- Whether the Claude Agent SDK beats the CLI as the T0 substrate, given the need for per-turn hook
  and subagent instrumentation. (The sub-agent assigned to this died mid-response; unresearched.)

## 10. Decisions required from a human

Per `rules/orchestration.md`, this is high-risk + medium-confidence + redefine-system, so it
escalates rather than proceeding. Decisions are recorded in `ESCALATIONS.md`, which is the
authority; this section is the readable mirror.

**Decided 2026-08-08 (Minh Tran) — D1 / D6 / D7:**

- **D1 → ablation.** `Δ(harness on vs off)` is the primary output; 2x run cost accepted.
- **D6 → `ANTHROPIC_API_KEY` approved for manual, non-CI runs only.** This does not reverse the
  prior CI decisions in §3.1 — it stays outside CI.
- **D7 → adopt Harbor**, with the §5.7 corroboration rule. Decided knowing §4.4.3 weakened the case:
  the ablation lever itself needs no Harbor, so what is being bought is containers, parallelism, the
  trajectory model and T2 adapters. Reopens as "hand-roll" if S0 fails the container hop or arm64
  emulation cost proves impractical.

**Decided 2026-08-08 (Minh Tran) — D2 / D3 / D4 / D5:**

- **D2 → arm B is the headline treatment.** Every number is arm A vs arm B. Arm C is not run, so
  results describe *this repo's harness*, not this laptop's plugin set, and must be cited that way.
- **D3 → ~$50–100 per T1 run.** Sizes T1 at ~8–10 fixtures x 2 arms x n=3–5, which is what SC-C needs.
- **D4 → `benchmarks/`**, chosen *against* the recommendation so the toolless contract of `evals/`
  stays unambiguous. Required mitigation: `benchmarks/README.md` opens with a note that this is not
  the pre-2026-07 `benchmarks/` renamed to `evals/` by `specs/evals-folder-refactor`.
- **D5 → T2 in scope, run rarely, on a fresher adapter.** SWE-bench Verified excluded as a scoring
  suite; smoke test only. Adapter choice deferred to S5, to be made on a measured run.

The original open-question text for each is kept below for the record:
- **D2 — Arm B or arm C as the headline treatment?** B (`--setting-sources project`) is attributable
  to this repo. C (full local) is what you actually experience. Reporting both costs 2x.
- **D3 — Budget ceiling.** What is the acceptable spend for T1, per run? This sets fixture count and
  repeat count, and therefore whether any cost claim can have a spread at all.
- **D4 — Reuse the `benchmarks/` name?** It was vacated by `specs/evals-folder-refactor`
  (`benchmarks/` → `evals/`). Re-occupying it risks confusing anyone reading that history.
  Alternative: `evals/execution/`.
- **D5 — Is T2 (external suites) in scope at all?** It is the most expensive part and the least
  connected to the harness's actual claim. Harbor makes it cheap to *reach* (one flag), but
  SWE-bench Verified is saturated/contaminated (§5.5), so a fresher adapter is needed, and
  Terminal-Bench images are amd64 — QEMU cost on this machine is unmeasured.
All seven are decided. `/writing-plans` is unblocked; **S0 is the first executable step** (§8).
