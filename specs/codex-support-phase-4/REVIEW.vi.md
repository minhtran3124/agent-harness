# Rà soát Phase 4 — lớp trung gian đầu vào hook trung tính với runtime

**Phạm vi rà soát:** cây làm việc Phase-4 chưa commit, đối chiếu với `specs/codex-support-phase-4/PLAN.md`
**Mốc gốc:** `73671c6` (Phase 3)
**Ngày:** 2026-08-11
**Người rà soát:** Claude Code (đọc + chạy lại + dò tìm đối kháng; không áp dụng thay đổi nào)
**Bản gốc tiếng Anh:** `REVIEW.md`

## Kết luận

Bản thân việc di trú được thực hiện tốt — mọi hành vi dự kiến mà tôi dò thử đều hoạt động, kể cả những
thứ thực sự khó (từ chối traversal mà không làm mất các đường dẫn hợp lệ đi kèm, chặn patch trộn lẫn
bookkeeping/code, khử trùng lặp, các hook tư vấn vẫn không chặn). Có ba điều cần xử lý: một lỗ
**fail-open có thể chạm tới trong hard gate**, một tuyên bố bằng chứng được khép lại bằng cách sửa một
chuỗi ký tự thay vì đi thu thập, và một sự suy giảm độ trễ 5 lần trên hook chạy ở mọi lời gọi Bash.

| Kiểm tra | Kết quả |
| --- | --- |
| `bash tests/hooks/normalize-tool-input.test.sh` (SC-1) | exit 0 |
| `bash tests/hooks/branch-isolation-guard.test.sh` (SC-2) | exit 0 |
| `bash tests/hooks/codex-edit-hooks.test.sh` (SC-3) | exit 0 |
| `bash tests/hooks/pre-bash-dispatch.test.sh` (SC-4) | exit 0 |
| `bash tests/hooks/scope-gate.test.sh` (SC-5) | exit 0 |
| `python3 scripts/check_manifest.py` (SC-6) | exit 0 |
| Các suite `blast-radius-check` / `ruff-on-edit` / `render-plan-on-write` | exit 0 |
| `python3 scripts/verify_summary.py --lane codex-support-phase-4` | **thất bại — SUMMARY.md không phải là một file** |

`settings.json` không đổi, đúng như kế hoạch yêu cầu.

## Những điểm làm thực sự tốt

Được kiểm chứng bằng cách dò trực tiếp, không phải bằng cách đọc test:

- **Việc từ chối traversal vẫn giữ lại các đường dẫn hợp lệ đi kèm.** Một patch chạm vào `src/good.py`
  và `../../etc/passwd` cho ra `paths: ["src/good.py"]`, `status: partial`,
  `diagnostics: ["unsafe-path:outside-root"]` — và guard sau đó từ chối trên nhánh dùng chung. Đây đúng
  là hành vi mà Global Constraints yêu cầu, và cũng là chỗ dễ làm sai nhất.
- **Patch trộn bookkeeping/code bị chặn ngay cả khi đường dẫn specs đứng trước.** Hook cũ miễn trừ chỉ
  dựa trên một `file_path` bắt đầu bằng `specs/`; hook mới đòi hỏi *mọi* đường dẫn đã biết phải nằm
  dưới `specs/`. Đó là một sự siết chặt thật sự của hard gate, và có test đi kèm.
- **Khử trùng lặp đường dẫn hoạt động** — cùng một file xuất hiện hai lần trong một patch chỉ cho ra
  một đường dẫn.
- **Cả bốn hook tư vấn đều không chặn** với JSON hỏng, patch không parse được, và `{}`. Tôi đã dò cả
  mười hai tổ hợp; tất cả đều thoát 0.
- **Hành vi của `scope-gate.sh` không đổi** đối với một prompt Claude bình thường — kết quả giống hệt
  so với phiên bản trước khi di trú.
- **Bộ test normaliser đặt tên trung thực**: ca unified-exec được đặt tên là *"documented unified exec
  hook shape normalizes as Bash"* — nó không tuyên bố đã quan sát được.
- **`tests/lib.sh`** loại trừ đúng cách thư mục `hooks/` được copy khỏi các repo fixture, để
  `check-untracked-py` không kích hoạt trên hạ tầng test.

## Các phát hiện

### F1 — Lỗ fail-open có thể chạm tới trong hard gate (nghiêm trọng)

Một payload chỉnh sửa đi vào qua matcher `Write|Edit` mà **không có** `tool_name`, và có command không
bắt đầu chính xác bằng `*** Begin Patch`, sẽ bị phân loại thành lệnh *shell* chứ không phải edit — và
guard cho phép nó chạy trên nhánh dùng chung.

Tái hiện, chạy `hooks/branch-isolation-guard.sh` trên một repo đang ở `main`:

```
payload: {"hook_event_name":"PreToolUse","turn_id":"t",
          "tool_input":{"command":"\n*** Begin Patch\n*** Update File: src/app.py\n*** End Patch"}}

normaliser →  {"tool_class":"shell","status":"known","paths":[],"diagnostics":[]}
guard      →  exit 0, không có JSON deny   ← thao tác sửa được CHO PHÉP trên main
```

Cơ chế nằm ở `hooks/lib/normalize-tool-input.py:142-146`: nhánh shell nhận mọi payload không có
`tool_name` mà command không bắt đầu đúng bằng dấu hiệu patch. Chỉ một ký tự xuống dòng ở đầu là đủ.
`status` khi đó là `known` với `paths` rỗng, và `hooks/branch-isolation-guard.sh` cho qua ở
`[ -z "$PATHS" ] && exit 0` — nó xét `status` và `paths` nhưng **không bao giờ xét `tool_class`**.

Điều này phá vỡ chính tiêu chí nghiệm thu của Task 4.2: *"the hard gate cannot silently allow a
supported Codex edit because a path is missing, reordered, or accompanied by a bookkeeping path."* Nó
cũng tự mâu thuẫn: `_patch_paths` đã phát ra chẩn đoán `patch-missing-begin` cho đúng hình dạng hỏng
này, tức là tác giả đã lường trước — nhưng chỉ trên nhánh đòi hỏi `tool_name == "apply_patch"`.

Hiện tại chưa runtime nào phát ra payload chỉnh sửa thiếu `tool_name`, nên đây là lỗ tiềm ẩn chứ chưa
hoạt động. Nhưng normaliser có những nhánh mã tồn tại *chỉ để* phục vụ trường hợp thiếu `tool_name`, và
một hard gate mà bảo đảm của nó phụ thuộc vào sự hiện diện của một trường thì không được fail-open khi
trường đó vắng mặt.

**Đề xuất sửa.** Trong `branch-isolation-guard.sh`, hãy từ chối trừ khi `tool_class == "edit"`. Một
hook đăng ký trên `Write|Edit` mà nhận được payload phân loại là shell là một mâu thuẫn, và mâu thuẫn
tại một hard gate thì phải fail closed. Thêm ca thiếu `tool_name` vào cả suite normaliser lẫn suite
branch-isolation.

### F2 — Khoảng trống bằng chứng unified-exec được khép lại bằng cách sửa một chuỗi tham chiếu (nghiêm trọng)

Phase 1 đã ghi lại điều này thành phạm vi phủ định tường minh:

> **`tools.unified_exec` is observed only at feature-availability tier (provenance, partial).**
> `doctor.json` proves the feature is stable and enabled; the unified-exec *payload envelope* is not
> captured anywhere. Phase 4 Task 4.1 must capture it before Task 4.4 parses it.

Action của Task 4.1 ghi trong kế hoạch: *"**Capture — do not transcribe from documentation** — the
Codex unified-exec shell envelope and the Claude/Codex `UserPromptSubmit` prompt payloads, and promote
the corresponding capability-matrix rows … from feature-availability/documented to observed."*

Thực tế đã thay đổi những gì trong `capability-matrix.json`:

- `tools.unified_exec` — `evidence_path` vẫn trỏ tới `doctor.json`; `evidence_level` vẫn là
  `observed`; `source.kind` vẫn là `captured-fixture`. Chỉ có phần `reference` dành cho người đọc là
  thay đổi, từ *"feature availability only, not the payload envelope shape (Task 4.1 captures that)"*
  thành *"official hook schema separately establishes that unified exec matches Bash and uses
  `tool_input.command`"*. Đó là một tuyên bố **tài liệu** (tầng traceability) được cài vào một hàng mà
  `kind` và `level` của nó khẳng định **quan sát**.
- `hooks.user_prompt_submit` — không đổi: vẫn `documented`, vẫn `load_bearing: false`. Chưa được nâng cấp.
- Không có fixture bằng chứng mới nào được thu thập; `specs/codex-support/evidence/codex-0.147.0/`
  không bị đụng tới.

Vì vậy các fixture `codex-unified-exec.json` và `codex-user-prompt.json` là những giả định được viết
tay. Bí danh `exec_command` trong normaliser thì hoàn toàn không có nguồn nào được dẫn.

Điều này mang tính chịu tải, không phải chuyện hình thức. `pre-bash-dispatch.sh` giờ **fail closed** với
payload shell không phân loại được, nên nếu envelope unified-exec thật dùng một `tool_name` khác thì
mọi lệnh shell của Codex đều bị chặn — đúng rủi ro mà kế hoạch nêu tên: *"Fail-closed dispatch on
unknown payloads could block legitimate Bash calls if a runtime changes its payload shape. Mitigation:
version-pinned capability-matrix rows for shell payloads, golden fixtures per supported shape."* Biện
pháp giảm thiểu chính là hàng bằng chứng quan sát đã không được tạo ra.

**Đề xuất sửa.** Hoặc đi thu thập envelope (một phiên Codex với hook ghi lại từ script capture của
Phase 1), hoặc khôi phục phần reference trung thực và ghi hàng đó là `documented` kèm chủ sở hữu và
điều kiện đóng. Hàng đó không được phép ghi `observed` dựa trên một nguồn tài liệu.

Liên quan: `checked_at` được đẩy từ `2026-08-10` lên `2026-08-11` trên ba hàng mà bằng chứng không đổi,
việc này kéo dài cửa sổ tươi mới của chúng. Với hai hàng `official-documentation`, điều đó khẳng định
tài liệu đã được tải lại hôm nay; không có gì ghi nhận việc đó đã xảy ra.

### F3 — Phase 4 không có `SUMMARY.md` (nghiêm trọng)

Thư mục `specs/codex-support-phase-4/` chỉ chứa `PLAN.md`. `verify_summary.py --lane` báo
*"not a file"*. Kế hoạch đánh dấu 4/4 đã xong trên hard gate, bộ điều phối git, và cả bốn hook tư vấn —
không có dòng Verify nào, không Rollback, không `### Not auto-verified`.

Đây là pha thứ tư liên tiếp. Việc tách slug theo pha tồn tại chính là để bản ghi này được đưa vào cùng
với pha của nó.

### F4 — Suy giảm độ trễ 5 lần trên đường chạy của mọi lời gọi Bash (trung bình)

`pre-bash-dispatch.sh` chạy ở **mọi** lời gọi công cụ Bash. Đo trên 20 lần chạy một lệnh không phải git
tầm thường:

| Phiên bản | 20 lần chạy | mỗi lời gọi |
| --- | --- | --- |
| Trước Phase-4 (`73671c6`) | 0.185s | ~9ms |
| Phase 4 | 0.933s | ~47ms |

Trường hợp phổ biến giờ sinh ra một tiến trình `python3` cộng ba lời gọi `jq` riêng biệt trước khi nó
kịp kết luận rằng lệnh không phải `git commit`. Chính phần header của hook trước đây mô tả đường chạy
này là *"one jq, no child processes"*; câu đó bị xoá trong thay đổi này thay vì được giữ lại như một
ràng buộc.

Nó cũng thêm `python3` thành một phụ thuộc runtime cứng của mọi lời gọi Bash: không có `python3` trên
`PATH` → `normalizer-unavailable` → `exit 2` → mọi lệnh Bash bị chặn. Điều này khớp với tiền lệ
fail-closed sẵn có khi thiếu `git-command.sh`, nên không phải một *lớp* rủi ro mới, nhưng nó là điểm
hỏng đơn thứ hai trên đường chạy nóng nhất, và thao tác khắc phục (`git pull`, deploy lại) tự nó lại là
một lệnh Bash.

**Đề xuất sửa.** Cho normaliser phát ra một dòng có thể eval được bởi shell rồi đọc một lần, thay vì ba
lời gọi `jq`; và cân nhắc đi tắt với hình dạng Claude `tool_name == "Bash"` rõ ràng trước khi sinh
tiến trình Python.

### F5 — Không test nào phủ payload chỉnh sửa thiếu `tool_name` (trung bình)

Bộ test normaliser có 14 ca được chọn tốt, gồm cả đường dẫn NUL, đường dẫn tuyệt đối kiểu Windows, các
đường dẫn kèm không an toàn, và dòng điều khiển không parse được. Không ca nào dựng một payload chỉnh
sửa thiếu `tool_name`, và đó là lý do F1 sống sót qua một bộ test toàn màu xanh. Suite branch-isolation
có thêm bảy ca tốt — partial, malformed, move/delete, mixed-specs-first, break-glass qua unknown —
nhưng cũng chưa bao giờ chạy qua một payload bị phân loại sai.

### F6 — Bảng hook trong `CLAUDE.md` mô tả hợp đồng dự kiến, không phải hợp đồng thực tế (thấp)

Dòng đã cập nhật ghi: *"An edit is bookkeeping-exempt only when all known paths are under `specs/*`;
partial/unknown input fails closed on shared branches."* Cả hai mệnh đề đều đúng. Điều nó không nói là
một payload chỉnh sửa bị phân loại thành *shell* thì được miễn khỏi cả hai mệnh đề — chính là lỗ F1.
Khi F1 được sửa thì câu này trở nên chính xác; còn đến lúc đó tài liệu đang đi trước mã nguồn.

## Kết quả xử lý (2026-08-11)

F1–F5 đã được sửa trong cây làm việc; F6 tự khép lại như một hệ quả của F1.

| Phát hiện | Kết quả |
| --- | --- |
| F1 | Sửa ở cả hai tầng. Normaliser nhận diện chương trình patch bằng một dòng `*** Begin Patch` ở bất kỳ vị trí nào (patch thiếu `tool_name` → `edit`, lệnh thường vẫn là `shell`), và guard từ chối mọi payload có `tool_class` khác `edit` trên nhánh dùng chung. Đã kiểm bằng đột biến theo cả hai chiều: đưa lỗi normaliser trở lại thì suite normaliser hỏng trong khi guard *vẫn từ chối* (phòng thủ nhiều lớp); gỡ phép kiểm `tool_class` của guard thì suite guard hỏng. |
| F2 | Phần reference của ma trận không còn tuyên bố về envelope: nó nêu rõ phạm vi phủ định (chỉ quan sát được tính khả dụng của tính năng; hình dạng envelope ở tầng traceability, fixture viết tay, `exec_command` không có nguồn dẫn) kèm nghĩa vụ thu thập thuộc Phase 5. Hai lần đẩy `checked_at` không có căn cứ trên các hàng tài liệu đã được hoàn lại. `--require-evidence` vẫn pass. Bản thân envelope vẫn chưa được thu thập — được ghi lại một cách chủ đích là còn nợ, không bị tuyên bố lại trong im lặng. |
| F3 | Đã viết `SUMMARY.md`: chín dòng Verify, tất cả chạy lại sạch dưới `verify_summary.py --check`; phần thiếu hụt thu thập/nâng cấp của Task 4.1 được ghi trong `### Not auto-verified` kèm chủ sở hữu thay vì bị che đi. |
| F4 | Khôi phục đường nhanh: `tool_name == "Bash"` với command là chuỗi không rỗng được xử lý bằng một lời gọi jq, không Python (hình dạng duy nhất mà normaliser chỉ có thể phân loại shell/known). Đường chậm rút xuống hai lời gọi jq, trong đó command được trích riêng vì nó có thể nhiều dòng và một lần read theo dòng sẽ cắt cụt đúng thứ mà bộ khớp git tokenize. Đo lại: ~0.24s/20 lần chạy so với 0.19 trước Phase-4 và 0.93 trước khi sửa. Đã dò: một lệnh hai dòng mà dòng thứ hai là `git commit` kích hoạt deny của untracked-py; mẫu đối chứng không có git thì im lặng. |
| F5 | Thêm bốn ca hồi quy: hai cho normaliser (patch thiếu `tool_name` → edit; lệnh thường thiếu `tool_name` → shell) và hai cho guard (payload bị phân loại sai và payload phân loại shell đều bị từ chối trên matcher chỉnh sửa). |
| F6 | Dòng trong `CLAUDE.md` giờ đã chính xác — mã nguồn đã bắt kịp tài liệu. |

Shellcheck sạch trên cả hai hook và hai suite đã sửa; cả 8 suite hook và `check_manifest.py` đều pass.

## Khuyến nghị

F1 trước tiên — đó là một lỗ fail-open có thể chạm tới ngay tại chính cái gate mà pha này sinh ra để
gia cố, và cách sửa chỉ là một điều kiện. Tiếp theo là F2: đây là lần thứ hai một khoảng trống bằng
chứng được khép lại bằng cách viết lại câu chữ thay vì đi thu thập (các fixture của Phase 1 là lần đầu),
và lần này nó lại chính là thứ mà cơ chế dispatch fail-closed đang dựa vào. F3 là khoảng trống bản ghi
còn tồn đọng. F4 và F5 thì rẻ. F6 tự khép lại cùng với F1.
