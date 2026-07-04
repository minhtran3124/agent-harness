# Tổng hợp chuyên sâu: Nên cải thiện skill `brainstorming` thế nào — và bằng chứng

> Ngày: 2026-06-15
> Đầu vào: `docs/research/2026-06-15-ce-brainstorm-comparison.md` + `docs/research/2026-06-15-superpowers-comparison.md`
> Mục tiêu: Lọc ra những thay đổi mang lại **hiệu quả thực sự**, kèm bằng chứng ngoài (academic + industry) để biện minh CÓ nên update và update NHƯ THẾ NÀO.
> Phương pháp bằng chứng: 4 truy vấn web có chủ đích cho 4 tuyên bố chịu lực nhất (anchoring, LLM self-correction, product discovery, cost-of-change). Nguồn liệt kê ở cuối. Mọi tuyên bố cấu trúc về 2 skill đã đối chiếu trực tiếp với văn bản trong context.

---

## 0. Khung đánh giá

Mỗi đề xuất được chấm trên 3 trục: **giá trị thực** × **sức mạnh bằng chứng** × **chi phí/rủi ro triển khai**. Chỉ những mục thắng cả ba mới đưa vào Tier 1. Đặc biệt chú ý: bằng chứng dưới đây **đảo ngược một khuyến nghị cũ** (xem mục 5).

Hai sự thật nền (đã xác lập ở 2 doc trước):
- Skill `brainstorming` của ta là **fork của superpowers**, đã được nâng cấp (subagent review thay self-review, +xia2, +lane, +docs/solutions). → Ta là **superset** của superpowers nhưng **kém tinh vi hơn ce-brainstorm**.
- `rules/orchestration.md` của ta nói `design.md` co giãn theo tín hiệu và lane `tiny` đi thẳng tới sửa trực tiếp — **mâu thuẫn** với câu "mọi dự án, không ngoại lệ" trong SKILL.md hiện tại.

---

## TIER 1 — Bằng chứng mạnh, giá trị cao, NÊN LÀM

### 1.1 Đưa Product Pressure Test vào (4 gap lenses) — *tính mới + bằng chứng mạnh nhất*

**Hiện trạng:** skill ta chỉ "ask clarifying questions" chung chung. Không có cơ chế phát hiện khoảng trống lập luận sản phẩm.

**Đề xuất:** thêm một bước **phân tích nội bộ (agent tự quét)** trước khi đề xuất phương án, theo 4 lăng kính của ce-brainstorm: evidence / specificity / counterfactual / attachment. Chỉ nêu khoảng trống **có thật** thành câu hỏi mở, lồng vào dòng đối thoại — không bắn ra như checklist.

**Bằng chứng ngoài (mạnh):** đây không phải sáng chế của ce-brainstorm — nó là **The Mom Test** (Rob Fitzpatrick) được tự động hóa. Nguyên tắc lõi của The Mom Test trùng khớp gần như 1:1 với các gap lenses:
- *"Ask about past behavior, not hypotheticals"* → **evidence gap** ("điều cụ thể nhất ai đó đã làm — trả tiền, dựng workaround?").
- *"How do they currently address the problem? What alternatives have they investigated?"* → **counterfactual gap** ("hôm nay họ làm gì khi gặp vấn đề?").
- *"Past behavior is real; hypothetical answers are mostly unreliable."* → chính là lý do các probe phải hỏi việc đã xảy ra, không phải ý kiến tương lai.

→ Đây là một thực hành sản phẩm **đã được kiểm chứng trong ngành suốt >10 năm**, không phải mốt. Rủi ro adoption thấp (chỉ là kỷ luật hỏi), giá trị cao (ngăn xây nhầm thứ — lỗi đắt nhất). **Verdict: LÀM.**

**Cách update (cụ thể):** thêm một mục con dưới "Ask clarifying questions" trong `SKILL.md`:
- Trước khi sang "Propose approaches", quét opening của user qua 4 lăng kính (kèm 1 câu hỏi mẫu mỗi lăng kính).
- Chỉ probe lăng kính nào thực sự khuyết. Probe để mở (không menu) — vì menu sẽ mách user "loại bằng chứng nào được tính".
- Ghi chú nguồn: "dựa trên The Mom Test — hỏi hành vi quá khứ, không hỏi giả định."

### 1.2 Làm brainstorming nhận biết lane — *sửa lỗi nhất quán + bằng chứng tỉ lệ*

**Hiện trạng:** câu "Every project goes through this process... regardless of perceived simplicity" mâu thuẫn trực tiếp với `orchestration.md` (lane tiny → sửa thẳng) và với artifact policy (design.md theo tín hiệu).

**Phân giải mâu thuẫn (quan trọng — không phải chỉ nới lỏng):** HARD-GATE ("trình design + được duyệt trước khi implement") là luật **bên trong** skill brainstorming. `feature-intake` mới là cái quyết định **có bước vào** brainstorming hay không. Với lane `tiny`, ta **không gọi brainstorming** → không có xung đột. Vấn đề nằm ở câu chữ "mọi dự án regardless of simplicity" — nên sửa thành **"mọi dự án *đáng* brainstorm"**, và để độ sâu artifact + review co giãn theo lane.

**Bằng chứng ngoài:** nguyên lý cân xứng nỗ lực-rủi ro được chống lưng bởi dữ liệu **cost-of-change của Boehm** — lỗi yêu cầu (requirements) phát hiện muộn đắt hơn 50–200× so với sửa sớm. Hệ quả hai chiều:
- Với việc **đáng kể**: đầu tư brainstorm + review sớm là rẻ so với hậu quả → giữ full ceremony.
- Với việc **tiny**: chi phí hậu quả thấp, nên ceremony nặng là lãng phí thuần → cắt.

*Lưu ý trung thực về bằng chứng:* con số "100×/200×" của Boehm lấy từ dự án waterfall TRW/IBM thập niên 1970 và **bị tranh luận** với agile hiện đại (xem Slashdot debate). **Hướng** (sớm = rẻ hơn) vững; **độ lớn** thì không nên trích tuyệt đối. Dùng nó để biện minh *sự cân xứng*, không phải để dọa bằng con số.

**Verdict: LÀM** (đây vừa là cải tiến vừa là sửa lỗi đúng-đắn nội bộ).

**Cách update (cụ thể):**
- Đầu `SKILL.md`: đọc `specs/<slug>/SUMMARY.md` → `Lane:` nếu feature-intake đã chạy.
- Sửa anti-pattern "This Is Too Simple": HARD-GATE vẫn áp **khi đã ở trong brainstorming**; nhưng brainstorming không nên được gọi cho lane tiny.
- Bảng co giãn: `tiny` → không vào skill này / căn chỉnh ngắn, có thể bỏ `design.md`; `normal` → flow hiện tại + subagent review 1 vòng; `high-risk` → full chain + subagent loop tới 5 vòng.

---

## TIER 2 — Bằng chứng mạnh, công cố vừa phải

### 2.1 Đảo thứ tự: trình bày hết phương án RỒI mới khuyến nghị (anti-anchoring)

**Hiện trạng:** SKILL.md ta ghi *"Lead with your recommended option and explain why"* (kế thừa từ superpowers). ce-brainstorm làm ngược: present-all-then-recommend.

**Bằng chứng ngoài (mạnh, và đặc biệt khớp bối cảnh AI):** **anchoring bias** là một trong những thiên kiến nhận thức được xác lập chắc nhất — thông tin đầu tiên trở thành "mỏ neo" bóp méo phán đoán sau đó. Quan trọng hơn: một nghiên cứu 2025 trên *AI-assisted decision making* (ScienceDirect) cho thấy **khuyến nghị của AI trực tiếp neo phán đoán của con người** — đúng kịch bản của ta (agent đưa khuyến nghị cho user). Dẫn bằng khuyến nghị = đặt mỏ neo trước khi user kịp cân nhắc các phương án.

**Verdict: LÀM** — thay đổi rẻ nhất (sửa câu chữ), bằng chứng mạnh, khớp bối cảnh AI-đưa-khuyến-nghị. Đây là điểm hiếm hoi ce-brainstorm vượt cả ta lẫn superpowers gốc.

**Cách update:** đổi 2 chỗ trong `SKILL.md`:
- "Exploring approaches": *"Present all approaches and their trade-offs first; give your recommendation only after the user has seen the full set."*
- Key Principles: bỏ "Lead with your recommended option", thêm "Present-then-recommend (avoid anchoring)".

### 2.2 Checkpoint tổng hợp phạm vi trước khi viết `design.md`

**Hiện trạng:** ta duyệt design theo **từng section** (step 5) rồi viết doc. Không có bước "thu nhỏ — xác nhận toàn cảnh".

**Insight của ce-brainstorm:** *duyệt từng mảnh ≠ duyệt tổng thể*. Sau đối thoại one-question-at-a-time, user đã đồng ý nhiều thứ rời rạc nhưng chưa bao giờ thấy bức tranh ghép lại — nơi các **hệ quả không hiển nhiên** của việc kết hợp câu trả lời lộ ra.

**Bằng chứng ngoài:** Boehm cost-of-change lần nữa — checkpoint này bắt lỗi *phạm vi/yêu cầu* **trước khi** doc rơi xuống `writing-plans`/implementation, tức ở điểm rẻ nhất trong đường cong chi phí.

**Đánh giá thực tế:** vì ta **đã có** duyệt từng section, giá trị gia tăng tập trung ở 2 phần ce-brainstorm có mà ta thiếu: (a) **integration check** — chủ động ghép câu trả lời để lộ hệ quả; (b) **call-outs** — nêu các "đặt cược phạm vi" để user xác nhận/điều hướng. Phần "tóm tắt lại toàn bộ" thì trùng một phần với section-approval.

**Verdict: LÀM PHIÊN BẢN GỌN** — thêm một bước xác nhận-toàn-cảnh ngắn (không phải bê nguyên cỗ máy 2-stage/Path A/B/soft-cut của ce-brainstorm vào — quá nặng cho ta). Trọng tâm: integration check + 1–3 call-out trước khi viết doc.

**Cách update:** thêm bước 5.5 giữa "Present design" và "Write design doc": *"Trước khi viết, ghép các quyết định lại và nêu (1) hình dạng tổng thể 1–3 câu, (2) 0–3 call-out là hệ quả/đặt cược phạm vi không hiển nhiên. Chờ xác nhận rồi mới viết."*

---

## TIER 3 — Bằng chứng ĐẢO NGƯỢC khuyến nghị cũ

### 3.1 ⚠️ KHÔNG dùng self-review của superpowers cho tầng nhẹ — bằng chứng phản bác

**Khuyến nghị CŨ (trong doc superpowers):** "dùng self-review nhẹ của superpowers cho tiny/Lightweight, giữ subagent loop cho normal/high-risk."

**Bằng chứng làm tôi RÚT LẠI một phần khuyến nghị này:** Huang et al., *"Large Language Models Cannot Self-Correct Reasoning Yet"* (ICLR 2024) — LLM **tự sửa mình mà không có phản hồi ngoài** thường không cải thiện, và **có lúc còn tệ đi** sau khi tự sửa. Self-review (agent tự đọc lại spec mình vừa viết) chính là kịch bản intrinsic self-correction mà paper này cảnh báo.

→ Hệ quả: **review độc lập bằng subagent của ta là lựa chọn ĐÚNG đã được kiểm chứng** (subagent = "phản hồi ngoài"). Không nên hạ cấp xuống self-review chỉ để tiết kiệm, kể cả với việc nhỏ — vì self-review là đúng cái setting yếu nhất.

**Sắc thái cân bằng (không tuyệt đối hóa):**
- Paper mới hơn (*Self-Correct with Key Condition Verification*, EMNLP 2024) cho thấy self-correction **CÓ** thể hoạt động với phương pháp prompting đúng. Nên đây không phải "self-review luôn vô dụng".
- Quan trọng: self-review **kiểu checklist xác minh** (quét TBD/placeholder, mâu thuẫn, đúng phạm vi) gần với *verification* hơn là *reasoning self-correction* — rủi ro thấp hơn nhiều. Quét placeholder không phải "tự sửa lập luận".

**Verdict (đã hiệu chỉnh):** Với lane nhẹ, **không** bỏ review độc lập để thay bằng agent tự phê bình lập luận. Nếu cần tầng rẻ, hãy (a) dùng **checklist self-verification cơ học** (TBD/placeholder/mâu thuẫn — an toàn) HOẶC (b) dùng **subagent độc lập 1 vòng** (rẻ hơn full loop nhưng vẫn là phản hồi ngoài). Giữ subagent loop đầy đủ cho high-risk. → Đây là ví dụ bằng chứng ngoài trực tiếp chỉnh lại thiết kế.

---

## KHÔNG ưu tiên (giá trị thấp cho bối cảnh của ta)

- **HTML output / non-software routing / CONCEPTS.md vocab capture** (từ ce-brainstorm): ta là repo FastAPI nội bộ; các tính năng này tốn công bảo trì, ít giá trị.
- **Resume detection brainstorm** (Phase 0.1): hữu ích nhưng biên; để sau.
- **Section catalog prose-economy đầy đủ của ce-brainstorm:** đáng tham khảo cho `spec-document-reviewer-prompt.md`, không cần bê nguyên.

---

## Lộ trình đề xuất (xếp theo ROI)

| # | Thay đổi | Bằng chứng | Chi phí | Rủi ro |
|---|---|---|---|---|
| 1 | Anti-anchoring: present-then-recommend | Anchoring bias + AI-anchoring study (mạnh) | Rất thấp (sửa câu) | Rất thấp |
| 2 | Lane-aware + sửa mâu thuẫn "every project" | Boehm proportionality + nhất quán nội bộ | Thấp | Thấp |
| 3 | Product Pressure Test (4 gap lenses) | The Mom Test (industry-proven) | Vừa | Thấp |
| 4 | Synthesis checkpoint gọn (integration check + call-outs) | Boehm cost-of-change | Vừa | Thấp |
| 5 | Giữ review độc lập; KHÔNG hạ xuống self-review | LLM-cannot-self-correct (ICLR'24) | 0 (đã đúng) | — |

**Khuyến nghị tổng:** làm #1 và #2 trước (rẻ, một phần là sửa lỗi đúng-đắn), rồi #3 (giá trị cao nhất), rồi #4. #5 là xác nhận giữ nguyên thiết kế hiện tại (đừng "tối ưu" nhầm hướng).

Mọi thay đổi đụng `skills/brainstorming/SKILL.md` (core skill, rủi ro cao theo rules) → cần đi qua feature-intake + plan trước khi sửa.

---

## Nguồn

- Anchoring bias (tổng quan + AI context): [The Decision Lab](https://thedecisionlab.com/biases/anchoring-bias), [EBSCO Research Starters](https://www.ebsco.com/research-starters/social-sciences-and-humanities/anchoring-cognitive-bias), [ScienceDirect — anchoring in AI-assisted decision making (2025)](https://www.sciencedirect.com/science/article/pii/S0268401225000076)
- LLM tự sửa: [Huang et al., "LLMs Cannot Self-Correct Reasoning Yet", ICLR 2024 (arXiv:2310.01798)](https://arxiv.org/abs/2310.01798); phản đề có điều kiện: [Self-Correct with Key Condition Verification, EMNLP 2024 (arXiv:2405.14092)](https://arxiv.org/pdf/2405.14092)
- Product discovery / hỏi hành vi quá khứ: [The Mom Test — mtlynch.io review](https://mtlynch.io/book-reports/the-mom-test/), [UXtweak — What Is the Mom Test](https://blog.uxtweak.com/the-mom-test/), [3 Rules to Customer Interviews](https://www.atlantaventures.com/blog/the-3-rules-to-customer-interviews-from-the-mom-test)
- Cost-of-change (Boehm) + tranh luận độ lớn: [Steve McConnell — An Ounce of Prevention](https://stevemcconnell.com/articles/an-ounce-of-prevention/), [DZone — Real Cost of Change](https://dzone.com/articles/real-cost-change-software), [Slashdot — Do Late Bugs Really Cost More?](https://developers.slashdot.org/story/03/10/21/0141215/software-defects---do-late-bugs-really-cost-more)
