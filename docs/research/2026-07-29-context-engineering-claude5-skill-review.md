# Research — Context Engineering cho Claude 5 & rà soát skill/rule trong harness-skills

> Ngày: 2026-07-29 · Nguồn: [The New Rules of Context Engineering for Claude 5-Generation Models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)
> (Anthropic blog) · Câu hỏi: repo `harness-skills` (skills + rules + CLAUDE.md) nên áp dụng gì từ
> triết lý context-engineering mới này, và hiện đang lệch/khớp ở đâu?
>
> Phương pháp: fetch + trích toàn văn bài viết → khảo sát thực tế repo bằng 1 subagent Explore
> (line count, mật độ ngôn ngữ cứng nhắc MUST/NEVER/ALWAYS, kiểm tra lặp lại, progressive
> disclosure, prose vs. schema) → đối chiếu 2 nguồn để ra đề xuất. Đây là tài liệu **research/đề
> xuất**, chưa triển khai — các mục ở phần 4 là candidate cho một lane riêng nếu được duyệt.

---

## 1. Tóm tắt bài viết

**Phát hiện cốt lõi:** Anthropic đã lược bỏ hơn 80% system prompt của Claude Code cho các model
thế hệ mới (Opus 5, Fable 5) mà không đo được suy giảm hiệu suất trên coding eval. Các model mới
đủ khả năng phán đoán nên phần "giàn giáo quy tắc" (rule-scaffolding) nặng nề trở thành yếu tố gây
hại ròng — tạo chi phí cân nhắc thừa và tê liệt do chỉ dẫn mâu thuẫn (ví dụ cũ: "để lại tài liệu
khi phù hợp" đối lập với "KHÔNG được thêm comment").

**5 thay đổi, cũ → mới:**

| Cũ | Mới |
|---|---|
| Quy tắc tường minh ("không bao giờ viết docstring nhiều đoạn, tối đa một dòng") | Hướng dẫn theo phán đoán ("khớp mật độ comment với code xung quanh") |
| Ví dụ minh họa cách dùng tool đúng | Thiết kế tool rõ ràng (tham số/enum rõ ràng) tự ngụ ý cách dùng đúng |
| Nhồi toàn bộ thông tin vào system prompt từ đầu | Tiết lộ dần (progressive disclosure) — tách thành Skills load theo nhu cầu, schema tool trì hoãn |
| Lặp lại cùng chỉ dẫn ở cả system prompt lẫn mô tả tool | Một nơi thẩm quyền duy nhất cho mỗi chỉ dẫn |
| Lưu memory thủ công qua phím tắt `#` | Tự động ghi nhận memory |
| Spec bằng markdown thuần | Tham chiếu phong phú — HTML mockup, test suite thật, rubric, code thật |

**Hướng dẫn thực tế của bài viết:**
- CLAUDE.md nên gọn nhẹ, chỉ chứa điều "không hiển nhiên" (bỏ qua những gì Claude tự khám phá
  được từ filesystem).
- Dùng `/doctor` để cân chỉnh lại context định kỳ.
- Loại bỏ mâu thuẫn giữa system prompt / Skills / lượt yêu cầu của user.
- Ưu tiên spec dạng code (mockup HTML, test suite, rubric) hơn mô tả văn xuôi/ảnh chụp màn hình —
  vì code là ngôn ngữ model hiểu với độ trung thực cao.

## 2. Ý tưởng chắt lọc

Chủ đề xuyên suốt: **đừng quyết định thay model những gì model có thể tự quyết, và đừng nói cùng
một điều hai lần.** Chỉ ràng buộc tuyệt đối ở nơi một phán đoán sai thực sự tốn kém (không thể đảo
ngược, ảnh hưởng diện rộng, liên quan bảo mật/mất dữ liệu); còn lại nói rõ *lý do* (why) và để
model tự quyết *cách làm* (how). Về cấu trúc: ít quy tắc tuyệt đối hơn, nhiều điểm tham chiếu
nguồn-duy-nhất hơn, nội dung chỉ load khi task thực sự cần.

## 3. Đối chiếu với repo hiện tại

Khảo sát thực hiện bằng 1 subagent Explore, đọc toàn văn `rules/behavior.md`,
`rules/orchestration.md`, `CLAUDE.md`; sample-read các SKILL.md lớn nhất.

### 3.1 Những gì repo đã làm đúng

- **Không SKILL.md nào vượt 76 dòng** (`feature-intake` lớn nhất trong 12 skill) — còn xa ngưỡng
  cần tiết lộ dần thêm. `rules/*.md` dao động 9–180 dòng (`plan-format.md` lớn nhất), `CLAUDE.md`
  92 dòng — tất cả dưới ngưỡng ~300 dòng.
- **7/12 skill đã externalize chi tiết** ra `references/`, `templates/`, `tests/`, hoặc file
  prompt riêng thay vì gộp vào một SKILL.md monolithic: `brainstorming`, `compound`,
  `finishing-a-development-branch`, `subagent-driven-development`, `visual-planner`,
  `writing-plans`, `xia2`.
- **`rules/behavior.md` — tài liệu định hình phán đoán chung — có 0 lượt xuất hiện
  MUST/NEVER/ALWAYS/hard-gate.** Dùng ngôn ngữ mềm ("bias toward caution", "use judgment"), đúng
  tinh thần "tin tưởng model" của bài viết.
- **Ngôn ngữ cứng nhắc tập trung đúng chỗ**: MUST/NEVER/hard-gate xuất hiện chủ yếu ở
  `rules/auto-correct-scope.md` (5 lượt) và `rules/orchestration.md` (3 lượt) — cả hai quản lý
  ranh giới tự chủ và hành động không thể đảo ngược. Đúng nguyên tắc "chỉ ràng buộc nơi phán đoán
  sai thực sự tốn kém" — không cần sửa.
- **4 skill cốt lõi được kiểm tra** (feature-intake, correctness-review,
  subagent-driven-development, writing-plans) đều **tham chiếu** (`Read rules/...` ở đầu) thay vì
  copy-paste rule chung — nguyên tắc nguồn-duy-nhất được tôn trọng khá tốt ở tầng này.
- **`rules/plan-format.md` đã dùng schema/ví dụ inline thật** (task block ~dòng 1-164) thay vì mô
  tả văn xuôi — đúng nguyên tắc "code hơn mô tả" của bài viết.

### 3.2 Những điểm lệch khỏi triết lý bài viết

> Đánh số nối tiếp danh sách 4 mục gốc trong phần thảo luận trước khi viết doc này — mục **1**
> (ngôn ngữ cứng nhắc đặt đúng chỗ) đã chuyển sang §3.1 vì không phải điểm lệch, nên phần này bắt
> đầu từ **2**.

**(2) Lane/Confidence taxonomy lặp lại ở 4 nơi, không có điểm định nghĩa gốc duy nhất.**
`tiny | normal | high-risk` và `high | medium | low` xuất hiện ở:
- `rules/orchestration.md` (mục "Intake fields")
- `rules/auto-correct-scope.md` (bảng lane-aware autonomy, dòng ~19-26)
- `skills/feature-intake/SKILL.md` (bước classify/assign, dòng ~23-32; bảng Routes dòng ~48)
- `CLAUDE.md` (chuỗi workflow, dòng ~21-34)

Mỗi chỗ có góc nhìn khác nhau (phạm vi tự chủ vs. yêu cầu bằng chứng vs. quy trình phân loại vs.
chuỗi workflow) nên không phải copy-paste thuần, nhưng không có điểm neo "định nghĩa nằm ở đây,
chỗ khác chỉ link tới". Đây đúng kiểu lặp lại bài viết cảnh báo: nếu sửa một bản mà quên sửa bản
khác, chúng lệch nhau âm thầm — vi phạm nguyên tắc "một nơi thẩm quyền duy nhất".

> **Thảo luận 2026-07-29 (rà soát trước khi triển khai mục 2 ở §4).** Đọc lại cả 4 nơi cho thấy
> đề xuất gốc gộp nhầm 4 thứ khác nhau làm một. Chỉ 1/4 nơi thật sự chứa *định nghĩa* — thuật toán
> phân loại (`feature-intake/SKILL.md` Step 3, dòng 23-25: hard gate → `high-risk`; 0-1 flag +
> 1-file → `tiny`; 2-3 flag → `normal`; 4+ → `high-risk`). Ba nơi còn lại chứa thông tin **không
> thể thay bằng link mà không mất nội dung**: `orchestration.md` §Intake fields khai field +
> consumer (`risk-corroboration.sh`, trust ledger), không phải cách tính; `auto-correct-scope.md`
> bảng lane-aware là **hệ quả tự chủ** của mỗi lane (autonomy/plan/human-confirm) — một trục thông
> tin khác hẳn, không trùng lặp; `CLAUDE.md` (dòng 21-36) đã tự trỏ nguồn từ trước ("See
> `rules/orchestration.md`, `skills/feature-intake/SKILL.md`... for the full inventory") và không
> liệt kê đủ enum — không cần sửa. Cái thật sự lặp lại chỉ là **chuỗi giá trị enum** xuất hiện ở
> 3/4 nơi, giống một type dùng chung ở nhiều module — rủi ro hẹp hơn nhiều so với mô tả gốc: drift
> khi rename, không phải chỉ dẫn mâu thuẫn.
>
> Cân nhắc 2 hướng khắc phục: (1) chỉ gắn nhãn "nguồn gốc" trỏ về `feature-intake/SKILL.md` Step 3
> ở 2 nơi còn lại — rẻ, không đổi hành vi, nhưng không tự động ngăn drift; (2) cơ giới hóa bằng
> script check enum values giữa các file (giống pattern `scripts/verify_summary.py --lane` +
> `check_manifest.py` đã làm cho evidence mapping) — ngăn drift thật nhưng tốn công hơn nhiều
> (sửa `scripts/`, cần test riêng) để giải quyết một rủi ro **chưa từng xảy ra** trong lịch sử
> repo — ngược nguyên tắc "đừng thiết kế cho yêu cầu giả định" của chính CLAUDE.md.
>
> **Quyết định:** hướng (1) — thu hẹp. Thêm 1 dòng ở `rules/orchestration.md` §Intake fields và
> `rules/auto-correct-scope.md` bảng lane-aware, trỏ về `feature-intake/SKILL.md` Step 3 là nơi
> thuật toán phân loại sống. Không xóa/thay bảng hay thuật toán nào ở 3 nơi kia. Chưa triển khai —
> để lại cho một lượt riêng.

**(3) `correctness-scorer-prompt.md` nhúng giai thoại văn xuôi thay vì case có cấu trúc.**
Dòng ~93-98 kể một câu chuyện văn xuôi ("Worked example, 2026-07-13, PR #51") thay vì bảng/rubric
như `skills/feature-intake/tests/*.md` đã làm cho canary case. Nguyên tắc "tham chiếu độ trung
thực cao hơn ví dụ văn xuôi" gợi ý chuyển thành test case có cấu trúc — pattern repo đã dùng ở nơi
khác (`skills/xia2/tests/`, `skills/feature-intake/tests/`), chỉ chưa áp dụng ở đây.

> **Thảo luận 2026-07-29 (rà soát trước khi triển khai mục 3 ở §4).** Điểm quan trọng bị bỏ sót
> ở lần khảo sát đầu: đoạn giai thoại này **không phải tài liệu bên lề** — nó nằm bên trong khối
> ` ``` ` (dòng 31-138) chính là nội dung `prompt: |` gửi thẳng cho scorer subagent lúc runtime.
> Ngược lại, `feature-intake/tests/lane-classification-cases.md` — pattern được lấy làm hình mẫu —
> là file canary/eval nằm **ngoài** context runtime, chỉ dùng để kiểm hồi quy `SKILL.md`, không
> được nạp vào prompt lúc chạy. Hai việc khác bản chất: một là few-shot calibration sống trong
> prompt thật, một là fixture kiểm định bên ngoài. Do đó "bê nguyên giai thoại ra
> `skills/correctness-review/tests/` và xóa khỏi prompt" — như đề xuất gốc mô tả — là **thay đổi
> hành vi runtime**, không phải "sửa tài liệu thuần" như bảng rủi ro ở §4 từng ghi.
>
> **Quyết định:** giữ giai thoại **in-prompt** (không chuyển ra `tests/`), chỉ **nén còn 1-2 dòng
> structured** (case + verdict) để cắt phần văn xuôi thừa mà không mất tín hiệu hiệu chỉnh cho
> model chấm điểm. Chưa triển khai — sửa `correctness-scorer-prompt.md` dòng 93-98 để lại cho một
> lượt riêng.

**(4) `context-propagation-audit` là skill duy nhất không có file `references/` hỗ trợ.**
Ở mức 38 dòng thì chưa cần tách — chỉ ghi nhận làm điểm cần theo dõi nếu skill này phình to.

## 4. Đề xuất (candidate cho lane riêng, chưa triển khai)

| # | Đề xuất | Giá trị | Rủi ro/effort |
|---|---|---|---|
| 2 | ~~Chỉ định orchestration.md là nguồn chính thức, 3 chỗ còn lại link tới~~ → **Gắn nhãn "nguồn gốc" trỏ về `feature-intake/SKILL.md` Step 3 (nơi thuật toán phân loại thật sự sống) ở `rules/orchestration.md` §Intake fields và `rules/auto-correct-scope.md` bảng lane-aware; không xóa/thay nội dung nào ở 2 nơi này hay ở `CLAUDE.md`** (quyết định sau thảo luận §3.2 mục 2 — xem hộp thảo luận) | Đóng lỗ hổng "không biết định nghĩa taxonomy nằm ở đâu" mà không mất bảng autonomy hay thuật toán phân loại đang có | Thấp — 2 dòng thêm ở 2 file doc, không đổi `scripts/`/`hooks/`; không tự động ngăn drift khi rename lane (đã cân nhắc và loại phương án cơ giới hóa vì tốn công cho rủi ro chưa từng xảy ra) |
| 3 | ~~Chuyển giai thoại ra `tests/`~~ → **Nén giai thoại "Worked example PR #51" trong `correctness-scorer-prompt.md` (dòng 93-98) thành 1-2 dòng structured, giữ nguyên vị trí in-prompt** (quyết định sau thảo luận §3.2 mục 3 — xem hộp thảo luận) | Cắt văn xuôi thừa mà không mất tín hiệu hiệu chỉnh cho scorer model lúc runtime | Thấp-trung bình — sửa nội dung nằm trong prompt runtime thật (không phải doc thuần); nên đối chiếu lại 1-2 lượt scorer sau khi sửa để chắc hành vi score-0 trên `unmodified-line` không đổi |
| 4 (không làm) | Tách `context-propagation-audit` ra `references/` | Chưa cần — 38 dòng, dưới ngưỡng | — |
| 1 (không làm) | Giảm mật độ MUST/NEVER ở `auto-correct-scope.md`/`orchestration.md` | Sai hướng — đây là đúng chỗ để có ngôn ngữ cứng theo chính bài viết (ranh giới tự chủ, hành động khó đảo ngược) | — |

**Khuyến nghị:** mục 2 và 3 vẫn là hai mục có giá trị triển khai thật, nhưng không còn đồng nhất
về hồ sơ rủi ro sau thảo luận. Mục 2, sau khi xác định chỉ 1/4 nơi (`feature-intake/SKILL.md` Step
3) chứa định nghĩa thật và 3 nơi còn lại không thể thay bằng link mà không mất nội dung, đã thu hẹp
xuống thành 2 dòng anchor thuần túy — sửa tài liệu, không đổi `scripts/`/`hooks/`, không mất bảng
autonomy hay thuật toán phân loại nào đang có. Mục 3, sau khi xác định giai thoại nằm trong prompt
runtime (không phải doc bên lề), là sửa nội dung ảnh hưởng hành vi model chấm điểm — vẫn nhỏ (1
file, nén 5 dòng còn 1-2 dòng) nhưng nên đối chiếu hành vi scorer trước/sau, không coi là "không
đổi logic" nữa. Cả hai vẫn có thể làm trực tiếp (lane tiny) nếu được duyệt — không cần plan/design
riêng, chỉ cần thêm bước đối chiếu cho mục 3.

## 5. Trạng thái

Mục 2 và mục 3 **đã triển khai** (2026-07-29, branch `chore/context-eng-lane-anchors` off
`simplify`), theo đúng hướng chốt sau thảo luận:

- `rules/orchestration.md` §Intake fields — thêm 1 câu trỏ về `skills/feature-intake/SKILL.md`
  Step 3–4 làm nguồn định nghĩa taxonomy.
- `rules/auto-correct-scope.md` §Lane-aware autonomy — thêm 1 câu tương tự, giữ nguyên bảng
  autonomy.
- `skills/correctness-review/correctness-scorer-prompt.md` dòng 93-95 — nén giai thoại PR #51 từ
  6 dòng văn xuôi còn 3 dòng structured (Case/Verdict), vẫn in-prompt.

Full test suite (`bash scripts/run-tests.sh`) chạy sau khi sửa: `ALL GREEN` (278 unit test +
toàn bộ shell test file pass). Chưa commit — chờ xác nhận của người dùng. Mục 1 và mục 4 giữ
nguyên kết luận "không làm".
