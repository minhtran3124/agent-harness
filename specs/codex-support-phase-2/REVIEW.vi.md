# Rà soát Phase 2 — quyết định đóng gói

**Phạm vi rà soát:** cây làm việc Phase-2 chưa commit, đối chiếu với `specs/codex-support-phase-2/PLAN.md`
**Mốc gốc:** `be9bc21` (đợt rà soát/sửa Phase-1)
**Ngày:** 2026-08-10
**Người rà soát:** Claude Code (đọc + chạy lại; không áp dụng thay đổi nào)
**Bản gốc tiếng Anh:** `REVIEW.md`

## Kết luận

Phạm vi và mức độ tuân thủ đều tốt: mọi file trong danh sách `Files:` của Task 2.1/2.2 đều có mặt,
không đụng vào file nào ngoài phạm vi, và mọi kiểm tra trong phạm vi đều pass. Các khiếm khuyết nằm ở
**bằng chứng chứng minh được điều gì**, không nằm ở thứ đã được xây dựng.

| Kiểm tra | Kết quả |
| --- | --- |
| `bash tests/scripts/codex-packaging-probe.test.sh` (SC-1) | exit 0 — 12 passed |
| `python3 scripts/check_codex_packaging.py specs/codex-support/packaging-decision.md` (SC-2) | exit 0 |
| `python3 scripts/check_codex_capabilities.py … --require-evidence` | exit 0 |
| `python3 scripts/check_plan_contract.py specs/codex-support-phase-2/PLAN.md` | exit 0 |
| `python3 scripts/verify_summary.py --lane codex-support-phase-2` | exit 0 |
| `python3 scripts/verify_summary.py --check codex-support-phase-2` | **exit 1** — xem F5 |
| `bash scripts/run-tests.sh` | `ALL GREEN`, 489 test Python |

Con số 489 khớp chính xác với tuyên bố trong SUMMARY (480 + 9 test checker mới).

## Những điểm làm thực sự tốt

Ghi lại phần này vì các phát hiện bên dưới có phạm vi hẹp, còn phần còn lại của pha thì không.

- Bộ test tất định khẳng định **đúng** giao thức 14 lời gọi CLI, đúng thứ tự, bằng regex
  (`tests/scripts/codex-packaging-probe.test.sh:114-116`). Đó là một hợp đồng thật, không phải test cho có.
- Mọi lời gọi CLI đều được khẳng định là đã chạy dưới `HOME` **và** `CODEX_HOME` cách ly, kèm một file
  mốc của caller chứng minh cấu hình thật không bị đụng tới.
- Một vòng đời thất bại thì **không** xuất bản bằng chứng dở dang — được kiểm chứng bằng cách tiêm lỗi
  (`FAKE_MARKETPLACE_FAIL=1`).
- Phát hiện cache dung sai phiên bản: tài liệu builder nói phân đoạn cache cục bộ là `local`, còn CLI
  0.147.0 thực tế dùng phiên bản manifest `0.0.1`. Probe phát hiện thư mục duy nhất đang tồn tại thay vì
  gán cứng một trong hai. Đây là một phát hiện thượng nguồn có thật, và được xử lý đúng.
- Ranh giới "chưa quan sát được thực thi runtime" được thực thi ở ba nơi độc lập — trường fixture
  `runtime_execution_observed`, checker (`check_codex_packaging.py:131-132`), và mục
  `## Unresolved gaps` của tài liệu quyết định. Vòng đời CLI không bao giờ được phép giả dạng thành
  bằng chứng thực thi.

## Các phát hiện

### F1 — Ứng viên `direct` không quan sát được gì cả (nghiêm trọng)

Khối ứng viên direct (`scripts/probe_codex_packaging.sh:274-334`) **không hề gọi Codex**.

Bằng chứng: nhật ký lời gọi của chính probe khi chạy với CLI giả ghi nhận 14 lần gọi — `--version`,
`--strict-config --help`, và 12 lệnh `plugin …`. Cả 12 lệnh đều thuộc ứng viên hybrid. Không lệnh nào
liên quan tới project direct.

Sáu kiểm tra của nó được tính trên chính những file mà probe tự tạo ra khoảng 140 dòng trước đó
(`:135-141`):

| Kiểm tra | Thực chất nó kiểm tra cái gì |
| --- | --- |
| `skill_discovery_surface` | biến `installed` (`:285`) — "những file tôi vừa copy có tồn tại" |
| `hook_registration_visible` | **cùng** biến `installed` đó |
| `agent_discovery_surface` | **cùng** biến `installed` đó |
| `conflict_preserves_local_and_writes_incoming` | hai lời gọi `write_text` viết ngay tại chỗ (`:287-291`) |
| `source_update_staged` | `incoming.name.endswith(".harness-incoming")` trên cái tên vừa dựng ở dòng trên |
| `cleanup` | nó xóa file đi, rồi khẳng định file đã biến mất |

Mọi kiểm tra đều đúng do cách xây dựng, nên `packaging-direct.json` chỉ có thể phát ra
`passed: true, status: observed`. Không có đầu vào nào khiến nó báo thất bại.

Hai hệ quả:

- `conflict_preserves_local_and_writes_incoming` viết lại hành vi `.harness-incoming` ngay tại chỗ thay
  vì gọi `scripts/deploy-harness.sh`. Vì vậy nó không chứng minh được gì về cơ chế chống xung đột thật.
- Task 2.1 yêu cầu cả hai ứng viên đi qua "discovery, install, upgrade, conflict, và removal". Tài liệu
  quyết định thì nói với người đọc: *"The direct candidate also passed representative project-file
  install, update/conflict, incoming-sidecar, removal, and cleanup checks."* Người đọc sẽ hiểu đó là một
  phép so sánh; thực tế thì không phải.

**Đề xuất sửa.** Ngừng trình bày khối direct như một probe. Hãy xuất nó ra dưới dạng `status: unknown`
kèm chủ sở hữu và điều kiện đóng (Phase 5 sẽ chứng minh discovery ở mức project), đúng như cách Phase 1
xử lý Linux/WSL. Còn nếu muốn có một probe direct thật sự, nó phải yêu cầu Codex liệt kê skills/agents
của project và phải gọi `deploy-harness.sh` cho trường hợp xung đột.

### F2 — Nhánh dự phòng không có đường thực thi (nghiêm trọng)

Task 2.2: *"Select hybrid only if every required discovery/lifecycle case passes; otherwise select
direct sync."* Cái "otherwise" đó không thể ghi lại được:

- `run_cli` (`probe_codex_packaging.sh:181-196`) gọi `die` khi bất kỳ lệnh CLI nào thất bại, nên một
  hybrid thất bại sẽ **không sinh ra fixture nào cả**.
- `check_codex_packaging.py:127-130` từ chối mọi bằng chứng chứa một check `false` hoặc `status` khác
  `observed` — và nó xác thực `hybrid_evidence` với `direct_evidence` y hệt nhau, bất kể ứng viên nào
  được chọn.

Vậy nên một quyết định dạng "hybrid thất bại, do đó chọn direct" là không thể biểu diễn: nó sẽ cần một
fixture hybrid ghi nhận thất bại, mà checker thì từ chối, còn probe thì không bao giờ ghi ra. Cơ chế dự
phòng chỉ tồn tại dưới dạng văn xuôi và một chuỗi `fallback_trigger`; nó chưa từng được thực thi lần nào.

Điều này quan trọng hơn chuyện gọn gàng — cơ chế dự phòng chính là lớp bảo vệ mà kế hoạch đặt ra để
tránh đưa Phase 5 vào một ranh giới đóng gói không phù hợp.

**Đề xuất sửa.** Cho phép probe xuất bản một fixture hybrid không-pass (`status: unknown` kèm check thất
bại) thay vì `die`, và dạy cho checker biết rằng ứng viên **không được chọn** có thể mang kết quả thất
bại — đó chính xác là bằng chứng biện minh cho việc chọn ứng viên còn lại.

### F3 — `strict_config: true` là một hằng số (trung bình)

Dòng `probe_codex_packaging.sh:364` gán cứng `True` vào bản đồ checks của hybrid. Probe strict-config
thật nằm cách đó khoảng 185 dòng (`:177-179`) và `die` khi thất bại, nên giá trị được ghi lại tình cờ
đúng ở thời điểm hiện tại — nhưng xóa probe đó đi thì fixture vẫn báo check này xanh. Đây đúng là dạng
"xanh có thể nghĩa là bị bỏ qua": một hằng số không thể phân biệt được với một phép đo.

Nó cũng yếu ngay trên chính tiêu chí của mình: `codex --strict-config --help` chứng minh cờ được chấp
nhận ở cấp cao nhất, chứ không chứng minh một cấu hình đã được parse ở chế độ strict. Status Log có ghi
rằng kiểm tra này được *tách riêng có chủ ý* (vì `codex --strict-config plugin …` bị 0.147.0 từ chối),
điều đó khiến việc gán cứng kết quả càng khó hiểu hơn chứ không phải dễ hiểu hơn.

### F4 — `no_op_reinstall` không kiểm tra rằng lần cài lại là no-op (trung bình)

Dòng `probe_codex_packaging.sh:359` là `(raw / "plugin-reinstall.stdout").is_file()` — luôn đúng vì
`run_cli` đã tạo file đó bằng chuyển hướng và sẽ `die` nếu mã thoát khác 0. Điều đó chứng minh lần `add`
thứ hai đã thành công, cũng có giá trị nhất định, nhưng không chứng minh nó có tính lũy đẳng.

Sau lần reinstall không có gì kiểm tra lại rằng cache vẫn chứa đúng một thư mục phiên bản với nội dung
không đổi: phép kiểm tra tính duy nhất chạy *trước* đó (`:205-216`), còn khẳng định kế tiếp (`:238`) là
sau khi đã gỡ cài đặt.

### F5 — Dòng Verify dùng pytest thất bại khi chạy lại (trung bình)

```
$ python3 scripts/verify_summary.py --check codex-support-phase-2
PASS     [Packaging lifecycle contract]  exit=0
SC-FAIL  [Packaging decision unit contract]  criterion=SC-2  sc_expected=0  actual=1
         command: python3 -m pytest scripts/test_check_codex_packaging.py -q
PASS     [Packaging decision evidence]  exit=0
```

Trình thông dịch mặc định trên máy này không có pytest; `run-tests.sh` thì ưu tiên phân giải một venv
riêng. Đây **đúng** là khiếm khuyết đã sửa ở Phase 1 và đã được ghi vào
`specs/codex-support-phase-1/SUMMARY.md` kèm lý do nêu rõ — nó tái diễn ở đây.

SC-2 vẫn còn một dòng phủ nhờ checker quyết định, nên cổng phủ SC vẫn pass. Nhưng
`scripts/ci-strict-gate.sh` có chạy lại các dòng Verify, và một dòng chỉ pass dưới một trình thông dịch
duy nhất thì không phải là bằng chứng chạy lại được.

**Đề xuất sửa.** Bỏ dòng đó đi và dẫn bộ unit test bằng văn xuôi, như Phase 1 đã làm.

### F6 — `packaging.plugins` bị nâng lên `status: supported` (thấp)

Hàng này mang `support_target: advisory` và `load_bearing: false`, còn bằng chứng của chính nó mang
`runtime_execution_observed: false`. Giá trị ở Phase 1 là `advisory`, khớp với quan sát thực tế hơn.

Việc nâng cấp này không phải tùy chọn: `check_codex_packaging.py:190-196` **bắt buộc**
`status == "supported"`. Một cổng ép ra tuyên bố rộng hơn bằng chứng của nó là điều đáng nêu ra tự thân
— đó chính là lớp lỗi mà pha này ở những chỗ khác lại phòng thủ rất tốt.

### F7 — Bộ sanitizer của probe yếu hơn của Phase 1 (thấp)

Dòng `probe_codex_packaging.sh:396` chỉ khớp `/Users/|/home/|/root/`. Còn `_private_strings` của Phase 1
gắn cờ **mọi** chuỗi bắt đầu bằng `/`. Một đường dẫn tạm `/var/folders/…` sẽ lọt qua sanitizer của chính
probe và chỉ bị bắt sau đó bởi `check_codex_packaging.py:86-90`, nơi dùng luật chặt hơn. Hai hợp đồng
khác nhau cho cùng một công việc, trong cùng một pha.

Hiện tại chưa có rò rỉ nào — các fixture chỉ nhúng giá trị boolean và một chuỗi phiên bản.

### F8 — Chốt chặn chống trùng HOME không thể kích hoạt (thấp)

Dòng `probe_codex_packaging.sh:146-151` so sánh `$WORK/home` — vừa được `mktemp -d` tạo ra — với `$HOME`.
Hai giá trị này không bao giờ bằng nhau, nên chốt chặn này không thể sai. Nó trông như phép kiểm tra an
toàn cho việc cách ly, nhưng bảo đảm thật sự lại đến từ chính `mktemp`, và không có gì khẳng định điều đó.

## Khuyến nghị

F1 và F2 là hai điều cần đóng trước khi phần này được đưa vào. Cùng nhau, chúng có nghĩa là quyết định
đóng gói đang dựa trên một ứng viên thật và một ứng viên tự chứng minh chính nó, còn lối thoát mà nó nêu
tên thì không thể thực thi. F3–F5 rẻ và thuần cơ học. F6–F8 có thể ghi lại thành phạm vi phủ định trong
mục `### Not auto-verified` của SUMMARY nếu không sửa.

Bất cứ điều gì không sửa đều nên được nêu trong `### Not auto-verified` kèm tầng bằng chứng của nó, theo
`CLAUDE.md` → Gate verifiability. Cụ thể, dòng hiện có trong SUMMARY

> The committed evidence contains no user paths, auth, transcripts, model calls, or unrelated
> configuration.

là chính xác, nhưng SUMMARY không nói rằng bằng chứng của ứng viên direct cũng không chứa *quan sát nào
về Codex*. Điều đó thuộc về bản ghi.

## Kết quả xử lý (2026-08-10)

Tất cả phát hiện đã được xử lý trước khi tiếp tục pha kế tiếp:

- **F1:** direct nay là `unknown` có owner; file đại diện không còn bị trình bày như quan sát từ
  Codex, và Phase 5 sở hữu điều kiện đóng discovery/conflict rõ ràng.
- **F2:** lỗi lifecycle hybrid vẫn xuất evidence không-pass; checker chỉ bắt ứng viên được chọn phải
  pass, và unit test chứng minh có thể chọn một fallback đã được chứng minh độc lập.
- **F3:** strict parsing được đo thật: key lạ phải sinh diagnostic strict-config, còn config rỗng hợp
  lệ phải parse tới biên không có terminal mà không gọi model.
- **F4:** reinstall so sánh phiên bản cache duy nhất và fingerprint cây nội dung trước/sau; fault
  injection chứng minh nội dung thay đổi làm check thất bại.
- **F5:** đã bỏ Verify row pytest độc lập. Bộ 11 unit test vẫn được đăng ký trong
  `scripts/run-tests.sh`; lỗi ban đầu không tái hiện ở lần chạy cuối.
- **F6:** `packaging.plugins` là advisory với evidence lifecycle đã quan sát, không phải evidence
  runtime supported.
- **F7:** sanitizer của probe nay đệ quy từ chối mọi Unix/Windows absolute path hoặc `file://`, đồng
  nhất với checker.
- **F8:** so sánh alias caller dư thừa được thay bằng assertion có thể kiểm chứng rằng hai state root
  rỗng, khác nhau và là con trực tiếp đã resolve của thư mục probe mới.
