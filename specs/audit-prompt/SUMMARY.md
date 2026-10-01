# audit-prompt — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate — the diff edits skills/*/SKILL.md-adjacent dispatch prompts, agents/*.md, rules/*.md and CLAUDE.md.
Flags: existing-behavior, multi-domain
Affects: workflow-engine (skills, agents, rules, CLAUDE.md instruction text)
Input-type: maintenance
Route: high-risk — design and research come from the approved prompt audit (specs/audit-prompt/research-brief.md); writing-plans → this worktree → implement → context-propagation-audit → correctness-review → intent-review → finishing-a-development-branch (PR into audit-prompt)
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> new 1 branch call "audit-prompt" (check out from main branch)
> start for fixing/updating following research above on current branch
> after that create PR to the "audit-prompt"

Context from the same conversation: "the research above" is the prompt audit published as
specs/prompt-audit-project-skills/audit-report.md (skills, findings S1–S9) and
config-audit.vi.md (CLAUDE.md, AGENTS.md, rules, agents, findings C1–C18), copied here as
`research-brief.md`.

Reading chosen: `audit-prompt` is created from `main` and pushed as the PR base; the fixes are made
on a work branch `fix/audit-prompt-findings` cut from it, and the PR targets `audit-prompt`.
"Fixing following research" means applying the findings the audit gave a concrete diff for
(S2, S3, C1, C2, C3, C4, C5, C7, C8, C9, C10, C11). Findings the audit marked `flag` (S1, S4–S9,
C6, C12–C18) need a decision and are out of scope.

## What changed

Applied the twelve prompt-audit findings that came with a concrete diff (S2, S3, C1–C5, C7–C11) across `agents/`, `rules/`, `CLAUDE.md` and two skill prompts plus `skills/README.md`: corrected stale pointers in `agents/PROJECT.md`, added the pytest targeted-run form, trimmed the `test-runner` description, retired legacy `<verify>`/`<action>`/`<files>` field names, switched `python` to `python3`, dropped a pinned model reference, made the code-review-graph instruction conditional, stopped the deploy rewrite from inverting README check 1.8, and added `lane` / `harness_delta` to the implementer report with a returned `Harness-Delta:` line. The full repository suite (`bash scripts/run-tests.sh`) ran green (638 pytest passed) and is cited here rather than as a Verify row.

### Rationale

The audit already fixed the replacement text, so each change was applied as written and grouped by directory into three disjoint tasks. Findings marked `flag` were left out because each needs a human decision.

### Alternatives considered

- Applying every finding including the `flag` ones — rejected: those need a decision (deploy ownership, model binding, eval re-baselining).
- Rewording beyond the audit's text — rejected by the plan's Global Constraints.

### Deviations

- Process: the three implementers ran in parallel in one worktree without committing; the controller committed each task (`585e5be`, `2f09a8e`, `05bc692`) to avoid a shared git index (`docs/solutions/harness/parallel-implementers-share-one-git-index.md`).
- Rule 2 — `2b82ffc`: after task review, added a returned `Harness-Delta:` line to the implementer prompt (completes C5's intent) and reworded `rules/wave-parallelism.md:43`; made by the controller, outside the audit's hunk text.
- `design.md` and `research-brief.md` stand in for brainstorming and xia2: the audit was the research and the user's request approved its diffs.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| SC-1 check | `grep -rqF "skills/xia2/SKILL.md" agents/PROJECT.md agents/PROJECT.template.md` | 1 | expected exit 1 | SC-1 |
| SC-2 check | `grep -qF "inside its own" agents/PROJECT.template.md` | 1 | expected exit 1 | SC-2 |
| SC-3 check | `grep -qF "Coding Style & Naming Conventions" agents/PROJECT.md` | 0 | expected exit 0 | SC-3 |
| SC-4 check | `grep -qF "python3 -m pytest" agents/PROJECT.md` | 0 | expected exit 0 | SC-4 |
| SC-5 check | `grep -qF "PYTESTS" agents/PROJECT.md` | 0 | expected exit 0 | SC-5 |
| SC-6 check | `grep -qF "example>" agents/test-runner.md` | 1 | expected exit 1 | SC-6 |
| SC-7 check | `grep -rqF -e "<verify>" -e "<action>" -e "<files>" rules/orchestration.md rules/wave-parallelism.md rules/auto-correct-scope.md CLAUDE.md` | 1 | expected exit 1 | SC-7 |
| SC-8 check | `grep -qF -e "<verify>" -e "<action>" -e "<files>" skills/subagent-driven-development/implementer-prompt.md` | 1 | expected exit 1 | SC-8 |
| SC-9 check | `grep -rqF "python scripts/" rules/auto-correct-scope.md rules/plan-format.md` | 1 | expected exit 1 | SC-9 |
| SC-10 check | `grep -qF "python scripts/" skills/README.md` | 1 | expected exit 1 | SC-10 |
| SC-11 check | `grep -qF "Opus 5.x" rules/behavior.md` | 1 | expected exit 1 | SC-11 |
| SC-12 check | `grep -qF "MCP server is connected" CLAUDE.md` | 0 | expected exit 0 | SC-12 |
| SC-13 check | `grep -qF "modes from the index" skills/README.md` | 1 | expected exit 1 | SC-13 |
| SC-14 check | `grep -qF "harness_delta" skills/subagent-driven-development/implementer-prompt.md` | 0 | expected exit 0 | SC-14 |
| SC-15 check | `grep -qF "You reason best" skills/subagent-driven-development/implementer-prompt.md` | 1 | expected exit 1 | SC-15 |
| SC-16 check | `grep -qF "BY DEFAULT" skills/intent-review/intent-reviewer-prompt.md` | 1 | expected exit 1 | SC-16 |
| SC-17 check | `bash scripts/lint-doc-truth.sh` | 0 | expected exit 0 | SC-17 |
| context-propagation regression | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | 10 passed | |
| agent definition renderer | `python3 -m pytest scripts/test_render_agent_definitions.py -q` | 0 | 12 passed (Task 1.1) | |

### Not auto-verified

- The edits change agent behavior as intended — reached traceability (grep checks that text changed); no agent run was re-observed.
- C5 approval — the audit marked it as needing confirmation; applied on the reading recorded under Intent. The PR calls it out as droppable.
- Delivery to this repo's sessions and to consumers — reached traceability; the derived `.claude/` copy was not redeployed, and two edited files are bootstrap-owned (see Advisory Findings).

### Context-Propagation Audit

Diff `b10ca31..2b82ffc`. Result: **PASS**.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `agents/PROJECT.md` (C1, C3, C4) | `coding` agent, `test-runner` agent, `finishing-a-development-branch` | implementer, test-runner, main | explicit Read | `agents/coding.md:13-19`, `agents/test-runner.md:12,17`, `skills/finishing-a-development-branch/SKILL.md:22` |
| `agents/PROJECT.template.md` (C1) | new consumer installs (scaffold) | none at runtime | copied at install | not an agent context |
| `agents/test-runner.md` description (C10) | agent registry | main | always-loaded agent list (deployed copy) | frontmatter field; `scripts/test_render_agent_definitions.py` pins model/tools only (12 passed in Task 1.1) |
| `rules/behavior.md` (C9) | every session | main | always-loaded (no `paths:`) | `tests/scripts/rule-loading-tiers.test.sh` inventory; wording only, no rule changed |
| `rules/orchestration.md` (C8) | controller; `agents/coding.md:32` | main, implementer | always-loaded; explicit pointer | wording only (`Verify` field name) |
| `rules/wave-parallelism.md` (C8) | SDD controller | main | paths-triggered + explicit Read | `skills/subagent-driven-development/SKILL.md` Preflight; `scripts/render_skill_prompt.py:20-25` registry |
| `rules/auto-correct-scope.md` (C7, C8) | implementer, correctness finders, intent-review | implementer, reviewer | explicit Read | `implementer-prompt.md:88`, `correctness-review/prompts/shared.md:105`, `intent-review/SKILL.md:39`; registry `render_skill_prompt.py:27-29` |
| `rules/plan-format.md` (C7, example rows) | writing-plans, plan reviewer | main, reviewer | explicit Read | `writing-plans/SKILL.md:9`, `plan-document-reviewer-prompt.md:5` |
| `CLAUDE.md` (C8, C11) | every session | main | always-loaded | C11 is a main-session tool instruction |
| `implementer-prompt.md` (S2, C5, C8, Harness-Delta return line) | implementer; controller; `compound` | implementer, main | pasted dispatch template (registered fragment) | `render_skill_prompt.py:27-29`; `Harness-Delta: backlog` literal matched by `compound/subagents/solution-extractor-prompt.md:89` and `context-analyzer-prompt.md:9`; `tests/scripts/context-propagation-regression.test.sh` 10 passed |
| `intent-reviewer-prompt.md` (S3) | intent reviewer | reviewer | pasted dispatch template | `intent-review/SKILL.md:27` |
| `skills/README.md` (C2, C7) | readers via `CLAUDE.md:57` pointer | main | on-demand Read (deployed copy) | deploy rewrite regex from `scripts/deploy-harness.sh:399-406` applied to the new lines: check 1.8 no longer gains a `.claude/harness-manifest.json` path; line 229 becomes `python3 .claude/scripts/verify_summary.py` |

Not a failure, recorded: every authority above reaches this repo's sessions through the derived
`.claude/` copy, which stays stale until `bash scripts/deploy-harness.sh` runs. That deploy was not
run here because it needs the user's confirmation.

### Advisory Findings

Correctness review over `b10ca31..2b82ffc`: six finder angles, nine deduplicated locations, each
scored by an independent scorer. Threshold 75; every score fell below it, so none entered the fix
loop. Recorded here for the human.

| Location | Score | Finding | Suggested follow-up |
| --- | --- | --- | --- |
| `agents/PROJECT.md:15` | 50 | Pointer now targets root `AGENTS.md`, which `install-harness.sh` / `deploy-harness.sh` do not ship; dangles in a consumer with no `AGENTS.md` | Mark the bullet harness-repo-specific, as the Test-execution section already is |
| `skills/subagent-driven-development/implementer-prompt.md:117` | 50 | New `lane` report field has no input: neither the prompt nor `task_brief.py` carries the lane | Pass the lane in the dispatch (template slot or brief), or drop the field |
| `CLAUDE.md:99` | 50 | Graph paragraph now limits the server to structural questions, while the table below still offers `semantic_search_nodes` and `get_review_context` for keyword search and snippets | Defer the "what for" to the table, or widen the sentence |
| `skills/subagent-driven-development/implementer-prompt.md:118` | 25 | Report-file key `harness_delta` vs returned line `Harness-Delta:`; miners are LLM prompts, so a miss is unconfirmed | Use one spelling |
| `skills/subagent-driven-development/implementer-prompt.md:106` | 0 (pre-existing) | `SKILL.md:54-55` still lists a three-item return; the returned line reaches the transcript regardless | Align `SKILL.md`'s return list |
| `CLAUDE.md:71` | 0 | `Files` is the generic field name for both syntaxes; no bug | none |
| `rules/plan-format.md:99-100` | 0 (pre-existing) | Example rows call `verify_summary.py --lint`, a flag that does not exist (exit 2) | Point the rows at `python3 scripts/check_plan_contract.py specs/<slug>/PLAN.md` |
| `skills/README.md:208` | 0 (pre-existing) | Check 1.8 omits the hook's embedded-defaults fallback | "…the manifest in the git index, else the embedded defaults; never a `.claude/` copy" |
| `skills/README.md:308` | 0 (unmodified line) | Still says "copy `<verify>`" for the visual-planner button | Rename to "copy `Verify`" |

Also reported, outside the scored set (Rule 4, needs a decision): `rules/behavior.md` and
`agents/PROJECT.md` are `BOOTSTRAP_OWNED_FILES` in `scripts/deploy-harness.sh`, so on an existing
install a re-sync keeps the old copy and writes the new one as `.harness-incoming`. These two fixes
need a manual merge in every installed repo.

Task-review Minor findings carried forward: `agents/README.md:37` repeats the stale xia2 claim (file
was not audited); `AGENTS.md:32` still says Python follows `ruff` with no ruff config wired; the
intent-reviewer edit leaves one line of about 150 characters.

### Intent Findings

Intent review over `b10ca31..2b82ffc` (blind to PLAN.md; oracle = the user's request plus the two
audit reports). Every hunk traces to an audit `rewrite` finding; no excess. Four findings, each
recorded here:

- **gap, deferred — `flag` findings not applied.** S1, S4–S9, C6, C12–C18 have no hunk. The audit
  itself marks each as needing a decision; the PR description lists them for the user.
- **gap, deferred — `.claude/` not redeployed.** Both audits say "redeploy after applying". `.claude/`
  is gitignored, so it cannot land in this PR, and the user's standing rule is not to touch `.claude/`
  without confirmation. Until `bash scripts/deploy-harness.sh` runs, sessions in this repo still read
  the old text. Raised in the PR for the user.
- **drift, advisory — H6 widened.** `implementer-prompt.md:105-107` also returns a
  `Harness-Delta: <value>` line, beyond H6's two report bullets; it serves C5's stated rationale
  (compound mines the returned summary).
- **drift, advisory, equivalent — `rules/wave-parallelism.md:43`** says "confirm every task's
  `Verify` passed" rather than a bare tag swap.

### Rollback

- `git revert <sha>` for each commit on `fix/audit-prompt-findings`, or close the PR unmerged.

### Harness-Delta

- none
