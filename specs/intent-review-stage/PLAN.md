---
slug: intent-review-stage
status: active
owner: Minh Tran
created: 2026-06-11
---

# Intent Review Stage

> **For Claude:** REQUIRED SUB-SKILL: Use subagent-driven-development (hoặc executing-plans ở
> session song song) để thực thi plan này task-by-task.

**Goal:** Thêm oracle thứ ba vào chuỗi review — `/intent-review` đối chiếu diff cuối với **intent
gốc nguyên văn** (cố tình mù PLAN.md), để bắt trường hợp "pass plan + pass test nhưng không phải
thứ người dùng xin".

**Architecture:** Skill mới theo đúng khuôn `correctness-review` (skill mỏng + prompt template +
hai entry point standalone/in-flow + residual gate), lắp vào `subagent-driven-development` SAU
correctness-review, TRƯỚC `finishing-a-development-branch`. Oracle input được bảo đảm tồn tại
bằng cách capture request nguyên văn vào `### Intent` của SUMMARY ngay tại intake. Ba oracle mù
lẫn nhau: spec-review (oracle=PLAN) · correctness-review (oracle=runtime, mù plan) ·
intent-review (oracle=intent, mù plan).

**Tech Stack:** Markdown skills (khuôn `skills/correctness-review/`), không hook/settings mới,
doc-truth lint giữ đồng bộ README/CLAUDE.md.

---

## 1. Motivation

Chuỗi review hiện tại có hai oracle: spec reviewer hỏi "khớp PLAN không?", correctness reviewer
hỏi "runtime có sai không?" (mù plan). Không gate nào hỏi "người yêu cầu có nhận ra đây là thứ
họ xin không?" — nếu intake/design hiểu lệch intent, mọi tầng pass nhất quán mà kết quả vẫn sai
(Goodhart: `<verify>` do chính plan-author viết, chỉ đo cái plan nghĩ là quan trọng). Gate người
duy nhất sau implementation là merge PR, nhưng không có artifact nào giúp người merge đối chiếu
theo intent. Gap này được chẩn trong phiên 2026-06-11 (xem `### Intent` và `### Rationale` của
`specs/intent-review-stage/SUMMARY.md`).

## 2. Non-goals

- **KHÔNG** làm phase-level UAT/Acceptance section trong PLAN template, TEST_MATRIX-from-design,
  PR-body intent map — các mục bổ trợ, defer sau khi stage này chạy thật ≥1 lần.
- **KHÔNG** thêm hook/settings mới — stage này là skill prompt + wiring docs, không có gate máy.
- **KHÔNG** sửa correctness-review — hai oracle giữ tách bạch, không trộn.
- **KHÔNG** auto-xoá "excess" (code thừa ngoài intent) — xoá chức năng là Rule-4; excess chỉ
  được report + cần người duyệt.

## 3. Success Criteria

1. `/intent-review` invokable standalone trên diff bất kỳ; và là stage bắt buộc trong
   `subagent-driven-development` (digraph + Red Flags + prompt list đều phản ánh).
2. Mọi intake mới capture request nguyên văn: `templates/SUMMARY.template.md` có `### Intent`,
   `feature-intake` Step 6 ghi nó.
3. Taxonomy finding `gap / excess / drift` với routing rõ (fix-loop vs escalate vs report-only)
   + residual gate (mọi finding: fixed-có-sha hoặc ghi bền) — documented trong SKILL.md.
4. Reviewer prompt cấm đọc PLAN.md/research-brief.md một cách tường minh (mù plan).
5. `bash scripts/lint-doc-truth.sh` xanh (README/CLAUDE.md tham chiếu path mới tồn tại);
   `bash scripts/run-tests.sh` xanh — gate chính thức là CI (settings-wiring local đỏ cho tới
   khi human deploy sync, đã ghi nhận từ plan trước).
6. PR của plan này tự pass `ci-strict-gate.sh` (diff chạm `^templates/` → SUMMARY lane
   high-risk + Verify rows thật — dogfood chính gate vừa build).

## 4. Tasks

### Wave 1 — Skill mới + capture intent (2 task song song, file disjoint)

#### Task 1.1 — Skill `/intent-review`: SKILL.md + reviewer prompt

```xml
<task id="1.1" wave="1">
  <files>skills/intent-review/SKILL.md, skills/intent-review/intent-reviewer-prompt.md</files>
  <action>Viết skill mới theo đúng khuôn skills/correctness-review/ (frontmatter name +
  description; hai entry point; pipeline; residual gate; relationship section). Nội dung bắt
  buộc: (1) Oracle input — đọc `### Intent` từ specs/SLUG/SUMMARY.md (request nguyên văn) +
  Success Criteria của specs/SLUG/design.md NẾU tồn tại; nếu cả hai vắng → DỪNG, yêu cầu người
  cung cấp intent (không tự suy diễn từ plan). (2) Blind rule — reviewer KHÔNG được đọc PLAN.md
  / research-brief.md; lý do ghi rõ: đối xứng với correctness-review mù plan để bắt bug,
  intent-review mù plan để bắt drift. (3) Dispatch — một reviewer subagent fresh-context
  (intent-reviewer-prompt.md), nhận: intent oracle + diff đầy đủ (BASE=trước task 1,
  HEAD=hiện tại, hoặc range người dùng nêu khi standalone) + danh sách file touched. Model:
  khác implementer (ensemble diversity, theo nếp correctness-review). (4) Taxonomy + routing —
  `gap` (intent xin, chưa ship): rõ ràng + trong scope → implementer fix-loop → re-review;
  mơ hồ → ESCALATIONS.md. `drift` (ship khác cách intent mô tả): hành vi tương đương → ghi
  nhận advisory kèm giải thích; khác hành vi → fix-loop hoặc escalate như gap. `excess` (ship
  thứ không ai xin): report-only, removal cần người duyệt (Rule-4: removing functionality).
  (5) Residual gate — trước khi báo done: mọi finding fixed-có-sha hoặc ghi bền (SUMMARY
  `### Intent Findings` / ESCALATIONS.md); thiếu là hard block. (6) Relationship — bảng so với
  spec-review/correctness-review/code-review (3 oracle mù lẫn nhau). Prompt template: cấu trúc
  theo correctness-reviewer-prompt.md — vai trò, input block, blind rules, output format (bảng
  verdict: finding | loại | bằng chứng trong diff | câu trích intent bị vi phạm | đề xuất
  route), yêu cầu trích NGUYÊN VĂN câu intent cho mỗi finding (chống reviewer tự bịa intent).
  Khác biệt CÓ CHỦ ĐÍCH so với khuôn correctness-review: KHÔNG có SCORE/THRESHOLD stage và
  KHÔNG tạo scorer prompt — routing theo taxonomy gap/excess/drift thay cho scoring; đừng
  clone máy móc score/threshold từ khuôn.</action>
  <verify>test -f skills/intent-review/SKILL.md && test -f skills/intent-review/intent-reviewer-prompt.md && grep -q "gap" skills/intent-review/SKILL.md && grep -qi "PLAN.md" skills/intent-review/intent-reviewer-prompt.md</verify>
  <done>Skill đầy đủ 6 thành phần, prompt có blind rule + output format; chưa wire vào đâu (wave 2)</done>
</task>
```

#### Task 1.2 — Capture intent nguyên văn tại intake

```xml
<task id="1.2" wave="1">
  <files>templates/SUMMARY.template.md, skills/feature-intake/SKILL.md</files>
  <action>(a) templates/SUMMARY.template.md: thêm section `### Intent` ngay sau header block
  (trước `## What changed`), comment hướng dẫn: "request NGUYÊN VĂN của người dùng tại intake —
  KHÔNG paraphrase, không tóm tắt; đây là oracle của /intent-review; nếu request qua nhiều
  lượt hội thoại, trích các câu chốt scope theo thứ tự thời gian". KHÔNG đổi header block
  (6 dòng: Lane/Confidence/Reason/Flags/Affects/Input-type) — section mới nằm ngoài vùng grep
  của risk-corroboration/ledger. Lưu ý pre-existing drift (mention, không sửa trong task này):
  comment đầu template vẫn nói "five header fields" dù đã 6 — báo lại trong summary. (b) skills/feature-intake/SKILL.md: Step 6 thêm chỉ thị ghi
  `### Intent` với request nguyên văn vào SUMMARY (một dòng trong khối emit + một câu giải
  thích "oracle cho /intent-review ở cuối workflow"). Lưu ý thực thi: diff task này chạm
  templates/ → ci-strict-gate sẽ yêu cầu SUMMARY của slug này có Lane: high-risk + Verify
  thật — đã thỏa (specs/intent-review-stage/SUMMARY.md).</action>
  <verify>grep -q "### Intent" templates/SUMMARY.template.md && grep -q "Intent" skills/feature-intake/SKILL.md</verify>
  <done>Mọi intake mới tự sinh oracle cho intent-review; header machine-read không đổi</done>
</task>
```

### Wave 2 — Wiring vào workflow (2 task song song, file disjoint; sau wave 1 vì doc-truth lint check path tồn tại)

#### Task 2.1 — Lắp stage vào `subagent-driven-development`

```xml
<task id="2.1" wave="2">
  <files>skills/subagent-driven-development/SKILL.md</files>
  <action>Cập nhật 4 chỗ, giữ nguyên văn phong tài liệu: (1) câu mở đầu Overview: chuỗi final
  trở thành "...final adversarial correctness review, THEN one intent review against the
  original request, before shipping". (2) Process digraph: sau node "Correctness reviewer finds
  bugs?" nhánh "no" → node mới "Run /intent-review (oracle: SUMMARY ### Intent + design.md;
  blind to PLAN)" → diamond "Intent findings?" → yes: "Implementer fixes gaps / escalate per
  routing" (vòng về re-review) → no: "Use finishing-a-development-branch". (3) Section mới
  ngắn "Final Intent Review" sau "Final Adversarial Correctness Review": delegate sang
  /intent-review, KHÔNG re-implement pipeline; nêu range + lý do tồn tại (3 oracle mù lẫn
  nhau). (4) Red Flags thêm: "Skip the intent review, or hand off with unrouted intent
  findings" và "Run intent review with the implementer's context (must be fresh subagent,
  blind to PLAN.md)". (5) Example Workflow (dòng ~285–297): cập nhật đoạn kể chuyện cuối —
  sau correctness review thêm bước intent review trước khi "Hand off to
  finishing-a-development-branch" (nếu không sẽ mâu thuẫn digraph mới). Prompt Templates list:
  thêm dòng trỏ sang skills/intent-review/. Lưu ý: file này KHÔNG được lint-doc-truth quét —
  verify grep là check duy nhất, nên dùng case-insensitive + đếm đủ 5 site.</action>
  <verify>grep -ci "intent[- ]review" skills/subagent-driven-development/SKILL.md | awk '{exit ($1>=6)?0:1}'</verify>
  <done>Stage là bắt buộc trong flow: overview + digraph + section + red flags + example + prompt list đều phản ánh</done>
</task>
```

#### Task 2.2 — Cập nhật inventory + handoff map + workflow chain

```xml
<task id="2.2" wave="2">
  <files>skills/README.md, CLAUDE.md</files>
  <action>(a) skills/README.md: bảng "Review & Shipping" thêm dòng `/intent-review` (Trigger:
  sau correctness-review — đối chiếu diff với intent gốc, mù PLAN; Standalone trên diff bất kỳ
  khi có intent statement; Output: verdict gap/excess/drift → fix hoặc escalation). Handoff map:
  sửa dòng subagent-driven-development thành `→ /correctness-review → /intent-review → /compound
  → /finishing-a-development-branch`, thêm dòng `/intent-review ──► (standalone — cùng pipeline,
  cần ### Intent trong SUMMARY hoặc intent do người cung cấp)`. Full Cycle diagram: chèn bước
  sau correctness-review. (b) CLAUDE.md: Skill Workflow chain sửa thành `... →
  correctness-review (final adversarial pass) → intent-review (kết quả ↔ intent gốc, mù plan)
  → compound → finishing-a-development-branch`. Chạy lint-doc-truth sau khi sửa — mọi path
  tham chiếu phải tồn tại (wave 1 đã tạo).</action>
  <verify>bash scripts/lint-doc-truth.sh && grep -q "intent-review" skills/README.md && grep -q "intent-review" CLAUDE.md</verify>
  <done>Inventory/handoff/chain nhất quán 3 nơi; doc-truth lint xanh</done>
</task>
```

### Wave 3 — Kiểm chứng chéo + dogfood

#### Task 3.1 — Consistency sweep + chạy stage lên chính diff của plan này

```xml
<task id="3.1" wave="3">
  <files>specs/intent-review-stage/SUMMARY.md, docs/harness-experimental/trust-metrics.md</files>
  <action>(a) Chạy full suite (`bash scripts/run-tests.sh`) — chấp nhận settings-wiring local
  red đã biết (pre-deploy, CI là gate); mọi check khác phải xanh. (b) DOGFOOD: invoke
  /intent-review standalone lên chính diff của plan này (BASE=trước wave 1), oracle = `### Intent`
  của specs/intent-review-stage/SUMMARY.md — stage mới phải tự review được chính nó (smoke test
  thật đầu tiên: liệu diff có ship đúng "oracle thứ ba, mù plan, đối chiếu intent" như intent
  mô tả?). (c) Ghi kết quả dogfood + mọi finding vào SUMMARY (`### Verify` rows pipe-free +
  `### Intent Findings` nếu có); finding loại gap/drift → fix ngay trong wave này theo routing
  của chính skill. (d) Append dòng ledger docs/harness-experimental/trust-metrics.md theo
  schema 9 cột hiện hành (Affects = templates/SUMMARY.template.md + workflow chain). Lưu ý
  (c): các Verify row ghi vào SUMMARY phải RE-RUNNABLE trên CI — ci-strict-gate chạy lại chúng
  qua verify_summary.py --check, không phải chỉ là record.</action>
  <verify>grep -q "dogfood" specs/intent-review-stage/SUMMARY.md && grep -q "intent-review-stage" docs/harness-experimental/trust-metrics.md && bash scripts/lint-doc-truth.sh</verify>
  <done>Stage được kiểm chứng bằng chính nó trên diff thật; SUMMARY có evidence + ledger có dòng mới</done>
</task>
```

## 5. Risks

| Risk | Mitigation |
|---|---|
| Reviewer "mù plan" nhưng intent statement quá mỏng → verdict vô dụng hoặc bịa intent | Prompt bắt buộc trích NGUYÊN VĂN câu intent cho mỗi finding; oracle vắng → DỪNG hỏi người, không suy diễn từ plan |
| Intent-review thành rubber-stamp (luôn ✅ vì "có vẻ khớp") | Khuôn adversarial như correctness-review: mặc định giả định ≥1 lệch tồn tại; taxonomy 3 loại ép reviewer tìm theo từng trục; dogfood task 3.1 là canary đầu tiên |
| Stage mới làm chuỗi dài thêm với task tiny/normal không có design.md | Oracle chính là `### Intent` (luôn có sau task 1.2) — không yêu cầu design.md; stage chỉ bắt buộc trong subagent-driven-development (normal/high-risk), tiny lane không qua chuỗi này |
| `templates/` diff trip ci-strict-gate trên PR | Chủ đích (dogfood gate mới): SUMMARY slug này đã ở lane high-risk + sẽ có Verify rows thật trước khi PR |
| Hai oracle cho cùng câu hỏi khi design.md tồn tại (Intent vs Success Criteria lệch nhau) | SKILL.md quy định thứ bậc: request nguyên văn thắng; lệch giữa hai oracle là một finding loại drift phải escalate (tín hiệu design đã lệch intent từ đầu) |

## 6. Status Log

- 2026-06-11 — Plan created (intake: Lane high-risk — hard gate templates/ + workflow redefine,
  Confidence high — giải pháp do người dùng chỉ định đích danh; brainstorming skip: không có
  design fork, phương án đã chốt trong hội thoại).
