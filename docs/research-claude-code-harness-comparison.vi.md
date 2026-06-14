# Nghiên cứu: Chachamaru127/claude-code-harness so với harness-skills của chúng ta

> Phân tích chuyên sâu https://github.com/Chachamaru127/claude-code-harness (clone tại v4.15.0,
> ~1.625 file: 188 file skill, 176 file Go, 195 file test, 170 file benchmark, 122 file docs).
> So sánh với repo này (`harness-skills`).
> Ngày nghiên cứu: 2026-06-12. Phương pháp: clone toàn bộ + 3 lượt đọc sâu song song
> (skills/workflow · lõi Go/tự động hóa · testing/benchmarks/tính khả chuyển).

---

## 1. Những điều họ làm tốt nhất

### 1.1 Lõi cưỡng chế (enforcement) viết bằng Go thay vì hook bash

Engine guardrail của họ là ~54K dòng Go biên dịch thành một binary duy nhất (`bin/harness`),
được dispatch từ một file khai báo `hooks/hooks.json` (hơn 40 loại hook). Các rule R01–R14
là hàm thuần `(RuleContext) → {Decision, Reason}`, đánh giá theo nguyên tắc khớp-đầu-tiên-thắng:

- **Chặn cứng (hard-deny)**: sudo (R01), ghi vào đường dẫn được bảo vệ — `.git/`, secrets,
  `*.pem`, SSH key, file rc của shell, `.claude/hooks` (R02), đọc file chứa secret (R09),
  sửa trực tiếp file `settings.json` được sinh tự động (tự bảo vệ).
- **Break-glass ask**: ghi vào `.env` chỉ được hỏi (ask) *nếu* lý do đã được đăng ký trước
  trong `harness.toml`; nếu không thì bị từ chối (R03).
- **Cảnh báo (advisory)**: cưỡng chế TDD (R14), lệnh bị cấm với reviewer (R08) — cảnh báo,
  ghi log, không chặn, cho đến khi một giai đoạn rollout nâng cấp chúng lên.

Vì sao quan trọng: quyết định an toàn về kiểu (type-safe), ngân sách độ trễ 10ms mà không
interpreter nào đạt được, audit trail lưu trong SQLite (8 bảng: sessions, signals,
task_failures, work_states…), và một state machine sống sót qua các lần restart session.

### 1.2 Benchmark với thống kê thực sự — họ *đo* xem harness có hiệu quả không

Đây là điều hiếm nhất trong giới prompt-framework. `benchmarks/breezing-bench/` chứa một
nghiên cứu hai giai đoạn về việc các chỉ dẫn validation của họ có cải thiện tỉ lệ thành
công của agent hay không:

- Thăm dò (exploratory): 3 task × 30 lần chạy → tỉ lệ pass **93,3% so với 20,0%**
  (p<0,001, Cohen's h=1,69).
- Khẳng định (confirmatory, thiết kế độc lập): 10 task × 100 lần chạy → **84% so với 40%**
  (p<0,000005), hiệu chỉnh Holm–Bonferroni theo từng task, khai báo rõ các nguy cơ với
  tính hợp lệ (threats to validity), và một sổ chi phí trung thực (+34% thời gian thực,
  +54% số tool call để đổi lấy mức tăng +44 điểm phần trăm).
- Dữ liệu chạy thô, config và script phân tích được lưu trữ ngay trong repo.

Họ cũng giới hạn phạm vi tuyên bố một cách chặt chẽ ("breezing = `npm run validate` + chỉ
dẫn sửa lỗi", không phải toàn bộ pipeline) và khai báo các yếu tố gây nhiễu — kỷ luật
pre-registration áp dụng cho một prompt framework.

### 1.3 Sự trung thực theo bậc bằng chứng: `not_observed != absent`

Mỗi host (Claude Code / Codex / OpenCode / Cursor / Copilot) mang một bậc (tier) rõ ràng —
`supported` / `internal-compatible` / `candidate` / `future` — và **một tier chỉ được nâng
lên khi repo này tự nắm giữ bằng chứng bootstrap + trigger + runtime + release của chính
nó**. Tuyên bố hỗ trợ không bao giờ được thừa kế từ dự án thượng nguồn. Cùng nguyên tắc
nhận thức luận đó chạy bên trong các skill: kết quả tìm kiếm không có, file chưa đọc, hay
memory không khả dụng phải được giữ ở trạng thái `unknown` — worker agent trả về một
`advisor-request` thay vì đoán mò khi một task thay đổi hành vi mà không có spec path lẫn
lý do bỏ qua spec.

### 1.4 Definition of Done kiểm tra được bằng máy cho từng task

Mỗi dòng task trong Plans.md mang một DoD là *danh sách validator*, không phải văn xuôi:

```
(a) agents/worker.md chứa "600s stall" — grep ≥1 kết quả
(b) schema validation pass
(e) ./tests/validate-plugin.sh PASS
```

Việc hoàn thành task trở thành thứ CI phát hiện được. Marker trạng thái nhúng luôn commit
hash (`cc:完了 [hash]`), nên bảng kế hoạch đồng thời là một sổ cái (ledger).

### 1.5 Tính khả chuyển đa công cụ từ một nguồn duy nhất

`skills/` là nguồn sự thật duy nhất (SSOT); `scripts/sync-skill-mirrors.sh` +
`build-opencode.js` sinh ra các bản mirror cho Codex/OpenCode/Cursor, với lớp phủ
`skills-codex/` cho các override riêng theo host và CI kiểm tra độ lệch (drift) giữa
adapter và mirror. Sửa một skill là lan tỏa khắp nơi; sự phân kỳ là một lỗi CI, không
phải tài liệu mục nát.

### 1.6 Giới hạn công cụ theo vai trò ngay trong frontmatter

Agent reviewer của họ về mặt cấu trúc không thể gian lận: `disallowedTools: [Write, Edit,
Bash, Agent]` trong frontmatter — tính độc lập của review được harness cưỡng chế, không
phải nhờ một prompt nhờ vả lịch sự. Worker không thể spawn agent lồng nhau; phán quyết
APPROVE của reviewer tuyên bố rõ là không cấp quyền commit/push (commit là một cổng riêng).

---

## 2. Những điều chúng ta đang làm tốt (đôi khi tốt hơn)

| Lĩnh vực | Vị thế của chúng ta |
|---|---|
| **Định tuyến theo làn rủi ro** | Hệ thống làn của `/feature-intake` (tiny/normal/high-risk + confidence) chi tiết hơn cách chia phẳng "lightweight vs non-trivial" của họ. Đường tắt cho sửa typo của họ là một trường hợp đặc biệt; làn của chúng ta là *nguyên tử định tuyến*, được `risk-corroboration.sh` đối chiếu hậu kiểm với diff đã stage — họ không có thứ gì tương đương việc *máy kiểm tra làn đã khai báo so với những gì thực sự bị thay đổi*. |
| **Nghi thức tỉ lệ với rủi ro, cổng con người tỉ lệ với độ mơ hồ** | Vòng lặp của họ mặc định cần phê duyệt (người dùng duyệt mọi contract). Notify-and-proceed của chúng ta cho công việc normal-lane độ tin cậy cao + `ESCALATIONS.md` từ-chối-khi-không-phản-hồi là một mô hình tự chủ phát triển hơn. Họ tối ưu cho một người vận hành kỷ luật; chúng ta tối ưu cho sự tự chủ có giới hạn. |
| **Ba oracle review độc lập** | Pipeline của chúng ta tách spec compliance → code quality → `/correctness-review` (đối kháng, giả định có bug) → `/intent-review` (diff so với yêu cầu nguyên văn, cố ý mù với PLAN). `/harness-review` của họ là một evaluator duy nhất kiểm tra spec/Plans alignment + TDD. Oracle "qua được plan, qua được test, nhưng không phải thứ người dùng yêu cầu" của intent-review không có đối trọng bên họ. |
| **Tích lũy tri thức (knowledge compounding)** | `/compound` với bốn loại track (bug/knowledge/decision/**failure**), phân loại mức độ nghiêm trọng lên `critical-patterns.md`, gộp có nhận biết va chạm, rebuild toàn bộ INDEX, và trường staleness 30 ngày — giàu hơn nhiều so với harness-mem của họ (một daemon recall tùy chọn, không có schema cho *loại* bài học và không có mô hình suy giảm/độ tin cậy). Cơ chế suy giảm độ tin cậy trong agent-memory của chúng ta (`high/medium/low` + `review-by`) cũng không có đối trọng. |
| **Review hiểu cấu trúc codebase** | MCP code-review-graph của chúng ta (impact radius, affected flows, tests-for, lớp phủ blast-radius trên PLAN.html) cho review ngữ cảnh cấu trúc. Review của họ dựa trên đọc file. |
| **Song song theo wave** | Wave không-chồng-file với spawn song song trong một message và giao thức thu thập kết quả là mô hình thực thi song song tường minh hơn work.yaml Phase 1–4 của họ. |
| **Phạm vi tự sửa (auto-correct scope)** | Rule 1–4 (auto-fix / auto-add / auto-fix-blocking / STOP) với báo cáo `### Deviations` bắt buộc là một hợp đồng tự chủ chi tiết hơn các NG-rule của worker bên họ. |

Lưu ý trung thực: nhiều điểm mạnh của họ nằm đúng chỗ chúng ta yếu nhất — các cổng của
chúng ta sống trong bash + văn bản prompt, và chúng ta **không có bằng chứng thực nghiệm**
nào rằng chuỗi của mình cải thiện kết quả.

---

## 3. Những điều chúng ta có thể học từ repo này

1. **Chứng minh harness hiệu quả — bằng con số.** Chúng ta khẳng định chuỗi của mình
   (intake → plan → review hai tầng → correctness → intent) bắt được vấn đề; họ chạy 130
   lần có kiểm soát và công bố p-value cùng *chi phí* của mức cải thiện. Bài học: một
   harness là một tuyên bố sản phẩm, và tuyên bố cần bằng chứng đã thực thi. Ngay cả một
   phiên bản nhỏ — 10 task, có/không có `/correctness-review`, đếm số bug lọt lưới — cũng
   biến lời chào hàng của chúng ta từ niềm tin thành phép đo.

2. **Cưỡng chế bằng cấu trúc thắng cưỡng chế bằng prompt.** Reviewer của họ không thể
   ghi; reviewer của chúng ta được dặn là đừng ghi. `disallowedTools` / `allowed-tools`
   trong frontmatter cho các agent ở giai đoạn review là một bảo đảm cấu trúc chi phí
   bằng không mà chúng ta chưa dùng.

3. **`not_observed != absent` như một hợp đồng có tên, lặp lại nhiều tầng.** Chúng ta có
   tinh thần đó (bằng chứng-trên-khẳng-định, "không bao giờ liệt kê lệnh chưa chạy")
   nhưng họ *đặt tên* cho quy tắc nhận thức luận và lặp lại nó ở mọi tầng — planning,
   worker, reviewer, support tier. Một quy tắc có tên thì grep được, dạy được, và trích
   dẫn được trong review.

4. **Config được sinh tự động kèm tự bảo vệ.** Cơ chế sync `harness.toml` →
   `settings.json` của họ cộng với guardrail *từ chối sửa trực tiếp file được sinh ra*
   loại bỏ hoàn toàn lớp lỗi config-drift. Cặp `settings.json` vs `settings.local.json`
   của chúng ta có lint doc-truth (tốt) nhưng không gì ngăn một lần sửa tay gây trôi dạt.

5. **Tuyên bố trong tài liệu gắn với bậc bằng chứng.** README của họ không bao giờ nói
   "chạy được với X" mà thiếu tier và điều kiện thăng hạng. Handoff map trong
   skills/README của chúng ta có thể mang đúng điều đó: handoff nào được CI kiểm chứng
   so với chỉ được ghi chép (các skill superpowers bên ngoài của chúng ta chính xác là
   tier "candidate" mà họ sẽ từ chối gọi là supported).

6. **Hạch toán chi phí trung thực.** Họ báo cáo rằng chất lượng tốn +34% thời gian thực
   và +54% tool call. Chúng ta chưa bao giờ định lượng chuỗi đầy đủ tốn bao nhiêu so với
   làn tiny — biết con số này mới là thứ biện minh (hoặc cắt giảm) nghi thức theo từng làn.

---

## 4. Ý tưởng áp dụng cho dự án của chúng ta

Sắp xếp theo đòn bẩy / công sức:

### Thắng nhanh (vài ngày)

1. **`disallowedTools` cho các agent review.** Cấp cho subagent của `/correctness-review`
   và `/intent-review` bề mặt công cụ chỉ-đọc khi dispatch (không Write/Edit/Bash gây
   thay đổi). Độc lập review về mặt cấu trúc với một dòng config.
   *(Đòn bẩy cao, công sức không đáng kể.)*

2. **Áp dụng nguyên văn quy tắc `not_observed != absent`.** Thêm vào `rules/behavior.md`
   §1 và vào prompt của các skill correctness-/intent-review: một phát hiện "không tìm
   thấy caller nào" phải nêu rõ *đã tìm ở đâu*; một khẳng định chưa kiểm chứng phải giữ
   ở `unknown` thay vì kết luận là không tồn tại.

3. **Commit hash trong trạng thái plan.** Mở rộng quy ước Status Log của PLAN.md để mỗi
   dòng task hoàn thành ghi luôn commit sha (họ nhúng nó vào marker trạng thái). Chúng ta
   đã làm một phần trong khâu thu thập wave; biến nó thành bất biến theo-từng-task mà
   lint doc-truth có thể kiểm tra.

### Trung bình (1–2 tuần)

4. **DoD kiểm tra được bằng máy trong `<done>`.** Hiện `<verify>` của chúng ta là một
   lệnh duy nhất và `<done>` là văn xuôi. Mượn mẫu validator-đánh-chữ-cái của họ: cho
   phép `<done>` là một checklist mà mỗi mục kiểm tra được bằng grep/test/schema, để
   "done" trở thành thứ một hook chạy lại được thay vì để agent phán xét.

5. **Break-glass cho đường dẫn được bảo vệ.** Danh sách STOP của Rule 4 (settings.json,
   hooks/*, render_plan.py) hiện cưỡng chế bằng prompt. Chuyển mẫu R02/R03 của họ thành
   một hook PreToolUse: chặn cứng ghi vào danh sách high-blast, kèm lối thoát "hỏi với
   lý do đã đăng ký trước" — yêu cầu nêu lý do biến một lần override thành một bản ghi
   audit.

6. **Bảng bậc bằng chứng cho chính các tích hợp của chúng ta.** Một bảng trong
   skills/README: mỗi skill ngoài / phụ thuộc MCP / cạnh handoff → `ci-proven` /
   `manually-verified (ngày)` / `documented-only`, với quy tắc một cạnh chỉ được nâng
   bậc khi có bản ghi chạy thực. Rẻ để thêm; diệt được sự mục nát thầm lặng.

### Cược lớn hơn (đáng một spec riêng cho mỗi cái)

7. **Một micro-benchmark cho chuỗi review.** Gieo N task nhỏ với bug / lệch intent đã
   cài sẵn; chạy có và không có `/correctness-review` + `/intent-review`; ghi tỉ lệ bắt
   được và chi phí token vào `benchmarks/`. Chỉ 10 task × 5 lần chạy đã cho chúng ta con
   số thực đầu tiên — và một chuông báo regression mỗi khi sửa các skill. Đây là thực
   hành đáng "đánh cắp" nhất.

8. **Biên dịch các cổng nóng thành một binary thực sự (hoặc ít nhất một dispatcher).**
   11 hook bash của chúng ta mỗi cái tự parse lại state mỗi lần được gọi. Mô hình của họ
   — một entrypoint, bảng matcher khai báo, khớp-đầu-tiên-thắng, sổ cái SQLite, fail-open
   với timeout — sẽ làm các cổng của chúng ta nhanh hơn, test được như unit, và cho sổ
   cái trust-metrics một kho lưu trữ thật. Go là lựa chọn của họ; với chúng ta, ngay cả
   một dispatcher Python/Go duy nhất gom `commit-quality-gate` + `risk-corroboration` +
   `branch-guard` + `blast-radius` cũng thu được phần lớn lợi ích.

9. **Sổ cái session/state.** State machine SQLite của họ (sessions, signals,
   task_failures, work_states + bộ đếm leo thang khi retry) là thứ mà
   `state-breadcrumb.sh` + STATE.md của chúng ta muốn lớn lên thành: tiếp tục phiên,
   phát hiện lỗi lặp lại (trigger leo thang "cùng một `<verify>` fail ≥2 lần" hiện dựa
   vào trí nhớ của orchestrator), và telemetry sức khỏe subagent trở thành truy vấn thay
   vì quy ước.

### Những thứ rõ ràng không đáng sao chép

- **Mirror đa công cụ (Codex/OpenCode/Cursor).** Hố phức tạp lớn nhất của họ (~480 file).
  Chúng ta chỉ nhắm Claude Code; không có gì để được lợi.
- **Vòng lặp duyệt-mọi-thứ.** Mặc định "người dùng duyệt mọi contract" của họ sẽ là một
  bước lùi so với mô hình tự chủ lane/confidence của chúng ta.
- **Memory daemon chạy ngoài process.** Hệ docs/solutions + agent-memory dạng file với
  suy giảm độ tin cậy của chúng ta đơn giản hơn và đã có cấu trúc tốt hơn harness-mem.

---

## Tóm tắt (TL;DR)

Họ xây phần *kỹ thuật* quanh một harness: guardrail biên dịch, chứng minh thống kê, tuyên
bố theo bậc bằng chứng, "done" kiểm tra được bằng máy. Chúng ta xây phần *phán đoán*
quanh một harness: làn rủi ro, tự chủ có giới hạn, ba oracle review, tri thức tích lũy có
suy giảm. Những thứ đáng học nhất theo đòn bẩy: (1) benchmark chính chuỗi review của
mình, (2) làm các agent review chỉ-đọc về mặt cấu trúc, (3) đặt tên và cưỡng chế
`not_observed != absent`, và (4) gom các cổng bash thành một dispatcher test được kèm sổ
cái state.
