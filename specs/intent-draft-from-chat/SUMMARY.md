# intent-draft-from-chat — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate (changes skills/feature-intake procedure; likely templates/INTENT.template.md and docs); existing behavior (chat-only intake path changes)
Flags: existing behavior, workflow-engine
Affects: skills/feature-intake (intake entry path), templates/INTENT.template.md, intent-review oracle source
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

hiện tại thì với việc new feature mà user chỉ chat ko thì sẽ ko có file intent.md
hãy support việc là nếu user provide intent thông qua chat thì trigger việc AI model sẽ tự động viết intent.md theo format template + nội dung chat của user
sau đó yêu cầu user review và approve nếu đúng hoặc tự modify nếu thấy cần chỉnh sửa

### Intake notes

- Builds on PR #284 (intent.md entry, `specs/intent-md-entry/`): today a chat-only intake writes no intent.md and no `Intent-source:` line.
- Confidence high: one outcome — chat → AI drafts `specs/<slug>/intent.md` from the template → user reviews, then approves or edits. Open design choices for brainstorming (not competing readings): which lanes trigger a draft (tiny?), how approval is recorded (user edits `Status:` vs says "approved" in chat), who commits the draft, and how the AI-written draft relates to the verbatim chat oracle.
- Research depth handoff: high-risk → xia2 starts Deep; no external surface expected.

## What changed

<filled at completion>

### Rationale

<filled at completion>

### Alternatives considered

- none

### Deviations

- Plan review — added `Bash(git config user.name)` to feature-intake `allowed-tools` (design named only `git add`/`git commit`); needed for the design's `Author:` = git `user.name`. Exact-pattern grant.
- Task 1.2 — to fit the 600-word budget the implementer turned the Routes table into a list and tightened wording; task review confirmed no instruction lost.

### Task review findings (Minor, rolled up)

- 1.1: SC-10 not independently re-run by the reviewer (re-run in the full suite, ALL GREEN). Template comment's approval sentence did not mention auto-approval — fixed in 1380d38.
- 1.2: "When intake ran" weaker than "intake record exists"; "as in step 2" imprecise; "ask to commit the intent" ambiguous — all fixed in 1380d38.
- 1.3: IF-03/04/05/09 did not name the proposed lane/confidence; IF-13 not updated — fixed in 1380d38. Error-behavior rows without a canary (Author `unknown`, commit skip on no change, staged files excluded, hook refusal, `none — intent.md is the request` fallback) — not covered by canaries; see Not auto-verified.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| skill word budget | `python3 scripts/audit_skill_prompts.py` | 0 | feature-intake 599/600 words incl. frontmatter | SC-1 |
| allowed-tools line | `grep -qxF -- "allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git log *), Bash(git diff *), Bash(git branch --show-current), Bash(git switch -c *), Bash(git add -- specs/*), Bash(git commit -m *), Bash(git config user.name), Bash(ls *), Bash(python3 scripts/verify_summary.py *), Bash(python3 runtime/run_state.py *)" skills/feature-intake/SKILL.md` | 0 | | SC-2 |
| tool conformance | `python3 scripts/check_skill_tool_conformance.py` | 0 | all instructed commands permitted | SC-3 |
| draft pointer | `grep -qF -- "references/draft-intent.md" skills/feature-intake/SKILL.md` | 0 | | SC-4 |
| draft strings | `python3 -c "import sys;t=open('skills/feature-intake/references/draft-intent.md').read();sys.exit(0 if all(s in t for s in ['## Original request','(assumed)','git add -- specs/<slug>/intent.md','git commit -m \"docs(specs): intent for <slug>\" -- specs/<slug>/intent.md','auto-approved: tiny/high']) else 1)"` | 0 | | SC-5 |
| oracle wording | `grep -qF -- "auto-approved by intake" rules/terminology.md` | 0 | | SC-6 |
| template comment | `grep -qF -- "intake drafts" templates/INTENT.template.md` | 0 | | SC-7 |
| runtime-neutral | `python3 scripts/check_runtime_neutral_sources.py` | 0 | | SC-8 |
| skill bash lint | `bash scripts/lint-skill-bash.sh` | 0 | | SC-9 |
| doc truth | `bash scripts/lint-doc-truth.sh` | 0 | | SC-10 |
| canaries | `grep -qF -- "DI-08" skills/feature-intake/tests/intent-file-cases.md` | 0 | DI-01..DI-09 | SC-11 |
| old wording removed | `grep -qF -- "human-written intent" rules/terminology.md` | 1 | expected exit 1 | SC-12 |
| template header | `grep -qx -- "Author: <name>" templates/INTENT.template.md` | 0 | | SC-13 |
| legacy scoping | `grep -qF -- "legacy" skills/feature-intake/SKILL.md` | 0 | | SC-14 |

### Context-Propagation Audit

PASS (controller, main session, at f39accb). Search surface: `grep -rn -e "draft-intent" -e "never in .*intent.md" -e "human-written" -e "chat-only intake" -e "Intake notes" skills agents rules templates`; `grep -n "intent.md" skills/intent-review/*.md`.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `references/draft-intent.md` (two cases, commit, approved-wins) | feature-intake run | main session | explicit Read: SKILL.md Step 1 "follow `references/draft-intent.md`" | `skills/feature-intake/SKILL.md:19`; deployed at `.claude/skills/feature-intake/references/` (deploy 2026-10-10); real-install trial |
| SKILL.md Steps 1/5/6 (entry rule, legacy no-pin, `### Intent` sources) | feature-intake run | main session | always loaded with the skill | SKILL.md body |
| allowed-tools `git add`/`git commit`/`git config user.name` | feature-intake run | runtime permission | frontmatter | SC-2, SC-3; trial commits succeeded |
| `## Original request` inside intent.md | intent-review reviewer | fresh child | pasted: reviewer prompt INTENT input pastes the pinned intent.md text (which contains the section) | `skills/intent-review/intent-reviewer-prompt.md:44` |
| `rules/terminology.md` hard exclusion 1 (approved or auto-approved; drafts editable) | any agent touching `specs/**` | main + children reading specs | paths-triggered (`specs/**`) | rule frontmatter `paths:` |
| Template comment (two authoring paths) | drafting model | main session | explicit Read: draft-intent step 1 "from `templates/INTENT.template.md`" | `references/draft-intent.md:6` |
| "approved intent wins over `## Original request`" | re-pin (`references/re-pin.md` step 4) | main session | **not delivered** — re-pin re-classifies from intent.md plus the request in `### Intent` and is not told this rule | advisory: re-pin rules are out of scope (design Non-goals); a re-pin where the committed intent differs from the original request can still be read as a conflict, as in PR #284 today |

### Not auto-verified

- Classification (lane/confidence) is a judgment at intake — traceability only.
- Full suite `bash scripts/run-tests.sh` ended ALL GREEN after wave 1 — re-run, cited in prose (whole-suite rows are not allowed in `### Verify`).
- **Real install, 2026-10-10 — truth, one trial each.** `install-harness.sh --profile standard` from this branch into a fresh repo, then `claude -p "/feature-intake <slug> …"` (Claude Code 2.1.296, acceptEdits, scoped allowlist): (1) tiny/high README title → intent committed `(auto-approved: tiny/high)`, `Status: approved`, `## Original request`, SUMMARY pinned to the `git log` SHA, Intake notes `auto-approved: tiny/high`; (2) normal CSV export → draft, no SUMMARY, no commit; (3) then `approve` in a new run → intent committed, `### Intent` holds the original request (not "approve"); (4) high-risk rate-limit draft, then "change: 10 not 5" → draft edited, no commit; (5) legacy slug (SUMMARY, no intent) → no intent.md written; (6) a person's `Status: draft` intent on a tiny change → not auto-approved, unchanged, no commit; (7) user set `Status: approved` (uncommitted) and said `done` → committed, SUMMARY written; (8) a person's approved-but-uncommitted intent with an ordinary request → file byte-identical, no commit. 7/8 matched; (7) exposed a defect: the change in (4) left `## Original request` saying 5, so approval was read as a chat conflict (`low`, escalated). Fixed in f39accb (change replies append to `## Original request`; an approved intent wins over it); re-run of draft → change → approve on a normal slug: no escalation, `## Original request` holds both messages, lane `normal`. Not re-runnable from this repo (headless model runs).
- Canaries `skills/feature-intake/tests/intent-file-cases.md` are prose — traceability. Error-behavior rows without a canary or trial: `Author: unknown` when `user.name` is unset, commit skipped when nothing changed, other staged files excluded from the commit (git behavior probed separately: pathspec commit leaves other staged files staged), hook refusal → stop.

### Rollback

- `git revert -m 1 <merge-sha>` of the PR merge into `sdlc`; prose/template only, no data or state migration. A consumer re-sync (`scripts/install-harness.sh`) after the revert restores the previous skill text.

### Harness-Delta

- backlog — the worktree guard refuses heredocs or inline scripts whose text contains "git commit" (task 1.3 and 1.2 implementers, and the controller); every such edit had to run from a scratchpad script file. Recurring across PR #284 and this run.
