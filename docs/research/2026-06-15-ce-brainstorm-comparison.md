# Nghiên cứu: So sánh `ce-brainstorm` với skill `brainstorming` của chúng ta

> Ngày: 2026-06-15
> Nguồn: `everyinc/compound-engineering-plugin` — skill `compound-engineering:ce-brainstorm` (v3.12.0)
> Phạm vi: Phân tích đối chiếu để rút ra bài học cải tiến cho `skills/brainstorming/SKILL.md`
> Đã đọc: `ce-brainstorm/SKILL.md` + `references/synthesis-summary.md` + `references/brainstorm-sections.md`; và `skills/brainstorming/SKILL.md` của repo này.

---

## 1. `ce-brainstorm` là gì

Một skill trả lời câu hỏi **CÁI GÌ** (WHAT) cần xây — không phải **LÀM THẾ NÀO** (HOW). Nó chạy trước `/ce-plan` (skill lo phần HOW). Output bền vững của nó là một **tài liệu yêu cầu (requirements doc) đúng kích cỡ**, và đặc điểm cốt lõi: **mức độ nghi thức (ceremony) co giãn theo quy mô công việc**, thay vì cố định.

Cấu trúc các pha:

- **Phase 0** — xác định format output, phát hiện/tiếp tục (resume) brainstorm cũ, phân loại lĩnh vực (phần mềm / phi phần mềm / không cần brainstorm), quyết định *có cần brainstorm hay không*, và phân loại quy mô thành **Lightweight / Standard / Deep**, với Deep còn chia tiếp **feature-vs-product**.
- **Phase 1.2 Product Pressure Test** — quét nội bộ (agent tự phân tích) qua các "lăng kính khoảng trống" (gap lenses): evidence / specificity / counterfactual / attachment / durability; chỉ những khoảng trống thực sự tồn tại mới được nêu thành câu hỏi.
- **Phase 1.3** — đối thoại với các "rigor probe" dạng câu hỏi mở + một **integration check** trước khi thoát pha ("ghép những gì user đã nói lại, phát hiện hệ quả không hiển nhiên").
- **Phase 2** — đề xuất hướng tiếp cận bằng một góc nhìn cố tình phi hiển nhiên (đảo ngược / bỏ ràng buộc / loại suy), trình bày tất cả phương án trước rồi mới khuyến nghị, có thể thêm một phương án "thách thức" upside cao hơn; độ chi tiết giới hạn ở mức *cơ chế (mechanism)*, không bao giờ đụng tới kiến trúc.
- **Phase 2.5 Synthesis Summary** — một checkpoint xác nhận phạm vi (scope) *trước khi* viết doc (hai tầng: bản nháp nội bộ 3-bucket → bản tổng hợp hội thoại đã nén), có cổng Path A/B, các "keep-test", ngân sách bullet theo tier, cơ chế soft-cut khi xoay vòng, và kỷ luật trình-bày-lại-sau-khi-sửa.
- **Phase 3** — viết doc *chỉ khi đáng viết*, theo một catalog section phong phú với quy tắc tiết kiệm văn phong.

---

## 2. Bảng so sánh kiến trúc

| Khía cạnh | `brainstorming` (của ta) | `ce-brainstorm` |
|---|---|---|
| Nghi thức (ceremony) | **Cố định** — "mọi dự án, không ngoại lệ", luôn full checklist + HARD-GATE | **Co giãn** — bỏ qua nếu đã rõ, có tier Lightweight/Standard/Deep |
| Luôn viết doc? | Có (`design.md` luôn luôn) | Không — có cổng "có đáng viết doc không?" |
| Pha kiểm tra độ chặt trước khi đề xuất | Không có | **Product Pressure Test** (5 gap lenses) |
| Sinh phương án | "đề xuất 2-3 hướng" | + bắt buộc một góc phi hiển nhiên + phương án thách thức |
| Thứ tự khuyến nghị | **Dẫn bằng khuyến nghị trước** | **Trình bày hết rồi mới khuyến nghị** (chống mỏ neo / anti-anchoring) |
| Checkpoint phạm vi | Không (nhảy thẳng từ design → viết) | **Phase 2.5 synthesis** + vòng lặp sửa đổi |
| Kỷ luật đặt câu hỏi | "ưu tiên trắc nghiệm, mở cũng được" | Quy tắc rõ + bài test khi nào câu mở mới xứng đáng |
| Review độc lập | Có vòng lặp subagent spec-document-reviewer ✅ | (tách thành skill riêng `ce-doc-review`) |
| Hỗ trợ trực quan | Companion trình duyệt tương tác ✅ | Sơ đồ/HTML tĩnh trong doc |
| Phát hiện resume | Không có | Phase 0.1 ✅ |
| Tách WHAT/HOW | Mờ — design bao gồm "kiến trúc, component, data flow, error handling, testing" | Rõ — chỉ mức cơ chế; kiến trúc → ce-plan |

---

## 3. Những điều đáng học (xếp theo ưu tiên)

### 1. Đúng kích cỡ nghi thức — và sửa một mâu thuẫn nội bộ ta đang có
Đây là điều lớn nhất. Skill của ta bắt buộc full chain cho cả "một todo list, một util một-hàm, một thay đổi config — tất cả." Nhưng chính `rules/orchestration.md` của ta lại nói ngược lại: `design.md` chỉ kích hoạt theo tín hiệu ("chỉ khi có nhánh thiết kế thực sự (≥2 phương án khả thi) hoặc high-risk"), và `feature-intake` định tuyến lane **tiny** đi thẳng tới sửa trực tiếp. Nghĩa là skill brainstorming hiện đang **mâu thuẫn với chính hệ thống lane của ta**. `ce-brainstorm` xác nhận độc lập rằng hướng co giãn là đúng.

**Khuyến nghị:** làm cho brainstorming nhận biết lane — Lightweight/tiny chỉ cần căn chỉnh ngắn gọn và có thể bỏ qua `design.md`; HARD-GATE và vòng review chỉ áp cho normal/high-risk.

### 2. Product Pressure Test (các gap lenses)
Thực sự mới mẻ và giá trị cao — ta hoàn toàn chưa có. Các lăng kính evidence / specificity / counterfactual / attachment / durability biến brainstorming từ *trích xuất yêu cầu* thành *thẩm vấn sản phẩm*, và cách đóng khung "agent tự phân tích nội bộ, chỉ nêu khoảng trống có thật" tránh được kiểu checklist hình thức. Đây là ý tưởng dễ ghép vào nhất.

Tóm tắt 5 lăng kính:
- **Evidence gap** — phát biểu có nhu cầu/mong muốn nhưng chưa chỉ ra điều gì user đã thực sự làm (thời gian bỏ ra, tiền đã trả, workaround đã dựng). → Hỏi điều cụ thể nhất ai đó đã làm về việc này.
- **Specificity gap** — mô tả người hưởng lợi ở mức trừu tượng đến mức agent phải tự bịa ra họ là ai. → Yêu cầu nêu tên một người/phân khúc hẹp cụ thể và điều gì thay đổi cho họ.
- **Counterfactual gap** — không thấy rõ hôm nay user làm gì khi gặp vấn đề, và điều gì thay đổi nếu không ship gì cả. → Hỏi workaround hiện tại và nó tốn kém ra sao.
- **Attachment gap** — coi một hình dạng giải pháp cụ thể là "thứ đang xây", thay vì giá trị mà hình dạng đó phải mang lại. → Hỏi phiên bản nhỏ nhất vẫn mang lại giá trị thật trông như thế nào.
- **Durability gap** (chỉ Deep-product) — giá trị dựa trên một trạng thái thế giới có thể dịch chuyển. → Hỏi ý tưởng trụ ra sao trước các thay đổi gần kề hợp lý nhất.

### 3. Checkpoint tổng hợp trước khi viết (Phase 2.5)
Ta nhảy thẳng từ "duyệt design" sang "viết design.md". `ce-brainstorm` chèn một bước xác nhận phạm vi với insight: *"user đã đồng ý từng thứ riêng lẻ trong đối thoại nhưng chưa bao giờ thấy bức tranh toàn cảnh."* Hình dạng hai tầng (bản nháp nội bộ đầy đủ → checkpoint hội thoại đã nén) + kỷ luật sửa-trước-khi-viết là một cổng chất lượng có ý nghĩa, và rẻ hơn vòng subagent review của ta vì nó nằm inline.

### 4. Chống mỏ neo trên các phương án — một mâu thuẫn trực tiếp cần giải quyết
Skill của ta nói *"Dẫn bằng phương án khuyến nghị."* `ce-brainstorm` nói *trình bày hết phương án trước, rồi mới khuyến nghị,* vì dẫn bằng khuyến nghị làm user bị "neo" sớm. Lập luận của họ hợp lý; nên đánh dấu đây là một quyết định cần cân nhắc chủ động, chứ không lặng lẽ giữ cách của ta.

### 5. Kỷ luật câu hỏi sắc bén hơn + integration check
Interaction Rule 5 của họ (bài test rõ ràng khi nào câu hỏi nên mở thay vì menu — *"nếu bạn phải gắng gượng để lấp đầy các ô lựa chọn thì câu hỏi đó là câu mở"*) và việc các rigor probe *cố tình* để mở (để menu không "mách" cho user biết thế nào là câu trả lời tốt) đều rất sắc. Ngoài ra integration check trước khi thoát pha không có tương đương ở ta.

### 6. Ranh giới WHAT/HOW sạch hơn
Design của ta bao gồm "kiến trúc, component, data flow, error handling, testing" — kéo HOW vào trong brainstorm. Vì workflow của ta đã có `xia2 → writing-plans` ở hạ nguồn, doc design có thể giữ ở mức cơ chế/hành vi và để các plan lo kiến trúc. (Lưu ý: các consumer của `design.md` có thể đang kỳ vọng mức chi tiết đó — cần kiểm tra trước khi đổi.)

**Ưu tiên thấp hơn:** phát hiện resume (Phase 0.1), catalog section theo kiểu prose-economy trong `brainstorm-sections.md`, và bài "stress test" quyết định có đáng viết doc không.

---

## 4. Những thứ ta đang làm tốt hơn (nên giữ)

- **Review độc lập nhúng sẵn** — vòng lặp subagent spec-document-reviewer của ta là review đối kháng có cấu trúc ngay trong skill; `ce-brainstorm` đẩy việc đó sang skill riêng `ce-doc-review`.
- **Visual companion tương tác** — mockup trình duyệt vượt trội sơ đồ tĩnh cho các câu hỏi về layout/wireframe.
- **Tích hợp lane/hard-gate** — HARD-GATE + việc đọc decision-track trong `docs/solutions/` (không đề xuất lại các phương án đã bị bác) gắn brainstorming vào hệ thống quản trị rộng hơn.

---

## 5. Các thay đổi cụ thể đề xuất (theo ưu tiên)

1. **Làm brainstorming nhận biết lane** (giải quyết mâu thuẫn nội bộ với `orchestration.md`) — *giá trị cao, đồng thời là sửa lỗi tính đúng đắn.*
2. **Thêm pha Product Pressure Test** trước khi đề xuất phương án — *tính mới cao nhất.*
3. **Thêm checkpoint tổng hợp/xác nhận phạm vi** trước khi viết `design.md`.
4. **Quyết định vấn đề mỏ neo** (dẫn-bằng-khuyến-nghị vs trình-bày-rồi-khuyến-nghị) — cần quyết định của con người.
5. **Siết kỷ luật câu hỏi** + thêm integration check.

Tất cả đều là thay đổi tới một core skill (`skills/brainstorming/SKILL.md`) — đúng loại edit mà rules của ta coi là rủi ro cao hơn, nên đã dừng ở mức phân tích thay vì sửa file.
