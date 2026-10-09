# gh-261-sdd-report-handoff — Summary

Lane: high-risk
Confidence: medium
Reason: workflow-engine hard gate — the fix edits the SDD dispatch prompts (`implementer-prompt.md`), `skills/subagent-driven-development/SKILL.md` and the always-on `rules/orchestration.md` subagent contract
Flags: workflow-engine, existing behavior
Affects: subagent-driven-development implementer → task-reviewer handoff; rules/orchestration.md "Subagent contract"
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> ok open issues cho
> """
> - Subagent không ghi được report vào .harness-state/sdd/, nên mình phải tự chép report của chúng.
> - Hook branch-isolation chặn ghi file ở thư mục gốc của scratchpad.
> - Ví dụ verify_summary.py --lint trong plan-format.md gọi một flag không tồn tại
> """

> sau đó fix #261 tiếp đi

Issue #261 (https://github.com/minhtran3124/agent-harness/issues/261): the SDD implementer handoff tells each implementer to write its report to `[IMPLEMENTER_REPORT_PATH]` under `.harness-state/sdd/`, but on the gh-258 run all four implementers were refused. The Write tool refused, and the Bash heredoc fallback was refused by the worktree-isolation check. The controller transcribed each inline report by hand. Target: decide which side owns the report file, either (a) the controller writes it from the implementer's inline return, or (b) subagents can write the path. Then make the prompts, SKILL and rule say so, and pin the contract with a test.

Confidence is `medium`: the goal is clear, but (a) and (b) are materially different designs. The documented default is (a), which #261 itself prefers: it does not depend on a runtime policy outside the harness, so it also holds on Codex. Brainstorming confirms the choice.

## What changed

The SDD implementer no longer tries to write its own report file, which the runtime refuses. `implementer-prompt.md` tells it to return the full structured report inline and not write a report file. The SDD `SKILL.md` makes the controller write it verbatim to `.harness-state/sdd/report-<task>.md` before each task review. The always-on `rules/orchestration.md` Subagent contract carries the details:
- a "transcribed by controller" header;
- fix-round reports appended under `## Fix round <n>`;
- `BLOCKED`/`NEEDS_CONTEXT` writes no file and removes a stale one;
- no recognisable status is treated as `NEEDS_CONTEXT`.

The task reviewer still receives `IMPLEMENTER_REPORT_PATH`. `tests/scripts/sdd-artifact-handoffs.test.sh` pins the contract with presence and absence checks. The backlog row is closed and the solution entry's guardrail is now `existing:`.

### Rationale

The refusal comes from the runtime ("Subagents should return findings as text"), so subagents cannot own the file. Having the controller own it keeps the reviewer contract, the artifact for re-review and `resume`, and the audit trail, and it is the guardrail already recorded in `docs/solutions/` after two prior occurrences (approach A, chosen by the user after a comparison).

### Alternatives considered

- B — drop the report file and paste the report into the reviewer prompt: rejected. It changes the reviewer contract and `check_task_review_contract.py`, breaks "never paste report contents into prompts", and loses the artifact for re-review and resume.
- Let subagents write the file: not viable, because the refusal is runtime policy.

### Deviations

- Rule 3: the full suite failed `scripts/test_audit_skill_prompts.py`. The SDD `SKILL.md` was already at the 600-word progressive-disclosure ceiling on `main`, and the new bullet took it to 646. The SKILL bullet now keeps only the core rule. The header, rewrite-after-fix and no-file-on-`BLOCKED`/`NEEDS_CONTEXT` details moved to the always-on `rules/orchestration.md` Subagent contract, departing from design §4.2's placement (behavior unchanged). Commit `974e686`.
- Rule 1: the task re-review noted that the moved details live only in `rules/orchestration.md`, which the Codex adapter does not load through `agents/PROJECT.md`. The SKILL bullet now names `rules/orchestration.md` by path (598 words). Commit `cf0567d`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 scripts/verify_summary.py --lane gh-261-sdd-report-handoff` | 0 | intake-time check only | |
| handoff presence/absence checks | `bash tests/scripts/sdd-artifact-handoffs.test.sh` | 0 | sdd-artifact-handoffs: passed | SC-1 |
| task-reviewer contract unchanged | `python3 scripts/check_task_review_contract.py` | 0 | task-review-contract: passed | SC-2 |
| isolated-prompt deliveries hold | `python3 scripts/render_skill_prompt.py --check-all` | 0 | all contracts present | SC-3 |
| backlog closed, guardrail existing, affects orchestration | `python3 -c "import sys;b=open('docs/harness-experimental/improvement-backlog.md').read();s=open('docs/solutions/harness/sdd-report-file-handoff-refused-for-subagents.md').read();sys.exit(0 if 'done (2026-10-09, gh-261)' in b and 'existing:' in s and 'proposed:' not in s and 'rules/orchestration.md' in s else 1)"` | 0 |  | SC-4 |
| INDEX matches a fresh rebuild (date line ignored) | `python3 -c "import subprocess,sys;n=subprocess.run([sys.executable,'scripts/rebuild_solution_index.py','--dry-run'],capture_output=True,text=True).stdout;f=open('docs/solutions/INDEX.md').read();k=lambda t:[l for l in t.splitlines() if not l.startswith('> Last updated')];sys.exit(0 if k(n)==k(f) else 1)"` | 0 |  | SC-5 |
| SKILL.md word ceiling | `python3 scripts/audit_skill_prompts.py --json` | 0 | SDD SKILL.md 600 words (ceiling 600) |  |
| `--check` ignores only the date; a real change still fails | `python3 -c "import subprocess,sys,tempfile,pathlib,re;r=pathlib.Path(tempfile.mkdtemp());d=r/'docs/solutions/a';d.mkdir(parents=True);(d/'x.md').write_text('---\nproblem_type: bug\nconfirmed_at: 2026-01-01\n---\n');s=['scripts/rebuild_solution_index.py','--root',str(r)];run=lambda *a:subprocess.run([sys.executable,*s,*a],capture_output=True).returncode;run();i=r/'docs/solutions/INDEX.md';i.write_text(re.sub(r'Last updated: \S+','Last updated: 2000-01-01',i.read_text()));a=run('--check');(d/'y.md').write_text('---\nproblem_type: bug\nconfirmed_at: 2026-02-01\n---\n');b=run('--check');sys.exit(0 if a==0 and b==1 else 1)"` | 0 | temp INDEX; date-only diff exit 0, added entry exit 1 | SC-6 |
| backlog row names where the guard landed | `python3 -c "import sys;b=[l for l in open('docs/harness-experimental/improvement-backlog.md') if 'sdd-report-file-handoff-refused-for-subagents' in l];sys.exit(0 if len(b)==1 and 'sdd-artifact-handoffs.test.sh' in b[0] else 1)"` | 0 | | SC-7 |
| solution INDEX current via plain `--check` | `python3 scripts/rebuild_solution_index.py --check` | 0 | INDEX.md is current | |

### Correctness Review

Range `b0d2a92..HEAD` (`.harness-state/sdd/package-branch.md`). Six FIND angles; 3 locations after dedup; one independent scorer each; threshold 75. No finding reached 75. All three scored 50. The user chose to fix all three, at `f7663b1`, and a focused re-check passed:
- `rules/orchestration.md:42` — fix-round handling. The report is now appended under `## Fix round <n>`; BLOCKED/NEEDS_CONTEXT removes a stale report; no status is treated as NEEDS_CONTEXT.
- `skills/subagent-driven-development/SKILL.md:56` — "Never paste … report contents" is now scoped "into prompts".
- `tests/scripts/sdd-artifact-handoffs.test.sh:15` — presence checks on `orchestration.md` for `report-<task>.md`, `transcribed by controller` and `## Fix round`. A mutation run proved they fail when the paragraph is deleted, and all three fail on `main`'s text.

Wave 2 (`1fce665..a2e533e`, `.harness-state/sdd/package-wave2.md`): the same six FIND angles; 2 locations after dedup; one independent scorer each; threshold 75. Neither reached 75, so neither was fixed:
- `rules/orchestration.md:47` scored 25. After a fix dispatch returns BLOCKED and a later one returns DONE, the rule does not say whether the fresh file is a first report or a `## Fix round <n>` section. No wrong status follows from it: either shape leaves one current status for the reviewer. Fixed anyway at the user's request (`bd461eb`): the fresh file is "written as a first report (the controller header, no `Fix round` heading, round numbering restarts)", and a new `grep -qF` pins that phrase. A focused re-check of `941553a..bd461eb` passed correctness, test and intent with no gap, drift or excess.
- `scripts/rebuild_solution_index.py:62` scored 5. An INDEX.md that is not UTF-8 or cannot be read makes `--check` crash with a traceback (still exit 1) instead of printing "stale". The same unguarded `read_text` was already there at `1fce665`.

### Advisory Findings

Wave 2 (`1fce665..a2e533e`, at the user's request) closed the three Minors below. The removal and no-status clauses are now pinned; `task-reviewer-prompt.md` names `## Fix round <n>` sections, with the latest round current; a fresh `report-<task>.md` follows any file-writing return after a removal (`93900ee`, `a2e533e`). The backlog Proposal cell now names where the guard landed.

Remaining Minors from the wave-2 task reviews, not fixed:
- `grep -qF 'Fix round'` on `task-reviewer-prompt.md` proves the text exists somewhere in the file, not that it sits inside the fenced dispatched prompt.
- `scripts/test_rebuild_solution_index.py` has a duplicate `import sys` that predates this branch.

Original list (now closed):
- The test does not pin the BLOCKED/NEEDS_CONTEXT removal clause or the no-status clause. Changing "removes" to "keeps" still passes. Suggested additions: `grep -qF 'removes any existing'` and `grep -qF 'no recognisable status'` on `rules/orchestration.md`.
- `task-reviewer-prompt.md` does not say a report may hold several `## Fix round` sections, or that the latest round's status is the current one.
- After a BLOCKED fix removes the report, the next `DONE` starts a fresh file. That is the natural reading, but it is not stated.

### Intent Findings

- Intent review (plan-blind) over `b0d2a92..ed7bade`: ✅ no gap, drift or excess. Clauses checked: option (a) chosen with no hybrid left; prompts, SKILL and rule all say so; the contract is pinned by a test; the original "mình phải tự chép report" complaint is addressed. SC-1..SC-5 are proven by Criterion rows.
- Wave 2 intent review (plan-blind) over `1fce665..a2e533e`: ✅ no divergence. Item 1 is covered: `--check` masks only the date, the count is still compared, and three tests cover it. Minors (a)–(d) are closed as asked.

### Context-Propagation Audit

**Result: PASS**, with one advisory. Search surface: `grep -rnI` for `IMPLEMENTER_REPORT_PATH`, `report-<task>`, `report file`, `harness-state/sdd`, `orchestration.md` over `skills/`, `rules/`, `agents/`, `adapters/`, `scripts/`, `tests/`, plus `adapters/codex/project/harness-instructions.md` and `agents/PROJECT.md`.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `implementer-prompt.md` Report Format ("do not write a report file") | implementer | subagent (isolated) | pasted (the dispatched prompt text) | `sdd-artifact-handoffs.test.sh` presence check |
| SDD `SKILL.md` bullet ("the controller writes it verbatim to `report-<task>.md`") | SDD controller | main | the skill body, loaded on invocation | `sdd-artifact-handoffs.test.sh` presence checks |
| `rules/orchestration.md` Subagent contract (header, rewrite after fix, no file on BLOCKED/NEEDS_CONTEXT) | SDD controller (Claude) | main | always-on rule (no `paths:` frontmatter) | `tests/scripts/rule-loading-tiers.test.sh` exit 0 |
| same | SDD controller (Codex advisory) | main | explicit path in the SKILL bullet (`per rules/orchestration.md`, `cf0567d`); Codex rules otherwise come from `agents/PROJECT.md`, which does not name `orchestration.md` | **Advisory:** the pointer is present, but Codex Reading it is not proven (traceability only) |
| `IMPLEMENTER_REPORT_PATH` input | task reviewer | subagent (isolated) | unchanged; the controller now fills the path | `check_task_review_contract.py` exit 0 |
| solution entry Guardrail `existing:` | planning / compound sessions | main | `docs/solutions/INDEX.md` plus the `session-knowledge.sh` pointer | SC-5 (INDEX matches rebuild) |

Wave 2 (`1fce665..a2e533e`): **PASS**. Search surface: `grep -rn` for `Fix round`, `starts a fresh`, `rebuild_solution_index` over `skills/`, `rules/`, `scripts/`, `tests/`, `hooks/`, `.github/`.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `task-reviewer-prompt.md` "latest round's status is the current one" | task reviewer | subagent (isolated) | pasted (the sentence is inside the dispatched fence) | `sdd-artifact-handoffs.test.sh` `Fix round` presence check |
| `rules/orchestration.md` removal / fresh-file / no-status clauses | SDD controller | main | always-on rule | `sdd-artifact-handoffs.test.sh` presence checks; `rule-loading-tiers.test.sh` exit 0 |
| `rebuild_solution_index.py --check` date mask | compound skill and consumer repos | main | `skills/compound/SKILL.md` runs the script; `deploy-harness.sh:50` lists it among the consumer scripts, so re-sync ships the fix | `test_rebuild_solution_index.py` (7 passed); SC-6 |

### Not auto-verified

- The controller copies the report verbatim. Judgment-tier: the "transcribed by controller" header marks where the file came from; nothing compares it to the implementer's return.
- A Codex controller reads `rules/orchestration.md` through the SKILL pointer. Traceability only: the pointer is present, and no Codex run was observed.

### Minor review findings

- Task 1.1 (`7523f0c`): an overlong SKILL.md line. Resolved by the fix-round rewrite (`974e686`, `cf0567d`).
- Task 1.2 (`6a36b3c`): the closed backlog row's Proposal cell still says "plus a context-propagation regression presence case". Left as the historical proposal; the solution entry's Guardrail says where the checks actually live.
- Task 1.1 fix round: the details split across SKILL.md and orchestration.md. Addressed by the explicit path pointer (`cf0567d`).

### Rollback

- Prose and contract-test change to the SDD handoff; undo with `git revert -m 1 <merge-sha>` of the PR.
- Consumers that re-synced keep the new handoff text until their next re-sync after a revert. A locally edited protected file (`rules/orchestration.md` is not bootstrap-owned; skills are synced) lands beside the incoming copy as `.harness-incoming`.

### Harness-Delta

- fix-direct (wave 2, `547a493`, at the user's request): `scripts/rebuild_solution_index.py --check` also compared the `> Last updated:` date, so on `main` it reports "INDEX.md is stale" any day after the last rebuild, even when every entry is current (observed 2026-10-09: the only diff was the date). This PR's SC-5 compares everything except that line. `--check` now masks only that date and still compares the entry count; three pytest cases pin it.
