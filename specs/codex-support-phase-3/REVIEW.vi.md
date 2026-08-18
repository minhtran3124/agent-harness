# Rà soát Phase 3 — trung tính hoá nguồn ngữ nghĩa

**Phạm vi rà soát:** cây làm việc Phase-3 chưa commit, đối chiếu với `specs/codex-support-phase-3/PLAN.md`
**Mốc gốc:** `4a5a721` (Phase 2)
**Ngày:** 2026-08-10
**Người rà soát:** Claude Code (đọc + chạy lại; không áp dụng thay đổi nào)
**Bản gốc tiếng Anh:** `REVIEW.md`

## Kết luận

Đây là pha làm tốt nhất cho tới nay. Bộ lint đếm chính xác thay vì chỉ là danh sách cho phép, ma trận
ngữ cảnh thực sự liệt kê đủ cả mười nơi tiêu thụ bị cô lập, và các test deploy/install khẳng định hành
vi thật. Có hai điều cần xử lý trước khi phần này được đưa vào: một tài liệu vai trò agent đã mất đoạn
văn bản mang tính chịu tải mà không test nào nhìn thấy, và pha này hoàn toàn không có `SUMMARY.md`.

| Kiểm tra | Kết quả |
| --- | --- |
| `python3 scripts/check_runtime_neutral_sources.py --root .` (SC-1) | exit 0 |
| `bash tests/scripts/context-propagation-regression.test.sh` (SC-2) | exit 0 — 6 passed |
| `python3 -m pytest scripts/test_render_agent_definitions.py -q` (SC-3) | 8 passed dưới venv của harness; **exit 1** dưới trình thông dịch mặc định — xem F3 |
| `python3 scripts/check_manifest.py` (SC-4) | exit 0 |
| `python3 scripts/check_plan_contract.py …` | exit 0 |
| `python3 scripts/verify_summary.py --lane codex-support-phase-3` | **thất bại — SUMMARY.md không phải là một file** |
| `bash scripts/run-tests.sh` | `ALL GREEN`, 513 test Python |

`settings.json` và `AGENTS.md` ở gốc không bị đụng tới, đúng như kế hoạch yêu cầu.

## Những điểm làm thực sự tốt

- **Bộ lint không thể bị nới lỏng âm thầm.** `check_runtime_neutral_sources.py` so sánh một *số đếm
  chính xác* theo từng cặp (path, category) với những gì nó quan sát được. Một vi phạm mới sẽ gây lệch
  số đếm và in ra dòng vi phạm; một vi phạm bị xoá sẽ gây lỗi số đếm cũ. Điều này mạnh hơn hẳn một danh
  sách cho phép.
- **`templates/` nằm trong `scan_roots` và có 0 phát hiện.** Việc trung tính hoá template của Task 3.3
  đã hoàn tất và được kiểm bằng máy, chứ không chỉ là tuyên bố.
- **Cả 13 phát hiện còn lại đều là ngoại lệ có chủ sở hữu**, kèm chủ sở hữu Phase-5 và điều kiện đóng —
  văn bản thông điệp của hook/script và các fixture test. Không có cái nào là vi phạm nguồn chung trá hình.
- **10 unit test của lint đều không rỗng nghĩa**: phát hiện finding không có chủ kèm báo cáo dòng/danh
  mục, từ chối đường dẫn cũ, chốt chặn dương tính giả cho lời gọi được escape và cho đường dẫn kho, quy
  tắc chính sách vendor chỉ nằm trong frontmatter, từ chối mục trùng lặp.
- **`test_each_policy_delivery_edge_is_load_bearing`** đột biến *mọi* cạnh đã khai báo trong ma trận và
  khẳng định checker phải báo lỗi. Bản thân checker được chứng minh là chịu tải, không chỉ là được chạy qua.
- **Các test deploy/install khẳng định hành vi**: `reviewer.md` đã render phải mang `model:` và `tools:`,
  các file JSON binding thời-nguồn **không** được deploy, và một agent tuỳ biến của người dùng phải sống
  sót qua lần đồng bộ lại.
- **`task-reviewer-readonly.test.sh` đã được trỏ lại đúng chỗ** — nó khẳng định nguồn ngữ nghĩa *không*
  chứa chính sách runtime, còn artifact *đã render* thì mang danh sách trắng cấu trúc. Đó đúng là hình
  dạng phù hợp cho một pipeline dựa trên render, và nó vẫn giữ được khẳng định phủ định của mình.
- **Độ trung thực khi render phần lớn là chính xác tuyệt đối**: `task-reviewer.md` và `test-runner.md`
  render ra **giống hệt từng byte** so với bản đã commit trước Phase-3.

## Các phát hiện

### F1 — `agents/reviewer.md` mất hai tuyên bố chịu tải, và không test nào thấy được (nghiêm trọng)

Render các agent Claude rồi so với bản gốc trước Phase-3: `task-reviewer` và `test-runner` giống hệt
từng byte, `coding` chỉ khác thứ tự khoá frontmatter (F4), còn `reviewer` khác biệt **về ngữ nghĩa** ở
hai chỗ.

**Phần description.** Bản gốc nêu rõ bảo đảm mang tính cấu trúc và lý do chọn model:

> It is structurally read-only: the tools whitelist excludes Write, Edit, and Agent, so review
> independence is enforced by the harness, not by instruction. The frontmatter pins the default
> (claude-opus-5) so a forgotten dispatch never inherits the implementer's model; the correctness
> scorer overrides it to claude-opus-4-8 (a distinct model from the finders) per the
> ensemble-diversity rule in the reviewer prompts.

Bản thay thế bỏ cả tuyên bố "enforced by the harness, not by instruction" lẫn toàn bộ chỉ dẫn về quy
tắc đa dạng hoá ensemble:

> It is read-only, cannot delegate, and returns findings rather than fixes. Runtime bindings enforce
> the available tools and model-class isolation.

**Phần thân.** Câu sau đây bị xoá hẳn:

> **Acknowledged limitation:** Bash can technically mutate state; the "never fix" rule below is the
> only guard on that channel. The structural guarantee covers Write/Edit/Agent.

và được thay bằng "A read-only inspection shell may be available … never use it to mutate state."

Điều đó biến một tuyên bố phạm vi phủ định tường minh thành một bảo đảm ngầm định. Bản thân binding thì
trung thực — `runtime-bindings.json` ghi `"shell": "Bash limited by role contract to read-only
inspection"`, tức là bằng *hợp đồng*, không phải bằng cấu trúc — nhưng phần thân vai trò thì không còn
nói điều đó với agent nữa. Đây chính là kiểu thất bại mà `CLAUDE.md` → Gate verifiability nêu đích danh:
một tuyên bố không được khẳng định tầng cao hơn tầng nó thực thi.

Nó cũng vi phạm chính Global Constraint của kế hoạch: các định nghĩa Claude dẫn xuất "must retain the
intended model, tools, descriptions, and role bodies **except for approved invocation/path
neutralisation**". Viết lại description và xoá một đoạn thân không thuộc loại nào trong hai loại đó.

**Vì sao không có gì bắt được.** `test_claude_render_preserves_legacy_model_tools_and_role_body` khẳng
định `rendered_body == source_body` — cả hai vế cùng dịch chuyển, nên trôi dạt phần thân là vô hình do
cách xây dựng. Chỉ model và tools mới có golden thật (`LEGACY_CLAUDE`); tên test thì tuyên bố quá mức
phần còn lại. Action của Task 3.4 yêu cầu "so sánh ngữ nghĩa Claude được sinh ra với các vai trò trước
khi refactor"; phép so sánh đó chỉ tồn tại cho model/tools.

**Đề xuất sửa.** Khôi phục phần description và câu về giới hạn được thừa nhận (chỉ trung tính hoá tên
công cụ vendor nếu cần), và mở rộng `LEGACY_CLAUDE` thêm hash hoặc golden cho thân/description để một
lần viết lại trong tương lai sẽ làm hỏng bộ test.

### F2 — Phase 3 không có `SUMMARY.md` (nghiêm trọng)

Thư mục `specs/codex-support-phase-3/` chỉ chứa `PLAN.md` (và file HTML render kèm theo).
`verify_summary.py --lane codex-support-phase-3` báo *"not a file"*.

Kế hoạch đánh dấu 4/4 task đã xong trên 66 file chạm vào chính bộ máy workflow — skills, rules, agents,
templates và `deploy-harness.sh` — mà không có dòng Verify nào, không có Rollback, và không có
`### Not auto-verified`. Đây là pha thứ ba liên tiếp bản ghi bị tụt lại sau mã nguồn; việc tách slug
theo pha thực hiện ở `be9bc21` tồn tại chính là để bản ghi này *có thể* được đưa vào theo từng bước.

### F3 — Kiểm tra của SC-3 không thể pass dưới trình thông dịch mặc định (trung bình)

`python3 -m pytest scripts/test_render_agent_definitions.py -q` thoát với mã 1 ở đây — trình thông dịch
đang hoạt động không có pytest; `run-tests.sh` thì ưu tiên phân giải một venv riêng (bộ test pass ở đó:
8 test).

Đây là lần tái diễn thứ tư của cùng một khiếm khuyết, và lần này nó nằm ngay trong **bảng SC của kế
hoạch**, vốn được viết trong đợt tách pha — nên một SUMMARY Phase-3 trung thực sẽ không thể phủ SC-3
bằng lệnh đó.

**Đề xuất sửa.** Thay lệnh kiểm tra của SC-3 bằng một lệnh độc lập với trình thông dịch —
`python3 scripts/render_agent_definitions.py --check` đã được cài đặt sẵn và thoát 0/1 — rồi dẫn bộ
pytest bằng văn xuôi.

### F4 — `coding.md` render ra với thứ tự khoá frontmatter bị đảo (trung bình)

Bộ render nối `model:` vào cuối, nên giờ `color:` đứng trước nó trong khi bản gốc có `model:` đứng
trước. Về ngữ nghĩa thì giống hệt đối với Claude, nhưng file render không còn ổn định từng byte so với
lần deploy trước: `.claude/agents/coding.md` của mọi consumer sẽ đổi nội dung ở lần đồng bộ kế tiếp, và
bản đã deploy trong chính kho này đã khác với thứ mà `render_agent_definitions.py` sinh ra bây giờ.

Một bộ render có điểm mạnh là tính tất định thì nên giữ nguyên thứ tự khoá của nguồn và chèn
`model`/`tools` vào đúng chỗ.

### F5 — Ma trận ngữ cảnh chỉ kiểm tra sự hiện diện, không kiểm tra sự chuyển giao (trung bình)

`check_all` kiểm tra `token not in text`. Tôi đã kiểm tra thủ công cả mười cạnh đã khai báo, và **mọi
cạnh hiện tại đều là một chỉ dẫn Read thực sự, đặt trước điểm sử dụng** — ví dụ
`skills/intent-review/SKILL.md:38` "Before any fix routing, **read `rules/auto-correct-scope.md`**".
Vậy nội dung hôm nay là đúng.

Khoảng trống nằm ở chỗ phép kiểm tra có thể bảo vệ được điều gì: một lần chỉnh sửa trong tương lai hạ
một bước Read xuống thành một lần nhắc thoáng qua (một footer "Related:", một câu văn phụ) vẫn giữ cho
phép kiểm tra màu xanh. Cách diễn đạt của SC-2 — "reaches … through an explicit read or a checked
equivalent" — và tên test "complete contextual-rule consumer matrix is checked" đều nghe mạnh hơn so
với việc chỉ kiểm tra sự hiện diện của chuỗi. Hai mỏ neo lịch sử (implementer, đoạn dùng chung của
correctness) thì có khẳng định theo vị trí và test đột biến; tám cạnh mới thì chỉ có sự hiện diện.

Thuộc tầng traceability. Nên nêu ra như phạm vi phủ định thay vì sửa, trừ khi việc thêm khẳng định theo
vị trí là rẻ.

### F6 — Hai mục `required: []` quyết định chính sách bằng lý lẽ chứ không bằng phép kiểm tra (trung bình)

`correctness-scorer` khai báo không cần quy tắc nào, với lý lẽ *"Scores evidence only; Rule
classification and fix routing occur after scoring in the controller."* Điều đó hợp lý.

`task-reviewer` cũng khai báo không cần, với lý lẽ *"Consumes a normalized task brief and review
package; it does not parse plan syntax or route fixes."* Điều này đáng bàn hơn: task reviewer đưa ra
phán quyết **spec**, và việc đánh giá xem một sai lệch của implementer có phải là một auto-fix hợp lệ
theo Rule 1–3 hay không thì hoàn toàn có thể cần tới `rules/auto-correct-scope.md`. Việc ghi lại quyết
định kèm lý lẽ là đúng quy trình — checker thậm chí còn bắt buộc một mục rỗng phải *có* lý lẽ — nhưng
riêng lựa chọn này đáng được xem lại lần nữa trước khi nó đông cứng thành hợp đồng.

### F7 — Đường dẫn kho theo nghĩa đen bị thay bằng placeholder (thấp)

`skills/visual-planner/SKILL.md` giờ ghi `python3 <visual-planner-dir>/render_plan.py …` ở ba lệnh,
trong khi trước đó nó nêu đích danh `skills/visual-planner/render_plan.py`. `skills/xia2/README.md`
cũng được xử lý tương tự cho phần hướng dẫn cài đặt.

Action của Task 3.3 nói hãy thay văn bản lời gọi "while **preserving literal repository paths**" — việc
này làm ngược lại. Động cơ thì hợp lý (thư mục skill của Codex không phải là `skills/visual-planner/`),
nhưng đó là một sai lệch so với văn bản của task, và không có gì kiểm tra rằng agent phân giải
placeholder đó cho đúng. Hoặc mở rộng phạm vi đã nêu của task, hoặc ghi lại đây là một deviation.

### F8 — `agents/README.md` thay ID model cụ thể bằng lớp model (thấp)

Bảng inventory giờ ghi "review high-capability, distinct from implementer" ở chỗ trước đây ghi
`claude-opus-5`. Các ID vẫn còn trong `agents/runtime-bindings.json` nên không mất gì — nhưng điều này
đảo ngược một phần commit `670ccbc` ("pin explicit model IDs for each review sub-agent") ở mức tài
liệu, và người đọc bảng inventory agent không còn thấy được model nào đang chạy. Thêm một dòng trỏ tới
file bindings là đủ để khép lại.

## Kết quả xử lý (2026-08-11)

F1–F4 đã được sửa trong cây làm việc; F5–F8 được ghi lại thành phạm vi phủ định trong
`specs/codex-support-phase-3/SUMMARY.md` → `### Not auto-verified`.

| Phát hiện | Kết quả |
| --- | --- |
| F1 | Đã khôi phục phần description và câu **Acknowledged limitation** vào `agents/reviewer.md` bằng cách diễn đạt trung tính với runtime. Test mới `test_rendered_roles_retain_load_bearing_substance` ghim phần nội dung cốt lõi trên chính artifact *đã render*; đã kiểm bằng đột biến (xoá câu đó thì bộ test hỏng, khôi phục thì pass). |
| F2 | Đã viết `SUMMARY.md`. Sáu dòng Verify, tất cả chạy lại sạch dưới `verify_summary.py --check`; phần Rollback nêu rõ bước đồng bộ lại bắt buộc; `### Not auto-verified` mang bảy mục kèm tầng bằng chứng. |
| F3 | Kiểm tra của SC-3 giờ là `python3 scripts/render_agent_definitions.py --check` (thoát 0 ở đây, 1 khi root sai). Hai dòng `Verify` ở mức task vẫn nêu pytest và được giữ nguyên — chúng ghi lại thứ mà implementer đã chạy, và viết lại phép kiểm tra của một task đã hoàn thành là sửa lại lịch sử. |
| F4 | `render_agent_definitions.py` chèn `tools`/`model` ngay sau `description`, đúng chỗ chúng được viết ban đầu. `coding.md`, `task-reviewer.md` và `test-runner.md` giờ render ra **giống hệt từng byte** so với bản trước Phase-3; `reviewer.md` chỉ khác ở phần trung tính hoá tên vendor đã được duyệt. |
| F5, F6, F8 | Ghi lại thành phạm vi phủ định kèm tầng bằng chứng. |
| F7 | Ghi lại thành một deviation về phạm vi, kèm lý do (thư mục skill của Codex không phải `skills/visual-planner/`) và phần bề mặt chưa được test. |

Một phát hiện mới nảy sinh trong lúc sửa và được ghi thành Harness-Delta thay vì sửa tại đây:
`hooks/blast-radius-check.sh` chỉ phân giải một plan đang hoạt động, nên khi `codex-support-phase-1`
và `-phase-3` cùng ở trạng thái `active`, việc sửa một file hợp lệ của Phase-3 lại bị cảnh báo dựa
trên tập file của Phase-1. Việc tách slug theo pha khiến chuyện nhiều plan cùng active là bình thường.

## Khuyến nghị

F1 và F2 cần xử lý trước khi phần này được đưa vào. F1 là một sự suy yếu thật sự của tuyên bố về tính
độc lập của reviewer, nằm đúng trong file mà toàn bộ mục đích là để nêu điều đó cho chính xác, còn test
lẽ ra phải bắt được thì lại rỗng nghĩa đối với phần thân. F2 là khoảng trống bản ghi ở pha thứ ba liên
tiếp.

F3 và F4 thì rẻ. F5, F6 và F8 hoàn toàn có thể ghi lại thành phạm vi phủ định trong mục
`### Not auto-verified` của SUMMARY, kèm tầng bằng chứng theo `CLAUDE.md` → Gate verifiability. F7 cần
hoặc một ghi chú về phạm vi, hoặc một chỉnh sửa văn bản của task.
