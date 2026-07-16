# compound-ddr-improvements — Summary

Lane: normal
Confidence: high
Reason: harness improvement touching 2 skill-doc files (>1 file rules out tiny); no risk flags or hard gates fired — prose/skill-doc changes only, no hooks, scripts, or settings.
Flags: none
Affects: skills/compound (skill doc + decision-extractor subagent prompt)
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> "check link https://www.mattpeters.co.uk/blog/02-lets-talk-about-ddrs, đọc và review xem thử nó đang nói đến gì, có ảnh hưởng gì đến harness của chúng ta không?"

> "new branch and làm 3 cải tiến nhỏ đó luôn đi"

The "3 cải tiến nhỏ" refers to the three gaps identified in the DDR review earlier in the same conversation:
1. Thêm giới hạn độ dài (word budget) cho entries trong `docs/solutions/`
2. Dùng format Always/Never ✅/❌ cho các entry loại decision
3. Cho `/compound` tự động hút mục "Alternatives" từ `specs/<slug>/SUMMARY.md` lên knowledge base

## What changed

Adopted three information-density practices from Matt Peters' DDR (Design Decision Records) post into the `/compound` skill: (1) a word-budget/density guideline for `docs/solutions/` entries, (2) Always/Never ✅/❌ imperative-rule format guidance for decision-track content, (3) an explicit input source telling the Decision Extractor to harvest the `### Alternatives considered` section of the active `specs/<slug>/SUMMARY.md`.

### Rationale

`docs/solutions/` entries are loaded into agent context (via `session-knowledge.sh` and on-demand reads), so verbosity has a real context-window cost; imperative ✅/❌ rules are easier for agents to comply with than narrative rationale; and rejected alternatives recorded per-feature in SUMMARY.md were previously harvested only by judgment, not by an explicit step.

### Alternatives considered

- Enforce the word budget mechanically (lint/hook) — rejected as over-engineering for a guideline; prose guidance in the skill is the minimum change that captures the value.
- Add a new "Constraints & Rules" section to the decision-track template — rejected to avoid changing the template schema in two places (SKILL.md inline + `templates/decision-track.md`); instead the format guidance lives in the extractor prompt so rules land inside the existing `Decision & Rationale` section.

### Deviations

- Used a plain in-place branch (`git checkout -b`) instead of `/using-git-worktrees` for a normal-lane task — docs-only change on a clean tree; a worktree without deployed `.claude/` breaks the Skill tool (see agent memory), and there is no collision risk with other checked-out work.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Harness test suite incl. doc-truth lint | `bash scripts/run-tests.sh` | 0 | ALL GREEN — 173 passed, 1 skipped |

### Rollback

- `git revert <sha>`

### Harness-Delta

- backlog — `skills/finishing-a-development-branch/SKILL.md` Step 1b ("Update `CHANGELOG.md` + `VERSION` … commit these with the work") contradicts the event-sourced bookkeeping flow: `post-merge-maintenance.yml` inserts the CHANGELOG entry and bumps VERSION from the merged SUMMARY, so following Step 1b manually would duplicate both. Step 1b should be rewritten to defer to the post-merge bot.
