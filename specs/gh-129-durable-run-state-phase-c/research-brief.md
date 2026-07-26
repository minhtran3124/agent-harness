# Research Brief — Phase C (Core Workflow Checkpoints)

Depth mode: **Deep** (multiple Deep signals fire: touches high-blast files —
`hooks/session-knowledge.sh` per Common Signals' "hook scripts", and
`.github/workflows/post-merge-maintenance.yml` per "CI config"; also touches the
workflow-engine surface, `skills/*/SKILL.md`, which this repo's own manifest classifies as a
hard-gate-equivalent signal).

**Stop condition applied for local reuse (Step 4).** `specs/gh-129-durable-run-state-phase-c/design.md`
and a dedicated audit agent dispatched during `/brainstorming` (this session) already performed
exhaustive local investigation — reading all four target skills in full, both SessionStart hooks,
`harness-status.sh`, `post-merge-maintenance.yml`, `bookkeeping.sh`, and `runtime/run_state.py`'s
FSM/CLI — and a second review round *empirically executed* the corrected FSM chain and the
tiny-lane no-op path against the real CLI, not just read the code. That fully answers "what
already exists locally, what's the extension point, what's the risk" — repeating it here would
duplicate work already done and verified. This brief instead completes Deep mode's remaining
requirement (upstream/docs coverage, Steps 5-6) and consolidates the local findings for the
planning stage.

---

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Reuse existing (extend 2 existing SKILL.md files' natural checkpoints, 1 hook, add 1 script section + 1 CI step; no new abstraction, no new dependency) |
| **Why this is the lightest credible path** | Every extension point already exists and was read in full: `feature-intake` Step 6, `subagent-driven-development` Step 1 + pre-review-chain, `finishing-a-development-branch` Step 3, `session-knowledge.sh`'s existing `additionalContext` mechanism, `bookkeeping.sh`'s existing slug/SHA resolution. Phase C adds calls at these points; it invents no new mechanism. |
| **Confidence** | 90% (the one real risk found — the FSM edge bug — was found, fixed, and empirically re-verified during brainstorming, not left open) |
| **Next step** | Proceed to `/writing-plans` using `design.md` §3-4 as the task source. |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Harness distribution tooling + its own operational CI (a skills-and-hooks framework, self-hosting) |
| Primary language + runtime | Bash (skills prose + hook/CI scripts) + Python 3 stdlib-only (`runtime/run_state.py`) + GitHub Actions YAML |
| Frameworks / platforms | None (no web framework, no ORM); GitHub Actions is the only "platform" touched (`post-merge-maintenance.yml`) |
| Relevant packages | None — stdlib-only by repo convention, confirmed again for this phase (no new dependency anywhere in design.md) |
| Detectable versions | N/A (no lockfile) |
| Important constraints | `docs/solutions/harness/automation-readiness.md` — fail-safe (`\|\| true`, never an exception-allowlist) + "warranted & objectively verifiable" test for any standing automation, both satisfied per design.md §4; `docs/solutions/harness/gate-mode-as-data-decisions.md` — keep policy data-driven, not hardcoded (not directly triggered here, no new gate mode introduced) |

---

## Feature Understanding and Assumptions

- **Requested feature:** wire the merged Phase A/B run-state engine into 8 checkpoints across the
  core workflow (intake, planning/execution, finishing, SessionStart, harness-status) plus
  `shipped`-on-merge automation, all confirmed with the user across a multi-round brainstorm.
- **What success appears to mean:** a normal/high-risk-lane spec's run advances through
  `queued→investigating→planning→implementing→verifying→ready_to_merge→shipped` as the
  corresponding skill/workflow milestones fire, visible via `list --active` at SessionStart and
  in `harness-status`; nothing ever fails a skill or CI job because `run_state.py` failed; `tiny`
  lane and RUN-less specs are unaffected.
- **Assumptions from the request:** all resolved during brainstorming — SessionStart extends the
  existing hook rather than adding a new one; the 3-risk handling for the merge-time transition
  is non-fatal-always; `tiny` lane gets no synthetic/mock chain, it simply stops at
  `investigating`; `harness-status.sh`/`post-merge-maintenance.yml` are meta-repo-only (not
  portable) and this is stated explicitly rather than silently discovered later.
- **Assumptions still needing confirmation:** none outstanding — every fork surfaced during
  brainstorming was resolved with the user, including the FSM-bug fix (re-verified empirically).

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `skills/feature-intake/SKILL.md` Step 6 (SUMMARY.md emission point) and Step 7 (routing table) — read in full during brainstorming's audit |
| `Local` | `skills/subagent-driven-development/SKILL.md` Step 1 ("mark plan active", `status: proposed → active`) and the pre-`/correctness-review` handoff point — read in full |
| `Local` | `skills/finishing-a-development-branch/SKILL.md` Step 3/Step 4 (PR creation, `status: shipped` precedent) — read in full |
| `Local` | `hooks/session-knowledge.sh` (105 lines, read in full) — SessionStart → `additionalContext` JSON contract, `exec 2>/dev/null`, every branch `exit 0` |
| `Local` | `.claude/settings.json` hooks section — confirmed exactly one SessionStart hook registered today (`session-knowledge.sh`) |
| `Local` | `scripts/harness-status.sh` (103 lines, read in full) — no existing per-spec iteration; aggregate-ledger-only today |
| `Local` | `.github/workflows/post-merge-maintenance.yml` (read in full) — `pull_request_target: [closed]`, `merged == true` guard, `MERGE_SHA` env var, checks out base branch only |
| `Local` | `scripts/bookkeeping.sh:57` — slug resolution from merged PR's changed-file list (`grep -oE 'specs/[^/]+/SUMMARY\.md'`), with a `pr-N` fallback when no match |
| `Local` | `runtime/run_state.py` — `FORWARD_TRANSITIONS` dict (lines 182-194), directly confirmed (twice, across two review rounds) to support the full 8-checkpoint chain and to reject invalid transitions cleanly (exit 2, no corruption, lock releases correctly even on rejection) |
| `Local` | `docs/solutions/harness/automation-readiness.md` — fail-safe + warranted tests, both satisfied |
| `Local` | `grep -rniE "run_state\|runtime/run" skills/ hooks/ scripts/harness-status.sh` → empty — greenfield confirmed |
| `Inference` | GitHub Actions `pull_request_target` + base-branch-only checkout is itself the standard mitigation for "don't trust PR head in a privileged workflow" — the existing `post-merge-maintenance.yml` already follows this pattern; Phase C's new step inherits the same trust boundary by adding to the same job rather than a new trigger |

---

## Local Findings

(Already exhaustively covered in `design.md` and the brainstorming audit — summarized, not
repeated in full.)

- **Extension points:** all 8 checkpoints attach to points that already exist and already do a
  structurally similar thing (a state-like transition, e.g. PLAN.md's `status:` frontmatter, or
  a data-injection point, e.g. `session-knowledge.sh`'s `additionalContext`). No new mechanism.
- **Reusable as-is:** `bookkeeping.sh`'s slug-from-merged-PR resolution (step 8); `cmd_list`'s
  `--active --json` output shape (steps 6-7); the `RunStateError.exit_code` contract (0/2/3) for
  building the non-fatal wrapping uniformly.
- **What's missing locally (and correctly deferred, not built here):** `run_state.py list
  --prompt` (Phase A dropped it; Non-goal per design.md §5, nothing in Phase C needs it); any
  CI-failure/human-review-wait signal to drive `awaiting_ci`/`awaiting_review`/etc. (Non-goal).

---

## Upstream Findings

Searched `site:github.com github actions post-merge state machine transition custom cli` and
`site:github.com "workflow lifecycle" hook additionalContext session state tracking claude`.
Results were sparse and low-relevance: most hits were either generic CI/CD state-machine
libraries (e.g. Temporal, Airflow-adjacent) aimed at long-running distributed jobs — a different
problem class (durable execution across service boundaries) from this repo's need (a single
git-native event log + projection for solo/small-team agent-driven development, already built in
Phase A). No upstream repo found doing "LLM coding-agent SKILL.md prose + GitHub Actions +
stdlib CLI" in this specific combination — unsurprising, since `runtime/run_state.py`'s design
(Phase A) was itself built from first principles for this repo's exact shape, not adapted from
an existing library. **Nothing upstream changes the local design** — confirming Phase A/B/C's
"build from scratch, stdlib-only" choice remains the lightest credible path, not a rejection of
an available library nobody looked for.

## Docs Findings

GitHub Actions official docs (`docs.github.com`) confirm `pull_request_target`'s `merged`
context field and `merge_commit_sha` are exactly what `post-merge-maintenance.yml` already uses
(`github.event.pull_request.merge_commit_sha`) — version-agnostic (Actions context fields, not a
versioned library), current as of this research. No deprecation notices, no recommended
alternative API. This confirms design.md §4.3's path-selection/SHA-plumbing claims against
official docs, not just local file reading.

---

## Recommendation

- **Primary recommendation:** Reuse existing (extend 2 skills' existing checkpoints + 1 hook +
  1 script section + 1 CI step; no new abstraction).
- **Why this is the lightest credible path:** every attachment point was already load-bearing
  for a structurally similar concern before this phase touched it.
- **Why the next-best alternative lost:** a dedicated new SessionStart hook (rather than
  extending `session-knowledge.sh`) was considered and rejected during brainstorming — same
  trigger, same contract, doubling hook count for no separation-of-concerns benefit given
  `automation-readiness.md`'s "is this really distinct" test. A synthetic/mock FSM chain for
  `tiny` lane was also considered and rejected — the user confirmed the simpler "stop at
  investigating, let later checkpoints no-op" design.
- **What would change this recommendation:** if a future phase needs `tiny` lane tracked past
  `investigating`, or if `awaiting_ci`/`awaiting_review` states need real signals — both are
  explicit Non-goals here, not silently out of reach.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:** Low, given the FSM-edge bug was caught and empirically re-verified before
  this brief was written (not a residual unknown). The 3 risks around the merge-time transition
  (slug fallback, state-precondition mismatch, path selection) are designed-for, not open.
- **Evidence gaps:** None outstanding for local reuse (stop condition applied, justified above).
  Upstream/docs coverage (this brief's own contribution) found no gap-closing external pattern —
  expected, given the problem's repo-specific shape.
- **Version uncertainties:** N/A.
- **Follow-up questions for the user:** None — every fork was resolved during `/brainstorming`.

---

## Source Pack

- **Local files read:** `skills/feature-intake/SKILL.md`, `skills/writing-plans/SKILL.md`,
  `skills/subagent-driven-development/SKILL.md`, `skills/finishing-a-development-branch/SKILL.md`,
  `hooks/session-knowledge.sh`, `hooks/state-breadcrumb.sh`, `.claude/settings.json`,
  `scripts/harness-status.sh`, `.github/workflows/post-merge-maintenance.yml`,
  `scripts/bookkeeping.sh`, `runtime/run_state.py`, `harness-manifest.json`,
  `docs/solutions/harness/automation-readiness.md`,
  `docs/solutions/harness/gate-mode-as-data-decisions.md`,
  `docs/solutions/harness/gap-closure-decisions.md`,
  `specs/gh-129-durable-run-state-phase-a/{SUMMARY.md,PLAN.md}`,
  `specs/gh-129-durable-run-state-phase-b/{SUMMARY.md,PLAN.md,design.md}`,
  `specs/gh-129-durable-run-state-phase-c/design.md`.
- **Upstream repositories or pages checked:** GitHub code search (`site:github.com`), no
  specific repository found close enough to cite by URL — search summarized above.
- **Official docs domains or pages checked:** `docs.github.com` (GitHub Actions `pull_request_target`
  context, `merge_commit_sha` field).

---

## Evidence Boundary

> Confirmed from artifacts: every local file/line reference above (read directly during
> brainstorming, several re-verified by actual CLI execution across two spec-review rounds); the
> GitHub Actions context-field claims (checked against official docs, not just local file usage).
>
> Inferred from patterns: the `pull_request_target` trust-boundary framing (§ Evidence Ledger) —
> a reasonable, standard-practice inference about why the existing workflow is shaped the way it
> is, not a claim sourced from a specific doc passage.
>
> Not checked: whether any other repo that has installed this harness has independently built a
> similar post-merge automation (would require access to those repos, out of scope and not
> necessary for this phase's design).
