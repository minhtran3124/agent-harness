# Nghiên cứu: repo `harness-skills` đối chiếu REQ.md — đáp ứng được gì, thiếu gì, cải thiện gì

> **Câu hỏi:** Repo hiện tại đáp ứng được bao nhiêu phần của "The Harness Approach" (REQ.md)?
> Thiếu gì, cải thiện gì để đáng tin cậy hơn, và hạn chế cấu trúc nào cần khắc phục?
> **Ngày:** 2026-06-11
> **Phương pháp:** 2 agent khảo sát song song (inventory + adversarial gap audit) trên toàn bộ
> skills/ hooks/ rules/ templates/ tests/ docs/, sau đó xác minh tại chỗ các điểm mâu thuẫn
> (PROJECT.md, ledger, defaults, test coverage). Kế thừa 2 nghiên cứu trước:
> `research-compound-loop-closure.md` (2026-06-08) và `research-repository-harness-ideas.md` (2026-06-09).
> **Lưu ý xác minh:** một finding của agent audit ("CI không test hành vi hook") bị bác —
> `tests/hooks/` có đủ 10 file test hành vi; ledger `docs/harness-experimental/trust-metrics.md`
> đã tồn tại, được git-track, có 5 dòng dữ liệu thật (khác với trạng thái vaporware ghi nhận 2026-06-09).
> **Cập nhật cùng ngày (sau phản hồi của owner):**
> (1) Đây là **repo nguồn** tạo/setup harness — `docs/solutions/` rỗng là trạng thái kỳ vọng
> (entries sinh ra ở repo tiêu thụ hoặc qua dogfood), không phải defect.
> (2) `specs/` **đã được bỏ khỏi `.gitignore`** (`#specs/`) — finding "audit trail không persist"
> đã được giải quyết về cơ chế; còn lại việc commit lần đầu + cập nhật doc còn khẳng định ngược
> (`CLAUDE.md:61`, `rules/plan-format.md:125`) và quyết định có ignore riêng `PLAN.html` hay không.

---

## Source questions (from REQ.md, deleted 2026-07-17)

> REQ.md was removed as a stale stub (issue #67 Phase 2, wave 1). Its six harness
> questions — the subject this assessment scores against — are preserved verbatim:
>
> - What should I read first?
> - What type of work is this?
> - Which product contract does it affect?
> - How risky is the change?
> - What proof will show the work is done?
> - What decision or lesson should future agents inherit?

---

## 1. TL;DR

- **Điểm theo 6 câu hỏi REQ.md: trả lời tốt 4/6.** Mạnh nhất là *"How risky?"* (Q4) và
  *"What type of work?"* (Q2) — có classifier + hook corroboration bằng máy. Yếu nhất là
  *"Which product contract does it affect?"* (Q3 — **không có cơ chế nào trả lời**) và
  *"What lesson should future agents inherit?"* (Q6 — máy móc đã build nhưng **kho rỗng, vòng lặp bán-khép**).
- **Khoảng cách lớn nhất giữa thiết kế và thực tế:** hạ tầng enforce (hooks, CI, test, ledger) đã
  trưởng thành đáng kể, nhưng **lớp dữ liệu chưa được nạp**. Với `docs/solutions/` và
  `agent-memory/` điều này là *kỳ vọng* (repo nguồn — dữ liệu sinh ở repo tiêu thụ); hệ quả thật
  còn lại là pipeline `/compound` **chưa được kiểm chứng end-to-end với dữ liệu thật**, và
  `xia2/PROJECT.md` vẫn là template placeholder cho chính repo này.
- **Hai gate quan trọng nhất đang fail-open theo mặc định** (`REQUIRE_VERIFY=0`,
  `RISK_CORROBORATION_STRICT=0`). Riêng strict-default là **quyết định chủ đích có ghi trong ledger**
  ("strict-default decision: keep warn", slug `p3-hook-fixes`) — không phải bug, nhưng là tradeoff
  cần nhìn lại khi harness rời giai đoạn dogfood.
- **Proof hiện là assertion, chưa phải fact:** cột `Exit` trong bảng `### Verify` do agent gõ tay,
  không có gì chạy lại. Việc bỏ `specs/` khỏi gitignore (2026-06-11) giải quyết vế *persist* —
  artifact proof giờ commit được — nhưng vế *machine-verified* (re-run lệnh Verify) vẫn mở.

---

## 2. Repo đã đáp ứng được gì (đối chiếu 6 câu hỏi REQ.md)

| # | Câu hỏi REQ.md | Cơ chế trả lời | Mức enforce | Đánh giá |
|---|---|---|---|---|
| Q1 | What should I read first? | `CLAUDE.md` auto-load + `@`-import `rules/behavior.md`, `skills/README.md`; pointer tới `docs/solutions/critical-patterns.md`; `agents/PROJECT.md` cho execution agents | Document/convention — pointer tự nổi, **nội dung không tự nạp** | ✅ Khá — entry doc rõ, nhưng phụ thuộc model tuân theo pointer |
| Q2 | What type of work is this? | `/feature-intake`: 6 input-type, 10-flag checklist, 3 lane (tiny/normal/high-risk) + confidence → ghi `specs/<slug>/SUMMARY.md` | **Hook-corroborated** — `risk-corroboration.sh` chặn commit khi diff trip hard-gate mà Lane < high-risk | ✅ Mạnh nhất hệ thống |
| Q3 | Which product contract does it affect? | Chỉ gián tiếp: mục High-Blast Files / Shared Contracts trong `xia2/PROJECT.md` | **Không có** — PROJECT.md là placeholder; SUMMARY template không có field contract/module; intake không hỏi | ❌ Không được trả lời |
| Q4 | How risky is the change? | 10-flag + hard gates (intake) · `risk-corroboration.sh` · `blast-radius-check.sh` · `branch-guard.sh` · Rule 1–4 `auto-correct-scope.md` | Hook chặn được — **nhưng fail-open khi thiếu Lane** (trừ khi `RISK_CORROBORATION_STRICT=1`) | ✅ Mạnh, có lỗ mặc định |
| Q5 | What proof will show the work is done? | Bảng `### Verify` (SUMMARY) · `<verify>` per task (PLAN.md, <60s, exit-0) · `TEST_MATRIX.md` · `commit-quality-gate.sh` (secrets + debug + targeted pytest) | Một phần — pytest targeted có chạy thật; nhưng check `### Verify` là **opt-in** (`REQUIRE_VERIFY=1`) và chỉ grep sự hiện diện, **không chạy lại lệnh** | ⚠️ Trung bình — proof là self-reported |
| Q6 | What lesson should future agents inherit? | `/compound` (4 track bug/knowledge/decision/failure) · `docs/solutions/` schema + INDEX · `critical-patterns.md` · ledger `trust-metrics.md` (committed, 5 dòng) · `agent-memory/` confidence-decay | Pull-only — `/xia2` và `/brainstorming` có đọc lại, **không có SessionStart auto-load** | ⚠️ Thiết kế tốt; kho rỗng là kỳ vọng (repo nguồn) nhưng pipeline chưa kiểm chứng thực chiến, loop bán-khép |

### Đối chiếu 5 failure mode mà REQ.md muốn ngăn

| Failure mode (REQ.md) | Đã ngăn chưa | Bằng cách nào |
|---|---|---|
| Agent sửa code trước khi hiểu intent | ✅ phần lớn | `/feature-intake` bắt buộc chạy đầu; `scope-gate.sh` cảnh báo prompt có ý định implement mà không có plan (nhưng chỉ warn, không chặn) |
| Constraint chỉ sống trong chat | ✅ phần lớn | `rules/` + `CLAUDE.md` committed; SUMMARY/ESCALATIONS template hoá quyết định; `specs/` đã bỏ ignore (06-11) nên constraint per-task giờ persist được — cần commit lần đầu |
| Kỳ vọng validation mơ hồ / phát hiện muộn | ⚠️ một nửa | `<verify>` per task + `### Verify` + TEST_MATRIX có khuôn; nhưng REQUIRE_VERIFY mặc định tắt, không re-run |
| Tradeoff kiến trúc bị lặp lại thay vì kế thừa | ❌ chưa | Cơ chế `/compound` → `docs/solutions/` có, nhưng 0 entry, 0 critical pattern, loop chỉ pull |
| Request lớn không được bẻ thành story-sized | ⚠️ một nửa | `plan-format.md` có ngưỡng (>3 steps / >2 files / >30min) + wave-parallelism + `check_plan_format.py` validate **format**; nhưng ngưỡng kích thước chỉ là prose, không gì kiểm |

### Nền hạ tầng đã có (điểm cộng đáng kể)

- **9 hook wired** + 1 dormant, bảng hook trong CLAUDE.md **khớp** `settings.json` (đã xác minh).
- **Test thật:** 10 file test hành vi hook (`tests/hooks/*.test.sh`), 2 test script, pytest cho
  `check_plan_format` / `render_plan` / feature-intake canaries; CI `harness-ci` chạy ubuntu+macos
  kèm **doc-truth lint** (fail khi doc tham chiếu path không tồn tại — chính là thuốc cho đợt drift 06-09).
- **Ledger `trust-metrics.md` đã build, committed, có dữ liệu** — gap lớn nhất của nghiên cứu 06-09
  (IDEA-01) đã được đóng ở tier nhẹ.
- 14 skill phủ trọn vòng đời intake → brainstorm → research → plan → execute → review → compound → ship.

---

## 3. Repo đang thiếu gì

Xếp theo mức nghiêm trọng:

1. **(Cao) Q3 không có lời giải — không registry contract/domain nào.**
   SUMMARY template có Lane/Confidence/Reason/Flags nhưng không có field "contract/module bị ảnh hưởng";
   intake không hỏi; `xia2/PROJECT.md` (nơi thiết kế để khai High-Blast Files + Shared Contracts)
   **vẫn là placeholder `<your project name>` cho chính repo này** → `/xia2` mất nguồn tín hiệu chính,
   PROJECT-CONFIG-GATE đáng lẽ phải halt.
2. **(Cao → một nửa đã giải quyết 06-11) Proof không re-run; persist đã mở khoá nhưng chưa hoàn tất.**
   `specs/` đã bỏ khỏi `.gitignore` → SUMMARY/PLAN/ESCALATIONS/STATE/TEST_MATRIX commit được
   (10 slug + STATE.md hiện đang untracked, chờ commit lần đầu). Việc còn lại: (a) cột Exit trong
   `### Verify` vẫn do agent tự khai, không cơ chế nào chạy lại (IDEA-02 chưa làm); (b) 2 doc tracked
   vẫn khẳng định ngược — `CLAUDE.md:61` ("specs/ is fully gitignored") và `rules/plan-format.md:125`;
   (c) cần quyết định có ignore riêng artifact dẫn xuất (`PLAN.html`) hay không.
3. **(Hạ cấp: kỳ vọng của repo nguồn) Kho tri thức rỗng.** `docs/solutions/INDEX.md` 0 entry,
   `critical-patterns.md` "none yet", `agent-memory/` chỉ có README — **đây là trạng thái đúng của
   repo nguồn**: dữ liệu sinh ra ở repo tiêu thụ harness, hoặc qua dogfood. Hai hệ quả thật còn lại:
   (a) pipeline `/compound` (collision handling, severity triage, INDEX rebuild) **chưa từng chạy với
   dữ liệu thật** nên chưa được kiểm chứng end-to-end; (b) vòng lặp đọc-lại vẫn bán-khép ở mọi repo
   deploy harness (chỉ pull qua `/xia2`/`/brainstorming`, không SessionStart hook — kết luận 06-08
   vẫn nguyên hiệu lực và áp cho consumer).
4. **(Vừa) Hai gate chủ lực fail-open mặc định.** `REQUIRE_VERIFY=0` (evidence check tắt) và
   `RISK_CORROBORATION_STRICT=0` (diff trip hard-gate mà *không khai Lane* → chỉ warn). Ghi nhận:
   keep-warn là quyết định chủ đích trong ledger — nhưng nghĩa là tầng an toàn cuối phụ thuộc
   kỷ luật khai Lane của agent.
5. **(Vừa) Story-sizing là guideline, không phải gate.** Ngưỡng >3 steps / >2 files không được
   script nào kiểm; một plan 10-file 1-wave vẫn đi qua trơn tru.
6. **(Vừa) Không version/changelog cho payload phân phối.** `install-harness.sh` pin `main`,
   consumer nhận HEAD lặng lẽ (IDEA-15, chưa làm).
7. **(Thấp) `auto-test-on-change.sh` dormant** — feedback test bị dồn về commit-time.
8. **(Thấp) `scope-gate.sh` chỉ advisory** — không gì *buộc* `/feature-intake` chạy trước; cả
   workflow routing phụ thuộc model tuân thủ prompt.

---

## 4. Cải thiện gì để đáng tin cậy hơn (ưu tiên giảm dần)

1. **Chạy `/bootstrap-xia2` điền `xia2/PROJECT.md` cho chính repo này** — rẻ nhất, mở khoá Q3+Q4:
   khai High-Blast Files thật (`settings.json`, `hooks/*`, `skills/visual-planner/render_plan.py`…),
   Shared Contracts (schema SUMMARY, ledger columns, hook exit-code contract).
2. **Thêm field `Affects:` (contract/module) vào `templates/SUMMARY.template.md` + một bước hỏi
   trong `/feature-intake`** — câu trả lời trực tiếp cho Q3; ledger thêm cột tương ứng để query được.
3. **`scripts/verify-summary.py` (IDEA-02): chạy lại bảng `### Verify`, ghi đè cột Exit bằng exit
   code thật** — chuyển proof từ assertion sang fact. Đã có tiền lệ khuôn (`check_plan_format.py` + test).
   Lưu ý footgun: chỉ chạy slug active, yêu cầu lệnh idempotent; sửa `commit-quality-gate.sh` là Rule-4.
4. **Khép vòng tri thức:** SessionStart hook in `INDEX.md` + `critical-patterns.md` (mức "vừa"
   trong research 06-08). Rule-4 (đụng `settings.json`) → cần người xác nhận. Song song:
   bắt đầu *thực sự chạy* `/compound` sau các phiên có lesson — hạ tầng đọc đã có sẵn, đang đói dữ liệu.
5. **Nâng dần fail-open → fail-closed có chủ đích:** bật `REQUIRE_VERIFY=1` +
   `RISK_CORROBORATION_STRICT=1` **trong CI trước** (an toàn, không chặn local dev), đo tỷ lệ vỡ
   qua ledger vài tuần rồi mới cân nhắc bật local. Tôn trọng quyết định keep-warn hiện hữu —
   đây là đề xuất nâng theo giai đoạn, không phải đảo quyết định.
6. **Hoàn tất việc mở specs/ (đã bỏ ignore 06-11):** (a) commit lần đầu 10 slug + STATE.md đang
   untracked; (b) sửa 2 doc còn khẳng định ngược (`CLAUDE.md:61` mục Gotchas,
   `rules/plan-format.md:125`) — và rà các skill mô tả "PLAN.html untracked/local-only"
   (`skills/README.md`, `visual-planner`); (c) quyết định ignore riêng artifact dẫn xuất
   (`specs/**/PLAN.html`) để tránh commit file HTML build được lại từ PLAN.md.
7. **Gate kích thước story:** mở rộng `check_plan_format.py` đếm `<files>`/steps mỗi task, warn khi
   vượt ngưỡng `plan-format.md` — biến ngưỡng prose thành check chạy được.
8. **Drift tự bắt:** `scripts/harness-audit.sh` (IDEA-04/12 gộp) check phantom references định kỳ —
   doc-truth lint trong CI đã phủ một phần, phần còn lại là SUMMARY thiếu Verify, PLAN active mà
   Status Log nguội, solutions `confirmed_at` >30 ngày.
9. **VERSION + CHANGELOG cho installer** (IDEA-15) khi bắt đầu có consumer thứ hai.

---

## 5. Hạn chế cấu trúc & cách khắc phục

| Hạn chế | Bản chất | Khắc phục |
|---|---|---|
| **Enforcement bằng prompt** — skill là markdown; lane mapping, escalation, subagent contract đều là prose model *nên* tuân theo | Cố hữu của prompt-framework; model có thể bỏ qua bất kỳ bước nào không có hook chặn | Tiếp tục chuyển các check load-bearing xuống hook/script exit-code (tiền lệ tốt: `check_plan_format.py`, `risk-corroboration.sh`, doc-truth lint). Ưu tiên: lane→evidence mapping (IDEA-10) để 3 bản sao prose có một nguồn sự thật chạy được |
| **`specs/` từng local-only** — đã bỏ ignore 2026-06-11, nhưng chuyển đổi chưa hoàn tất | Hạn chế gốc đã được gỡ về cơ chế; rủi ro còn lại là trạng thái nửa vời (slug chưa commit, doc nói ngược) | Commit lần đầu specs/; sửa `CLAUDE.md:61` + `rules/plan-format.md:125`; ignore riêng `PLAN.html` dẫn xuất; ledger vẫn là lớp tổng hợp xuyên-slug |
| **Hook detection bằng grep/regex** — đã có false-positive thật (ledger: "corroboration regex false-positive on tests/hooks/" ×2) | Regex trên diff không hiểu ngữ nghĩa; sẽ tiếp tục có cả false-positive lẫn false-negative | Đã đi đúng hướng (fix precision + 10 test hành vi). Chấp nhận đây là lưới thô — không tinh chỉnh vô hạn; tầng bù là review adversarial (`/correctness-review`) |
| **Vòng tri thức phụ thuộc người gọi skill** — `/compound` không tự chạy, solutions không tự nạp | "Pointer auto, content on-demand" | SessionStart hook (mục 4.4); thêm trigger nhắc `/compound` đã có (commit hook hint ≥5 app/ files) nhưng chưa từng có dịp nổ — theo dõi qua ledger |
| **Dogfood một người, Claude-Code-only** — chưa kiểm chứng đa-agent/đa-máy/đa-consumer | Mọi con số tin cậy hiện tại đến từ 1 user; fail-open chấp nhận được *vì* chỉ 1 user kỷ luật | Không vội agnostic-hoá (kết luận 06-09 vẫn đúng). Khi có consumer thứ 2: HARNESS.md vào payload installer + marked-block (IDEA-14/13) + VERSION |
| **Pipeline tri thức chưa qua thực chiến** — kho rỗng là kỳ vọng của repo nguồn, nhưng hệ quả là collision handling, severity triage, INDEX rebuild của `/compound` chưa chạy với dữ liệu thật bao giờ | Thiết kế chưa được kiểm chứng end-to-end trước khi deploy cho consumer | Dogfood `/compound` ngay tại repo nguồn cho các phiên harness gần đây (5 slug trong ledger đều có lesson đáng ghi — vd. quyết định keep-warn, false-positive regex) — vừa smoke-test skill vừa có corpus mẫu cho consumer |

---

## 6. Kết luận

Repo này **đã vượt qua giai đoạn "bộ prompt rời rạc"**: có classifier intake thật, gate commit bằng
máy, test + CI cho chính harness, ledger committed, và (từ 06-11) `specs/` persist được — tức là
4/6 câu hỏi REQ.md có cơ chế trả lời, trong đó Q2/Q4 ở mức tốt hiếm thấy với một prompt-framework.
Vì đây là **repo nguồn**, kho tri thức rỗng không phải defect; ba việc quyết định độ tin cậy giai
đoạn tới: **(1) hoàn tất chuyển đổi specs/** (commit lần đầu + sửa doc nói ngược + ignore PLAN.html
dẫn xuất), **(2) chuyển proof từ self-reported sang machine-verified** (re-run Verify, nâng strict
theo giai đoạn), và **(3) dogfood `/compound` + điền `xia2/PROJECT.md`** để pipeline tri thức được
kiểm chứng trước khi consumer dựa vào nó. Câu hỏi Q3 (product contract) là lỗ hổng thiết kế duy nhất
chưa có cơ chế nào — cần thêm field + điền PROJECT.md, không cần xây hệ thống mới.
