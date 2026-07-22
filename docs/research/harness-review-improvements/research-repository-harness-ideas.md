# Nghiên cứu: `hoangnb24/repository-harness` — ý tưởng nào nên áp dụng

> **Nguồn:** https://github.com/hoangnb24/repository-harness (clone HEAD, tag `harness-cli-v0.1.9`)
> **Ngày:** 2026-06-09
> **Phương pháp:** clone repo, 25 agent đọc song song từng subsystem (Rust CLI, SQLite durable layer,
> trace/scoring, evolution infra, intake lifecycle, distribution), map đối chiếu với repo này, mỗi ý tưởng
> qua một skeptic phản biện trước khi tổng hợp. 16 ý tưởng được trích → chấm verdict adopt/adapt/skip + fit_score.
> **Xác minh tại chỗ (đã chạy lệnh):** `specs/` gitignored; `docs/solutions/` và `docs/harness-experimental/`
> không tồn tại trên đĩa dù được tham chiếu nhiều nơi; 4 standalone skill trong `skills/README.md` là phantom;
> `validate-buzz-commands.sh` phantom; `render-plan-on-write.sh` có trên đĩa + đang fire nhưng thiếu trong bảng hook CLAUDE.md.

---

## 1. TL;DR

- **Repo của họ về bản chất là một SẢN PHẨM phân phối, agent-agnostic**: một **CLI Rust biên dịch** (clap + SQLite nhúng qua rusqlite) bọc trong kiến trúc clean 4 lớp, cài qua `curl | bash` vào repo bất kỳ, có CI cross-compile 5 nền tảng, checksum SHA256, auto-changelog/tag mỗi PR. Đây là một **công cụ**, không phải bộ prompt.
- **Khác biệt chiến lược lớn nhất — một câu**: họ là **durable + measured + portable** (trạng thái trong DB queryable, chất lượng được *chấm điểm* và *gate bằng exit code*, cài được vào mọi repo/agent); chúng ta là **prompt + file + bespoke** (skill markdown, trạng thái markdown gitignored, đặc thù Claude-Code, single-user dogfood).
- **Ý tưởng mạnh nhất của họ — "entropy score"**: một con số sức khỏe harness 0–100 (thấp = tốt) tổng hợp từ 6 tín hiệu drift có trọng số (orphaned story×10, broken tool×8, unverified×5, stale×3...). Chúng ta **không có một con số nào** trả lời "quy trình của ta có đang mục ruỗng không?".
- **Ý tưởng đáng giá thứ hai — verify thực thi được**: `verify_command` lưu *trên record*, được CLI **chạy lại** (`story verify` / `verify-all`), ghi pass/fail + timestamp, exit 1 khi fail. Bảng `### Verify` của ta chỉ là exit code do người **gõ tay**, không bao giờ chạy lại.
- **Cảnh báo trung thực xuyên suốt**: phần lớn cỗ máy đó (≈2.700 dòng `infrastructure.rs`, JSON serializer tự viết tay, registry hardcode, score-context với đường dẫn doc nhúng cứng trong Rust) là **over-engineering cho một dogfood một người**. Nhiều rubric chấm điểm nhúng cứng layout repo của họ vào Rust biên dịch → tự rot khi doc di chuyển, đúng cái entropy mà công cụ định phát hiện.
- **Xác minh tại chỗ phơi bày lỗi drift trong CHÍNH repo ta**: `docs/solutions/` và `docs/harness-experimental/` (ledger trust-metrics) **không tồn tại trên đĩa** dù được CLAUDE.md/skill/`harness-status.sh` tham chiếu; 4 standalone skill trong `skills/README.md` không có thật; `render-plan-on-write.sh` có trên đĩa nhưng **thiếu** trong bảng hook của CLAUDE.md; `validate-buzz-commands.sh` được liệt kê nhưng không tồn tại. Đây chính là "broken registry / over-claiming" mà một maturity-audit sẽ bắt được.

## 2. Repo này khác gì chúng ta

| Trục | Họ (`repository-harness`) | Chúng ta (`harness-skills`) |
|---|---|---|
| Bản chất | CLI Rust biên dịch + SQLite | Skill = prompt markdown (`/skill-name`) |
| Trạng thái | `harness.db` — 7 bảng typed, FK, CHECK enum, WAL, queryable (`query sql`) | Markdown gitignored dưới `specs/<slug>/` — không schema, không query, không tồn tại sau clone |
| Tổng hợp xuyên việc | JOIN/GROUP BY toàn lịch sử | Mỗi slug là một hòn đảo; chỉ grep được |
| Verification | `verify_command` lưu trên record, **chạy lại**, ghi pass/fail+timestamp, exit 1 | Bảng `### Verify` gõ tay; hook chỉ `grep` sự hiện diện, không chạy lại |
| Chất lượng record | `score_trace` 0–3 tier theo lane, **exit 1** nếu dưới yêu cầu | Hợp đồng subagent = prose, không ai parse độ đầy đủ |
| Sức khỏe harness | `audit` → entropy 0–100 + 6 query drift + ID vi phạm | Không có số; chỉ quy ước "30 ngày = stale", không ai tính |
| Self-improvement | `propose` đếm friction lặp (≥2), confidence theo count, ghi backlog | `/compound` = LLM đọc transcript 1 phiên, không đếm xuyên phiên |
| Lane mapping | Hàm Rust thuần, unit-test (tiny→Minimal...) | Prose trong `feature-intake/SKILL.md`; chỉ `risk-corroboration.sh` regex gate |
| Tool registry | Manifest queryable, arg schema, `since`, broken-tool check | Bảng prose trong README/CLAUDE.md — đã drift khỏi đĩa |
| Phân phối | `curl|bash` + PowerShell, CI release 5 nền tảng, checksum, auto-changelog/tag | Có `install-harness.sh`/`deploy-harness.sh`; **không** CI, không version, không changelog, không tag |
| Entry doc | `AGENTS.md` vendor-neutral + cầu `--claude` import vào CLAUDE.md | Hardwired Claude-Code; entry là CLAUDE.md; không có `AGENTS.md` (chỉ `HARNESS.md`) |
| Người dùng | Sản phẩm cho nhiều agent/contributor (Claude/Codex/Cursor) | Dogfood một người, Claude-Code only |

## 3. Ý tưởng nên ADOPT

> Không có ý tưởng nào ở verdict thuần "adopt-as-is" — bản chất họ là compiled tool, ta là markdown. Tất cả ý tưởng giá trị đều là **ADAPT** (mục 4). Mục này trống một cách trung thực: **không nên bê nguyên xi bất kỳ cơ chế nào của họ**, vì mọi cơ chế đều giả định DB/binary mà ta cố tình không có.

## 4. Ý tưởng nên ADAPT (xếp theo fit_score giảm dần)

### IDEA-02 — `verify_command` lưu + chạy lại được (fit 72)
**Gap thật:** `commit-quality-gate.sh` chỉ `grep -q '^### Verify'` (kiểm tra *sự hiện diện*); exit code trong bảng là **do agent gõ tay**, không có gì chạy lại lệnh hay lưu kết quả/timestamp.
**Reshape cho ta (bash/python, KHÔNG DB):**
- Thêm `scripts/verify-summary.py` (theo khuôn `check_plan_format.py`): parse bảng `### Verify` trong `specs/<slug>/SUMMARY.md`, chạy từng `Command` (timeout 60s, từ repo root), **ghi đè cột Exit bằng exit code THẬT** + dòng `Verified: <timestamp>`. Exit 1 nếu fail hoặc claimed ≠ actual.
- `--all`: glob `specs/*/SUMMARY.md`, in tally kiểu họ (`N checked, P passed, F failed, S skipped`).
- Nâng cấp `commit-quality-gate.sh`: khi `REQUIRE_VERIFY=1`, thay `grep` bằng gọi `verify-summary.py`.
- Sửa comment trong `templates/SUMMARY.template.md`: cột Exit do máy ghi đè, agent thôi tự khẳng định.
**Cảnh báo:** `--all` chạy lệnh từ MỌI slug (kể cả branch bỏ dở) → footgun nếu lệnh có side-effect (`alembic upgrade`); mặc định chỉ chạy slug active, yêu cầu lệnh read-only/idempotent. Sửa `commit-quality-gate.sh`/`settings.json` là **Rule-4 high-blast** → phải qua full chain. Lưu trữ timestamp ít giá trị vì `specs/` gitignored; giá trị nằm ở *việc chạy lại*, không ở record bền.

### IDEA-12 — Maturity ladder gated bằng evidence kiểm tra được (fit 72)
**Premise được xác minh ngay tại đây:** CLAUDE.md/README/HARNESS.md/`skills/README.md` tham chiếu nhiều subsystem **không tồn tại trên đĩa**.
**Reshape (lấy NGUYÊN TẮC, bỏ ladder/matrix):**
1. `scripts/check-harness-claims.sh` (hoặc gộp vào `harness-status.sh`): assert mọi subsystem tham chiếu trong doc đều tồn tại; exit non-zero + in cặp "claimed in X, absent on disk".
2. `HARNESS_MATURITY.md` **phẳng**: bảng `Subsystem | Claimed-in | Present-on-disk | Status` — KHÔNG phải matrix 6×11. Một dòng Covered chỉ khi checker pass.
3. Wire **advisory (non-blocking)**.
**Bỏ:** ladder H0–H5 và matrix 11-responsibility — đó là phần dành cho sản phẩm phân phối nhiều adopter; với dogfood một người nó thành matrix tự rot.

### IDEA-03 — Chấm điểm độ đầy đủ record, gate bằng exit code theo lane (fit 68)
**Gap:** hợp đồng subagent (Commits/Files/Lane/Deviations/Verify/Harness-Delta) là prose không ai parse.
**Reshape:** thêm `hooks/record-quality-gate.sh` (PreToolUse `git commit`, cạnh `risk-corroboration.sh`) — **dùng lại đúng cách resolve Lane của `risk-corroboration.sh`**: grep `^Lane:`, normalize tiny|normal|high-risk. Map lane→section bắt buộc: tiny→header (Lane/Confidence/Reason); normal→ + 1 dòng `### Verify` non-placeholder; high-risk→ + `### Rollback`. Miss → in danh sách thiếu + exit 2. Mặc định WARN, bật chặn bằng `RECORD_QUALITY_STRICT=1` (theo nếp `RISK_CORROBORATION_STRICT`). **KHÔNG** viết module Python, KHÔNG thêm field duration/token, KHÔNG bê "anti-laziness sentinel".
**Cảnh báo:** tiny-lane direct edit có thể commit không kèm SUMMARY → phải fallback WARN khi không có SUMMARY. Ship WARN trước rồi mới flip.

### IDEA-10 — Lane→evidence mapping thành code testable (fit 68)
**Gap:** mapping lane→ceremony chỉ là prose ở `feature-intake/SKILL.md` Step 7, lại bị **nhân bản 3 nơi** (Step 3, `rules/auto-correct-scope.md` Rule 4, `risk-corroboration.sh`) mà không gì giữ đồng bộ.
**Tiền lệ đã có:** `scripts/check_plan_format.py` (174 dòng) + `scripts/test_check_plan_format.py` (218 dòng) — ta ĐÃ encode quy ước markdown thành code có test.
**Reshape:** `scripts/check_lane_evidence.py` + test. Một mapping nguồn-sự-thật duy nhất; script đọc `specs/<slug>/SUMMARY.md` thật, exit non-zero nếu thiếu artifact. **Consumer là mấu chốt** — gate vào specs dir thật. Wire warn-first hook + cho Step 7 và `auto-correct-scope.md` trỏ về script này làm nguồn duy nhất.

### IDEA-04 — Audit drift + một con số sức khỏe 0–100 (fit 68)
**Gap (đã xác minh, tệ hơn mô tả):** `docs/solutions/` và `docs/harness-experimental/trust-metrics.md` **không tồn tại** dù được tham chiếu nhiều nơi; `harness-status.sh` cố đọc ledger và rơi vào `[not found]`.
**Reshape (bash+python, computed — KHÔNG để model assert, KHÔNG DB):** `scripts/harness-audit.sh`:
1. **phantom references** — grep path được trích dẫn nhưng không có trên đĩa;
2. SUMMARY có nhưng thiếu dòng `### Verify`;
3. PLAN status:active nhưng Status Log cũ;
4. `docs/solutions` có `confirmed_at:` >30 ngày (degrade về 0 khi dir trống);
5. orphan `.py` untracked (dùng lại `check-untracked-py.sh`).
Giữ **trọng số trong data** (assoc array / json sidecar) vì caveat của họ đúng: trọng số là magic number chưa hiệu chỉnh. **Báo cả tổng thô lẫn banded** — đừng `min(100)` âm thầm. Emit JSONL vào `docs/harness-experimental/audit-log.jsonl`, wire như dòng opt-in trong `harness-status.sh`, **không** làm blocking hook.

### IDEA-05 — Generator self-improvement từ friction tích lũy (fit 68)
**Gap:** tín hiệu `Harness-Delta` (fix-direct/backlog/none) trong SUMMARY là gitignored → **chết ngõ cụt**; `/compound` chỉ đọc 1 phiên, không đếm xuyên phiên. `docs/research/harness-review-improvements/research-compound-loop-closure.md` của ta đã chẩn loop này "mở/bán-khép".
**Reshape (markdown/grep, hybrid):**
1. Thêm cột `Harness-Delta` vào ledger `docs/harness-experimental/trust-metrics.md` (committed, dòng có ngày);
2. Mở rộng `harness-status.sh --propose`: group friction theo key normalize, gate count≥2, confidence (high≥3 else medium), emit proposal;
3. Backlog = `docs/harness-experimental/improvement-backlog.md`;
4. **Hybrid là bản mạnh nhất:** gate đếm ≥2 là filter deterministic; bước cluster ngữ nghĩa near-duplicate giao cho LLM của `/compound`. Wire một dòng vào `skills/compound/SKILL.md` để entry vượt ngưỡng thành trigger.
**Cảnh báo:** chỉ đáng nếu dev *thực sự triage*; nếu không, backlog thành nghĩa địa (anti-pattern "unread artifacts"). Ưu tiên thấp hơn việc đóng read-back loop.

### IDEA-14 — Cập nhật marked-block idempotent cho CLAUDE.md (fit 66)
**Gap:** `/compound` **cấm tự ghi CLAUDE.md** vì không có cơ chế cập nhật in-place an toàn; installer hiện `cp -R`.
**Tiền lệ:** `hooks/state-breadcrumb.sh` đã quản một section markdown delimited (`## Session End Log`); CLAUDE.md đã có marker `<!-- code-review-graph MCP tools -->`.
**Reshape:** `scripts/lib/marked-block.sh` với `upsert_marked_block <file> <begin> <end> <content>`: backup trước, `cmp -s` no-op nếu trùng, `awk` thay block giữa `<!-- HARNESS:BEGIN/END -->`, append nếu vắng. Gọi từ `install-harness.sh` để refresh vùng harness trong CLAUDE.md của project đích. **Để nguyên** `/compound` Step 6 — đây là tiền đề cho cầu AGENTS.md (IDEA-13), không phải để mở khóa auto-write compound.

### IDEA-08 — Vòng predicted-vs-actual outcome (fit 62)
**Gap:** decision/solution docs có rationale + confidence nhưng **không** ghép prediction-tại-tạo với outcome-đo-được.
**Reshape (2 field YAML + grep):** thêm `predicted_impact:` và `actual_outcome: null` vào `skills/compound/templates/decision-track.md`; mở rộng read tại planning-time của `/xia2` để surface docs có predicted set nhưng outcome null & confirmed_at >30 ngày ("open prediction loops"). **Cảnh báo:** rủi ro chính là `actual_outcome` mãi null → field write-only; chỉ đáng vì cực rẻ.

### IDEA-07 — Ghi intervention typed (human-correction là data) (fit 62)
**Gap:** `ESCALATIONS.md` chỉ bắt lát "hỏi-trước-khi-làm"; khi human **sửa** một diff autonomous *sau đó* → zero trace. Mà luận điểm cốt lõi của ta (Lane×Confidence = "giảm/biện minh can thiệp người") cần đúng dữ liệu này để biết autonomy có *thực sự earned* không.
**Reshape (markdown + compound, KHÔNG DB):** `templates/CORRECTIONS.template.md` (append-only `specs/<slug>/CORRECTIONS.md`): `type: correction|override|rework|approval`, `source`, `lane`, `what`, `commit`. Phân biệt cứng: escalation (hỏi-trước) ở `ESCALATIONS.md`; correction (quan-sát-sau) ở `CORRECTIONS.md`. Mở rộng FAILURE_TRACK miner của `/compound` để đọc nó. **Cảnh báo:** đếm "≥2 lần" xuyên specs gitignored không tin cậy → data chỉ directional. Ship consumer CÙNG template hoặc skip.

### IDEA-15 — Auto-changelog + version trên merge (fit 62)
**Gap (đã xác minh):** không CHANGELOG/VERSION/tag/CI nào; **installer pin `BRANCH=main`** → mọi user lặng lẽ nhận HEAD-of-main, **không có version surface**.
**Reshape (KHÔNG bê CI Rust/pull_request_target của họ):** thêm `CHANGELOG.md` + `VERSION` root; cho `skills/finishing-a-development-branch/SKILL.md` prepend entry lúc merge + bump VERSION (patch mặc định, minor/major khi đổi contract skill/hook); wire VERSION vào `install-harness.sh` để echo version vừa cài. Chỉ thêm 1 `release.yml` (release-please) *sau khi* bản thủ công chứng minh được duy trì.

### IDEA-09 — Tool/skill registry queryable + check tồn tại (fit 62)
**Gap (3 lỗi live, đã xác minh):** README liệt 4 standalone skill không có thật; CLAUDE.md liệt `validate-buzz-commands.sh` (phantom) và **bỏ sót** `render-plan-on-write.sh`.
**Reshape (1 bash check, KHÔNG registry sản phẩm):** `hooks/inventory-drift-check.sh` (kiểu `check-untracked-py.sh`): scan `skills/*/SKILL.md` (field `name:` là ground truth), `hooks/*.sh`, entry hook trong `settings.json`; assert mọi tên trong `skills/README.md`/bảng CLAUDE.md tồn tại trên đĩa và ngược lại; exit non-zero on drift. **Bỏ:** ToolEntry struct, taxonomy, semver, arg schema, SQLite.

### IDEA-01 — Lớp state durable, queryable (fit 58)
**Sự thật quan trọng:** ta **đã thiết kế** ledger cross-slug (`feature-intake/SKILL.md` trỏ tới `docs/harness-experimental/trust-metrics.md`; `harness-status.sh` đã parse nó) **nhưng chưa bao giờ build**.
**Reshape (tier nhẹ nhất, KHÔNG SQLite):**
1. Tạo + **track** `docs/harness-experimental/trust-metrics.md`; khóa schema cột trong header và `SUMMARY.template.md`;
2. `scripts/query-ledger.sh`: `--high-risk-no-verify`, `--friction`, `--stats`;
3. CHỈ nâng lên JSONL + script Python ~40 dòng nếu grep/awk trên markdown quá giòn; **không** nhảy SQLite trừ khi qua hàng nghìn dòng.
**Lý do không cao hơn:** schema 7 bảng + migration + WAL của họ là kiến trúc của *sản phẩm phân phối*; với một người, durable state chỉ đáng nếu *có người hành động trên query*.

### IDEA-06 — Chấm điểm context-read (fit 42)
**Chỉ ADOPT nửa data, BỎ nửa scorer.** `xia2/SKILL.md` đã là read-list theo phase với guardrail over-read ngầm.
**Reshape:** tạo `rules/context-rules.md` — ma trận phase × lane Must/Should/Skip + gợi ý token budget là **hint mềm, không gate**. **BỎ scorer:** không build `score-context`, không hook PostToolUse(Read), không ledger files_read — chính họ gọi phase-inference của họ là "brittle/over-fit".

### IDEA-13 — AGENTS.md agnostic + cầu @-import Claude (fit 38)
**Reshape rất hẹp, bác phần lớn.** Framing "agnostic, Codex/Cursor" là non-fit. "Tách doctrine portable" phần lớn **đã xong**: `HARNESS.md` chính là doc doctrine; CLAUDE.md đã dùng `@`-import. **Gap thật duy nhất:** payload installer **không gồm** `HARNESS.md`/`CLAUDE.md` → project đích nhận skills nhưng không có entry doc.
**Reshape:** thêm `HARNESS.md` vào PAYLOAD của `install-harness.sh`; dùng cơ chế marked-block (IDEA-14) inject 1 dòng `@.claude/HARNESS.md` vào CLAUDE.md của consumer. **KHÔNG** rename thành AGENTS.md, KHÔNG issue template Codex/Cursor.

## 5. Ý tưởng nên SKIP (và vì sao)

- **IDEA-11 — Schema versioning + brownfield importer (fit 18, verdict SKIP).** Hoàn toàn **phụ thuộc vào IDEA-01 (một DB) mà ta đã từ chối**. "Schema" của ta là vài template markdown mà **git đã version sẵn** (diffable, revertable, zero machinery). Không có corpus brownfield nào để ingest (một người, 2 slug active). Build importer lúc này là **speculative** (vi phạm `behavior.md` §2). **Hành động: chưa làm gì**; ghi dependency có điều kiện vào decision-track để agent tương lai không re-propose độc lập.

> **Nguyên tắc xuyên suốt phần SKIP/ADAPT:** mọi cơ chế chỉ "fit" *vì họ là compiled tool có DB* — JSON serializer tay, ASCII table tay, `compiled_tool_registry()` hardcode, score-context với path nhúng cứng trong Rust, `pull_request_target` auto-push-main — đều là **wrong altitude** cho một prompt-framework. Port **khái niệm** (verify chạy được, trace tier, context matrix, entropy) thành file/hook là đúng; port **chất nền binary** là sai.

## 6. "Một version khác" — phác thảo

Nếu ta thực sự muốn một **v2** lấy cảm hứng từ họ, hình hài tối thiểu khả thi (KHÔNG Rust, KHÔNG SQLite):

- **Lõi: một ledger committed + queryable bằng grep/awk.** Đây là *điều kiện tiên quyết* cho mọi thứ khác (scoring, audit, propose, predicted-vs-actual đều cần nơi để query). Cụ thể: build *thực sự* `docs/harness-experimental/trust-metrics.md` mà ta **đã thiết kế nhưng chưa bao giờ tạo** — committed, header cột cố định (Date|Slug|Lane|Confidence|Verify|Harness-Delta|Hook-outcome), `scripts/query-ledger.sh` cho vài query đặt sẵn.
- **Tầng đo lường (build trên lõi):** `scripts/harness-audit.sh` (entropy số 0–100, trọng số trong data), `scripts/verify-summary.py` (chạy lại Verify table), `hooks/record-quality-gate.sh` (gate độ-đầy-đủ theo lane). Mỗi cái là một file/hook, exit-code-gating — bám đúng tiền lệ `check_plan_format.py`.
- **Tầng portability (build sau cùng):** marked-block updater (IDEA-14) + `HARNESS.md` vào payload + VERSION/CHANGELOG. Đây là phần đưa harness vào repo khác *an toàn*, nhưng vẫn Claude-first — KHÔNG đuổi theo agnostic Codex/Cursor (zero consumer).

**Có đáng không — ý kiến thẳng:** Một **v2 toàn diện kiểu họ là KHÔNG đáng** cho một dogfood một người — nó nhập nguyên nợ bảo trì (migration, drift markdown↔DB, build toolchain) để phục vụ một người chủ yếu cần "show all high-risk no-verify" vài lần. Nhưng **lõi ledger + 2–3 file đo lường thì RẤT đáng**, vì (a) ta đã *thiết kế* ledger và để nó vaporware, (b) xác minh tại chỗ cho thấy ta *đang* over-claim subsystem không tồn tại, và (c) chúng dùng đúng tiền lệ bash/python đã được chấp nhận. Lằn ranh trung thực: **build cho query có thể gọi tên hôm nay, không build cho analytics platform giả định.**

## 7. Đề xuất bước đi kế tiếp (quick wins trước)

1. **Sửa drift đã xác minh ngay (≈0 effort, cao nhất).** Bỏ 4 standalone skill ảo khỏi `skills/README.md`; bỏ `validate-buzz-commands.sh` khỏi bảng hook CLAUDE.md; thêm `render-plan-on-write.sh` vào bảng. _(ĐÃ LÀM — 2026-06-09.)_
2. **Build ledger đã thiết kế (IDEA-01, tier nhẹ).** Tạo + track `docs/harness-experimental/trust-metrics.md`, khóa schema cột, `scripts/query-ledger.sh`. Mở khóa IDEA-04/05/08.
3. **`scripts/harness-audit.sh` (IDEA-04).** Check (1) phantom references — sẽ tự bắt mọi drift; trọng số trong data; advisory, wire vào `harness-status.sh` thay nhánh chết.
4. **`scripts/check-harness-claims.sh` + `HARNESS_MATURITY.md` phẳng (IDEA-12).** Chồng lấn nhiều với #3; gộp chung được. Advisory, non-blocking.
5. **`scripts/check_lane_evidence.py` + test (IDEA-10).** Theo khuôn `check_plan_format.py`; hook warn-first.
6. **`hooks/record-quality-gate.sh` (IDEA-03).** Dùng lại resolve-Lane của `risk-corroboration.sh`; ship WARN trước.
7. **`scripts/verify-summary.py` (IDEA-02).** Medium, đụng Rule-4 (`commit-quality-gate.sh`/`settings.json`) → qua full chain.
8. **`scripts/lib/marked-block.sh` + wire installer (IDEA-14 → IDEA-13).** Quick win độc lập, mở đường đưa `HARNESS.md` vào payload.
9. **VERSION/CHANGELOG qua finishing skill (IDEA-15).** Đóng gap "installer pin main, no version".
10. **Sau cùng, có điều kiện:** IDEA-05/07/08 (self-improve loops) chỉ làm *sau khi* ledger có data thật và có cam kết triage.
11. **Không làm:** IDEA-11 (importer/migration) cho tới khi — nếu bao giờ — IDEA-01 lên DB thật.
