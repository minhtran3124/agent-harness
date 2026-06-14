# Plan khép khoảng trống harness — tổng hợp từ 6 nghiên cứu

> **Nguồn:** tổng hợp `research-openai-harness-engineering`, `research-claude-code-harness-comparison`,
> `research-repository-harness-ideas`, `research-compound-loop-closure`, `research-harness-req-assessment`,
> `research-agentic-engineering-roadmap`.
> **Ngày:** 2026-06-14.
> **Nguyên tắc xếp hạng:** số research docs cùng chỉ ra gap (đồng thuận = tin cậy) × đòn bẩy / công sức.
> **Lưu ý phạm vi:** mỗi item khi *thực thi* phải đi qua `/feature-intake` để gán lane. Item đụng
> high-blast (`settings.json`, `hooks/*`, `commit-quality-gate.sh`, `CLAUDE.md`) là **Rule-4** —
> cần người xác nhận trước (`rules/auto-correct-scope.md`).

---

## 0. Đã xong — không đưa vào plan (tránh lặp việc)

> **Đính chính 2026-06-14 (sau ground-truth check):** nhiều "gap" trong research đã được đóng giữa
> lúc research viết (06-08→06-13) và nay. Verify từng item trên đĩa trước khi implement.

Research từng nêu, nay đã giải quyết về cơ chế:

- ✅ **`not_observed != absent`** — đã có trong `rules/behavior.md §1` (comparison #3 coi là cần thêm; thực ra đã có).
- ✅ **Ledger `trust-metrics.md`** — đã build, committed, có ~9 dòng + cột `Affects` (IDEA-01 + một phần Q3 không còn vaporware).
- ✅ **`specs/` bỏ gitignore** — đã gỡ về cơ chế (chỉ còn việc commit lần đầu + sửa doc nói ngược — xem P2-G).
- ✅ **Doc-truth lint trong CI** (`scripts/lint-doc-truth.sh`) — đã bắt drift hook-table ↔ settings.json + phantom path refs.
- ✅ **P1-A `verify_summary.py` — XONG HẲN.** Script re-run `### Verify`, ghi đè Exit thật, `Verified:` timestamp, exit 1 on mismatch, `--check` mode; **đã wire** vào `commit-quality-gate.sh` (REQUIRE_VERIFY=1); có `test_verify_summary.py`. Dư địa duy nhất: default fail-open `REQUIRE_VERIFY=0` → thuộc P3-M.
- ✅ **P2-F SessionStart hook — XONG.** `hooks/session-knowledge.sh` đã wired (SessionStart), load `INDEX.md`+`critical-patterns.md`, silent khi store rỗng. Vòng tri thức đã khép ở tier "vừa" → research 06-08 (compound-loop-closure) **đã lỗi thời**.
- 🟡 **P1-B một phần** — `skills/compound/templates/failure-track.md` đã có mục `## Guardrail`. Còn thiếu phần tightening (xem P1-B bên dưới).

---

## 1. Bảng đồng thuận (gap × số research nêu)

| Gap | Research nêu | Đồng thuận | Đòn bẩy/Công sức | Rule-4? |
|---|---|---|---|---|
| **Proof là assertion, `### Verify` không re-run** | repo-harness IDEA-02, req #3, comparison #4 | 3 | Cao / Vừa | wiring có |
| **Ratchet chưa khép — `/compound` failure ra prose, không ra guardrail** | openai #3, repo-harness IDEA-05 | 2 | Cao / Vừa | không (sửa skill) |
| **"Verify the docs" — chưa có audit drift tự động** | openai #4, repo-harness IDEA-04/12, req #8 | 3 | Cao / Thấp | không (advisory) |
| **Review agent chưa read-only theo cấu trúc** | comparison #2 | 1 | Cao / Thấp | không |
| **Q3: không có registry contract; PROJECT.md placeholder** | req #1 (lỗ thiết kế duy nhất) | 1 | Cao / Vừa | không |
| **Vòng tri thức bán-khép — không SessionStart auto-load** | compound-loop (cả doc), req #4 | 2 | Vừa / Thấp | **có** (settings.json) |
| **MCP output bị coi là trusted** | openai #5 | 1 | Vừa / Thấp | nhẹ (CLAUDE.md) |
| **specs/ transition chưa hoàn tất (doc nói ngược)** | req #2/#6 | 1 | Vừa / Thấp | không |
| **Chưa có bằng chứng số: harness có hiệu quả không?** | comparison #1/#7 | 1 | Rất cao / Cao | không (thư mục mới) |
| **Lane→evidence mapping nhân bản 3 nơi** | repo-harness IDEA-10 | 1 | Vừa / Vừa | wiring có |
| **Story-sizing là guideline, không phải gate** | req #5/#7 | 1 | Vừa / Thấp | không |
| **Break-glass protected paths (Rule-4 chỉ prompt)** | comparison #5 | 1 | Vừa / Vừa | **có** (hook mới) |
| **Fail-open mặc định (REQUIRE_VERIFY=0, STRICT=0)** | req #4/#5 | 1 | Vừa / Thấp | **có** |
| **VERSION/CHANGELOG cho installer** | repo-harness IDEA-15, req #6 | 2 | Thấp / Thấp | không |
| **Hợp nhất bash gates thành 1 dispatcher + state ledger** | comparison #8/#9 | 1 | Cao / Rất cao | **có** (đại tu) |

---

## 2. Plan theo giai đoạn

> **Trạng thái thực thi 2026-06-14:** sau ground-truth, P1-A/P1-D/P2-F đã xong từ trước.
> P1-B và P1-C đã **thực thi xong trong phiên này** (✅ bên dưới). Test suite + lint-doc-truth xanh.

### Phase 1 — Quick wins, đồng thuận cao, ít/không Rule-4 (nên làm trước)

**P1-A · ✅ ĐÃ XONG TỪ TRƯỚC (xem mục 0) — `scripts/verify_summary.py` — biến proof từ assertion sang fact** *(IDEA-02, req #3, comparison #4)*
- **Gap:** cột `Exit` trong bảng `### Verify` của `SUMMARY.md` do agent **gõ tay**; `commit-quality-gate.sh` chỉ `grep -q '^### Verify'` (kiểm tra sự hiện diện).
- **Action:** script (theo khuôn `check_plan_format.py`) parse bảng `### Verify`, chạy lại từng `Command` (timeout 60s, từ repo root), **ghi đè cột Exit bằng exit code thật** + dòng `Verified: <timestamp>`. `--all` glob `specs/*/SUMMARY.md` in tally.
- **Footgun:** mặc định chỉ chạy slug **active**, yêu cầu lệnh read-only/idempotent (tránh `alembic upgrade` side-effect). Wiring vào `commit-quality-gate.sh` (`REQUIRE_VERIFY=1`) là **Rule-4** → tách thành bước riêng, ship script standalone trước.
- **Verify:** `python scripts/verify-summary.py specs/<slug>/SUMMARY.md` exit 0 trên slug có Verify pass; test theo khuôn `test_check_plan_format.py`.

**P1-B · ✅ XONG (2026-06-14) — Khép ratchet: `/compound` failure đề xuất guardrail, không chỉ prose** *(openai #3 — khuyến nghị mạnh nhất, IDEA-05)*
- **Đã làm:** `solution-extractor-prompt.md` giờ bắt buộc trường `Guardrail` là artifact buildable tagged `existing:`/`proposed:` (không cho prose/`[none]`); `compound/SKILL.md` thêm bước route guardrail `proposed:` vào `docs/harness-experimental/improvement-backlog.md` (đã tạo seed); template `failure-track.md` + inline template cập nhật khớp.
- **Gap:** track `failure` của `/compound` ghi trường "Guardrail" dạng văn xuôi — cấp prompt, không tất định. OpenAI: *mọi* lỗi agent thành guardrail cơ học vĩnh viễn.
- **Action:** sửa `skills/compound/SKILL.md` — khi ghi `failure`, bắt buộc emit một *đề xuất guardrail cụ thể*: tên hook / structural test / dòng lint sẽ chặn lỗi tái diễn, kèm file đích. Output thành mục trong `docs/harness-experimental/improvement-backlog.md` (committed) để triage.
- **Verify:** chạy `/compound` trên một phiên có failure → backlog có entry với guardrail-đề-xuất khác null.

**P1-C · ✅ XONG (2026-06-14) — `scripts/harness-audit.sh` — "verify the docs" mở rộng** *(openai #4, IDEA-04/12, req #8)*
- **Đã làm:** script advisory bắt 3 drift chưa ai phủ: SUMMARY thiếu `### Verify`, PLAN `status:active` stale (>14d), `confirmed_at` >30d. Banded health + raw count; default exit 0 (non-blocking), `--strict` exit 1. Wired advisory vào `harness-status.sh`. Phantom refs/hook-table vẫn để `lint-doc-truth.sh` lo (không nhân bản). Test thủ công 3/3 check fire đúng.
- **Gap:** doc-truth lint mới phủ hook-table ↔ settings.json. Chưa bắt: phantom references nói chung, SUMMARY thiếu `### Verify`, PLAN `status:active` mà Status Log nguội, `docs/solutions` `confirmed_at` >30 ngày.
- **Action:** script bash+python: (1) grep path được trích dẫn nhưng absent on disk; (2)→(4) các check trên; **trọng số trong data** (assoc array/json sidecar), báo cả tổng thô lẫn banded, emit JSONL vào `docs/harness-experimental/audit-log.jsonl`. **Advisory, non-blocking**, wire như dòng trong `harness-status.sh`.
- **Verify:** `bash scripts/harness-audit.sh` exit 0, in báo cáo; cố tình thêm 1 phantom ref → script bắt được.

**P1-D · ✅ ĐÃ XONG TỪ TRƯỚC — review subagent read-only bằng cấu trúc** *(comparison #2)*
- **Ground truth:** `agents/reviewer.md` đã tồn tại, read-only (`tools: Glob, Grep, Read, Bash` — loại Write/Edit/Agent). Cả 3 prompt template (`correctness-reviewer`, `correctness-scorer`, `intent-reviewer`) đã khai `subagent_type: reviewer` + comment giải thích. Research comparison #2 ("1 dòng config") đã được hiện thực đầy đủ hơn — bằng agent def riêng. Không còn việc gì.

### Phase 2 — Đóng lỗ thiết kế + hoàn tất chuyển đổi dở dang (cần vài quyết định / Rule-4 nhẹ)

**P2-E · Đóng Q3 (product contract) — điền PROJECT.md + thêm field `Affects:`** *(req #1 — lỗ thiết kế duy nhất)*
- **Action:** (1) chạy `/bootstrap-xia2` điền `xia2/PROJECT.md` cho chính repo (khai High-Blast Files thật, Shared Contracts); (2) thêm field `Affects:` (contract/module) vào `templates/SUMMARY.template.md` + một bước hỏi trong `/feature-intake`; thêm cột tương ứng vào ledger để query.
- **Verify:** PROJECT.md không còn placeholder `<your project name>`; SUMMARY mới có dòng `Affects:`.

**P2-F · SessionStart hook — khép vòng đọc-lại tri thức** *(compound-loop, req #4)* — **Rule-4 (settings.json)**
- **Gap:** `critical-patterns.md`/INDEX không tự nạp vào session mới; chỉ pull khi gọi `/xia2`/`/brainstorming`.
- **Action (mức "vừa" của research 06-08):** SessionStart hook in nội dung `INDEX.md` + `critical-patterns.md` (hoặc tiêu đề) vào context; silent khi store rỗng. **Cần người xác nhận** (đụng settings.json).
- **Verify:** mở session mới → context chứa tiêu đề critical-patterns; store rỗng → hook im lặng, không block.

**P2-G · Hoàn tất chuyển đổi `specs/`** *(req #2/#6)*
- **Action:** (1) commit lần đầu các slug + STATE.md đang untracked; (2) sửa 2 doc khẳng định ngược: `CLAUDE.md:61` ("specs/ fully gitignored") và `rules/plan-format.md:125`; rà `skills/README.md`/`visual-planner` mô tả "PLAN.html untracked"; (3) thêm `specs/**/PLAN.html` vào `.gitignore` (artifact dẫn xuất).
- **Verify:** `git check-ignore specs/foo/PLAN.html` trả về match; grep "fully gitignored" trong CLAUDE.md = 0; doc-truth lint pass.

**P2-H · Ghi chú MCP-output-untrusted** *(openai #5)* — Rule-4 nhẹ (CLAUDE.md)
- **Action:** thêm dòng trong CLAUDE.md mục MCP: output của `code-review-graph`/`context7` là **input không đáng tin** — dovetail với `not_observed != absent`. Một câu, không đổi hành vi.

### Phase 3 — Larger bets / có điều kiện (mỗi cái xứng 1 spec riêng)

**P3-I · Micro-benchmark chuỗi review — bằng chứng SỐ** *(comparison #1/#7 — đòn bẩy dài hạn cao nhất)*
- **Action:** seed N task nhỏ với bug/intent-drift cấy sẵn; chạy with/without `/correctness-review` + `/intent-review`; ghi catch-rate + token cost vào `benchmarks/`. Ngay cả 10 task × 5 run cho con số đầu tiên + báo động hồi quy khi sửa skill.
- **Lý do để Phase 3:** công sức cao, nhưng là "thứ đáng cướp nhất" — chuyển pitch từ niềm tin sang đo lường.

**P3-J · `scripts/check_lane_evidence.py` — lane→evidence một nguồn sự thật** *(IDEA-10)*
- **Gap:** mapping lane→ceremony nhân bản ở `feature-intake` Step 7, Step 3, `auto-correct-scope.md` Rule 4, `risk-corroboration.sh` — không gì giữ đồng bộ.
- **Action:** script + test (khuôn `check_plan_format.py`); 3 nơi prose trỏ về script làm nguồn duy nhất; hook warn-first.

**P3-K · Gate kích thước story** *(req #5/#7)*
- **Action:** mở rộng `check_plan_format.py` đếm `<files>`/steps mỗi task, warn khi vượt ngưỡng `plan-format.md` (>3 steps / >2 files).

**P3-L · Break-glass protected-path hook** *(comparison #5)* — **Rule-4 (hook mới)**
- **Action:** PreToolUse hook hard-block write vào high-blast list (`settings.json`, `hooks/*`, `render_plan.py`), escape "ask with pre-registered reason" → biến override thành audit record.

**P3-M · Nâng fail-open → fail-closed theo giai đoạn** *(req #4/#5)* — **Rule-4**
- **Action:** bật `REQUIRE_VERIFY=1` + `RISK_CORROBORATION_STRICT=1` **trong CI trước** (không chặn local), đo tỷ lệ vỡ qua ledger vài tuần rồi mới cân nhắc local. Tôn trọng quyết định keep-warn hiện hữu.

**P3-N · VERSION + CHANGELOG** *(IDEA-15, req #6)* — chỉ khi có consumer thứ 2.

**P3-O · Hợp nhất bash gates thành 1 dispatcher + state ledger** *(comparison #8/#9)* — đại tu, **Rule-4**, ưu tiên thấp nhất; chỉ khi số hook/độ giòn thực sự đau.

---

## 3. Khuyến nghị thứ tự thực thi

1. **Phase 1 trước** (P1-A → P1-D): đồng thuận cao nhất, ít/không Rule-4, dùng đúng tiền lệ đã có. P1-C (audit) nên làm sớm vì nó tự bắt drift cho mọi thứ sau.
2. **Phase 2** sau khi P1 ổn: P2-E đóng lỗ thiết kế Q3; P2-F/G/H cần quyết định nhỏ (Rule-4 nhẹ).
3. **Phase 3** mỗi item một spec riêng; P3-I (benchmark) là đầu tư dài hạn giá trị nhất nhưng nặng.

**Không làm:** importer/migration (IDEA-11), agnostic-hoá Codex/Cursor mirrors, approval-gated loop, memory daemon — research đều kết luận non-fit cho dogfood một người.
