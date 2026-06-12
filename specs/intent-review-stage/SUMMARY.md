# intent-review-stage — Summary

Lane: high-risk
Confidence: high
Reason: Hard gate — diff sẽ chạm `templates/SUMMARY.template.md` (high-blast theo PROJECT.md, bị `ci-strict-gate.sh` bắt qua pattern `^templates/`) và thay đổi chính workflow chain (orchestration: "redefine the workflow itself" → escalate); hướng đi không mơ hồ — người dùng chỉ định đích danh giải pháp.
Flags: existing behavior, weak proof (skill prompt không có test tự động)
Affects: templates/SUMMARY.template.md (5-field schema + section mới), workflow chain (subagent-driven-development → finishing), skills/README.md handoff map, skills/feature-intake/SKILL.md (Step 6)
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Nguyên văn yêu cầu (2026-06-11): "sau khi hoàn thành xong thì có cách nào để thật sự kiểm tra
là cái kết quả đó đảm bảo đúng với intent ban đầu chứ ko chỉ là pass theo plan hoặc test" →
chốt phương án: "viết intake + plan cho intent-review stage này như một harness improvement
tiếp theo". Intent-review = oracle thứ ba (intent), độc lập với hai oracle hiện có (plan của
spec-review, runtime của correctness-review); reviewer cố tình MÙ PLAN.md, đối chiếu diff với
yêu cầu gốc nguyên văn + Success Criteria của design.md.

## What changed

Thêm oracle thứ ba `/intent-review` vào chuỗi review. Skill mới
(`skills/intent-review/SKILL.md` + `intent-reviewer-prompt.md`) đối chiếu diff cuối với request
gốc nguyên văn, cố tình mù PLAN.md; finding phân loại `gap`/`excess`/`drift` với routing
(fix-loop · escalate · report-only) + residual gate. Capture intent nguyên văn tại intake
(`templates/SUMMARY.template.md` có `### Intent`, `feature-intake` Step 6 ghi nó). Wire thành
stage bắt buộc trong `subagent-driven-development` sau correctness-review (overview + digraph +
section + red flags + example + prompt list). Cập nhật inventory/handoff/chain ở
`skills/README.md` + `CLAUDE.md`.

### Rationale

Gap đã được chẩn trong phiên 2026-06-11 (đối thoại sau `docs/research-harness-req-assessment.md`):
chuỗi oracle hiện tại validate code↔plan và code↔runtime nhưng không có gate nào validate
kết-quả↔intent sau hoàn thành; nếu intake hiểu sai intent, toàn chuỗi pass nhất quán mà vẫn sai.
Hard gate (templates/ + workflow) đã được người dùng authorize trực tiếp bằng yêu cầu đích danh
— thỏa điều kiện "human narrowing scope" nên không cần escalate thêm.

### Alternatives considered

- Phase-level UAT / TEST_MATRIX-from-design / PR-body intent map (mục 2–4 của phân tích) —
  defer: bổ trợ chứ không thay thế oracle thứ ba; làm sau khi stage này chạy thật.
- Nhét intent-check vào correctness-review thay vì skill riêng — bị loại: trộn hai oracle
  (runtime vs intent) vào một reviewer làm mất tính mù-lẫn-nhau, và correctness-review được
  thiết kế "bug-only".
- Bỏ qua design.md, chỉ dùng request nguyên văn — bị loại một nửa: request nguyên văn là oracle
  chính (luôn có sau thay đổi này), design.md Success Criteria là oracle phụ khi tồn tại.

### Deviations

- Dogfood Finding #2 fix (gap) — committed `specs/intent-review-stage/` (PLAN.md + this SUMMARY)
  to the branch. The intake+plan deliverable existed on disk but was untracked (`??`); the intent
  reviewer caught it because the two existing oracles (spec/correctness) never inspect repo
  tracking state. Routed fix-loop → resolved in the Wave 3 commit.

### Intent Findings

<!-- Dogfood: /intent-review run standalone on this plan's own diff (BASE=f7d2d58, before wave 1).
     Oracle = the ### Intent block above. Reviewer was a fresh subagent (sonnet), blind to PLAN.md.
     First real smoke test of the stage — it reviewed its own diff. -->

- **#2 `gap` — FIXED.** `specs/intent-review-stage/` was untracked; the plan is the explicit
  co-deliverable of "viết intake + plan". Committed in Wave 3. (Real catch — exactly the class the
  third oracle exists for.)
- **#1 `drift` / #3 `excess` — advisory, resolved by authorization on record.** The reviewer read
  the intent as "viết intake + plan" and flagged shipping the full implementation as drift/excess.
  The full implementation **was authorized**: the user invoked `/executing-plans
  specs/intent-review-stage/PLAN.md` to execute this very plan — the reviewer is blind to that
  invocation (it only saw the plan-time `### Intent`). No code change needed; recorded here as the
  durable note the PR merger should see. Not escalated: authorization plainly exists.

  *Harness insight:* the intent oracle is captured at plan-authoring time ("write the plan") but
  the real intent at execution time is "execute the plan". The oracle can go stale between the two
  phases — see `### Harness-Delta`.

### Verify

<!-- Re-run by ci-strict-gate via verify_summary.py --check (diff touches templates/ → high-risk
     gate fires). Commands MUST be pipe-free: the parser splits table rows on `|`. -->

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Skill files + blind rule present (task 1.1) | `test -f skills/intent-review/SKILL.md && test -f skills/intent-review/intent-reviewer-prompt.md && grep -q "gap" skills/intent-review/SKILL.md && grep -qi "PLAN.md" skills/intent-review/intent-reviewer-prompt.md` | 0 | gap taxonomy + plan-blind rule |
| Intent captured at intake (task 1.2) | `grep -q "### Intent" templates/SUMMARY.template.md && grep -q "Intent" skills/feature-intake/SKILL.md` | 0 | oracle source |
| Stage wired ≥6 sites (task 2.1) | `test "$(grep -ci "intent[- ]review" skills/subagent-driven-development/SKILL.md)" -ge 6` | 0 | pipe-free count assert |
| Inventory/chain + doc-truth (task 2.2) | `bash scripts/lint-doc-truth.sh && grep -q "intent-review" skills/README.md && grep -q "intent-review" CLAUDE.md` | 0 | referenced paths exist |
| Ledger appended (task 3.1) | `grep -q "intent-review-stage" docs/harness-experimental/trust-metrics.md` | 0 | trust ledger row |

### Rollback

- `git revert <sha>` per-wave; không đụng settings.json/hooks nên revert sạch bằng git.

### Harness-Delta

- backlog (→ `/compound`) — **intent-oracle staleness.** The `### Intent` captured at intake is
  plan-authoring intent ("write the plan"); when execution is later authorized separately
  (`/executing-plans`), the oracle no longer reflects the live intent, so the intent reviewer
  flags the authorized implementation as drift/excess (dogfood #1/#3). Worth a follow-up: either
  re-capture/append intent at the execution handoff, or teach `/intent-review` to read the
  execution authorization (the `/executing-plans` invocation) alongside the intake `### Intent`.
- fix-direct — pre-existing drift noted (NOT fixed in this slug, out of scope): the comment atop
  `templates/SUMMARY.template.md` still says "five header fields" though there are six
  (Lane/Confidence/Reason/Flags/Affects/Input-type). Surfaced here per task 1.2; left for a
  dedicated touch so this diff stays surgical.
