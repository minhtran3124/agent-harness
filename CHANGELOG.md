# Changelog

All notable changes to this harness are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versions are tracked in the root `VERSION`
file. Bump on merge: **patch** for fixes/docs, **minor** for a new skill/hook or a changed
skill/hook contract, **major** for a breaking change to the workflow or a machine-read schema.

## [Unreleased]

### Added

- `merge-guard.sh`, a PreToolUse(Bash) hook that blocks any `gh pr merge` or `gh api .../pulls/<n>/merge` unless the PR base is `feat/*` (and not the default branch). It fails closed, unlike the other hooks (see `docs/hooks.md`). Issue #516.
- A per-ticket merge gate in `ship.js` (multi-ticket remote runs): review, one-ticket intent review and CI on the ticket PR. Only a ticket that passes is merged into `feat/<slug>`.
- Every PR the workflow opens carries a `Merge: auto|human` line and a readiness checklist.

### Changed

- The merge stage merges with `--match-head-commit <sha>` and no longer resolves conflicts, pushes or closes PRs: a conflicting or failing ticket stays open as a human merge. Local mode runs `git merge --abort` on a conflict.
- A ticket that fails its gate is `blocked` with the reason `human merge: gate <names> failed` and keeps its PR. The final PR is always a human merge.
- `/harness:setup` step 4 names the merge guard and no longer offers the `gh pr merge` allow rule (plugin hooks are not proven to fire for workflow agents).

### Fixed

- The SessionStart `clean-worktrees.sh` hook now has a 30 second timeout and runs only on `startup`, in its own group apart from `session-rules.sh`, so network I/O cannot stall session start.

### Documented

- `clean-worktrees.sh` details from #494: protected branch names (`develop`, `development`, `staging`, `production`, `release/*`, `release-*`), the skip of a worktree another live process uses (SessionStart sweep only), the SessionStart time budget (`CLEAN_BUDGET`, default 20 s) and the `CLEAN_RECREATE` guards.

## [5.1.1] — 2026-10-30

- Release v5.0.0: Harness v5 (plugin, autopilot, ship workflow, ADRs) (PR #408)

## [5.1.0] — 2026-10-29

### Added

- `clean-worktrees.sh` runs at SessionStart in sweep mode (no payload) and returns what it removed as `additionalContext`, so a PR merged on the GitHub web is cleaned. Issue #494.
- `clean-worktrees.sh` runs `git fetch -q --prune <remote>` first, removes `worktree-*` agent branches contained in a `<remote>/*` branch, and works without `gh` (upstream gone and tip an ancestor of `<remote>/main`).
- Settings in the `env` block of `.claude/settings.json`: `CLEAN_REMOTE`, `CLEAN_KEEP`, `CLEAN_STRICT`, `CLEAN_RECREATE` (see `docs/hooks.md`).

### Changed

- A squash-merged branch is now removed with `git branch -D` when a merged PR head equals the local tip (before: reported and kept). A branch with commits after the merge is still kept.

## [5.0.0] — 2026-10-28

**BREAKING.** The harness is now a Claude Code plugin, and a large part of the v2 machinery is gone. Epic #338, issues #349–#351. Read the migration steps below before you upgrade a project that installed the old copied `.claude/`.

### Breaking

- Install changes. The harness is a plugin (`plugins/harness/`, marketplace file `.claude-plugin/marketplace.json`). `scripts/deploy-harness.sh`, `scripts/install-harness.sh` and the agent renderer are removed.
- Skills are namespaced: run `/harness:<name>` (for example `/harness:autopilot`), and agents appear as `harness:<name>`.
- Hook profiles are gone. There is one fixed hook set, so `--profile minimal|standard|strict` no longer exists, and `harness-manifest.json` and `.claude/.harness-profile` are removed.
- Every rule except `rules/behavior.md` is removed (`architecture`, `guidelines`, `orchestration`, `research-depth`, `plan-format`, `wave-parallelism`, `auto-correct-scope`, `terminology`, `review-policy`). `techstacks/` is unchanged, but no rule points at it any more: reference it from your own `CLAUDE.md`.
- `harness-models.json`, the `harness-models` skill and `scripts/apply_model_config.py` are removed. Per-role models come from `agents/runtime-bindings.json` only.
- The run-state machine and SUMMARY verification are removed, so `specs/` artifacts (`SUMMARY`, `ESCALATIONS`, `QUESTIONS`, `INTENT`, review receipts, `RUN.json`) are no longer read or written. `specs/` is local scratch; put designs and decisions in `docs/adr/`.
- The review chain is `/code-review` plus `intent-review`. The `visual-planner` skill and the `reviewer` agent are removed (`task-reviewer` and `intent-reviewer` stay).
- `permissions.deny` (`.env` read and edit, force-push, push to `main`/`master`) reaches a project only through `/harness:setup`. A plugin cannot ship it.

### Added

- `plugins/harness/` plugin layout with a plugin manifest, a marketplace file, and the `setup` skill (see Migration).
- Hooks: `secrets-scan.sh` (PreToolUse, blocks a staged secret or `.env` on `git commit`), `pr-opened.sh` (PostToolUse, reminds to review after `gh pr create`), `clean-worktrees.sh` (PostToolUse, removes the worktree and branch of merged PRs, never with force flags) and `session-rules.sh` (delivers `rules/behavior.md` at session start).
- `scripts/check-md-links.sh` (dead markdown link check, run by `run-tests.sh`) and `scripts/check-plugin-version.sh` (plugin manifest version must equal `VERSION`). Minimal CI gates from PR 2 (#351).

### Removed

- Legacy hooks and their checks: `commit-gate.sh`, `branch-isolation-guard.sh`, `session-knowledge.sh`, `model-config.sh` and `hooks/lib/` (lane, escalation, receipt and run-state checks).
- `runtime/` (`run_state.py`, `resume_decision.py`), `verify_summary.py`, `check_review_receipt.py`, `resolve_finish_context.py`, `check_plan_contract.py`, `resolve-base-ref.sh`, `run_at_commit.py`, `check_manifest.py`, `check_gate_modes_smoke.py`, `check_slim_surface.py`, `check-contract-impact.sh`.
- Templates `SUMMARY`, `ESCALATIONS`, `QUESTIONS`, `INTENT` and `REVIEW-RECEIPT`, and `specs-STATE.md`.
- The `### Verify` check in `harness-audit.sh` (its `verify_missing` JSON key), and the `manifest_degraded` and `contract_impact` reports.
- v2 history docs (`research-loop.md`, stale plan and review docs under `docs/`); they stay in git history and the `legacy-v2.37.0` tag. Nothing here ships to consumers.

### Changed

- The `implementer` agent states inline what it needs from the removed rules: fix small bugs in your own change and report each as a deviation, and return BLOCKED for schema, contract, auth, dependency, `settings.json`, `hooks/` or feature-removal changes.
- `diagnosing-bugs` stops and asks the owner instead of writing an `ESCALATIONS.md` block, and reports its red and green results in the final message.
- The skill and agent checks scan `skills/*/SKILL.md` and `agents/*.md` instead of a manifest.

### Migration (from the old copied `.claude/`)

1. Install the plugin:
   ```bash
   claude plugin marketplace add minhtran3124/agent-harness
   claude plugin install harness@agent-harness
   ```
2. In the project, run `/harness:setup`. It lists the old copied files (skills, agents, hooks, `workflows/ship.js`, scripts, `templates/`, backup folders) and removes them only after you approve. It also removes the old hook entries from `.claude/settings.json` (after you agree), and asks separately about the old `.claude/rules/behavior.md` copy, which the plugin now delivers at session start. Keep both copies and every hook runs twice. The same run merges `permissions.deny` into `.claude/settings.json` (needs `jq`; you see a dry-run diff first), creates `agents/PROJECT.md` if missing, scaffolds `specs/`, `docs/solutions/` and `techstacks/` README files without overwriting, and adds `specs/` to `.gitignore`.
3. Restart Claude Code, then check that `/harness:autopilot` appears and `/autopilot` no longer does.
4. Your own files are kept: `specs/`, `docs/`, `techstacks/`, `agents/PROJECT.md`, `.claude/settings.local.json`, and any skill, agent or hook you wrote yourself.

### Known limits

Not verified yet (tracked for the dogfood run, #352): an unattended run of `ship.js` through the Workflow tool from the plugin cache, the hooks firing in a live session, and a git-sourced marketplace install. The plugin was validated locally with `claude plugin validate` and with `--plugin-dir`.

The merge stage needs the owner to allow `gh pr merge` into `feat/<slug>*`, and the Workflow tool needs `ship.js` readable by the session (see README Known limits).

## [2.37.0] — 2026-10-19

- docs: sync core and skill docs with current code (#290–#331) (PR #335)

## [2.36.0] — 2026-10-19

- feat(harness): per-agent and per-skill model and effort config (PR #332)
- feat(skills): diagnosing-bugs — six gated phases before any bug fix (#318) (PR #331)

## [2.35.0] — 2026-10-17

- feat(scripts): prove the red — require a code change after the red commit (#313 step 1) (PR #328)

## [2.34.0] — 2026-10-16

- feat(sdd): agreed test seams from plan to implementer to reviewer (#312) (PR #325)

## [2.33.0] — 2026-10-16

- feat(brainstorming): grill the design frontier in numbered rounds (#309) (PR #322)

## [2.32.0] — 2026-10-16

- feat(skills): deletion-test procedure for the 600-word skill ceiling (#308) (PR #319)

## [2.31.2] — 2026-10-16

- fix(verify_summary): apply red/green check to every bug-fix Input-type spelling (PR #304)

## [2.31.1] — 2026-10-16

- feat(evals): hardened intake-classifier eval runner (M5) (PR #305)

## [2.31.0] — 2026-10-15

- feat(workflow): failing-test-first protocol for bug fixes (E5) (PR #301)

## [2.30.0] — 2026-10-15

- docs(writing-plans): start SDD in this session without asking (PR #298)

## [2.29.0] — 2026-10-15

- docs: STE rewrite of the remaining harness prose (Phase 3) (PR #294)

## [2.28.1] — 2026-10-15

- ci(post-merge): add sdlc to the pull_request_target allowlist (PR #295)

## [2.28.0] — 2026-10-02

- feat(agents): run review roles on Opus 5.5 at medium effort and drop model-diversity rule (PR #244)

## [2.27.0] — 2026-10-02

- fix: apply prompt-audit findings to skills, rules, agents and CLAUDE.md (PR #242)

## [2.26.1] — 2026-09-30

- chore(specs): close specs left open after merge (PR #239)

## [2.26.0] — 2026-09-30

- feat(hooks)!: simplify the hook surface to 3 hooks with install profiles (PR #237)
  - **BREAKING.** Removed ten hooks. `pre-bash-dispatch.sh`, `check-untracked-py.sh`, `commit-quality-gate.sh`,
    `risk-corroboration.sh`, and `branch-guard.sh` are merged into one PreToolUse Bash hook,
    `hooks/commit-gate.sh`; `blast-radius-check.sh` becomes its commit-time plan-scope check.
    `ruff-on-edit.sh`, `render-plan-on-write.sh`, `scope-gate.sh`, and `state-breadcrumb.sh` are
    retired. The registered set is now `commit-gate.sh`, `branch-isolation-guard.sh`, and
    `session-knowledge.sh`.
  - Behavior changes: the untracked-`.py` deny runs only under `--profile strict`; blast radius is
    a commit-time warning instead of a per-edit one (`BLAST_RADIUS_STRICT=1` still blocks); the
    branch-guard warning on commits to `main` is retired; the `specs/STATE.md` Session End Log is
    no longer appended (existing logs stay as history; resume via `RUN.json`/`events.jsonl`);
    the scope-gate prompt nudge is retired; ruff-on-edit auto-formatting is retired; PLAN.html and
    the At-a-glance block render on demand via `render_plan.py --summarize` from the skills.
  - `scripts/install-harness.sh` and `scripts/deploy-harness.sh` take
    `--profile minimal|standard|strict` (default `standard`), stored in `.claude/.harness-profile`
    and reused by a re-sync without the flag.
  - Re-sync prunes the removed harness hooks from a consumer's `.claude/settings.json`, drops event
    keys left empty, and preserves the consumer's own hooks.

## [2.25.1] — 2026-09-29

- fix(hooks): judge branch isolation by where the edited file lives (PR #234)

## [2.25.0] — 2026-09-29

- refactor(prompts): align the prompt surface with Claude Opus 5.5 guidance (PR #233)

## [2.24.1] — 2026-09-28

- feat(agents): bind the coding role to Opus 5.5 and pin per-role effort (PR #230)

## [2.24.0] — 2026-09-28

- feat(harness): four adoptions from the Spotify comparison (PR #229)

## [2.23.1] — 2026-09-09

- chore(specs): mark the hook-root plan shipped and record its Status Log (PR #225)

## [2.23.0] — 2026-09-09

- fix(finishing,hooks): make RUN.json + events.jsonl travel with the PR (PR #226)

## [2.22.0] — 2026-09-09

- fix(hooks): resolve the project root from CLAUDE_PROJECT_DIR, never from SCRIPT_DIR (PR #221)

## [2.21.1] — 2026-09-09

- docs(research): compare this harness with spotify/portal-ai-plugins (PR #222)

## [2.21.0] — 2026-09-02

- fix(hooks): make secrets-scan test exemption depth-independent (PR #219)

## [2.20.1] — 2026-08-24

- docs(research-loop): ground-truth the current-state diagnosis (Phase 1) (PR #216)

## [2.20.0] — 2026-08-19

- fix(deploy,docs): make consumer-facing gates and references actually true downstream (PR #206)

## [2.19.3] — 2026-08-18

- docs: align AGENTS.md and README.md with the v3 tree (PR #209)

## [2.19.2] — 2026-08-18

- release(v3): evidence tiers, durable run state, and a runtime-neutral core (PR #207)

## [2.19.1] — 2026-07-27

- ci(sync): put the corrected post-merge trigger on main, where it is read (PR #176)

## [2.19.0] — 2026-07-22

- fix(review): close context-propagation escapes — issue #143 Phases 0–5 (PR #155)

## [2.18.0] — 2026-07-22

- fix(correctness-review): lower scorer threshold to 75 to match discrete anchors (PR #153)

## [2.17.0] — 2026-07-22

- refactor(evidence): consolidate lane validation (PR #150)

## [2.16.0] — 2026-07-22

- refactor(workflow): centralize branch isolation policy (PR #148)

## [2.15.0] — 2026-07-22

- refactor(compound): use canonical templates (PR #146)

## [2.14.0] — 2026-07-21

- fix(finishing-branch): make bookkeeping the single owner of VERSION/CHANGELOG (PR #144)

## [2.13.0] — 2026-07-21

- feat(rules): path-scope the contextual rules (`plan-format`, `wave-parallelism`, `auto-correct-scope`) via `paths:` frontmatter — loaded on demand instead of every session (~55% off the always-on rule payload); consuming skills gained explicit Read steps (write-flows don't trigger `paths:` injection — verified empirically on v2.1.216). Phase 3 (orchestration.md core split) deferred. Research: `docs/research/harness-review-improvements/2026-07-21-dynamic-rule-loading-research.md` (PR #141)

## [2.12.0] — 2026-07-21

- refactor(create-pr): drop File Changes table, reviewer-first Summary, conditional Diagram (PR #139)

## [2.11.0] — 2026-07-21

- refactor: remove dormant protected-path guard (PR #133)

## [2.10.0] — 2026-07-21

- feat: add ticket-source prefix for spec folders (gh-/lin-) (PR #126)
- feat: remove unused agent memory (PR #131)

## [2.9.1] — 2026-07-20

- chore(lint): widen doc-truth scope to agents/ and rules/ (4 → 17 docs) (PR #122)

## [2.9.0] — 2026-07-20

- feat(hooks): wire check_lane_evidence into the commit gate (Check 1.6) (PR #120)

## [2.8.0] — 2026-07-20

- docs(skills): sync workflow docs with current code (PR #119)

## [2.7.1] — 2026-07-17

- compound: skill-eval playbook + harness test/doc-lint gate scope (PR #116)

## [2.7.0] — 2026-07-17

- refactor(evals): rename benchmarks/ -> evals/, split skills vs workflow (PR #114)

## [2.6.7] — 2026-07-17

- feat(benchmarks): intake-classifier eval + blind baseline (PR #112)

## [2.6.6] — 2026-07-17

- docs(specs): backfill ### Verify block for entropy-trend SUMMARY (PR #110)

## [2.6.5] — 2026-07-17

- docs(solutions): refresh 4 stale KB entries against ground truth (PR #108)

## [2.6.4] — 2026-07-17

- docs(solutions): automation-readiness design gate (option A) (PR #106)

## [2.6.3] — 2026-07-17

- docs(techstacks): clarify AI-consumed / project-authored (keep at root) (PR #104)

## [2.6.2] — 2026-07-17

- feat(scripts): verify-row lint (pipe-free + <60s Verify commands) (PR #102)

## [2.6.1] — 2026-07-17

- docs(compound): crystallize 3 session lessons (PR #100)

## [2.6.0] — 2026-07-17

- feat(harness): decouple tech-stack into a project-owned techstacks/ folder (PR #98)

## [2.5.2] — 2026-07-17

- fix(deploy): prune deleted-skill orphans from .claude (safe-by-construction manifest) (PR #96)

## [2.5.1] — 2026-07-17

- feat(install): fold init-structure into install-harness (one command) (PR #94)

## [2.5.0] — 2026-07-17

- Promote v3 → main: remove bootstrap-xia2 (xia2 zero-config) (PR #92)

## [2.4.0] — 2026-07-17

- docs: correct branch-isolation-guard trigger in 5 stale sites (PR #88)

## [2.3.0] — 2026-07-17

- Promote v3 → main: Phase 2 waves 2 + 3 (PR #86)

## [2.2.2] — 2026-07-17

- Promote v3 → main: Phase 2 wave 1 + v3 CI wiring (PR #80)

## [2.2.1] — 2026-07-17

- docs(reviews): Phase 2 deep review — verify each deletion target (supersedes audit line items) (PR #77)

## [2.2.0] — 2026-07-16

- feat(hooks): mechanize the ESCALATIONS deny-on-no-response gate (review C5) (PR #75)

## [2.1.0] — 2026-07-16

- fix(hooks): strip comments before risk-corroboration keyword scan (review C4) (PR #73)

## [2.0.1] — 2026-07-16

- fix(ci): rewire post-merge bookkeeping to main (review C3) (PR #71)

## [2.0.0] — 2026-07-16

Milestone: the **v2 line** (0.3.0 → 0.14.0) is promoted to `main` and tagged
[`v2.0.0`](https://github.com/minhtran3124/agent-harness/releases/tag/v2.0.0) — the
rebuilt risk-and-trust harness. Highlights across the line: lane-based routing enforced
at write time (`branch-isolation-guard.sh`), `harness-manifest.json` as the single source
for hard gates, evidence-over-assertion verify/rollback gates, the `/intent-review` third
oracle, self-summarizing plans (visual-planner At-a-glance block), event-sourced post-merge
bookkeeping, conflict-guarded re-sync, the product-contract map, stack-agnostic `rules/`, and
tracked `specs/`. See the per-version sections below for the full merge history.

Folded in from Unreleased at tag time:

- feat(q3): product-contract map (Level A) — `contracts` block in `harness-manifest.json`, `scripts/check-contract-impact.sh` advisory mapper, `check_manifest.py` path validation, and a contract-impact reminder section in `harness-audit.sh` (MIN-64)
- fix(install-harness): a tty-less re-sync without `--yes` now prints the actionable "Re-run with `--yes`" message instead of dying on a raw `/dev/tty: Device not configured`; `--overwrite-conflicts` now implies `--yes` (it already named the destructive outcome), so `curl … | bash -s -- --overwrite-conflicts` works non-interactively. Covered by `tests/scripts/install-tty-gate.test.sh`
- fix(deploy-harness): `rules/behavior.md` is now conflict-guarded like the other project-owned files — a customized copy is kept and the incoming version saved as `rules/behavior.md.harness-incoming`, instead of being overwritten silently

## [0.14.0] — 2026-07-15

- fix: conflict-guarded re-sync — stop clobbering bootstrap-xia2 outputs (PR #50)

## [0.13.0] — 2026-07-15

- feat(visual-planner): self-summarizing PLAN.md — At-a-glance block (#54) (PR #63)

## [0.12.0] — 2026-07-15

- correctness-review: find by six parallel angles; fix four aborts in harness-status.sh (PR #51)

## [0.11.0] — 2026-07-13

- feat(branch-isolation): every lane cuts a branch before implementing — close the tiny-lane hole (PR #52)

## [0.10.0] — 2026-07-13

- fix(blast-radius): only an ACTIVE plan arms the hook — drop the stale-plan fallback (PR #53)

## [0.9.0] — 2026-07-09

- docs: clarify harness prompts (root docs + sub-agents + rules) (PR #48)

## [0.8.1] — 2026-07-08

- feat(q3): product-contract map (Level A) — contract-level blast radius [MIN-64] (PR #46)

## [0.7.3] — 2026-07-04

- feat: entropy has a trend — 6-check harness-audit + per-merge JSONL log (v0.3 Wave 4) (PR #42)

## [0.7.2] — 2026-07-04

- chore(hygiene): v0.3 Wave 6 — plan statuses shipped + research docs committed (PR #40)

## [0.7.1] — 2026-07-04

- fix(evidence): verify gates reject trivial proof — v0.3 Phase 3 (PR #38)

## [0.7.0] — 2026-07-04

- feat(governance): harness-manifest single source for hard gates — v0.3 Phase 2 (PR #35)

## [0.6.0] — 2026-07-03

- feat(ci): event-sourced post-merge bookkeeping — v0.3 Phase 1 (PR #34)

## [0.5.0] — 2026-07-03

- docs(skills): fix doc-truth drift across skill files — v0.3 Wave 0c (PR #33)

## [0.4.0] — 2026-07-03

- fix(hooks): session-knowledge resolves repo root via git (DR-2) — v0.3 Wave 0b (PR #32)

## [0.3.0] — 2026-07-03

- fix(hooks): close commit-gate command-matching bypass (DR-1) — v0.3 Wave 0a (PR #31)

## [0.2.0] — 2026-06-14

### Changed
- **Stack-agnostic `rules/` (MIN-25).** The `rules/` governance layer is no longer FastAPI-only.
  Universal rules ship identical everywhere; stack-specific guidance is a swappable profile:
  - FastAPI content moved verbatim to `templates/stacks/fastapi/{architecture,guidelines}.md`;
    `rules/architecture.md` + `rules/guidelines.md` are now stack-neutral skeletons (deploy still
    ships valid files).
  - `rules/plan-format.md`, `auto-correct-scope.md`, `wave-parallelism.md` keep FastAPI snippets
    only inside blocks tagged `example — substitute your stack`; in-prose stack tokens genericized.
  - **`bootstrap-xia2` now renders the stack profile per repo** — detect stack → bundled
    `templates/stacks/<stack>/` profile as a human-reviewed draft, else the generic
    `templates/stacks/_skeleton/` fallback; never a wrong-stack profile. (skill-contract change → minor)



First versioned snapshot of the harness — the skill framework, governance rules, hooks, CI, and
the research-driven gap-closure work.

### Added
- **Skill chain** — intake → brainstorm → research (xia2) → plan → execute → review
  (correctness + intent oracles) → compound → finish, plus `visual-planner` and `bootstrap-xia2`.
- **Machine gates** — `risk-corroboration`, `commit-quality-gate`, `blast-radius-check`,
  `branch-guard`, `check-untracked-py`, `ruff-on-edit`, `render-plan-on-write`, `scope-gate`,
  `state-breadcrumb`, `session-knowledge` (wired); `auto-test-on-change`,
  `protected-path-guard` (dormant).
- **CI** — `harness-ci.yml` runs `scripts/run-tests.sh` (bash contract tests + python units) and
  `scripts/ci-strict-gate.sh` (strict-in-CI proof gate for hard-gate paths) on ubuntu + macos.
- **Gap-closure (from 6 research docs)** — ratchet backlog in `/compound` (P1-B);
  `scripts/harness-audit.sh` advisory drift detector (P1-C); MCP boundary-of-trust note (P2-H);
  review-chain micro-benchmark re-run via the read-only `reviewer` agent, 5/5 catch (P3-I);
  `scripts/check_lane_evidence.py` lane→evidence single source (P3-J); story-size warning in
  `check_plan_format.py` (P3-K); `protected-path-guard` break-glass hook (P3-L).
