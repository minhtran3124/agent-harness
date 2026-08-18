# workflow-benchmark-suite — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-quality-gate.sh` Check 1.5 denies commits touching this slug while any
`decision:` is `pending`.)

> Note on sequencing: this file blocks committing the spec itself. That is intended — the design
> should not land as settled while its premise is undecided. `design.md` §10 carries the same seven
> decisions in prose for reading; this file is where they are recorded.

---

## E001

- raised_by: orchestrator
- date: 2026-08-08
- trigger: system-redefinition
- question: Is the benchmark's primary question the *ablation* (`Δ` harness-on vs harness-off), or absolute readiness ("is the harness good enough to trust unattended")?
- context: Blocks fixture design. The two questions need different fixture sets; the ablation needs a control arm, readiness needs a difficulty ladder. New evidence for A: `Claw-SWE-Bench` (`github.com/opensquilla/claw-swe-bench`, `arxiv.org/abs/2606.12344`) reports harness choice moving Pass@1 by **27.4pp** under a fixed model vs 29.4pp for model choice — the effect is large enough to measure, not noise.
- options:
  - A) Ablation — answers "does the harness pay for itself", needs 2x runs per task, cost doubles. **(recommended)**
  - B) Readiness — single arm, half the cost, but cannot attribute any result to the harness.
- default_if_no_response: BLOCK
- decision: **A — ablation.** The benchmark's primary output is `Δ(harness on vs off)`, not an absolute pass rate. Accepts 2x run cost per task. Fixture design proceeds on this basis (§5.3 keeps both the outcome tier O1–O4 and the harness-specific tier P1–P4, each run in both arms).
- decided_by: Minh Tran
- decided_at: 2026-08-08

## E002

- raised_by: orchestrator
- date: 2026-08-08
- trigger: ambiguous-direction
- question: Which arm is the headline treatment — B (`--setting-sources project`, this repo's harness only) or C (full local env, including ~50 user-level plugin skills)?
- context: Measured 2026-08-08: A=16 skills/$0.033, B=49 skills/$0.115–0.204, C=127 skills/$0.350. Reporting both costs 2x.
- options:
  - A) Arm B only — attributable to this repo, but not what you actually experience. **(recommended)**
  - B) Arm C only — matches lived experience, but a result cannot be credited to the harness.
  - C) Both — honest, 2x cost.
- default_if_no_response: BLOCK
- decision: **A — arm B is the headline treatment.** Every reported number is `arm A (--safe-mode)` vs `arm B (--setting-sources project)`. Arm C (full local) is not run; results therefore describe *this repo's harness*, not this laptop's plugin set, and must be cited that way.
- decided_by: Minh Tran
- decided_at: 2026-08-08

## E003

- raised_by: orchestrator
- date: 2026-08-08
- trigger: ambiguous-direction
- question: What is the acceptable spend per T1 run?
- context: Sets fixture count x arms x repeats. Measured cost noise is ±78% run-to-run, so n>=5 is required for any cost claim to have a spread rather than being a point estimate (`design.md` §4.3). A low ceiling means cost claims cannot be made at all — only pass/fail ones.
- options:
  - A) < $20/run — ~5 fixtures x 2 arms x n=1. Pass/fail signal only, no honest cost claim.
  - B) ~$50–100/run — ~8–10 fixtures x 2 arms x n=3–5. Supports SC-C. **(recommended)**
  - C) Unbounded — full suite with repeats.
- default_if_no_response: BLOCK
- decision: **B — ~$50–100 per T1 run.** Sizes T1 at roughly 8–10 fixtures x 2 arms x n=3–5, which is what SC-C needs: enough repeats that a cost figure carries a spread rather than being a point estimate against ±78% run-to-run noise.
- decided_by: Minh Tran
- decided_at: 2026-08-08

## E004

- raised_by: orchestrator
- date: 2026-08-08
- trigger: ambiguous-direction
- question: Reuse the top-level name `benchmarks/`, or nest as `evals/execution/`?
- context: `benchmarks/` was vacated by `specs/evals-folder-refactor` (renamed `benchmarks/` → `evals/`). Re-occupying the name risks confusing anyone reading that history.
- options:
  - A) `benchmarks/` — clean separation from `evals/`'s toolless contract; collides with repo history.
  - B) `evals/execution/` — no name collision; blurs the "evals are toolless" boundary. **(recommended — history is cheap to annotate, a blurred contract is not)**
- default_if_no_response: BLOCK
- decision: **A — `benchmarks/`** (chosen against the recommendation, deliberately: keeping the toolless contract of `evals/` unambiguous is worth the name collision). Mitigation required: `benchmarks/README.md` must open with a note that this directory is **not** the pre-2026-07 `benchmarks/` that was renamed to `evals/` by `specs/evals-folder-refactor`, so anyone reading git history is not misled.
- decided_by: Minh Tran
- decided_at: 2026-08-08

## E005

- raised_by: orchestrator
- date: 2026-08-08
- trigger: ambiguous-direction
- question: Is Tier 2 (external suites — SWE-bench / Terminal-Bench via Harbor) in scope?
- context: It is the least connected to the harness's own claim, but Harbor makes it roughly one flag rather than a build. Its purpose is a single check: is our internal suite too easy or self-flattering? Two new constraints: (1) **SWE-bench Verified is saturated/contaminated** as of 2026 (~88% clustering; OpenAI stopped reporting it after >60% of 138 audited tasks proved unsolvable as written), so it cannot falsify anything — a fresher adapter is needed; (2) Terminal-Bench images are **amd64**, so this machine runs them under QEMU with unmeasured emulation cost.
- options:
  - A) In scope, run rarely, on a *fresher* adapter than SWE-bench Verified — external-validity check. **(recommended)**
  - B) Out of scope — materially cheaper; internal suite is then unfalsified from outside.
  - C) In scope but deferred until after S4, once the arm64/QEMU cost is measured.
- default_if_no_response: BLOCK
- decision: **A — in scope, run rarely, on a fresher adapter than SWE-bench Verified.** Candidates: `swebench_multilingual`, `swesmith`, `aider_polyglot`. SWE-bench Verified is explicitly excluded as a scoring suite (saturated/contaminated); it may serve as a regression smoke test only. Adapter selection is deferred to S5 and must be made on a measured run, not on this list.
- decided_by: Minh Tran
- decided_at: 2026-08-08

## E006

- raised_by: orchestrator
- date: 2026-08-08
- trigger: hard-gate (external-provider)
- question: Approve `ANTHROPIC_API_KEY` (API billing) for benchmark runs, instead of subscription auth?
- context: Every container run needs it; `CLAUDE_CONFIG_DIR` isolation leaves the run unauthenticated (measured: `is_error: true`, cost 0). This contradicts a recorded prior decision — `docs/solutions/harness/skill-eval-blind-run-scoring.md:44` says a runner needing `ANTHROPIC_API_KEY` is "deliberately not built".
- options:
  - A) Approve for manual, non-CI runs only — keeps the prior decision's actual concern (LLM in per-commit CI) intact. **(recommended)**
  - B) Refuse — benchmark is then limited to local worktree runs with subscription auth, and no container arm is possible.
- default_if_no_response: BLOCK
- decision: **A — approved for manual, non-CI runs only.** `ANTHROPIC_API_KEY` may be used for benchmark container runs. This does **not** reverse `docs/solutions/harness/skill-eval-blind-run-scoring.md:44` or `specs/harness-tests-phase23/SUMMARY.md:29`: those rejected LLM calls in per-commit CI, and this suite stays manual-run per §3 non-goals. Promoting any benchmark to CI remains a separate decision that must pass `automation-readiness.md`.
- decided_by: Minh Tran
- decided_at: 2026-08-08

## E007

- raised_by: orchestrator
- date: 2026-08-08
- trigger: hard-gate (external-provider)
- question: Adopt Harbor (`github.com/harbor-framework/harbor`) as a dependency?
- context: harbor 0.20.0, Apache-2.0, `requires_python >= 3.12` (this machine has 3.10.11, so it installs as a `uv` tool with its own interpreter, not as a repo dependency). Third-party, executes agents with permissions bypassed, would become load-bearing for this repo's trust claims. It also introduces Docker, which the repo has never used (verified: zero Dockerfiles). Its task contract (`task.toml` / `instruction.md` / `environment/Dockerfile` / `tests/test.sh` / `solution/solve.sh`) maps onto this design almost one-to-one, and its `multi-reward` recipe natively expresses the outcome/process split. The alternative is a hand-rolled runner: ~10x the code, no containers, no cloud fan-out, no trajectory model, no third-party datasets.
- options:
  - A) Adopt, with the §5.7 corroboration rule (a Harbor-reported pass is re-verified by independently re-running `eval.sh` before any number is recorded). **(recommended)**
  - B) Hand-roll a runner — full control, no new dependency, much more code and no containers.
  - C) Defer until after S0, deciding on measured data.
- default_if_no_response: BLOCK
- decision: **A — adopt Harbor**, with the §5.7 corroboration rule (a Harbor-reported pass is re-verified by independently re-running the outcome oracle before any number is recorded). Decided in full knowledge that the §4.4.3 pre-spike weakened the case: the arm-B mechanism runs on the bare CLI, so Harbor's remaining value is containers, parallelism, the trajectory model, and T2 dataset adapters — not the ablation lever itself.
- decided_by: Minh Tran
- decided_at: 2026-08-08
- revisit_if: S0 shows the sentinel does not survive the container hop even via a custom adapter, or arm64/QEMU cost makes local runs impractical. Either outcome reopens this as option B.
