# Nghiên cứu — "Harness Engineering" của OpenAI và những gì repo này có thể học hỏi

> **Phương pháp:** harness deep-research (fan-out tìm kiếm web → tải 22 nguồn → trích xuất 100 luận điểm →
> xác minh đối nghịch 3 phiếu, 2/3 để loại). 25 luận điểm được xác minh, **15 xác nhận, 10 bị loại**.
> **Ngày:** 2026-06-13.
>
> **Lưu ý về tính trung thực của nguồn:** ba luận điểm lấy *trực tiếp* từ
> `openai.com/index/harness-engineering/` hiển thị là "bị bác bỏ" trong dữ liệu thô nhưng thực ra
> **đã bỏ phiếu trắng (0-0)** — các agent xác minh chạm giới hạn phiên, không phải bị bác bỏ thật sự. Phần
> tổng hợp bên dưới dựa vào 15 luận điểm sống sót qua xác minh đối nghịch 3 phiếu (bài viết của
> InfoQ, nguồn gốc về vòng lặp agent của Codex, một bài báo arXiv về harness, và các hướng dẫn thực hành),
> và đánh dấu các luận điểm từ trang gốc là được-củng-cố-nhưng-chưa-xác-minh. Chạy lại quá trình xác minh
> sẽ giúp củng cố những điều đó.

---

## 1. OpenAI muốn nói gì khi dùng "harness engineering"

Cách định khung lại cốt lõi, được xác nhận xuyên suốt các nguồn gốc + thứ cấp:

- **"Harness" chính là agent** — vòng lặp điều phối bao quanh model, không phải bản thân model.
  Codex gọi chính vòng lặp agent của mình là "the harness."
  [[unrolling-the-codex-agent-loop](https://openai.com/index/unrolling-the-codex-agent-loop/), 3-0]
- Harness engineering **chuyển kỹ sư con người từ việc viết code sang việc thiết kế môi trường,
  đặc tả ý định, và cung cấp phản hồi có cấu trúc** — agent thực hiện việc viết code.
  [[InfoQ](https://www.infoq.com/news/2026/02/openai-harness-engineering-codex/), 3-0]
- Harness **mã hóa scaffolding, vòng lặp phản hồi, tài liệu, và các ràng buộc kiến trúc
  thành các artifact máy-đọc-được mà agent tiêu thụ.** [InfoQ, 3-0]
- Cách định khung của giới thực hành (Augment Code): "kỷ luật thiết kế môi trường, ràng buộc, và
  vòng lặp phản hồi để giúp các AI coding agent đáng tin cậy ở quy mô lớn … *Con người lái. Agent thực thi.*"
  [[augmentcode](https://www.augmentcode.com/guides/harness-engineering-ai-coding-agents), 2-1]

Kết quả nổi bật — ~1 triệu dòng code trong một thử nghiệm nội bộ kéo dài ~5 tháng, bốn vấn đề
nổi lên — được xác minh qua bài viết của Milvus [3-0]. Phiên bản mạnh nhất về "không có dòng nào viết
tay" chỉ xuất hiện trên chính trang của OpenAI và chưa được xác minh trong lần chạy này.

## 2. Bốn vấn đề OpenAI gặp ở quy mô lớn, và cách họ khắc phục

[[Milvus](https://milvus.io/blog/harness-engineering-ai-agents.md), 3-0]

1. **Kiến trúc tài liệu** — thu nhỏ các file hướng dẫn khổng lồ; dùng các thư mục `docs/`
   có cấu trúc *kèm một linter để kiểm chứng tài liệu*.
2. **Kiểm chứng ở quy mô lớn** — tự động hóa trình duyệt + ngưỡng hiệu năng số cụ thể
   (không phải "nhìn ổn").
3. **Ràng buộc kiến trúc** — các linter tùy chỉnh ép buộc phụ thuộc theo tầng, cung cấp
   *bản sửa inline*.
4. **Phòng ngừa nợ kỹ thuật** — các agent nền quét tìm sai lệch và gửi PR
   tái cấu trúc.

## 3. Các nguyên lý chịu lực (đã xác minh)

| Nguyên lý | Bằng chứng |
|---|---|
| **Tính tất định hơn là prompt** — "bảo một agent tuân theo tiêu chuẩn trong prompt khác về bản chất so với việc cài đặt một linter chặn PR." | augmentcode, 3-0 |
| **Nguyên lý bánh cóc (ratchet)** — khi một agent mắc lỗi, hãy thiết kế một bản sửa vĩnh viễn để nó *không bao giờ mắc lại lỗi đó* (Mitchell Hashimoto). | [techtimes](https://www.techtimes.com/articles/316587/20260513/harness-engineering-emerges-fourth-paradigm-ai-engineering.htm), 3-0 |
| **Phòng thủ theo chiều sâu, 5 tầng độc lập, không có điểm hỏng đơn lẻ** — guardrail ở prompt → schema/allowlist → phê duyệt runtime → kiểm chứng ở cấp tool (blocklist mẫu nguy hiểm, phát hiện đọc dữ liệu cũ, cắt ngắn output) → lifecycle hook có thể chặn hoặc biến đổi tham số. | [arXiv](https://arxiv.org/html/2603.05344v2), 3-0 |
| **Ép buộc phân tầng cơ học** — các test cấu trúc kiểm chứng một chuỗi phụ thuộc có kiểm soát (Types→Config→Repo→Service→Runtime→UI) và chặn các vi phạm. | InfoQ, 2-0 |
| **Ranh giới tin cậy cho tool** — Codex sandbox *các tool của chính nó* nhưng dứt khoát KHÔNG mở rộng điều đó cho các MCP tool; chúng phải tự thực thi guardrail của mình. | [zenml](https://www.zenml.io/llmops-database/building-production-ready-ai-agents-openai-codex-cli-architecture-and-agent-loop-design), 3-0 |
| **Quản lý context-window là trách nhiệm của harness** — một lượt có thể thực hiện hàng trăm tool call và làm cạn cửa sổ. | OpenAI nguồn gốc, 3-0 |
| **Runtime dùng chung tái sử dụng** — lõi Codex là một thư viện Rust duy nhất dùng chung cho CLI/web/IDE/macOS, không phải keo dán riêng cho từng bề mặt. | [swequiz](https://www.swequiz.com/articles/openai-codex-architecture), 3-0 |
| **Phân cấp hướng dẫn theo tầng** — `AGENTS.override.md` / `AGENTS.md` xuyên các thư mục, giới hạn 32 KiB. | zenml, 3-0 |

**Các luận điểm bị loại** (sự tô vẽ của nguồn thứ cấp, *không phải* cách định khung thực tế của OpenAI):

- Phân loại "kiến trúc ràng buộc ba tầng" gọn gàng [0-3]
- "Agent = Model + Harness" như một nguyên lý mà OpenAI tuyên bố [0-3]
- "Harness engineering là *mô hình thứ tư*" [1-2]
- "Generator phải tách hoàn toàn khỏi evaluator, kiểu GAN" [0-3]

---

## 4. Những gì đáng "mượn" — ánh xạ vào repo này

Phát hiện nổi bật: **repo này đã hiện thực hầu hết các nguyên lý đã được xác minh của OpenAI.** Các
khoảng trống là cụ thể và nhỏ.

1. **Tính tất định hơn là prompt — đã làm.** Các hook (`risk-corroboration.sh`,
   `commit-quality-gate.sh`, `blast-radius-check.sh`) chính xác là "cài đặt một linter chặn
   PR" thay vì "lịch sự nhờ agent." Ý tưởng lớn nhất trong bài viết đã là
   kiến trúc của repo. ✅
2. **Phòng thủ theo chiều sâu — đã làm.** Các tầng ánh xạ ~1:1 với năm tầng của OpenAI: `rules/behavior.md`
   (prompt) → allowlist theo lane + Rule 4 của `auto-correct-scope.md` (schema/phê duyệt) → hook
   (cấp tool + lifecycle). ✅
3. **KHOẢNG TRỐNG — nguyên lý bánh cóc là mắt xích yếu nhất.** OpenAI: *mọi* lỗi của agent đều trở thành
   một guardrail cơ học vĩnh viễn. `/compound` viết một *tài liệu tri thức* (một track `failure` có
   trường "Guardrail") — nhưng tài liệu là cấp prompt, không phải tất định. **Hành động:** khi `/compound`
   ghi nhận một `failure`, nó nên *đề xuất một hook hoặc một test cấu trúc*, không chỉ văn xuôi. Khép
   kín vòng lặp từ "bài học được ghi lại" → "quy tắc được ép buộc cơ học." Repo này dừng cách bánh cóc
   đúng một bước.
4. **KHOẢNG TRỐNG — "kiểm chứng tài liệu."** OpenAI chạy một *linter trên tài liệu của họ*. Repo này có một
   trường hợp (lint doc-truth ở CI, fail khi bảng hook mâu thuẫn với `settings.json`).
   **Hành động:** mở rộng mẫu hình đó — lint bảng Integration Evidence Tiers, bản đồ handoff
   skill, và độ cũ của `confirmed_at` trong `docs/solutions/` một cách cơ học thay vì theo quy ước.
5. **Ranh giới tin cậy cho MCP tool.** Repo này bắt buộc dùng `code-review-graph` và `context7` nhưng
   coi output của chúng là đáng tin. Bài học của OpenAI: harness sandbox các tool của chính nó nhưng MCP
   tool tự thực thi guardrail của mình. **Hành động:** ghi chú trong CLAUDE.md rằng output của MCP-tool là
   đầu vào không đáng tin — khớp với quy tắc `not_observed != absent` hiện có.
6. **Agent nền phòng ngừa nợ.** OpenAI chạy các agent quét tìm sai lệch kiến trúc
   và mở PR tái cấu trúc. Repo này có sẵn nguyên liệu (`blast-radius-check`, điều phối
   subagent) nhưng chưa có lượt quét định kỳ. Phù hợp tự nhiên với `/schedule` hoặc `/loop`. Ưu tiên thấp nhất;
   là năng lực duy nhất hoàn toàn chưa có.

---

## 5. Kết luận

Harness engineering của OpenAI **hội tụ với những gì repo này đã xây** — bài viết
xác nhận đặt cược cốt lõi (cổng cơ học > tiêu chuẩn qua prompt, phòng thủ theo chiều sâu, artifact
quản trị máy-đọc-được). Hai ý tưởng thực sự đáng nhập về:

1. **Hoàn thiện bánh cóc**: các `failure` của `/compound` nên phát ra một *guardrail được đề xuất*, không chỉ
   một tài liệu. (Đòn bẩy cao hơn; thay đổi gọn trong output của track `failure`.)
2. **Lint chính các tài liệu quản trị của bạn** rộng hơn — mở rộng lint doc-truth ở CI hiện có sang
   các evidence tier và bản đồ handoff.

---

## Nguồn

**Nguồn gốc:**
- https://openai.com/index/harness-engineering/ (trang gốc — các luận điểm bỏ phiếu trắng lần chạy này)
- https://openai.com/index/unrolling-the-codex-agent-loop/
- https://arxiv.org/html/2603.05344v2

**Thứ cấp / thực hành:**
- https://www.infoq.com/news/2026/02/openai-harness-engineering-codex/
- https://milvus.io/blog/harness-engineering-ai-agents.md
- https://www.augmentcode.com/guides/harness-engineering-ai-coding-agents
- https://www.swequiz.com/articles/openai-codex-architecture
- https://www.zenml.io/llmops-database/building-production-ready-ai-agents-openai-codex-cli-architecture-and-agent-loop-design
- https://www.techtimes.com/articles/316587/20260513/harness-engineering-emerges-fourth-paradigm-ai-engineering.htm
- https://martinfowler.com/articles/harness-engineering.html
- https://addyosmani.com/blog/agent-harness-engineering/
