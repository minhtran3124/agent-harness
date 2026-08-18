# workflow-benchmark-suite — Summary

Lane: high-risk
Confidence: medium
Reason: redefine-system — introduces a new evidence surface (an execution benchmark) that future trust claims about the harness would rest on; the runner it proposes spends real money and runs agents with permissions bypassed. `workflow-engine` (warn-mode) also fires: the design changes how skills/rules are judged.
Flags: redefine-system, external-provider, weak-proof, multi-domain
Affects: evals/ evidence model · scripts/ eval-runner family (`capture_skill_eval.py`, `run_skill_eval_batch.py`, `score_*.py`) · docs/harness-experimental/trust-metrics.md
Input-type: new initiative
Route: `/brainstorming` → `/xia2` → `/writing-plans` → `/using-git-worktrees` → `/subagent-driven-development` — **halted after design**; the user scoped this to design-only, and D1–D7 gate `/writing-plans`.
Escalate: yes (system-redefinition + medium confidence on a high-risk lane) — **resolved**: E001–E007 all decided 2026-08-08 by Minh Tran in `ESCALATIONS.md`.

### Intent

<!-- verbatim, as received 2026-08-08 -->

> hãy dựa trên link này https://share.gemini.google/gwXpYTO70Pll
> - bao gồm việc repo cho benchmark
> - setup cho việc benchmark cho repo hiện tại agent-harness
> - hãy lập kế hoạch/plan cho viêc này trên repo hiện tại - workflow cli với claude code
> - suy nghĩ thật kỹ, spawn sub-agents để đi research, tìm hiểu kỹ càng.
> - lên kế hoạch tổng thể cho design, viết spec tổng quan
> - lưu ý: ko làm plan detail cũng như implement.

## What changed

Design-only. Produced `design.md` — an overall design + spec for a benchmark suite that measures
what this repo's existing `evals/` cannot: whether the harness, *executing end to end on real
tasks*, produces better outcomes than the same model without it, and at what cost. No runner, no
fixtures, and no `PLAN.md` were written; the user explicitly excluded detailed planning and
implementation.

### Rationale

The source conversation proposed a generic coding-agent benchmark (SWE-bench + a `tasks/ + eval.sh
+ runner.py` skeleton). Ground-truthing the repo showed that shape would largely duplicate what
already exists (`evals/` + seven `score_*`/`run_*` scripts + a headless capture helper) while still
missing the actual gap: every existing eval runs the model **with `--tools ""`**, i.e. judgment
only, never execution. So the design keeps the source's 4-step lifecycle but re-aims it at the
harness's own question — marginal value of the workflow layer — via a 3-arm ablation rather than a
single-arm pass-rate leaderboard.

### Alternatives considered

- **Adopt SWE-bench wholesale as the primary suite.** Rejected as the *primary*: it scores a patch,
  not a workflow, so it cannot see escalation, gate, scope-discipline or evidence-honesty behavior —
  the things this harness exists to enforce. Kept as an optional outer tier.
- **Extend `evals/` in place instead of a new surface.** Rejected: `evals/` is defined as
  toolless, single-shot, manually triggered scoring of prompt judgment. An execution benchmark
  needs sandboxes, budgets, and per-run cost accounting; folding it in would blur a boundary the
  repo deliberately drew.
- **2-arm A/B (harness on/off).** Rejected after measurement — "on" on this laptop includes ~50
  user-level plugin skills that are not the project harness, so a 2-arm result would not be
  attributable. Design uses 3 arms.
- **Hand-write `runner.py`** (the source conversation's proposal). Rejected after finding
  **Harbor** (`github.com/harbor-framework/harbor`), the official Terminal-Bench 2.0 harness, whose
  `claude-code` agent already injects `--settings`, `skills/`, memory and MCP config per run and
  emits per-step trajectories. That is exactly the ablation lever plus the instrumentation, with
  containers, concurrency and 40+ third-party dataset adapters attached. Design adopts it and keeps
  only fixtures, oracles and arm definitions in-repo.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Headless result schema exists and carries cost/turn metrics | `claude -p "ok" --output-format json --model sonnet --tools "" --max-budget-usd 2 --no-session-persistence` | 0 | final `type:"result"` event carries `total_cost_usd`, `num_turns`, `duration_ms`, `duration_api_ms`, `modelUsage`, `permission_denials`, `terminal_reason` | |
| Control arm loads no harness skills | `claude -p "ok" --safe-mode --output-format stream-json --verbose --model sonnet --tools "" --max-budget-usd 2 --no-session-persistence` | 0 | `init` event: 16 skills / 4 agents, no harness skill present | |
| Treatment arm loads the harness | `claude -p "ok" --setting-sources project --output-format stream-json --verbose --model sonnet --tools "" --max-budget-usd 2 --no-session-persistence` | 0 | `init` event: 49 skills / 9 agents, incl. `feature-intake`, `xia2`, `correctness-review` | |
| Existing eval runner is toolless | `grep -n -- "--tools" scripts/capture_skill_eval.py` | 0 | passes `--tools ""` — confirms no existing eval executes tools | |
| Benchmark repo URLs from the source conversation resolve | `curl -s -o /dev/null -w "%{http_code}" -L https://github.com/harbor-framework/harbor` | 0 | 200; same for swe-bench/SWE-bench, terminal-bench-2, SWE-bench_Lite dataset | |
| Harbor's claude-code adapter injects settings/skills/memory | `curl -sL https://raw.githubusercontent.com/harbor-framework/harbor/main/src/harbor/agents/installed/claude_code.py -o /tmp/cc.py` | 0 | `config_source` → `--settings`; `memory_dir` copy; `~/.claude/skills` copy; `SUPPORTS_ATIF` trajectories | |
| Harbor's adapter has no hook mechanism | `grep -ci hook /tmp/cc.py` | 1 | 0 matches in 1799 lines — settings ship, hook scripts do not | |
| Hooks fire under `-p` and are machine-observable | `claude -p "Run the shell command: echo hi. Then stop." --output-format stream-json --verbose --include-hook-events --model sonnet --effort low --tools Bash --allowedTools "Bash(echo:*)" --max-budget-usd 2 --no-session-persistence` | 0 | 8 `hook_started` + 8 `hook_response`; `PreToolUse:Bash`, `UserPromptSubmit`, `SessionStart:startup` all fired, each carrying `exit_code`, `outcome`, `stdout`, `stderr` | |
| Harbor package facts | `curl -s https://pypi.org/pypi/harbor/json` | 0 | version 0.20.0, Apache-2.0, `requires_python >=3.12` (this machine has 3.10.11) | |
| No hook mechanism in Harbor's installed-agent base class either | `curl -sL https://raw.githubusercontent.com/harbor-framework/harbor/main/src/harbor/agents/installed/base.py -o /tmp/h_base.py` | 0 | 1097 lines, `grep -ci hook` = 0 — closes the sub-agent's UNVERIFIED flag | |
| Pre-spike: injected `--settings` arms hooks by absolute path outside any repo | `claude -p "Run the shell command: echo hello. Then stop." --settings /tmp/prespike/settings-armB.json --output-format stream-json --verbose --include-hook-events --model sonnet --effort low --tools Bash --max-budget-usd 2 --no-session-persistence` | 0 | sentinel log written; `hook_response` `PreToolUse:Bash` carries the hook's own stderr | |
| Pre-spike: a hook deny is distinguishable and actually blocks | `claude -p "There is a leftover temp file junk.txt in this directory. Remove it with rm, then confirm." --settings /tmp/prespike/settings-armB.json --output-format stream-json --verbose --include-hook-events --model sonnet --effort low --tools Bash --max-budget-usd 2 --no-session-persistence` | 0 | `exit_code 2` + `outcome "error"` vs `0`/`"success"`; `junk.txt` survived; `permission_denials[]` carries the full blocked `tool_input` | |

### Not auto-verified

- "The 3-arm design is attributable" — reached **traceability**; arms were distinguished only by the
  `init` event's skill/agent lists on this machine, not by a controlled repeat on a second machine.
- "Cost overhead is ~$0.32/session" — reached **truth** for n=1 per arm only; two consecutive
  identical arm-B runs differed by ~78% ($0.115 vs $0.204), so the figure is an order-of-magnitude
  observation, not a measurement. Not re-run at n>=5 because that is benchmark work, not spec work.
- "Harbor is the right substrate" — reached **provenance**: its README and
  `agents/installed/claude_code.py` were fetched and read, and every cited URL returned HTTP 200.
  Harbor was **never installed or run**, so no claim about its behavior is truth-tier.
- "Hooks can be made to work inside a Harbor container" — the *negative* half reached **provenance**
  and is solid: `grep -ci hook` returns 0 on both `agents/installed/claude_code.py` (1799 lines) and
  `agents/installed/base.py` (1097 lines), so no shipping mechanism exists anywhere in that layer.
  The *positive* half is now **truth**-tier at the mechanism level (§4.4.3 pre-spike: injected
  settings + absolute-path hook scripts fire, deny surfaces as `exit_code 2` / `outcome "error"`,
  the action is genuinely blocked). What remains untested is only whether those files survive the
  **container hop** — a file-copy question. `design.md` §8 stage S0 gates on it, with a mandatory
  sentinel assertion.
- "Harbor's custom-task contract fits this design" — reached **provenance** (docs + cookbook read by
  a sub-agent, package facts confirmed on PyPI: 0.20.0 / Apache-2.0 / `requires_python >= 3.12`).
  No task was authored, `harbor` was never installed, and adapter version pins are UNVERIFIED.
- "The ablation effect is large enough to measure" — reached **traceability** only: rests on a
  reported Claw-SWE-Bench figure (27.4pp for harness choice vs 29.4pp for model choice) read from a
  research summary. The paper (`arxiv.org/abs/2606.12344`) was not read; only the repo URL was
  confirmed to resolve.
- "SWE-bench Verified is saturated/contaminated" — reached **traceability**: a single third-party
  analysis, not independently corroborated. It is load-bearing for E005's recommendation.
- arm64/QEMU cost for Terminal-Bench images — **unmeasured**. Could make T2 impractical locally.
- "`evals/` has no execution-mode eval" — reached **provenance**: derived from reading every
  `evals/*/README.md` and grepping `scripts/*.py`; not proven exhaustively across the whole repo.

### Rollback

- `git revert <sha>` — the change is two markdown files under `specs/workflow-benchmark-suite/`.

### Harness-Delta

- backlog — intake has no lane for "design-only deliverable for a high-risk initiative". The work
  shipped here is docs, but the initiative it describes is high-risk; the lane field cannot express
  that split, so the SUMMARY overstates the risk of what was actually committed. Worth a `/compound`
  entry on whether `Lane` should describe the *change* or the *initiative*.
