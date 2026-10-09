# gh-263-plan-format-lint-example — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate — the fix edits `rules/plan-format.md`, a rule that writing-plans and the plan reviewer Read before authoring and reviewing Success Criteria
Flags: workflow-engine
Affects: rules/plan-format.md (Success Criteria schema example)
Input-type: maintenance
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

> fix #263 trước đi

Issue #263 (https://github.com/minhtran3124/agent-harness/issues/263): the fenced Success Criteria example in `rules/plan-format.md` (lines 99–100 on `main`) uses `python3 scripts/verify_summary.py --lint specs/<slug>`, which exits 2 ("unrecognized arguments: --lint"), not the `exit 1` / `exit 0` its Expected cells claim. Target: replace it with a command that exists and behaves as the Expected column says. The issue marks extending a lint to catch this class as optional.

Confidence is `high`: observed at intake, `python3 scripts/check_plan_contract.py <PLAN.md>` exits 1 on a contract plan with no SC rows ("Success Criteria table has no SC rows") and 0 on a well-formed one, which matches the example's two Expected cells. The optional lint is a scope question for brainstorming, not an ambiguity in the fix.

## What changed

The fenced Success Criteria example in `rules/plan-format.md` now uses a command that exists: `python3 scripts/check_plan_contract.py specs/<slug>/PLAN.md`. The two rows read "A contract plan (one with a Global Constraints section) without SC rows is rejected" → `exit 1 — no SC rows`, and "A well-formed SC table passes the contract check" → `exit 0`. The old rows called `verify_summary.py --lint`, a flag that never existed, and exited 2.

### Rationale

`check_plan_contract.py` is the authority that rejects a contract plan without SC rows (exit 1, "Success Criteria table has no SC rows") and passes a well-formed one (exit 0). Both exit codes were measured, so the Expected cells hold. Deploy already rewrites its path to `.claude/scripts/` in consumer repos.

### Alternatives considered

- Add a `--lint` flag to `verify_summary.py`: rejected, because it would invent an interface to match a wrong doc.
- Add a test pinning this example: declined by the user (scope: fix the example only).
- Add a general lint of fenced `scripts/*.py` flags against `--help`: declined by the user; #263 marks it optional.

### Deviations

- Rule 1 — Correctness review found that the first SC-1 Behavior wording contained the literal `## Global Constraints`. `check_plan_contract.py` opts a plan into the contract on that raw substring before masking fences, so a legacy plan that copied the row exited 1. Reworded in `rules/plan-format.md` (and the design §4 / plan Action text to match). The same plan now exits 0. Commit `ff8ead1`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 scripts/verify_summary.py --lane gh-263-plan-format-lint-example` | 0 | intake-time check only | |
| bad --lint flag removed | `grep -qF 'verify_summary.py --lint' rules/plan-format.md` | 1 | no match | SC-1 |
| both rows call check_plan_contract.py with the design §4 text | `python3 -c "import sys;t=open('rules/plan-format.md').read();sys.exit(0 if t.count('python3 scripts/check_plan_contract.py specs/<slug>/PLAN.md')==2 and all(x in t for x in ['without SC rows is rejected','A well-formed SC table passes the contract check','exit 1 — no SC rows']) else 1)"` | 0 | count 2, texts present | SC-2 |
| example's command exits 1 (no SC rows) / 0 (well-formed) | `python3 -c "import subprocess,sys,tempfile,os;B=chr(124);T=chr(96);R=lambda c:B+B.join(c)+B;g='## Global Constraints\n\n- Safe\n\n';s='## 3. Success Criteria\n\n'+R([' ID ',' B ',' C ',' E '])+'\n'+R([' --- ']*4)+'\n'+R([' SC-1 ',' w ',' true ',' exit 0 '])+'\n\n';t='## 4. Tasks\n\n### Task 1.1 - x\n\n- **Files:** x\n- **Action:** x\n- **Verify:** true\n- **Done:** x\n- **Criteria:** SC-1\n- **Interfaces:** Consumes: input. Produces: '+T+'o.py'+T+'.\n';d=tempfile.mkdtemp();p=lambda n,x:(open(os.path.join(d,n),'w').write(x),os.path.join(d,n))[1];r=lambda f:subprocess.run([sys.executable,'scripts/check_plan_contract.py',f],capture_output=True,text=True);a=r(p('bad.md',g+t));b=r(p('ok.md',g+s+t));sys.exit(0 if a.returncode==1 and 'Success Criteria table has no SC rows' in a.stderr and b.returncode==0 else 1)"` | 0 | temp fixtures; cause string asserted | SC-3 |

### Not auto-verified

- An author who copies the example gets a working SC row. Tier reached: provenance only. The command and both exit codes were re-run on fixtures (SC-3), and a legacy plan containing the copied row was shown to stay legacy. No real plan authored from the example was observed.

### Context-Propagation Audit

**Result: PASS.** The change edits content inside one fenced example of `rules/plan-format.md`, not how the rule is delivered. Its consumers, all with explicit Reads registered in `scripts/render_skill_prompt.py` `CONTEXT_MATRIX`, are: writing-plans (`main.plan-author`), the plan document reviewer (`plan-document-reviewer`), the SDD controller (`main.plan-executor`) and resume (`references/resume.md`). Every consumer gets the whole file, so the corrected example reaches all of them. The rule's `paths: specs/**/PLAN.md` frontmatter is unchanged. Proof: `python3 scripts/render_skill_prompt.py --check-all` → "all contracts present" at `1c29222`. Search surface: `grep -rn 'rules/plan-format.md'` over `scripts/render_skill_prompt.py`, `skills/writing-plans/`, `skills/subagent-driven-development/`.

### Correctness Review

Range `b0d2a92..HEAD` via `.harness-state/sdd/package-branch.md`. Six FIND angles; 4 locations after dedup; one independent scorer each; threshold 75. No finding reached 75.

- `rules/plan-format.md:99` — score 50. The new Behavior cell carried the `## Global Constraints` opt-in sentinel (5 of 6 angles; reproduced). **Fixed anyway at `ff8ead1`**: this diff introduced it, the fix is a one-cell reword on a line the PR already owns, and the user chose to fix cheap advisories on #258. Re-verified: a legacy plan containing the new row exits 0.

### Advisory Findings

- `scripts/check_plan_contract.py:51` — score 0 (`unmodified-line`). The opt-in test `"## Global Constraints" not in text` runs on raw text, before `mask_fences`, as a substring. Any mention of the string (prose, inline code or a fence) opts a legacy plan in; this is the gh-175 "mention flips the parse mode" pattern. Fix: `re.search(r"(?m)^## Global Constraints\s*$", mask_fences(text))`. Follow-up issue candidate.
- `scripts/check_plan_contract.py:112` — score 0 (`unmodified-line`). `args.plan.read_text()` does not catch `OSError`. A missing or mistyped path raises `FileNotFoundError` and exits 1, the same code as a real rejection, so an `exit 1` SC row passes vacuously. Fix: catch `OSError` and return 2. Follow-up issue candidate.
- `rules/plan-format.md:100` — score 25. "A well-formed SC table passes" understates what exit 0 means: the whole contract must hold, and a legacy plan with no SC table also exits 0. Both rows also share one command and path. This illustration shape existed before the diff; left as is.

### Intent Findings

- Intent review (plan-blind) over `b0d2a92..HEAD`: ✅ no gap, drift or excess. Clauses checked: fix #263 with a working command whose Expected cells hold; the `--lint` call removed (repo-wide grep); scope limited to #263. SC-1..SC-3 each have a passing Criterion row.

### Minor review findings

- Task 1.1 (`1c29222`): the read-only task reviewer could not execute the checks. The controller re-ran them: SC-1 exit 1, SC-2 exit 0, SC-3 exit 0, and `bash scripts/run-tests.sh` ALL GREEN (799 passed).

### Rollback

- Prose-only change to one fenced example in `rules/plan-format.md`; undo with `git revert -m 1 <merge-sha>` of the PR.
- Consumers that re-synced keep the corrected example until their next re-sync after a revert; a locally edited `rules/plan-format.md` is kept and the incoming copy lands beside it as `.harness-incoming`.

### Harness-Delta

- none
