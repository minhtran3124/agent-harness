# review-prompt-eval-tool — Summary

Lane: normal
Confidence: high
Reason: no manifest hard gate (a new script, new eval fixtures and docs; no hook, settings, template or workflow-engine path); flags existing behavior (a new fixture joins the set that `run-tests.sh` checks) and weak proof (the tool's value shows only on real model runs)
Flags: existing behavior, weak proof
Affects: scripts/ (new eval tool), evals/skills/review-chain/ (new fixtures, README)
Input-type: harness improvement
Route: using-git-worktrees → writing-plans (more than 3 steps and more than 2 files) → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/review-prompt-eval-tool/intent.md @ 0a5ac18b8f703c9e68c00f758a43c74b4118e851

"làm cả 3" — a reply to the three follow-ups listed at the end of the runtime eval report
(`specs/review-policy/runtime-eval.md`, §Follow-ups):

1. Promote the driver into a tested `scripts/` tool, so the A/B can be re-run on any later prompt change. Today it lives in the session scratchpad.
2. Add a style-and-generated-file bait fixture so the do-not-report list is measured.
3. A second attempt on the discordant cells (`minor-only`) if variance matters for a decision.

### Intake notes

- Q1–Q3 of the draft (tool name and shape, 5 further `minor-only` attempts per arm, bait fixtures carrying one
  real bug) were approved with the intent, so confidence is high.
- Branch `feat/review-prompt-eval-tool` cut from `sdlc` before the intent commit (`sdlc` is the shared
  integration branch; intent-draft-from-chat advisory A3). The PR targets `sdlc`.
- Artifacts by signal: a PLAN (more than 3 steps and more than 2 files). No design (one approach, no fork) and
  no separate research brief beyond the facts recorded in the PLAN's Global Constraints, which come from the
  runtime eval run in this session.
- The two other spec drafts in the main checkout (`specs/hook-deny-route-lines`, E2) and the stale untracked
  copy of `specs/review-policy` are not part of this slug.

## What changed

Added `scripts/run_review_prompt_eval.py`, a tested tool (`run` and `report`) that runs the real review prompts of two git revisions on the planted-defect fixtures under identical conditions: each arm's prompts are built from that revision's own files, calls run in a minimal Read-only environment with per-call and shared total budget caps, results are published atomically and never overwritten, and failed calls are kept apart from model outcomes. Added two `core: false` fixtures, `bait-style-naming` and `bait-generated-file`, that measure the review policy's do-not-report list. Documented both in the review-chain README (new section, fixture revision v5). Used the tool for a real run of 38 calls ($2.95): the bait fixtures and five more attempts on `minor-only`; see `real-run.md`.

### Rationale

The first runtime eval lived in a session scratchpad and could not be re-run when a review prompt changes again; one parameterized tool keeps the arm isolation, the first-run-only records and the cost caps that the first run needed. The bait fixtures give the policy's generated-file and style exclusions something to be measured against.

### Alternatives considered

- Extend `run_review_chain_eval.py`: rejected; it sends its own hardcoded prompt and is the scripted path for a different question.
- Keep the scratchpad driver and cite its results: rejected; not re-runnable by anyone else.
- Wire the tool into CI: rejected; it needs an authenticated client and costs money.

### Deviations

- Task 3.1 (the real run) was executed by the controller in the main loop instead of being dispatched: it spends model money and records evidence, and `rules/orchestration.md` keeps such main-loop work with the controller. The run is covered by a task review of the report against the recorded data.
- Rule 1, by implementers after task review: Task 1.1 atomic records, recorded job failures, shared budget cap, `--watch-path` in `meta.json`, billed cost kept on failures, failed calls reported apart (c9a8126, 339250c); Task 1.2 policy source cited in both `truth.md`, cancelled wording and narrower base-index terms in the answer keys (a075cbd); Task 2.1 README wording on files, exit codes, parse counts and the report link (9a047b5).

### Task review findings (Minor, rolled up)

- Task 1.2 (fixtures): the bait patterns are deliberately broad and bound to their file (`style` on
  `sales.py`; `version`, `html` on the generated files), so an unforeseen real finding on those files that uses
  such a word counts as a false positive, and a bait finding filed against the wrong file or with an empty `file`
  counts as `other`. Lockfile hashes and URLs are made-up fixture data. Known properties of how the answer keys
  measure, stated in each `truth.md`.
- Task 1.2: the first fix round left one over-long unwrapped line in `bait-style-naming/truth.md`; cosmetic.
- Task 1.2 review: the controller built the review package from a base that also held Task 1.1's commit, so the
  scope comparison listed the tool's two files; build each task's package from only that task's commits.

- Task 1.1 (tool, first review): five Minor findings, all fixed in c9a8126 and 339250c (atomic records via a
  temp file and `os.link`; a per-job exception becomes a recorded `rc: "error"` call and exit 1; guarded
  `permission_denials`; a retry test; the total cap seeded from recorded cost and re-checked before the retry;
  `--watch-path` stored in `meta.json`), then two more Minor findings fixed in the same way (billed cost kept on
  failed calls; `report` separates failed calls from model outcomes and names fixtures the scorer excluded).
- Task 1.1 (open, recorded): a stream-json `assistant` event whose `message` is not an object still raises in the
  tool's own parsing; that call becomes an `rc: "error"` record with cost 0 although it was billed. Very rare
  malformed-output case; a one-line `isinstance` guard would close it.
- Task 1.1 (open, recorded): `os.link` needs a filesystem with hard links (stated in `--help`); in-flight calls can
  exceed `--max-total-usd` by up to workers x `--max-call-usd` (stated in `--help`); a recorded `rc: "error"` call is
  permanent, retrying it needs a new `--attempt`; whether the CLI's `--max-budget-usd` is a hard per-call limit was
  not observed.

- Task 2.1 (README): five Minor findings; four fixed in 9a047b5 (the task fixture's three separate files, the exact
  conditions that make `run` exit 1, the parse-rate denominator, the report link as a Markdown link). The "116 calls
  cost about $10.9" figure is not checkable on this branch; the controller verified it from the first run's logs
  ($10.61 full run plus $0.30 pilot). `lint-doc-truth.sh` does not scan `evals/`, so the link to
  `specs/review-policy/runtime-eval.md` (absent until PR #288 merges) is not lint-checked.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| SC-1 check | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_run_review_prompt_eval.py` | 0 | 19 passed, no model call | SC-1 |
| SC-2 check | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_run_review_prompt_eval.py -k arms_are_isolated` | 0 | 1 test: the base arm never receives head-only text | SC-2 |
| SC-3 check | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_run_review_prompt_eval.py -k never_overwrites` | 0 | 1 test: a recorded result is never overwritten, a rerun makes no call | SC-3 |
| SC-4 check | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_run_review_prompt_eval.py -k budget_cap` | 0 | 1 test: the total cap stops new calls | SC-4 |
| SC-5 check | `python3 scripts/run_review_prompt_eval.py --help` | 0 | usage printed | SC-5 |
| SC-6 check | `python3 scripts/score_review_chain_eval.py --check-truth evals/skills/review-chain/fixtures` | 0 | answer keys OK with both bait fixtures | SC-6 |
| SC-7 check | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_score_review_chain_eval.py` | 0 | 117 passed (scorer and runner tests unchanged) | SC-7 |
| SC-8 check | `grep -q run_review_prompt_eval.py evals/skills/review-chain/README.md` | 0 | README documents the tool | SC-8 |
| SC-9 check | `grep -q bait-style-naming evals/skills/review-chain/README.md` | 0 | README records fixture revision v5 | SC-9 |
| SC-10 check | `grep -q max-total-usd evals/skills/review-chain/README.md` | 0 | README documents the budget cap | SC-10 |
| SC-11 check | `python3 -c "import json,sys;d=json.load(open('specs/review-prompt-eval-tool/real-run-results.json'));sys.exit(0 if len(d['records'])>=38 else 1)"` | 0 | 38 records (28 bait, 10 variance) | SC-11 |
| SC-12 check | `test -s specs/review-prompt-eval-tool/real-run.md` | 0 | report exists | SC-12 |
| SC-13 check | `python3 -c "import os,sys;d='evals/skills/review-chain/fixtures';sys.exit(0 if all(os.path.isfile(f'{d}/{n}/{f}') for n in ('bait-style-naming','bait-generated-file') for f in ('intent.md','diff.patch','truth.md','truth.json')) else 1)"` | 0 | four files in each bait directory | SC-13 |

### Not auto-verified

- That the tool's numbers describe the real `reviewer` and `task-reviewer` subagents — reached truth for the conditions the tool fixes (safe-mode, Read-only, diff-only fixtures); not covered: the real agent environment, a repository to explore, the scorer stage, controller routing, Codex.
- That each bait answer key catches every worded variant of a bait finding — reached traceability (a 21-case classification check without a model call); an unmatched bait finding counts as `other`.
- The real-run numbers in `real-run.md` are one run per cell and are not re-runnable from the tree without spending money — reached provenance (records kept, scored by the repo's own scorers); the variance check shows `minor-only` is noisy in both arms.
- The README link to `specs/review-policy/runtime-eval.md` and the policy source cited in the bait `truth.md` files resolve only after PR #288 merges — reached none; `lint-doc-truth.sh` does not scan `evals/`.

### Rollback

- `git revert --no-edit c7c34f6^..9a047b5` removes the tool, its tests, the two fixtures and the README changes; nothing else changes (no hook, rule, skill or agent was touched, `.claude/` is not redeployed). The spec record under `specs/review-prompt-eval-tool/` can stay as history.

### Harness-Delta

- backlog — `writing-plans` demands `design.md` and `research-brief.md`, while the artifact policy for the normal lane asks for neither unless a signal fires; this run followed the artifact policy and put the research facts in the PLAN's Global Constraints.
- backlog — the commit-gate lane-evidence check judges the whole slug's SUMMARY and requires every PLAN SC to be covered, so a planned spec cannot be committed before implementation; the spec record stayed uncommitted until the end again.
- backlog — the worktree session guard refuses compound commands, loops and inline scripts that mention git, and reads the word `eval` in a grep as a command; helpers had to live in files.
