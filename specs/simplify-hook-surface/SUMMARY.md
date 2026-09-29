# simplify-hook-surface — Summary

Lane: high-risk
Confidence: high
Reason: hard gates high-blast (hooks/, settings.json) and workflow-engine (hook-driven gates, deploy/install contract); removes and merges enforcement surfaces
Flags: high-blast, workflow-engine, public-contract (consumer install/settings contract), cross-platform (Claude + Codex adapter), existing-behavior, multi-domain
Affects: hooks/, settings.json, scripts/deploy-harness.sh, scripts/install-harness.sh, harness-manifest.json, Codex adapter, tests/hooks/, CLAUDE.md hook table
Input-type: harness improvement
Route: brainstorming → xia2 (Deep) → writing-plans → using-git-worktrees → subagent-driven-development → context-propagation-audit → correctness-review → intent-review → compound → finishing-a-development-branch
Escalate: no (direction forks resolved by the user at intake; see Intent)

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

"hiện tại có 1 vấn đề là repo harness hiên tại có vẻ quá nhiều script hook, nó gây ra vài vấn đề như
- ko tương thích ngược vs những repo đã có 1 số hook rồi
- hook làm bị chậm và đôi lúc gây phiền toán

tôi muốn check lại toàn bộ và simplify hệ thống hook, để làm nó đơn giản, gọn nhẹ hơn nhưng vẫn giữ dc những gate quan trọng"

Scope decisions the user made at intake, in order:

1. The utility and nudge hooks (ruff-on-edit, render-plan-on-write, scope-gate, state-breadcrumb, blast-radius-check) are deleted outright ("Xoá hẳn").
2. branch-isolation-guard stays blocking by default ("Chặn mặc định").
3. Add three install profiles, minimal / standard / strict ("Có, 3 profile").

## What changed

The harness hook surface went from 8 registered commands across 5 events to 3: `hooks/commit-gate.sh` (PreToolUse Bash — one process that merges the secrets scan, escalation deny, lane evidence, run-state, risk corroboration, plan scope, app gates and the untracked-`.py` deny), `hooks/branch-isolation-guard.sh` (PreToolUse Write|Edit, now decided without python3 for Claude payloads), and `hooks/session-knowledge.sh` (SessionStart, INDEX pointer instead of 30 rows: ~11.8 KB → ~1.3 KB). Ten hooks were removed. Install/deploy take `--profile minimal|standard|strict` (default standard, persisted in `.claude/.harness-profile`); re-sync prunes retired hooks from a consumer's settings and keeps its own hooks. The Codex adapter, manifest, checkers, rules, skills, templates and docs were retargeted.

### Rationale

Approach A (one `commit-gate.sh` with check functions moved verbatim) was chosen by the user over a shared-context dispatcher (B, still 4 processes) and a Python rewrite (C, would make the secrets gate depend on python3). Profiles live in the manifest and the registered command line because `settings.json` `env` is dropped on re-sync (`docs/solutions/harness/gate-mode-as-data-decisions.md`). Consumer incompatibility was behavioural (ruff reformatting, Python-only gates), not registration — the existing merge already preserved consumer hooks.

### Alternatives considered

- Keep every hook and only optimize latency (one normalizer call) — rejected by the user.
- Keep the utility hooks on disk as opt-in — rejected by the user because the tests would still need maintaining.

### Deviations

- Task 1.1 (accepted, not a §2.5 demotion) — the untracked-`.py` deny in `hooks/commit-gate.sh` exits immediately instead of falling through to the remaining commit checks, as the old dispatcher did. The commit is denied either way; the other gates' diagnostics are deferred to the next attempt.
- Task 1.1 — retired `gate-integration` case "branch-guard stays non-blocking when the matcher lib is missing" (design §2.5: branch-guard retired).
- Task 1.1 — retired `blast-radius-check` case "partial edit payload warns and remains non-blocking even in strict mode": staged paths are always fully known at commit time (design §2.5: blast radius → commit-time warning).
- Task 1.2 review fix (d28b10f) — the fast path now leaves payloads carrying a `prompt` key, or a non-PreToolUse event, to the normalizer, keeping parity with its prompt classification.
- Task 1.1 review fix (e77a304) — `commit-gate.sh` fails closed when only the commit-or-push matcher is defined (the source hooks guarded the commit-only matcher).
- Task 1.3 (Rule 2) — added the case "multiple INDEX rows → pointer counts every data row".
- Task 1.4 (Rule 1) — `rules/plan-format.md` "regenerates idempotently on every save" became "on every run"; "every save" was true only of the removed hook.
- Task 3.1 — retired from `tests/hooks/repo-root-resolution.test.sh`: "scope-gate: no resolvable root → non-blocking" and "ruff-on-edit: no resolvable root → non-blocking" (design §2.5: scope-gate and ruff-on-edit retired), plus the two branch-guard cases "no root → non-blocking" and "warns for the project's branch, not the host's" (design §2.5: branch-guard retired).
- Task 3.1 — retired from `tests/hooks/spec-prefix-compat.test.sh`: "render-plan-on-write: prefixed PLAN.md renders PLAN.html" (design §2.5: PLAN.html render on demand via visual-planner).
- Task 3.1 — posture change, not an equivalence: the blast-radius "no resolvable project root → notes and exits 0" case from `tests/hooks/repo-root-resolution.test.sh` has no non-blocking successor. The plan-scope check now runs inside `hooks/commit-gate.sh`, whose unresolvable-root posture is fail-closed (block, `tests/hooks/commit-gate.test.sh` "no resolvable project root → BLOCKS"). This follows from design §2.5 (blast radius → commit time).
- Task 3.1 (Rule 2) — the two `tests/hooks/spec-prefix-compat.test.sh` blast-radius "active PLAN.md in a gh-prefixed folder" cases were retargeted to `hooks/commit-gate.sh` `check_plan_scope` instead of deleted; no prefixed-plan coverage existed in the commit-gate tests.
- Task 6.2 (Rule 1) — `skills/correctness-review/correctness-scorer-prompt.md` no longer tells the scorer to zero lint-level findings "because a linter would catch them": with `ruff-on-edit` retired, no linter is wired as a hook or CI gate. Design §2.5's "CI lint" rationale was wrong and is corrected in design.md.
- Task 6.3 — its edits landed in Task 6.1's commit `5484c69`, not a commit of its own: parallel implementers share one worktree index, and 6.1's `git commit` swept up 6.3's staged files. The content is as intended; only per-task commit attribution is lost. History was not rewritten.
- Task 6.3 (Rule 3) — also retargeted `scripts/ci-strict-gate.sh:60` ("risk-corroboration" without `.sh`, outside the grep pattern).

### Context-Propagation Audit

Verdict: **PASS** (isolated reviewer, two rounds; first round FAIL on F1–F3, repaired in `4edddf7`; residuals R-A–R-D closed in `7f7c370`).

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `skills/writing-plans/SKILL.md` step 5 — run `render_plan.py --summarize` after saving | writing-plans | main | skill body + `allowed-tools` grant | `check_skill_tool_conformance.py` (26 commands permitted) |
| `rules/wave-parallelism.md` step 3 — `--summarize` at each wave boundary | SDD controller | main | explicit Read `skills/subagent-driven-development/SKILL.md:38`; `paths:` frontmatter | `render_skill_prompt.py --check-all`; `context-propagation-regression.test.sh` |
| same | SDD controller via `resume <slug>` | new session | explicit Read `references/resume.md:3-5` | registry `render_skill_prompt.py` (`resume` requires wave-parallelism.md) |
| `skills/finishing-a-development-branch/SKILL.md` step 3 — `--summarize` before the shipped commit (F1) | finishing-a-development-branch | main | skill body; bare `Bash` grant | conformance lint; ordering read (render before `git add`) |
| derived `render_plan.py` path (F2) | agents in a deployed consumer | main, new session | `deploy-harness.sh rewrite_derived_paths` repoints `python3 skills/visual-planner/render_plan.py` | `consumer-subset.test.sh` "derived docs invoke render_plan.py at the deployed path, and it resolves" |
| `rules/orchestration.md` blast-radius trigger | main | main | always-loaded | `hooks/commit-gate.sh` `check_plan_scope`; `rule-loading-tiers.test.sh` |
| `task-reviewer-prompt.md` scope comparison (F3, R-A, R-B) | task-reviewer | reviewer | pasted template; inputs from `task_brief.py` (Files bullet) + `review_package.py` (diff stat); task-local BASE pinned in SDD SKILL.md | `context-propagation-regression.test.sh` presence + mutation case |
| `correctness-scorer-prompt.md` score-0 linter rule | correctness scorer | scorer | pasted fragment via `render_skill_prompt.py` | `--check-all` all contracts present |
| `rules/auto-correct-scope.md` gate retargets | implementer, correctness reviewer, intake | implementer, reviewer, main | explicit Reads (`implementer-prompt.md` FIRST: Read; `correctness-review` shared fragment) | `context-propagation-regression.test.sh` |
| `rules/plan-format.md` Files set / `--summarize` callers | writing-plans, plan reviewer, SDD, resume | main, reviewer, new session | explicit Reads | `render_skill_prompt.py --check-all` |
| CLAUDE.md hook table, profiles, gotchas; templates; skills/README.md; other retargets | every session / artifact readers | main, all | always-loaded / pasted into artifacts | `lint-doc-truth.sh`; no removed-hook name in authority files |

Known archival references (not live consumers): `specs/new-session-plan-resume/SUMMARY.md:192` cites collection-protocol "step 4" (now step 5). Pre-existing stale pointer left as-is: `scripts/check_review_receipt.py:141` cites "finishing-a-development-branch Step 4" (predates this branch).

### Correctness Review

Six finder angles (reviewer, `claude-opus-5`), 18 deduplicated locations, one independent scorer
each (`claude-opus-5-5`); threshold 75.

**Fixed (score ≥ 75):**

- L01 (100) — `hooks/commit-gate.sh` was committed `100644` while registered as a bare command, so the runtime got exit 126 and skipped every commit gate. Fixed in `58c6196` (mode `100755`), with an executability assertion added to `tests/scripts/settings-wiring.test.sh` (fails at `7f7c370`, passes at `58c6196`). Classified Rule 1 inside the user-approved plan scope (creating and registering this hook), although `hooks/*` is Rule 4 by path.
- L03 (100) — `skills/subagent-driven-development/SKILL.md` was over the 600-word ceiling (613), which failed `scripts/test_audit_skill_prompts.py`. Fixed in `58c6196`.

**Advisory (score < 75) — recorded, not auto-fixed:**

| ID | Score | Location | Finding |
| --- | --- | --- | --- |
| L02 | 0 | `tests/scripts/settings-wiring.test.sh:12-20`, `scripts/lint-doc-truth.sh:92` | No executability check existed (pre-existing). The wiring test now has one (`58c6196`); `lint-doc-truth.sh` still checks existence only. |
| L04 | 0 | `hooks/commit-gate.sh:111` | `check_untracked_py` scans from the hook's CWD before the repo root is resolved (pre-existing in `check-untracked-py.sh`); under strict, an untracked `.py` outside the CWD subtree is missed. |
| L05 | 0 | `scripts/capture_codex_capabilities.sh:589` | SessionEnd benchmark still gated on `jq`, which the fixture hook no longer needs (unmodified line). |
| L06 | 0 | `hooks/commit-gate.sh:586,640,697` | Pathspec `app/**/*.py` misses top-level `app/*.py` (pre-existing in `commit-quality-gate.sh`). |
| L07 | 0 | `hooks/lib/lane.sh:53-56` | Active-plan Lane fallback reads SUMMARY.md from the worktree, not the index, so an unstaged `Lane: high-risk` edit can satisfy risk corroboration (pre-existing). |
| L08 | 0 | `hooks/commit-gate.sh:683` | Bare `python -m pytest`; exit 127 is reported as a test failure (pre-existing). |
| L09 | 0 | `adapters/codex/plugin/hooks/hooks.json:8` | Codex runs commit-gate at the standard profile — declared out of scope (design §7). |
| L10 | 0 | `scripts/render_codex_adapter.py:40-43` | `_plugin_command` would quote arguments into the script path; not reachable from the bare root `settings.json` (unmodified line). |
| L11 | 25 | `hooks/commit-gate.sh:121` | Strict untracked-`.py` deny exits before other diagnostics (recorded deviation). |
| L12 | 50 | `CLAUDE.md:71` | Hook table implied strict alone re-runs the Verify table; wording corrected in `58c6196`. |
| L13 | 25 | `hooks/commit-gate.sh:131-137` | Lane-lib fail-closed guard applies under minimal too; trigger requires a corrupted install. |
| L14 | 0 | `scripts/deploy-harness.sh:103` | Manifest default profile not re-validated at deploy; `check_manifest.py` A3 catches the only trigger in CI. |
| L15 | 50 | `hooks/commit-gate.sh:154` | `git commit -a` / pathspec commits evaluate an empty staged set. Pre-existing for all gates except plan scope, which lost its edit-time backstop with the retired hook (warn-only by default). |
| L16 | 0 | `hooks/commit-gate.sh:610` | App-gate SUMMARY fallback uses `ls -t` (pre-existing). |
| L17 | 0 | `hooks/commit-gate.sh:317` | Run-state gate blocks a gitignored `RUN.json` with an unworkable `git add` hint (pre-existing; `REQUIRE_RUN_STATE_STAGED=0` escape). |
| L18 | 0 | `tests/scripts/settings-wiring.test.sh:28-30` | Derived-settings assertion is skipped in CI (no `.claude/`); `deploy-profile.test.sh` covers derivation in temp targets. |

Follow-up reviews: the fix commit `58c6196` re-review (verdict ISSUES, all Low, applied in `d8688c7`), then `58c6196..6aa93ca` tail review (verdict CLEAN; M1–M4 applied in `6aa93ca`, confirmed CLEAN). Remaining advisories:
- M5 — `tests/scripts/settings-wiring.test.sh:17` would report a registered command carrying an argument as `missing:` rather than parse it; not live (root `settings.json` registers bare paths).
- M6 — `skills/subagent-driven-development/SKILL.md` is at 599/600 words; the next prose addition fails `test_audit_skill_prompts.py`.

### Intent Findings

Intent review (reviewer, `claude-opus-5-5`, plan-blind) at `d8688c7`: no gaps. Every SC-1–SC-15 has a passing Verify row. It found eight divergences:

| # | Class | Finding | Resolution |
| --- | --- | --- | --- |
| 1, 3 | drift | `blast-radius-check.sh` was deleted, but its check survives as commit-time `check_plan_scope` (warn by default) plus the task reviewer's diff-vs-Files comparison. design.md SC-4 encodes this. | The user confirmed on 2026-09-29: keep it. The option the user chose at intake read "chức năng quan trọng (blast-radius) dời vào commit-gate/task-reviewer". |
| 2 | drift | `render-plan-on-write.sh` was deleted, but the At-a-glance refresh survives as explicit `render_plan.py --summarize` steps in writing-plans, the wave boundary, and the ship step. | The user confirmed on 2026-09-29: keep it. |
| 4 | drift | The untracked-`.py` deny moved from every repo to `--profile strict` only. | The user confirmed on 2026-09-29: strict-only. |
| 5 | drift | `minimal` runs only branch isolation and the secrets scan. | The user confirmed on 2026-09-29: this is intended. |
| 6 | excess | `branch-guard.sh` was retired; it is not in the user's delete list. | Report-only. It was part of approach A, which the user approved ("Bỏ branch-guard vì trùng"). |
| 7 | excess | The SDD per-task BASE definition and the wave-parallelism resume rationale were reworded. | Report-only. These are context-propagation audit repairs needed for the new reviewer scope check and the `--summarize` step. |
| 8 | excess | session-knowledge now injects an INDEX pointer instead of 30 rows. | Report-only. It serves "gọn nhẹ hơn", and approach A covered it. |

Note: the intent reviewer also flagged a stale header comment in `hooks/branch-isolation-guard.sh`. It was fixed in `11f5e9e` (comment only).

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| settings registration | `python3 -c "import json;h=json.load(open('settings.json'))['hooks'];assert sorted(h)==['PreToolUse','SessionStart'],sorted(h);assert sum(len(g['hooks']) for v in h.values() for g in v)==3"` | 0 | assertions hold | SC-1 |
| branch isolation | `bash tests/hooks/branch-isolation-guard.test.sh` | 0 |   branch-isolation-guard.test.sh: 38 passed | SC-2 |
| commit-gate | `bash tests/hooks/commit-gate.test.sh` | 0 |   commit-gate.test.sh: 78 passed | SC-3 |
| commit-gate risk | `bash tests/hooks/commit-gate-risk.test.sh` | 0 |   commit-gate-risk.test.sh: 51 passed | SC-4 |
| deploy/install profile | `bash tests/scripts/deploy-profile.test.sh` | 0 |   deploy-profile.test.sh: 23 passed | SC-5 |
| settings merge | `bash tests/scripts/settings-merge.test.sh` | 0 |   settings-merge.test.sh: 12 passed | SC-6 |
| manifest | `python3 scripts/check_manifest.py` | 0 | manifest: consistent — inventory ↔ disk ↔ settings.json ↔ hook_profiles ↔ commit-gate.sh a | SC-7 |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | ✓ doc-truth lint: source + derived paths exist; hook table matches settings.json | SC-8 |
| codex adapter | `python3 -m pytest -q scripts/test_render_codex_adapter.py` | 0 | 13 passed in 0.32s | SC-9 |
| codex probe | `bash tests/scripts/codex-capability-probe.test.sh` | 0 |   codex-capability-probe.test.sh: 40 passed | SC-10 |
| session-knowledge | `bash tests/hooks/session-knowledge.test.sh` | 0 |   session-knowledge.test.sh: 17 passed | SC-11 |
| no removed-hook names | `git grep -n -e ruff-on-edit -e render-plan-on-write -e scope-gate -e state-breadcrumb -e blast-radius-check -e branch-guard.sh -e check-untracked-py -e commit-quality-gate -e risk-corroboration.sh -e pre-bash-dispatch -- . :!specs :!docs/research :!docs/harness-experimental :!docs/solutions :!docs/harness-gap-closure-plan.md :!docs/harness-v03-plan-overview.md :!research-loop.md :!evals :!CHANGELOG.md :!tests/scripts/settings-merge.test.sh :!tests/scripts/deploy-profile.test.sh :!tests/scripts/codex-capability-probe.test.sh` | 1 | no matches | SC-12 |
| runtime-neutral | `python3 scripts/check_runtime_neutral_sources.py --root .` | 0 | runtime-neutral: specs/codex-support/neutralization-inventory.json passed | SC-13 |
| --summarize callers | `python3 -c "import pathlib as p;fs=['skills/writing-plans/SKILL.md','rules/wave-parallelism.md','rules/plan-format.md','skills/visual-planner/SKILL.md'];m=[f for f in fs if '--summarize' not in p.Path(f).read_text()];assert not m,m"` | 0 | assertions hold | SC-14 |
| commit-gate evidence | `bash tests/hooks/commit-gate-evidence.test.sh` | 0 |   commit-gate-evidence.test.sh: 24 passed | SC-15 |
| audit skill prompts | `python3 -m pytest -q scripts/test_audit_skill_prompts.py` | 0 | 8 passed (SDD SKILL.md 599/600 words) | |
| skill tool conformance | `python3 scripts/check_skill_tool_conformance.py` | 0 | 26 instructed commands permitted | |
| context propagation | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | 10 passed | |
| consumer subset | `bash tests/scripts/consumer-subset.test.sh` | 0 | 16 passed | |

### Not auto-verified

- Latency: per-edit wall time drops from ~215 ms (PreToolUse + slowest parallel PostToolUse) to ~130 ms — reached truth only as ad-hoc local timings (branch-isolation ~136 ms, non-git Bash ~16 ms); no benchmark gate re-runs them.
- Live Claude Code behaviour of the new surface in this repo — traceability only: the worktree's `.claude/` was intentionally not re-deployed, so the registered hooks were exercised only through test harnesses (`bash hooks/...`) and a direct-exec probe, never inside a live session. `settings-wiring.test.sh` "deploy derivation holds" is red locally for that reason and skipped in CI.
- `fast_rel` ↔ `normalize-tool-input.py` `_safe_relative` parity — provenance only (comment + ad-hoc differential probes by reviewers); no committed parity test.
- Codex runtime behaviour after the adapter regeneration — not re-run (needs `codex_harness_doctor.py` on a real install).
- The 16 advisory correctness findings (see `### Correctness Review`) are recorded, not fixed.

### Rollback

- Revert the branch merge: `git revert -m 1 <merge-sha>` (restores the ten hooks, the 8-command `settings.json`, and the old manifest/tests).
- Consumers: re-run `scripts/deploy-harness.sh --target <repo>` from the reverted harness; the merge re-registers the old hooks. `.claude/.harness-profile` is inert without the new deploy and can be deleted.

### Harness-Delta

- backlog → compound: parallel implementers sharing one worktree share one git index — a plain `git commit` swept a sibling's staged files and a `git reset --soft` orphaned a sibling's commit. Implementer briefs should require `git commit -- <paths>` and forbid `git reset`, or give each parallel task its own worktree.
- backlog → compound: a hook registered as a bare command must be executable in the index; tests that run hooks via `bash hooks/x.sh` cannot see a missing execute bit (now guarded by `settings-wiring.test.sh`).
- backlog: no Python lint gate remains after retiring `ruff-on-edit`; consider a CI ruff step.
- backlog: subagents cannot write `.harness-state/sdd/report-*.md` (harness refuses subagent report writes); the controller relayed reports.
