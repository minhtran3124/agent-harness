# review-policy — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate — edits review skill prompts, agents/reviewer.md, agents/task-reviewer.md, and adds rules/review-policy.md
Flags: existing behavior, weak proof, multi-domain
Affects: review chain (task review, correctness review, intent review, context-propagation audit)
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/review-policy/intent.md @ 33d6ed4ab1388a05c65397d70bac5ef5af649f53

"làm E1 di" — E1 in `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md` §6:

| **E1** | **Write a review policy (`REVIEW.md`-style) for the review skills**: what counts as Important vs Nit, a nit cap, a do-not-report list (generated files, anything CI already enforces), and a mandatory "compliance vs PLAN.md SC-n + SUMMARY Intent" pass label on each finding | Play 9 | new `REVIEW.md` or a section in `skills/correctness-review/` | normal (workflow-engine → audit) |

Reply to the draft (2026-10-11):

"1. đồng ý
2. đồng ý
3. hãy review lại toàn bộ agent/skills liên quan đến review trong workflow hiện tại (correct review, intent review, ...) và đảm bảo câu chữ đơn giản dễ hiểu, theo chuẩn của opus5.5"

### Intake notes

- Q1 (label: task reviewer → SC-n, intent review → Intent, correctness exempt) and Q2
  (`rules/review-policy.md`, explicit Read) decided by the user; Q3 (no nit count cap, Nits
  batched and non-blocking) approved with the intent, so confidence is high.
- The research note lists E1 as normal; intake raises it to high-risk because the manifest's
  workflow-engine gate covers skill prompts, agents/, and rules/.
- Branch `feat/review-policy` cut from `sdlc` before the intent commit (`sdlc` is the shared
  integration branch; intent-draft-from-chat advisory A3).
- Drafted-but-unapproved E2 intent (`specs/hook-deny-route-lines/intent.md`) stays untracked on
  the main checkout; it is not part of this slug.

## What changed

Added `rules/review-policy.md`, a path-scoped review policy that gives the task reviewer,
correctness review and intent review one vocabulary: Important versus Nit mapped onto each
existing scale (no blocking rule changes), Nits kept in the existing findings lists with no count
cap, a do-not-report list (generated files; lint/format already checked by a wired linter, with
runtime bugs still reportable; style/naming/formatting/maintainability for correctness and intent
review only), and finding labels (task reviewer `checked_against: SC-n | none`; intent review's
verbatim quote; correctness exempt). The three reviewer child prompts Read it explicitly, and
`scripts/render_skill_prompt.py` `CONTEXT_MATRIX` requires those Reads. All 17 review agent and
skill files were rewritten in plain wording (7,867 → 7,610 words), each checked file by file for
meaning equivalence. `CLAUDE.md` and `rule-loading-tiers.test.sh` now list five path-scoped rules.

### Rationale

One rules file read by an explicit Read reuses the existing `auto-correct-scope.md` delivery
pattern and its mutation-tested matrix check, instead of copying policy text into four prompts.
The policy describes the existing scales rather than replacing them, so no reviewer's blocking
behavior changes; behavior preservation of the rewrite was shown per file by an independent
meaning-equivalence review (design D6) because the scripted review-chain benchmark does not run
the skill prompts.

### Alternatives considered

- Two specs/PRs (policy, then rewrite): rejected; every prompt would be edited twice (design).
- Paste the policy into each prompt: rejected; four copies to keep in sync and more words.
- A count cap on Nits (playbook Play 9 uses 5): rejected; `opus-5-5-prompt-audit` decision 2
  removed review caps (D4).
- A behavioral eval of the rewrite (manual review-chain protocol, or a runner mode using real
  prompts): rejected by the user in favour of the per-file meaning-equivalence review.

### Deviations

- Plan, not a decision change: the design's "new test" for the Read lines is implemented by
  extending `scripts/render_skill_prompt.py` `CONTEXT_MATRIX` (research-brief recommendation),
  and that check lands in wave 4 (Task 4.1) rather than wave 3 so wave 3 stays file-disjoint;
  the suite stays green after wave 3 because the unchanged matrix still passes.

### Task review findings (Minor, rolled up)

- Task 2.1 (`agents/reviewer.md:22`): the "Cite your search surface" bullet reads as a description ("every absence claim … names the paths") rather than an imperative; meaning unchanged. Optional rewording.
- Task 2.2 (`skills/intent-review/SKILL.md:18`): "ask feature-intake to re-pin" made a skill the addressee — fixed in aca1284 (base wording "ask for feature-intake to re-pin" restored).
- Task 2.2 (`skills/intent-review/SKILL.md:32`): "Each finding quotes" turned a requirement into a description — fixed in aca1284 ("Each finding must quote").
- Task 2.2 (`skills/correctness-review/SKILL.md:14`): the "named, focused read" limit was moved onto the risk — fixed in aca1284.
- Task 2.2 (report): the claimed "scorer prompt"/"finder prompt" rename did not happen; not carried into the meaning-equivalence record.
- Task 2.3 (`skills/context-propagation-audit/SKILL.md:33`): "List each failed row and its repair" lost the verb reading of "repair" — fixed in aca1284 ("List and repair each failed row").
- Task 2.3 (report): word count re-measured by the controller with `len(text.split())`: 294 → 293 at 6a2c745 (292 after aca1284).
- Task 3.1 (`prompts/shared.md:66`, plan-mandated): replacing the style bullet with the policy pointer dropped "maintainability" from the finder's exclusions — fixed by naming maintainability in `rules/review-policy.md`'s correctness/intent exclusion.
- Task 3.1 (`correctness-reviewer-prompt.md:53`, `angles/call-site-impact.md:9`): two rewritten lines exceed the files' usual wrap width; formatting only, left as is.
- Task 3.2 (`correctness-scorer-prompt.md:293`): dispatcher step 2 says "For each location" instead of "For each deduplicated location"; step 1 still deduplicates to one candidate per location, so unchanged.
- Task 3.3 (`intent-reviewer-prompt.md:87-88`): the closed `gap` definition had become examples ("such as …") — fixed by restoring "a requested behavior, output, constraint, or surface that is missing".
- Task 3.3 (`intent-reviewer-prompt.md:117-118`): the out-of-scope line no longer names the owner of style; the policy's "Do not report" carries it, and the prompt now Reads the policy. Intended.
- Task 3.4 (`task-reviewer-prompt.md`): dropped the provenance pointer "matching `hooks/commit-gate.sh`'s `check_plan_scope`"; the exemption list is kept verbatim (verified against `hooks/commit-gate.sh:548`).
- Task 3.4 (`task-reviewer-prompt.md:5-8`): "rather than re-deriving it" had been dropped — restored.

### Meaning-equivalence review

Independent read-only reviewers compared `git show 33d6ed4:<file>` with HEAD for each rewritten
file (design D6). Items and their resolution:

#### Wave 2

- `agents/reviewer.md` — 290 → 275 words. Equivalent. Both the task reviewer and the
  equivalence reviewer flagged the "Cite your search surface" bullet as softened from "must name
  … never as absent" to a description; restored in the commit after aca1284 because it carries
  `rules/behavior.md` §1.
- `agents/task-reviewer.md` — 91 → 90 words. Equivalent; "a focused test you need" covers "a
  focused test that is required" (addressee, tool, and the ban on running it yourself unchanged).
- `skills/correctness-review/SKILL.md` — 388 → 387 words. Equivalent; "at the configured
  threshold" now reads "at or above" (the base already routed lower scores to advisory);
  "Otherwise, build the range as above" also covers an SDD call without a package.
- `skills/intent-review/SKILL.md` — 451 → 451 words. Equivalent. Changed (descriptive, no
  instruction): "The plan/spec reviewer is plan-oriented" → "The task reviewer checks the plan",
  matching the single task reviewer; accepted. Dropped rationale "— the user approved it" and the
  word "mechanical": accepted, no instruction depended on them.
- `skills/context-propagation-audit/SKILL.md` — 294 → 292 words. Equivalent.
- `skills/subagent-driven-development/references/review-chain.md` — 81 → 81 words. Equivalent;
  "Have each review resolve, escalate, or durably record every finding" keeps the same duty and
  timing.

#### Wave 3

- `skills/correctness-review/prompts/shared.md` — 1065 → 961 words. Not equivalent as first
  written: the intended policy pointer also brought in the policy's lint exclusion, which could
  make a finder hold back a runtime bug a linter also flags. Resolved by adding to
  `rules/review-policy.md`: "A runtime bug with a concrete trigger is still a finding even if a
  linter would also flag it; in correctness review the scorer decides whether a wired linter makes
  it moot." The generated-files exclusion is intended (design Architecture item 3). The old
  style/naming/formatting/maintainability exclusion is covered by the policy's
  correctness/intent bullet (maintainability added after task review). CAPS emphasis on the
  content-versus-confidence rule was removed; the rule is still stated in full. Otherwise
  equivalent.
- `skills/correctness-review/prompts/angles/call-site-impact.md` — 194 → 190 words. Equivalent.
- `skills/correctness-review/prompts/angles/enclosing-function.md` — 207 → 167 words. Equivalent
  (removed rationale only).
- `skills/correctness-review/prompts/angles/guard-completeness.md` — 406 → 402 words. Equivalent.
- `skills/correctness-review/prompts/angles/prior-art.md` — 240 → 234 words. Equivalent.
- `skills/correctness-review/prompts/angles/removed-behavior.md` — 203 → 203 words. Unchanged.
- `skills/correctness-review/prompts/angles/stack-defects.md` — 455 → 451 words. Equivalent.
- `skills/correctness-review/correctness-reviewer-prompt.md` — 150 → 150 words. Equivalent;
  "provenance" was dropped here but stays in `correctness-review/SKILL.md` and the scorer prompt,
  which the controller also reads.
- `skills/correctness-review/correctness-scorer-prompt.md` — 1546 → 1515 words. Equivalent; every
  anchor, auto-0 condition, the cap for unreadable code, threshold routing and dispatcher step kept.
- `skills/intent-review/intent-reviewer-prompt.md` — 1491 → 1446 words. Equivalent (after the
  closed `gap` definition was restored). Advisory: the policy also excludes generated files and
  already-linted findings from intent review (intended); the Read uses the repo-relative
  `rules/review-policy.md`, the same form as the existing `rules/auto-correct-scope.md` Read.
- `skills/subagent-driven-development/task-reviewer-prompt.md` — 315 → 315 words. Equivalent; the
  dropped `check_plan_scope` pointer was provenance only (exemption list verified against
  `hooks/commit-gate.sh:548`).

### Intent Findings

Plan-blind intent review over 33d6ed4..00e214f; no excess.

1. drift (behaviorally different) — the do-not-report list excludes only lint/format findings a
   wired linter already checks, not "anything CI already enforces". Escalated as E001; user
   decided A (keep the narrow scope), 2026-10-12.
2. drift (equivalent, advisory) — Nits stay in each reviewer's existing findings list rather than
   a separate batched list, so no output schema changes.
3. gap (ambiguous) — the correctness scorer does not Read the policy. Escalated as E002; user
   decided A (scorer exempt, matrix rationale stays), 2026-10-12.
4. drift (equivalent, advisory) — intent review's label is its existing verbatim intent quote.
5. drift (equivalent, advisory) — `prompts/angles/removed-behavior.md` was reviewed and left
   unchanged (an edit went over its word budget); its meaning-equivalence record says so.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| plan contract | `python3 .claude/scripts/check_plan_contract.py specs/review-policy/PLAN.md` | 0 | plan-contract passed | |
| SC-1 check | `python3 -c "import sys;t=open('rules/review-policy.md').read();sys.exit(not(t.startswith('---') and 'specs/*/SUMMARY.md' in t.split('---')[1] and all(h in t for h in ('## Important or Nit','## Nit reporting','## Do not report','## Finding labels'))))"` | 0 | policy frontmatter `specs/*/SUMMARY.md` and four sections present | SC-1 |
| SC-2 check | `bash tests/scripts/rule-loading-tiers.test.sh` | 0 | 3 passed | SC-2 |
| SC-3 check | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_render_skill_prompt.py` | 0 | 7 passed (matrix key set incl. intent-reviewer; mutation per required token) | SC-3 |
| SC-4 check | `bash tests/scripts/context-propagation-regression.test.sh` | 0 | 11 passed | SC-4 |
| SC-5 check | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_check_task_review_contract.py` | 0 | 2 passed (incl. negative test without `checked_against`) | SC-5 |
| SC-6 check | `python3 -c "import glob,sys;fs=['agents/reviewer.md','agents/task-reviewer.md','skills/correctness-review/SKILL.md','skills/correctness-review/correctness-reviewer-prompt.md','skills/correctness-review/correctness-scorer-prompt.md','skills/correctness-review/prompts/shared.md','skills/intent-review/SKILL.md','skills/intent-review/intent-reviewer-prompt.md','skills/subagent-driven-development/task-reviewer-prompt.md','skills/subagent-driven-development/references/review-chain.md','skills/context-propagation-audit/SKILL.md']+sorted(glob.glob('skills/correctness-review/prompts/angles/*.md'));n=sum(len(open(f).read().split()) for f in fs);print(n);sys.exit(n>7867)"` | 0 | prints 7610 (budget 7867) | SC-6 |
| SC-7 check | `bash tests/scripts/intent-prompt-contract.test.sh` | 0 | 3 passed | SC-7 |
| SC-8 check | `bash tests/scripts/scorer-threshold-contract.test.sh` | 0 | 6 passed | SC-8 |
| SC-9 check | `bash tests/scripts/correctness-prompt-composition.test.sh` | 0 | 4 passed | SC-9 |
| SC-10 check | `bash tests/scripts/inline-policy-drift.test.sh` | 0 | 3 passed | SC-10 |
| SC-11 check | `bash tests/scripts/final-review-package-contract.test.sh` | 0 | passed | SC-11 |
| SC-12 check | `bash tests/scripts/runtime-entry-bindings.test.sh` | 0 | 7 passed | SC-12 |
| SC-13 check | `bash tests/scripts/sdd-artifact-handoffs.test.sh` | 0 | passed | SC-13 |
| SC-14 check | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_render_agent_definitions.py` | 0 | 12 passed | SC-14 |
| SC-15 check | `bash tests/scripts/task-reviewer-readonly.test.sh` | 0 | passed | SC-15 |
| SC-16 check | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_audit_skill_prompts.py` | 0 | 8 passed | SC-16 |
| SC-17 check | `python3 scripts/check_runtime_neutral_sources.py --root .` | 0 | passed | SC-17 |
| SC-18 check | `bash scripts/lint-doc-truth.sh` | 0 | source + derived paths exist | SC-18 |
| SC-19 check | `python3 -c "import glob,sys;t=open('specs/review-policy/SUMMARY.md').read().split('### Meaning-equivalence review')[1].split('\n### ')[0];fs=['agents/reviewer.md','agents/task-reviewer.md','skills/correctness-review/SKILL.md','skills/correctness-review/correctness-reviewer-prompt.md','skills/correctness-review/correctness-scorer-prompt.md','skills/correctness-review/prompts/shared.md','skills/intent-review/SKILL.md','skills/intent-review/intent-reviewer-prompt.md','skills/subagent-driven-development/task-reviewer-prompt.md','skills/subagent-driven-development/references/review-chain.md','skills/context-propagation-audit/SKILL.md']+sorted(glob.glob('skills/correctness-review/prompts/angles/*.md'));m=[f for f in fs if f not in t];print(m);sys.exit(bool(m))"` | 0 | prints [] (all 17 files recorded) | SC-19 |

### Context-Propagation Audit

Range 33d6ed4..HEAD. New authority: `rules/review-policy.md` (path-scoped, `specs/*/SUMMARY.md`).
Reworded authorities: the 17 in-scope review files (delivery mechanics unchanged; meaning checked
per file above).

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `rules/review-policy.md` | `task-reviewer-prompt.md` | task reviewer (fresh) | explicit Read, line 17 | `CONTEXT_MATRIX["task-reviewer"]` `required_reads`; `scripts/test_render_skill_prompt.py` (mutation-tested); `context-propagation-regression.test.sh` 11 passed |
| `rules/review-policy.md` | `prompts/shared.md` → six angle compositions | correctness finders (fresh) | explicit Read, line 66; composed by `render_skill_prompt.py` | `CONTEXT_MATRIX["correctness-reviewer"]`; `correctness-prompt-composition.test.sh` 4 passed |
| `rules/review-policy.md` | `intent-reviewer-prompt.md` | intent reviewer (fresh, plan-blind) | explicit Read, line 118 | new `CONTEXT_MATRIX["intent-reviewer"]` entry; matrix key-set test |
| `rules/review-policy.md` | `correctness-scorer-prompt.md` | scorer (fresh) | none, by design | matrix rationale: scores evidence only; Important/Nit routing is the existing threshold in the controller (design D5) |
| `rules/review-policy.md` | correctness and intent controllers | main session | `paths:` injection when a SUMMARY is read (incidental, not counted) | routing unchanged (D5): Nit = existing advisory classes; no controller instruction depends on the policy |
| `rules/review-policy.md` | rule inventory | every session | `paths:` frontmatter keeps it contextual | `rule-loading-tiers.test.sh` 3 passed; `CLAUDE.md:7` lists five path-scoped rules |
| `rules/review-policy.md` | consumer installs | consumer sessions | `deploy-harness.sh` syncs `rules/` wholesale | inspected `scripts/deploy-harness.sh` rules sync (research brief) |

Result: PASS. No row is assumed or inferred from main-session behavior; the child Reads are
explicit and matrix-checked. Advisory (pre-existing, not introduced here): Codex ships no `rules/`,
so the policy Read — like the existing `rules/auto-correct-scope.md` Read — does not resolve in
Codex contexts.

### Correctness Review

Range 33d6ed4..00e214f. Six FIND angles dispatched with the rewritten prompts (each read
`rules/review-policy.md` and `rules/auto-correct-scope.md`); `prior-art` and `removed-behavior`
found nothing. Six deduplicated locations; four scored independently (threshold 75):

- `rules/review-policy.md:31-32` — the lint exclusion pointed at `agents/PROJECT.md` → Test
  execution, which lists no linters. Score 75 (Rule 1–3). Fixed in c692e81: "a linter or
  formatter wired into the project's CI or hooks". Re-scored at c692e81: 0, fixed, no new
  problem (cosmetic: uneven wrap at line 33; the line-14 escalation examples are not exhaustive,
  and line 13 defers to the owning skill).
- `rules/review-policy.md:13` — "An Important finding enters a fix round" ignored the skills'
  escalation routes for Rule 4 findings and ambiguous gaps. Score 50 (advisory); fixed anyway in
  c692e81 because the same lines were being edited.
- `skills/correctness-review/prompts/shared.md:66` (also the intent and task reviewer Reads) —
  in an installed consumer the policy lives at `.claude/rules/review-policy.md`, and
  `deploy-harness.sh` `rewrite_derived_paths` does not rewrite `rules/` paths. Score 25
  (advisory). Pre-existing convention shared by every `rules/auto-correct-scope.md` Read; the
  inline style rule in `shared.md` still holds. Backlog: rewrite `rules/` paths at deploy, or
  verify `required_reads` paths in the derived tree.
- `scripts/test_check_task_review_contract.py:22-30` — negative test asserts only `main() == 1`.
  Score 0: the stripped line holds no other required token and the copied files pass, so only the
  new entry can fail. Optional hardening: assert the stderr message.
- `scripts/render_skill_prompt.py:105` — `required_reads` regex accepts any earlier "Read" on the
  same line. `unmodified-line`, score 0, advisory.
- `scripts/render_skill_prompt.py:119-126` — a non-object `review-config.json` raises a traceback
  instead of the intended diagnostic (exit is still non-zero). `unmodified-line`, score 0,
  advisory.

### Runtime Eval

Added after the PR was opened, at the user's request. Method, criteria (written before the full run),
results and limits: `specs/review-policy/runtime-eval.md`; per-call records:
`specs/review-policy/runtime-eval-results.json`. A/B of the real prompts, base `33d6ed4` against head
`f23e4ac`, `claude-opus-5-5` at medium effort, 116 first-run calls, about $10.9.

All seven pre-registered criteria passed: core catches 5/5 in both arms; bonus 2/2 in both; false positives
13 (base) against 12 (head), one at confidence ≥ 75 in each; parseable output 51/51 in both; the head arm Read
the policy in 56 of 56 calls that were told to; task review 6/7 (base) against 7/7 (head) with `checked_against`
present on 7/7 replies. Cost: +17% (one extra Read turn per call, replies about 11% longer). Correction: the
design's claim that the task reviewer has no behavioral fixture was wrong (fixtures and scorer exist, only the
runner ignores the real prompt); recorded in `runtime-eval.md`.

### Not auto-verified

- That a fresh reviewer applies the policy it is told to Read — reached truth for the covered contexts: in the runtime eval 56 of 56 head-arm finder, intent and task-reviewer calls Read `rules/review-policy.md` (`runtime-eval.md`). Not covered: the real `reviewer` / `task-reviewer` subagent environment and Codex contexts.
- That the rewrite keeps each reviewer's behavior — reached truth for the fixtures the eval covers (5/5 core and 2/2 bonus catches, 6/7 → 7/7 task-review fixtures, one first run per cell) and none (judgment) elsewhere: per-file meaning-equivalence review. Not covered: variance, defect classes not seeded in the 7 + 7 fixtures, the scorer stage, controller routing, and the policy's own do-not-report effect (no bait fixture).
- The runtime eval itself is not a repo Verify row: its driver lives in the session scratchpad (follow-up: promote it to `scripts/`), so its numbers are recorded in `runtime-eval.md` and `runtime-eval-results.json`, not re-runnable from the tree — reached provenance (answer-key scorers from the repo), not re-run.

### Rollback

- Revert the implementation commits: `git revert --no-edit 21dd815^..c692e81`; no data, config, or deployed copy changes (`.claude/` is not redeployed). The spec record under `specs/review-policy/` can stay as history.

### Harness-Delta

- backlog — the commit-gate lane-evidence check judges the on-disk SUMMARY for any commit that
  stages a `specs/<slug>/` path, and SC coverage requires every PLAN SC row to be covered. At
  planning time no SC can be covered, so design/research/PLAN cannot be committed before
  implementation; this run kept the spec record uncommitted until coverage was complete.
- backlog — in consumer installs, rules deploy to `.claude/rules/` but prompts Read `rules/<name>.md`
  and `deploy-harness.sh` `rewrite_derived_paths` does not rewrite `rules/` (correctness finding,
  score 25; same for every existing `rules/auto-correct-scope.md` Read).
- backlog — the worktree session guard refuses compound shell commands and inline scripts that
  mention git, so implementers ran each check separately; the controller added
  `.harness-state/sdd/wordcount.py` as a workaround for the per-task word budget.
