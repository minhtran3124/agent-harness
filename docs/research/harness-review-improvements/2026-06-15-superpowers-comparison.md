# Nghiên cứu: So sánh `superpowers` với skill `brainstorming` của chúng ta

> Ngày: 2026-06-15
> Nguồn: `obra/superpowers` (GitHub, nhánh main) — skill `skills/brainstorming/SKILL.md` và README plugin
> Phạm vi: Phân tích đối chiếu để rút ra bài học cho `skills/brainstorming/SKILL.md`
> Phương pháp: Lấy nội dung qua WebFetch (model nhỏ tóm tắt, không phải raw 100%) rồi đối chiếu với skill đang có trong repo. Một số sắc thái câu chữ có thể mất; các kết luận cấu trúc đã được kiểm chứng bằng so trùng văn bản.

---

## 0. Phát hiện quan trọng nhất: đây là QUAN HỆ HUYẾT THỐNG, không phải đối thủ

Khác với `ce-brainstorm` (một sản phẩm song song có kỹ thuật mới để vay mượn), **`superpowers` là TỔ TIÊN của skill brainstorming — và của gần như toàn bộ workflow — trong repo này.** Bằng chứng: các skill cùng tên xuất hiện ở cả hai bên:

`brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `using-git-worktrees`, `finishing-a-development-branch`, `systematic-debugging`, `requesting-code-review`, `verification-before-completion`.

Riêng skill `brainstorming`: bản của ta **gần như giống hệt** superpowers, và ta đã chủ động **nâng cấp** nó ở vài điểm. Nói cách khác: ta không "học cái mới" từ superpowers brainstorming — ta đã là **superset** của nó. Điều đáng làm là (a) xác nhận dòng dõi để biết phải đồng bộ gì với upstream, và (b) nhặt vài thứ nhỏ ta đã bỏ qua khi fork.

Thứ hạng độ tinh vi của 3 skill brainstorm: **ce-brainstorm (cao nhất) > của ta (superpowers + subagent review + xia2 + lane) > superpowers brainstorming (gốc/baseline).**

---

## 1. `superpowers` là gì

Một plugin đóng gói nguyên một **phương pháp luận phát triển phần mềm**, không phải các gợi ý code rời rạc. Triết lý lõi (theo README):

1. **Test-Driven Development** — test luôn đi trước code.
2. **Systematic over ad-hoc** — quy trình thắng phỏng đoán.
3. **Complexity reduction** — đơn giản là mục tiêu hàng đầu.
4. **Evidence over claims** — kiểm chứng trước khi tuyên bố thành công.

Điểm đặc trưng: nó **"lùi lại và hỏi bạn thực sự đang cố làm gì"** trước khi thiết kế, và **bắt buộc** một pipeline tuần tự (không phải gợi ý tùy chọn):

> brainstorming → design validation → planning → subagent-driven development → testing → code review → branch completion

Skill `subagent-driven-development` của nó dispatch agent mới cho mỗi task với **review hai tầng** (tuân thủ spec → chất lượng code) — đây chính là mô hình mà `rules/orchestration.md` và `wave-parallelism.md` của ta đang dùng.

---

## 2. Skill `brainstorming`: cái gì GIỐNG HỆT (ta thừa hưởng)

- Quy trình **9 bước** (explore context → offer visual companion → ask Qs → 2-3 approaches → present design → write doc → review → user review → writing-plans).
- **HARD-GATE** câu chữ y hệt: *"Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it."*
- Anti-pattern **"This Is Too Simple To Need A Design"** — y hệt.
- **Key Principles** y hệt: one-question-at-a-time, multiple-choice preferred, YAGNI ruthlessly, explore alternatives, incremental validation, be flexible.
- **Visual companion** (mockup trình duyệt).
- Bước 4: **dẫn bằng phương án khuyến nghị** (giống ta — và đây chính là điểm `ce-brainstorm` làm ngược lại = present-then-recommend; xem doc ce-brainstorm).
- Design chia section theo độ phức tạp, duyệt từng section.
- Trạng thái kết thúc = `writing-plans`.

---

## 3. Cái gì ta ĐÃ THAY ĐỔI so với superpowers gốc

| Khía cạnh | superpowers (gốc) | của ta (đã sửa) | Đánh giá |
|---|---|---|---|
| Bước 6 — đường dẫn doc | `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` (phẳng, theo ngày) | `specs/<slug>/design.md` (theo thư mục slug, track trong git) | Của ta hợp với cấu trúc spec→plan→implement per-slug |
| Bước 7 — review spec | **Self-review** (tự quét: placeholder/TBD, mâu thuẫn nội tại, đúng phạm vi, mơ hồ) | **Vòng lặp subagent `spec-document-reviewer`** (độc lập, tối đa 5 vòng) | **Ta nâng cấp** — review độc lập > tự review |
| Bước nghiên cứu code cũ | Không có (đi thẳng brainstorm → writing-plans) | Chèn **`xia2`** trước writing-plans | Ta thêm khâu "khám phá cái đã tồn tại" |
| Đọc quyết định cũ | Không có | Đọc `docs/solutions/` decision-track (tránh đề xuất lại phương án đã bác) | Ta thêm |
| Phân loại rủi ro | Không có | Tích hợp `feature-intake` (lane tiny/normal/high-risk) | Ta thêm (dù skill brainstorming chưa tận dụng — xem doc ce-brainstorm) |

---

## 4. Vậy còn HỌC được gì từ superpowers?

Vì ta đã là superset, bài học ít hơn ce-brainstorm — nhưng vẫn có thật:

### 1. Self-review bước 7 như một cổng "luôn-bật, chi phí thấp"
Đây là điểm vay được giá trị nhất. Vòng subagent `spec-document-reviewer` của ta **mạnh nhưng nặng** — quá mức cho công việc nhỏ (tiny/Lightweight). Checklist self-review của superpowers (quét TBD/placeholder, nhất quán nội tại, đúng phạm vi, khử mơ hồ) là cổng **nhẹ, chạy luôn**.

→ **Ghép với khuyến nghị lane-awareness** từ doc `ce-brainstorm`: dùng **self-review của superpowers làm tầng nhẹ** (cho tiny/Lightweight) và **giữ vòng subagent cho normal/high-risk**. Tức là superpowers cấp cho ta đúng "cơ chế review tầng rẻ" mà phần co-giãn-nghi-thức đang cần.

### 2. Nhận thức dòng dõi & đồng bộ với upstream
Vì 9 skill của ta fork từ superpowers, mỗi lần upstream sửa HARD-GATE, Key Principles, hay quy trình brainstorm, ta nên biết để quyết định đồng bộ hay cố tình rẽ nhánh. Nên ghi rõ "đây là fork của superpowers, các điểm rẽ nhánh có chủ đích là: subagent review, xia2, lane, docs/solutions, specs/<slug>".

### 3. Triết lý xác nhận hướng đi của ta
Bốn nguyên tắc lõi của superpowers (TDD, systematic-over-ad-hoc, complexity-reduction, evidence-over-claims) đã nằm sẵn trong `rules/behavior.md` và `rules/orchestration.md` (mục "evidence over assertion"). Không có gì mới phải thêm — chỉ xác nhận ta đang đi đúng.

### 4. Các meta-skill đáng tham khảo (ngoài brainstorming)
- `writing-skills` — skill để viết skill (ta đang tham chiếu `/skill-creator` ở ngoài).
- `dispatching-parallel-agents` — mô hình fan-out agent (ta đã có trong orchestration/wave-parallelism).
Không trực tiếp về brainstorming nhưng là nguồn tham khảo khi tinh chỉnh hệ thống.

---

## 5. So sánh chéo: superpowers vs ce-brainstorm (cho brainstorming)

| Kỹ thuật | superpowers | của ta | ce-brainstorm |
|---|---|---|---|
| Co giãn nghi thức theo scope | ❌ (cố định) | ⚠️ (có lane nhưng skill chưa dùng) | ✅ (Lightweight/Standard/Deep) |
| Product Pressure Test (gap lenses) | ❌ | ❌ | ✅ |
| Synthesis checkpoint trước khi viết | ❌ | ❌ | ✅ |
| Anti-anchoring (present-then-recommend) | ❌ (dẫn bằng khuyến nghị) | ❌ (dẫn bằng khuyến nghị) | ✅ |
| Review spec | Self-review (nhẹ) | Subagent loop (nặng, độc lập) ✅ | Skill riêng ce-doc-review |
| Visual companion tương tác | ✅ | ✅ | ❌ (chỉ diagram tĩnh) |
| Khám phá code cũ trước plan | ❌ | ✅ (xia2) | ⚠️ (Phase 1.1 scan) |
| Phát hiện resume brainstorm | ❌ | ❌ | ✅ |

---

## 6. Khuyến nghị tổng hợp (gộp cả hai nghiên cứu)

1. **Làm brainstorming nhận biết lane** + **dùng self-review của superpowers cho tầng nhẹ**, giữ subagent loop cho normal/high-risk. (Giải quyết mâu thuẫn với `orchestration.md`, đồng thời tận dụng cơ chế rẻ của superpowers.)
2. **Thêm Product Pressure Test** (5 gap lenses) — học từ ce-brainstorm; tính mới cao nhất.
3. **Thêm synthesis/scope-confirmation checkpoint** trước khi viết `design.md` — học từ ce-brainstorm.
4. **Quyết định vấn đề mỏ neo** (present-then-recommend vs lead-with-recommendation) — superpowers VÀ ta đều dẫn bằng khuyến nghị; ce-brainstorm phản biện điều này. Cần con người quyết.
5. **Ghi chú dòng dõi**: đánh dấu rõ skill là fork của superpowers + danh sách điểm rẽ nhánh có chủ đích, để đồng bộ upstream về sau.

Tất cả đều đụng tới core skill (`skills/brainstorming/SKILL.md`) — loại edit rủi ro cao hơn theo rules của ta, nên dừng ở mức phân tích.
