# opus-5-5-review-bindings — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine (agents/*.md, review dispatch prompts), weakening-validation (removes two BindingError checks), remove-functionality (drops the ensemble-diversity rule); human authorized the drop explicitly
Flags: workflow-engine, weakening-validation, remove-functionality, existing-behavior
Affects: agents/runtime-bindings.json, scripts/render_runtime_entry.py, correctness-review and intent-review dispatch prompts, agents/reviewer.md
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no (the hard-gated decision — dropping ensemble diversity — was made by the human in-session)

### Intent

Prior turn (assistant recommendation, context): reviewer/task-reviewer pin `claude-opus-5`; moving them to `claude-opus-5-5` collides with the coding binding and breaks the ensemble-diversity rule; options are Sonnet 5.5 or accepting the same model.

User, verbatim:

> 1. reviewer dung opus 5.5 - medium effort
> 2. task review cung dung opus 5.5 - medium
> 3. chay eval review-chain + task review

User answers to the follow-up question (verbatim selections):

> Ghim reviewer = opus-5-5 sẽ trùng model với coding (opus-5-5) và vi phạm ensemble-diversity mà render_runtime_entry.py đang enforce. Xử lý thế nào? → "Bỏ diversity rule"
> Eval ... Chạy khi nào? → "Sau thay đổi (Recommended)"

## What changed

The Claude `reviewer` and `task-reviewer` roles now bind `claude-opus-5-5` at `medium` effort. The ensemble-diversity rule is gone: `scripts/render_runtime_entry.py` no longer rejects a scorer that shares the finders' model or an intent reviewer that shares the implementer's, and the review prompts, `agents/reviewer.md`, `agents/agent-contracts.json` and `agents/README.md` no longer claim it. Tests were updated to the new pins and a regression test now asserts both collapsed bindings validate. Codex bindings are unchanged.

### Rationale

Anthropic's Opus 5.5 migration guidance reports Opus 5.5 at `medium` effort outperforming Opus 5 at `high` on code review with fewer tokens; the user chose that model for both review roles and accepted losing cross-model diversity.

### Alternatives considered

- Keep diversity by moving coding to another model — rejected by the user.
- Reviewer on `claude-sonnet-5-5` — offered in the prior turn; user chose Opus 5.5.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Claude reviewer and task-reviewer are pinned to Opus 5.5 at medium effort | `python3 -c "import json; r=json.load(open('agents/runtime-bindings.json'))['runtimes']['claude']['roles']; assert all(r[k]['model']=='claude-opus-5-5' and r[k]['effort']=='medium' for k in ('reviewer','task-reviewer'))"` | 0 | re-run by controller 2026-10-02 at d41b78a | SC-1 |
| Codex role models are unchanged | `python3 -c "import json; r=json.load(open('agents/runtime-bindings.json'))['runtimes']['codex']['roles']; assert [r[k]['model'] for k in ('coding','reviewer','task-reviewer','test-runner')]==['gpt-5.6-sol','gpt-5.6-terra','gpt-5.6-terra','gpt-5.6-luna']"` | 0 | re-run by controller 2026-10-02 at d41b78a | SC-2 |
| The live runtime-entry binding validates with shared review models | `python3 scripts/render_runtime_entry.py --root . --check` | 0 | re-run by controller 2026-10-02 at d41b78a | SC-3 |
| Collapsed scorer/finder and intent-reviewer/implementer bindings are accepted, and stage goldens resolve to Opus 5.5 | `python3 -m pytest scripts/test_render_runtime_entry.py -q` | 0 | re-run by controller 2026-10-02 at d41b78a | SC-4 |
| Rendered Claude agents carry the new model/effort and keep the load-bearing reviewer claims | `python3 -m pytest scripts/test_render_agent_definitions.py -q` | 0 | re-run by controller 2026-10-02 at d41b78a | SC-5 |
| Shell runtime-entry contract passes with the new task-reviewer model | `bash tests/scripts/runtime-entry-bindings.test.sh` | 0 | re-run by controller 2026-10-02 at d41b78a | SC-6 |
| Install and deploy tests no longer pin the old reviewer model | `grep -qF "claude-opus-5\$'" tests/scripts/install-harness.test.sh tests/scripts/deploy-prune.test.sh` | 1 | re-run by controller 2026-10-02 at d41b78a | SC-7 |
| No agent, binding, contract or script source still requires or claims model diversity | `grep -qi -e "different model" -e "model different from" -e "distinct.from.implement" -e "distinct from .correctness_finder" -e "diversity" -e "must differ" agents/reviewer.md agents/agent-contracts.json agents/README.md agents/runtime-bindings.json scripts/render_runtime_entry.py scripts/test_render_runtime_entry.py scripts/test_render_agent_definitions.py` | 1 | re-run by controller 2026-10-02 at d41b78a | SC-8 |
| No review skill prose still requires or claims model diversity | `grep -qi -e "different model" -e "model different from" -e "distinct.from.implement" -e "distinct from .correctness_finder" -e "diversity" -e "must differ" skills/intent-review/SKILL.md skills/intent-review/intent-reviewer-prompt.md skills/correctness-review/correctness-scorer-prompt.md` | 1 | re-run by controller 2026-10-02 at d41b78a | SC-9 |
| Shared prompts stay free of vendor model labels and raw skill invocations | `python3 scripts/check_runtime_neutral_sources.py --root .` | 0 | re-run by controller 2026-10-02 at d41b78a | SC-10 |
| Documented paths and the hook table still resolve | `bash scripts/lint-doc-truth.sh` | 0 | re-run by controller 2026-10-02 at d41b78a | SC-11 |

### Not auto-verified

- Opus 5.5 at `medium` reviews at least as well as Opus 5 at `high` on this repo — reached traceability only (Anthropic's published claim); the follow-up review-chain and task-review evals measure it.
- Claude Code honors `effort:` in agent frontmatter and resolves `claude-opus-5-5` for subagents — reached traceability (rendered frontmatter asserted by tests); not re-run against the live runtime.
- Deployed `.claude/` copies pick up the change — not verified; requires a user-confirmed redeploy after merge.

### Context-Propagation Audit

Result: **PASS** (diff 796f310..d41b78a). Search surface: `grep -rn` for each changed prompt path and for `model_stage`, `subagent_type: reviewer`, `render_agent_definitions` across `skills/ scripts/ tests/ agents/ rules/ adapters/`, plus `scripts/deploy-harness.sh`.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `agents/runtime-bindings.json` Claude `reviewer`/`task-reviewer` model + effort | `.claude/agents/reviewer.md`, `task-reviewer.md` frontmatter → Task-tool `model:` for correctness finders, intent reviewer, task reviewer | reviewer, task-reviewer (child) | rendered at deploy (`deploy-harness.sh` `render_agents` → `render_agent_definitions.py`) | `test_render_agent_definitions.py` `LEGACY_CLAUDE`; `install-harness.test.sh`, `deploy-prune.test.sh` grep `model: claude-opus-5-5` in the rendered file |
| same bindings via `adapters/runtime-entry-bindings.json` stages | `render_runtime_entry.py --model-stage` (scorer, finder, intent, task stages) | main (render time) | CLI | `test_render_runtime_entry.py` goldens; `runtime-entry-bindings.test.sh` |
| `scripts/render_runtime_entry.py` diversity raises removed | live `--check` and every `--model-stage` call | main / CI | CLI | `test_collapsed_review_models_validate`; SC-3 |
| `correctness-scorer-prompt.md` "Score in fresh context" paragraph | scorer dispatch from `skills/correctness-review/SKILL.md` step 3 and the prompt's own step 2 (`:165`, "independent context") | scorer (child) | explicit file dispatch; registered in `scripts/render_skill_prompt.py` (`correctness-scorer`) | `correctness-prompt-composition.test.sh`, `scorer-threshold-contract.test.sh`, `runtime-entry-bindings.test.sh` (keeps `model_stage: correctness_scorer`) |
| `intent-reviewer-prompt.md` "Review in fresh context" paragraph | intent dispatch from `skills/intent-review/SKILL.md:27` | intent reviewer (child) | explicit file dispatch | `intent-prompt-contract.test.sh`, `final-review-package-contract.test.sh`, `runtime-entry-bindings.test.sh` |
| `skills/intent-review/SKILL.md:27` dispatch sentence | main-session controller of intent-review | main | skill load | inspected; SC-9 |
| `agents/reviewer.md` description | Claude Code agent registry (subagent selection); Codex TOML `description` | main (selection) | rendered at deploy | `LOAD_BEARING_SUBSTANCE` tokens still asserted |
| `agents/agent-contracts.json` reviewer `model_class` | Codex runtime-policy lines in rendered TOML | Codex child | rendered at install | free-form label; printed only (`render_agent_definitions.py:227`) |

Residual (not a failure): already-deployed `.claude/` copies (main checkout, consumers) keep the old pins and prose until redeploy; `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md:43,58` still names ensemble diversity as a requirement (dated learning, out of scope per design).

### Correctness Review

Diff 796f310..d41b78a, six plan-blind finder angles (`reviewer` agent), ten deduplicated locations, threshold 75. **No finding reached the fix loop (0 blocking).** Every finding is recorded below as advisory.

| # | Location | Claim | Score | Source |
| --- | --- | --- | --- | --- |
| A1 | `scripts/render_runtime_entry.py:98` | Deleting the diversity loop also drops enforcement for Codex, whose bindings still differ | 0 | scorer: the intended change; Codex bindings unchanged |
| A2 | `agents/runtime-bindings.json:24` | Reviewer effort lowered `high` → `medium` without prose | 0 | scorer: deliberate configuration (user decision) |
| A3 | `skills/correctness-review/correctness-scorer-prompt.md:27-32` | Deleted clause was the only cue that the scorer's model comes from the stage's role (`coding`), not `subagent_type: reviewer`; diverges on Codex | 25 | scorer: mismatch pre-exists at BASE; identical on Claude |
| A4 | `scripts/test_render_runtime_entry.py:25-61` | `test_live_binding_is_total` is tautological and Claude goldens no longer discriminate roles; a cross-wired stage map stays green | 50 | scorer: real, introduced, needs a mistaken config edit |
| A5 | `agents/runtime-bindings.json:98` | Codex reviewer `model_class` still says "distinct …" and renders as a mandatory policy line | 0 (unmodified line) | kept by design decision; candidate cleanup |
| A6 | `adapters/runtime-entry-bindings.json:5` | `correctness_scorer → coding` mapping is now unexplained; scorer model follows the implementer | 0 (unmodified line) | design follow-up |
| A7 | `.claude/agents/reviewer.md`, `task-reviewer.md` (worktree and main checkout) | Deployed agents keep `claude-opus-5` / `high` and the old description until redeploy | 0 (not in diff) | redeploy after merge, with user confirmation |
| A8 | `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md:22,43,58` | Learning record still states ensemble diversity as a requirement | 0 (unmodified line) | route to `compound` |
| A9 | `scripts/render_runtime_entry.py:90` | Non-object runtime entry raises `AttributeError` traceback instead of `BindingError` (exit still 1) | 0 (unmodified line) | pre-existing |
| A10 | `scripts/render_runtime_entry.py:43` | `schema_version: true` passes the `!= 1` check | 0 (unmodified line) | pre-existing |

Scored by four independent scorer dispatches (A1–A4); A5–A10 scored 0 by the rubric's mechanical unmodified-line rule, applied by the controller. Plan-blindness note: three finder angles reported that an early repo-wide grep printed `specs/` lines before they narrowed the exclusion; each states its findings came from source files.

### Intent Findings

Plan-blind intent review (`reviewer` agent) of 796f310..d41b78a: no excess; clauses "reviewer dung opus 5.5 - medium effort", "task review cung dung opus 5.5 - medium" and "Bỏ diversity rule" satisfied in all enforcing code and review prose. All SC-1..SC-11 proven by Verify rows.

- **gap — deferred (user-sequenced):** "3. chay eval review-chain + task review". The user chose "Sau thay đổi (Recommended)"; the evals need the new pins rendered into `.claude/`, so they run after merge and a user-confirmed redeploy (`design.md` §Follow-up). Not executed on this branch.
- **drift, equivalent — advisory:** `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md:43,58` still names ensemble diversity as a chain requirement → route to `compound` (reword to "independence").
- **drift, equivalent — advisory:** `agents/runtime-bindings.json:98` Codex reviewer `model_class` still says "distinct"; true for Codex today, kept by design; candidate cleanup.

Full suite: `bash scripts/run-tests.sh` exit 0, ALL GREEN (638 python tests), run by the controller after wave 1 and independently by the intent reviewer at d41b78a (cited here in prose; whole-suite rows are not Verify rows).

### Docs Re-review (d41b78a..7ebf9a8)

The compound commit touched `docs/`, so the receipt was re-earned by a read-only reviewer over that delta: **pass, 0 blocking**. Advisory minors, not applied (cosmetic; left for a follow-up):
- `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md:22` still says "model different from the implementer" (historically true; add a "true at the time" note).
- `sdd-report-file-handoff-refused-for-subagents.md`: `report-<task>.md` is practice, not tracked prose; `affects:` should add `rules/orchestration.md`; two live instructions coexist until the backlog row lands.
- `review-model-diversity-dropped-decisions.md` `affects:` could add `adapters/runtime-entry-bindings.json` and `skills/intent-review/SKILL.md`; the Anthropic claim and the refusal message are session observations, not repo-derivable.

### Rollback

- Revert the branch's code commits: `git revert d41b78a adc4bdb` (restores the pins, the validator loop, the prose and the tests).
- After revert, redeploy so rendered agents match: `bash scripts/deploy-harness.sh` (needs user confirmation).

### Harness-Delta

- backlog — subagent-driven-development asks implementers to write their report to `.harness-state/sdd/`, but Claude Code refused both implementers' Write of that file ("Subagents should return findings as text"); one wrote it via Bash, the other returned it inline and the controller transcribed it. The file-handoff contract needs to match the runtime rule.
