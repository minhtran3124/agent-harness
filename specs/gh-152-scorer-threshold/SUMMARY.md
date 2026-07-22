# gh-152-scorer-threshold — Summary

Lane: normal
Confidence: high
Reason: Changes existing documented review-gate behavior in prompt Markdown with no deterministic test coverage (flags 8, 9); no hard gate — skills/ Markdown is not in the manifest high-blast set.
Flags: existing-behavior, weak-proof
Affects: skills/correctness-review (SCORE→THRESHOLD contract), skills/subagent-driven-development, skills/README.md
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> tao gh issue cho bug scorer first va new branch to fix it

(Context from the same conversation: the "bug scorer" is the defect surfaced in agent-harness issue #143 Phase 5 and filed as issue #152 — "scorer anchors are `0/25/50/75/100` while the default threshold is `80`, so 'highly confident' 75 can never enter the fix loop." The user then replied "approved" to the proposal: "tiến hành fix trên branch này" — fix issue #152 on branch `fix/scorer-threshold-152` by lowering the default threshold to 75, preserving the never-≤50 floor rule.)

## What changed

Lowered the correctness-review fix-loop threshold from 80 to 75 in every consumer, so the discrete anchor "75 — Highly confident" can actually enter the fix-loop. Consumer sweep found five files, not the four listed in issue #152: `skills/correctness-review/{SKILL.md, correctness-scorer-prompt.md, correctness-reviewer-prompt.md}` plus `skills/README.md` and `skills/subagent-driven-development/SKILL.md`. The never-≤50 floor rule is preserved unchanged.

### Rationale

Option 1 from issue #152 (lower threshold to 75) is the smallest diff that makes the anchor set and threshold mutually consistent — the rubric already defines 75 as "real and will be hit in normal usage", so admitting it to the fix-loop aligns the mechanism with its own written semantics. Continuous scoring (option 2) or re-anchoring (option 3) would change the scorer contract itself.

### Alternatives considered

- Continuous 0–100 scores with threshold 80 — larger contract change, needs re-benchmarking of the scorer prompt (issue #143 Phase 5 territory).
- Revised anchors so one sits at/above 80 — same cost, no added benefit over aligning at 75.

### Deviations

- Rule 2 (consistency): issue #152 listed four threshold references; a repo-wide grep found two more consumers (`skills/README.md:119`, `skills/subagent-driven-development/SKILL.md:172`) — updated them too so no inline copy drifts from the source of truth.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| No stale pipeline threshold | `sh -c '! grep -rn "THRESHOLD(80)" skills/'` | 0 | zero remaining pipeline references |
| No stale prose threshold | `sh -c '! grep -rn "threshold 80" skills/'` | 0 | zero remaining prose references |
| New default present | `grep -cq "default \*\*75\*\*" skills/correctness-review/correctness-scorer-prompt.md` | 0 | scorer prompt states default 75 |
| Doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | paths + hook table consistent |

### Rollback

- `git revert <sha>` (single commit on `fix/scorer-threshold-152`)

### Harness-Delta

- backlog: issue #152's own consumer list was incomplete (4 of 6 references) — live demonstration of the #143 Phase 2 consumer-audit gap; noted on the issue rather than duplicated here.
