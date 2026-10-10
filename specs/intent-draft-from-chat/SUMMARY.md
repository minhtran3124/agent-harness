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

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| skill size baseline (intake) | `python3 scripts/audit_skill_prompts.py` | 0 | feature-intake SKILL.md at 599/600 words — new procedure must live in `references/` | |

### Not auto-verified

- Classification (lane/confidence) is a judgment at intake — traceability only.

### Rollback

- `git revert -m 1 <merge-sha>` of the PR merge into `sdlc`; prose/template only, no data or state migration. A consumer re-sync (`scripts/install-harness.sh`) after the revert restores the previous skill text.

### Harness-Delta

- none
