# Re-check `hoangnb24/repository-harness` (v0.1.10) — Adoption Audit & Đề xuất v2

- **Ngày:** 2026-07-03
- **Nguồn:** https://github.com/hoangnb24/repository-harness (clone HEAD, tag `harness-cli-v0.1.10`)
- **Bối cảnh:** đây là lần nghiên cứu THỨ HAI. Lần đầu: `docs/research-repository-harness-ideas.md` (2026-06-09, tại v0.1.9, 16 IDEA, kế hoạch 10 bước). Lần này có 2 input mới:
  1. **Deep review 2026-07-03** (`docs/research/2026-07-03-deep-review-harness-trustworthiness.md`) — tìm ra các failure mode hệ thống của repo ta;
  2. **Adoption audit** — soi từng IDEA cũ xem đã adopt đến đâu và còn sống không.
- **Phương pháp:** 2 agent song song (mechanism-level read repo họ · adoption audit repo ta), mọi claim verify bằng đọc code/git log.

---

## 1. TL;DR

- **Delta bên họ từ 06-09 → nay rất nhỏ:** chỉ thêm **inbound tool registry kind-aware với presence scanning** (US-027, PR #19) + fix installer + release v0.1.10. Toàn bộ Phase 4/5 (entropy, propose, interventions, trace scoring) đã nằm trong nghiên cứu cũ.
- **Phát hiện quan trọng nhất KHÔNG nằm bên họ mà nằm bên ta:** audit adoption cho thấy một **lằn ranh sạch tuyệt đối** — mọi thứ được **CI/hook enforce** (lint-doc-truth, verify_summary --check, ci-strict-gate, test suites) vẫn sống và chạy; mọi thứ dựa vào **kỷ luật append tay** (ledger, CHANGELOG, VERSION, backlog triage) **flatline đúng ngày 2026-06-14** — ngày burst adoption cuối cùng. PR #27 ship một hook wired mới (high-risk!) mà không có ledger row, không CHANGELOG entry, và **không gì chặn**.
- **Kết luận chiến lược:** repo ta đã tự chứng minh thesis "proof by machine, not assertion" trên chính mình trong 3 tuần. Bài học lớn nhất từ repo họ lần này không phải là một feature — mà là **nguyên tắc kiến trúc: bookkeeping phải được ghi bởi SỰ KIỆN (event), không phải bởi kỷ luật (discipline)**. Post-merge-maintenance.yml của họ là ví dụ hoàn hảo: CHANGELOG/tag/version được ghi bởi chính event merge, con người không bao giờ phải nhớ.
- **Đề xuất:** một **v2 theo hướng "Event-Sourced Trust Layer"** — 5 phase, chi tiết ở §6. Không Rust, không SQLite (giữ nguyên verdict cũ); chỉ đổi *ai là người ghi record*.

---

## 2. Delta bên họ từ v0.1.9 → v0.1.10

| Thay đổi | Nội dung | Đáng học? |
|---|---|---|
| US-027 tool registry (PR #19) | `tool register --kind cli\|binary\|mcp\|skill\|http` ghi *ý định*; `tool check` đối chiếu với *thực tế* bằng probe theo kind (PATH exec-check, file resolution, TCP), ghi `status + checked_at`, luôn exit 0. Degrade ladder: **Inactive** (chưa từng đăng ký → skip sạch) / **Degraded** (đăng ký nhưng mất trên đĩa → cờ "Weak proof") / **Full** | ✅ Rất đáng — xem §4.2 |
| Fix installer (PR #20) | Thêm file thiếu vào file-list installer | Không |
| Release v0.1.10 | Auto qua post-merge-maintenance | Cơ chế đáng học (§4.1) |

---

## 3. Adoption audit — nghiên cứu 06-09 đã được thực thi đến đâu

Adoption diễn ra 2 đợt: **06-11** (PRs #10–#13) và **06-14** (gap-closure #18–#25), route qua `docs/harness-gap-closure-plan.md`. **Sau 06-14: zero hoạt động adoption.**

| IDEA | Trạng thái | Bằng chứng |
|---|---|---|
| 01 ledger | **adopted-then-decayed** | trust-metrics.md tracked, schema locked (`2582d64`), 15 rows — nhưng `query-ledger.sh` không bao giờ build; row + commit cuối đều 06-14 (`fe43d1a`). PRs #27–#30 (kể cả high-risk branch-isolation-guard, có SUMMARY `929d4da`) **không có row nào** dù feature-intake Guardrails bắt buộc |
| 02 verify_summary | **adopted-faithfully** | Script + test, wired `commit-quality-gate.sh` (REQUIRE_VERIFY) + `ci-strict-gate.sh`, CI chạy thật. Footgun `--all` được né bằng cách *không implement* — đọc research an toàn nhất có thể |
| 03 record-quality-gate | **adopted-with-gaps (folded)** | Mapping lane→sections gộp vào `check_lane_evidence.py`; nhưng **không có PreToolUse hook nào gọi nó** — enforcement chỉ là CI unit test |
| 04 harness-audit | **adopted-with-gaps** | Script tồn tại (`4dd42df`), advisory, wired vào harness-status. Nhưng: không entropy 0–100, band hardcode (0/≤3/>3), **không audit-log.jsonl** → không lịch sử, không trend line — đúng cái "một con số theo thời gian" mà idea nhắm tới thì thiếu |
| 05 friction→propose | **adopted-with-gaps, cảnh báo đang thành sự thật** | Không `--propose`, không group count≥2. Backlog có **đúng 1 entry, status `open`, 19 ngày không ai đụng** — "backlog thành nghĩa địa" đang xảy ra |
| 07 CORRECTIONS | **not-adopted** (đúng plan — conditional) | Không file nào |
| 08 predicted/actual | **not-adopted** | Fields chỉ tồn tại trong chính research doc |
| 09/12 drift check | **adopted-faithfully (consolidated)** | `lint-doc-truth.sh` check 2 chiều bảng hook ↔ settings.json, chạy CI ubuntu+macos. HARNESS_MATURITY.md không tạo — vai trò do Evidence Tiers table gánh một phần |
| 10 lane evidence | **adopted-with-gaps** | Script + 13 tests trong CI. Nhưng: **feature-intake Step 7 không hề nhắc tới nó** dù auto-correct-scope.md *claim* là có — một doc-drift sống đúng class mà cả nỗ lực này nhắm tới, và `lint-doc-truth.sh` không bắt được (path tồn tại). Không hook runtime nào gọi script |
| 13/14 marked-block/HARNESS.md payload | **not-adopted (deferral có chủ đích)** | Re-deferred trong research-harness-req-assessment: "when a second consumer arrives" |
| 15 VERSION/CHANGELOG | **adopted-then-decayed** | Tạo `9e74138`, bump 0.2.0 `fe43d1a` (đều 06-14). Từ đó: PR #27 ship hook wired mới (minor-bump theo chính rule của CHANGELOG) + #28/#30 — `[Unreleased]` **rỗng**, VERSION đóng băng. Duy trì được đúng một chu kỳ release |

**Tỷ lệ:** 2 faithful · 5 with-gaps · 2 decayed · 4 not-adopted (~70% có công việc thật; bước 1–7, 9 của plan được thử; bước 8, 10 thì không).

**Lằn ranh sống/chết (bài học trung tâm):**

```
SỐNG  = được máy chạy:      lint-doc-truth (CI) · verify_summary --check (CI+hook) · ci-strict-gate (CI) · test suites (CI)
CHẾT  = chờ người append:   ledger rows · CHANGELOG entries · VERSION bumps · backlog triage · STATE.md Active Spec
```

---

## 4. Những cơ chế đáng học từ repo họ (mechanism-level, có caveat trung thực)

### 4.1. Post-merge maintenance bằng CI event — ⭐ đáng học nhất

`.github/workflows/post-merge-maintenance.yml`: `pull_request_target: closed` trên main, gate `merged == true`. Một step bash: `gh pr view` lấy title/author/files/mergeCommit → nếu file match regex CLI thì patch-bump version, prepend CHANGELOG entry có cấu trúc (date, PR#, author, merge SHA, file list), commit, push, tag idempotent (guard `git ls-remote --exit-code`), dispatch release workflow.

- **Giải đúng bệnh của ta:** record được ghi bởi *event merge*, không bởi kỷ luật ai cả. CHANGELOG của họ khớp chính xác mọi merge từ khi workflow land (PR #13/#19/#20); các merge trước automation đơn giản là vắng — một cutover trung thực.
- **Failure modes họ đã gặp:** chỉ fire trên PR merge (push thẳng main vô hình); chính automation cũng từng ship bug (`7e6c199` fix printf); race khi merge đồng thời.
- **Portability: xuất sắc** — thuần gh/jq/bash, drop-in cho repo ta.

### 4.2. Tool registry: register-vs-scan + degrade ladder (US-027 — mới)

Tách **ý định** (đăng ký) khỏi **thực tế** (probe theo kind). Ba trạng thái then chốt: *chưa-đăng-ký = không phải drift* (skip sạch); *đăng-ký-nhưng-mất = failed validity gate* (cờ Weak proof); *có mặt = Full*. `tool check` luôn exit 0 — "một extension mất là một sự thật cần báo, không phải một lỗi CLI".

- **Map thẳng vào bệnh của ta:** bảng hook trong CLAUDE.md *chính là* một registry — nhưng không gì scan nó (lint-doc-truth mới check path-tồn-tại, chưa check "skill X reference agent Y không tồn tại" — đúng lỗi `superpowers:code-reviewer` phantom mà deep review tìm ra).
- **Caveat họ tự khai:** `present` = "có trên đĩa", không phải "chạy được" (TOOL_REGISTRY.md:88-92).

### 4.3. Verify command lưu-và-chạy-lại + audit never-run/stale

`story verify` chạy `verify_command` đã lưu, ghi pass/fail + timestamp; `verify-all` batch; `audit` đếm command chưa-từng-chạy là drift. Pre-close gate (US-017) **advisory, không block**.

- **Cái gì chặn `true`? — Không gì cả.** Exit-0 của một lệnh do agent tự viết là toàn bộ "proof". Mitigation của họ là cấu trúc (human thấy `true` lúc review PR), không phải cơ chế. → Giải được "evidence không bao giờ được chạy lại" (bệnh STATE.md của ta), **không** giải được "evidence trivially satisfiable" (bệnh ci-strict-gate của ta — cả hai repo cùng lỗ này).
- **Ta phải tự thêm phần họ thiếu:** denylist (`true`, `:`, `echo`, `exit 0`) + bắt buộc command reference một path trong diff.

### 4.4. Entropy audit — một con số, có trend

6 check SQL cố định, mỗi cái là một "promise-vs-evidence mismatch": orphaned story ×10, verify chưa chạy ×5, backlog implemented thiếu `actual_outcome` ×2, stale >30d ×3, broken tool ×8 → weighted sum cap 100.

- Signal chọn tốt; trọng số tùy tiện chưa validate; chỉ thấy cái trong DB — việc không khai báo là vô hình (blind spot họ tự nhận). Nó dời bài toán từ "có ai append ledger không" sang "có ai record story không".
- **Ta port:** mỗi check ≈ 10 dòng Python trên `specs/*/SUMMARY.md` + front-matter docs/solutions; bỏ cap-100 màu mè; **quan trọng nhất là emit JSONL để có trend** — thứ harness-audit.sh hiện tại thiếu.

### 4.5. Intervention typed + propose rule-based + vòng khép tự police

`intervention` table (type: correction/override/escalation/approval; source: human/reviewer/ci/agent). `propose` **cố tình rule-based, không LLM** (decision 0007 — vì auditability): group friction/intervention text normalize, count≥2 → proposal kèm evidence/predicted_impact/validation_plan; confidence = count≥3→high. Đóng backlog item **bắt buộc** `actual_outcome`; item đóng thiếu outcome bị **entropy audit đếm là drift** — vòng lặp tự police chính nó.

- **Đây là mảnh ghép ta thiếu nhất cho luận điểm Lane×Confidence:** "autonomy có thực sự earned không" cần đúng data human-correction này. Grouping của họ naive (token-normalize, tự nhận trong 0007) — chấp nhận được.

### 4.6. Maturity claims bị cap bởi evidence kiểm tra được

HARNESS_MATURITY.md ladder H0–H5, mỗi level có criteria file-inspectable; repo họ tự chấm H3/H5 "Partial" và **nêu tên evidence còn thiếu**. Kỷ luật này ta đã có một phần (Evidence Tiers table) — đáng giữ và mở rộng.

### 4.7. Nguyên tắc quản trị (decision 0007, PHASE4/5)

- **Deterministic cho tầng evolution** (không để LLM tự đề xuất sửa policy của chính nó);
- **Advisory trước, blocking sau** — gate warn trước, "earn strictness";
- **Harness không bao giờ tự rewrite policy của mình** without human review;
- Mọi claim phase phải có story + Evidence section.

### Điểm yếu của họ (để không thần thánh hóa)

- **Gates check format, không check substance** ở mọi nơi: trace tier đếm field-presence (`["x"]` pass list-check, `harness_friction: "none"` pass Standard); placeholder-filled trace vẫn score Detailed. Lane của họ cũng **self-declared** tại `intake --lane` — cùng lỗi self-reference với ta.
- **Path nhúng cứng trong Rust biên dịch** (context rules, retrieval triggers) — doc rename là scorer rot âm thầm, không test nào buộc CONTEXT_RULES.md ↔ code. Context scoring là cơ chế yếu nhất: `files_read` do agent tự khai.
- **Dogfood của chính họ vô hình:** `harness.db` gitignored, binary absent — không record bền nào inspect được in-repo; Evidence sections ("26 passed") là prose không pin — đúng tier documented-only mà ta phạt.

---

## 5. So khớp: bệnh của ta (deep review 07-03) ↔ thuốc của họ

| Bệnh của ta (verified) | Cơ chế của họ | Mức khớp |
|---|---|---|
| Trust ledger chết 3 tuần; CHANGELOG/VERSION đóng băng sau 1 chu kỳ | Post-merge maintenance CI (§4.1) | **Trực tiếp — thuốc đúng bệnh** |
| Hard-gate list lệch 4 nguồn; skill reference agent phantom; reviewer.md claim sai | Registry register-vs-scan + degrade ladder (§4.2) | **Trực tiếp** (mở rộng lint-doc-truth hiện có) |
| STATE.md/harness-audit không lịch sử, không trend, "harness có đang mục không?" không trả lời được | Entropy score + JSONL trend (§4.4) | **Trực tiếp** |
| ci-strict-gate pass bằng `true`; rollback template chưa sửa vẫn pass | Verify lưu-và-chạy-lại (§4.3) — **nhưng họ cũng dính lỗi `true`** | **Một phần** — ta phải tự thêm substance denylist |
| Lane self-declared, hook chỉ enforce consistency; không data nào đo "autonomy earned chưa" | Intervention typed + propose + predicted-vs-actual loop (§4.5) | **Trực tiếp cho phần data**; self-declared lane thì họ cũng chưa giải |
| Backlog 1 entry mồ côi 19 ngày | Propose gate count≥2 + đóng-phải-có-outcome bị audit police (§4.5) | **Trực tiếp** |
| Commit-gate bypass, session-knowledge chết, break-glass unreachable | *(không có tương đương — bug bash của riêng ta)* | Phải tự fix, xem deep review §Critical |

---

## 6. Đề xuất v2 — "Event-Sourced Trust Layer"

**Nguyên tắc đổi mới duy nhất:** *mọi record mà harness mandate phải được ghi bởi một event máy (CI trigger, hook trigger), hoặc bị một checker máy chặn khi vắng. Không record nào được phép phụ thuộc vào việc agent/người "nhớ append".* Giữ nguyên chất nền markdown + bash + python (tái khẳng định verdict 06-09: không Rust, không SQLite). Ceremony giữ nguyên; chỉ đổi **ai là người ghi sổ**.

### Phase 0 — Vá nền móng (tiền đề, từ deep review — không thuộc cảm hứng repo họ)
Fix 2 critical + nhóm high: command matching 3 commit hook (tokenize, bắt `git … commit` mọi segment); session-knowledge root resolution; hard-gate list về 1 nguồn data (xem Phase 2); review chain cho executing-plans; tiền đề sai trong finishing-a-development-branch. *Không có Phase 0 thì mọi tầng đo lường phía trên đo một hệ thống đang thủng.*

### Phase 1 — Bookkeeping theo event (port §4.1)
- `.github/workflows/post-merge-maintenance.yml` bản của ta: trên PR merged → `gh pr view` JSON → **(a)** append row vào `trust-metrics.md` (Date|PR|Slug|Lane — lane đọc từ SUMMARY trong diff, `?` nếu vắng), **(b)** prepend CHANGELOG entry, **(c)** bump VERSION (minor khi diff đụng `hooks/`+`settings.json`, patch còn lại), **(d)** commit + push idempotent.
- Ledger từ nay **không ai append tay nữa** — xóa mandate "Append to the ledger" trong feature-intake Guardrails, thay bằng "CI appends; kiểm tra row sau merge".
- Fix `state-breadcrumb.sh` metric hỏng hoặc xóa `user_turns`; rotation cho Session End Log.

### Phase 2 — Một registry, một nguồn gate (port §4.2 + fix lệch 4 nguồn)
- `harness-manifest.yaml` (root, tracked) — nguồn sự thật duy nhất, 4 section: `skills` (name, path, handoffs, external-deps như agent types), `hooks` (path, event, matcher, wired), `agents`, `hard_gates` (danh sách 8 gate + regex signal).
- `scripts/check-manifest.py` (thay/mở rộng lint-doc-truth): probe theo kind — skill path tồn tại, hook registered đúng trong settings.json 2 chiều, agent type được skill reference phải có trong manifest, external dep vắng → **Degraded** (báo, không fail) theo degrade ladder của họ. Chạy CI.
- `feature-intake` Step 3, `auto-correct-scope.md` Rule 4, `risk-corroboration.sh` **cùng đọc `hard_gates` từ manifest** (hook parse yaml bằng python one-liner hoặc sinh file .sh từ manifest lúc CI) — hết lệch 4 nguồn về mặt cấu trúc.

### Phase 3 — Verify có substance + entropy có trend (port §4.3 + §4.4, vá lỗ họ cũng dính)
- `verify_summary.py`: thêm **substance denylist** (`true`, `:`, `echo …`, `exit 0`, command không reference path nào trong `git diff --name-only` của PR → FAIL với message rõ); fix em-dash duplicate + 3 semantics trap đã tìm ra; thêm `test_verify_summary.py` vào run-tests (1 dòng); sandbox verify command trên CI (timeout + không network nếu được).
- `check_lane_evidence.py`: rollback phải khác template byte-wise; lane match exact.
- `harness-audit.sh` → nâng thành entropy có 6 check + **emit `docs/harness-experimental/audit-log.jsonl` mỗi lần CI chạy** → có trend line thật. Check gồm: plan active >30d không status-log mới · SUMMARY thiếu Verify · verify never-re-run · backlog item open >14d · manifest Degraded rows · solutions confirmed_at >30d.

### Phase 4 — Vòng cải tiến khép kín (port §4.5, chỉ sau khi Phase 1–3 có data)
- `specs/<slug>/CORRECTIONS.md` append-only (type: correction|override|rework|approval, source, commit) — hook/skill ghi khi human sửa diff autonomous.
- `scripts/propose.py` rule-based (theo decision 0007 của họ: KHÔNG để LLM tự đề xuất sửa policy): group friction + corrections, count≥2 → backlog entry kèm `predicted_impact`; **đóng entry bắt buộc `actual_outcome`**, entry đóng thiếu outcome bị entropy audit đếm — vòng tự police.
- `/compound` giữ vai trò cluster ngữ nghĩa near-duplicate (hybrid như research cũ đề xuất).

### Phase 5 — (điều kiện) Portability
Giữ deferral hiện tại: marked-block + HARNESS.md payload chỉ làm "when a second consumer arrives". Không đổi.

### Không làm (tái khẳng định)
Rust/SQLite substrate · context-read scorer (self-reported files_read — họ cũng yếu) · schema versioning/importer · agnostic AGENTS.md cho Codex/Cursor (zero consumer) · maturity matrix 6×11.

### Thước đo thành công của v2
1. **Zero record chờ người append** — grep toàn repo không còn mandate "append X" nào mà không có event/checker đi kèm.
2. PR merge bất kỳ → trust ledger + CHANGELOG có entry trong ≤1 phút, không ai gõ.
3. `harness-audit` cho một con số + trend qua ≥3 tuần dữ liệu JSONL.
4. `ci-strict-gate` **không thể** pass bằng `| x | true | 0 | |` (có test chứng minh).
5. Hard-gate list tồn tại đúng **một** nơi máy đọc được; 3 consumer đều trỏ về nó (có test).

---

## 7. Bước đi kế tiếp đề xuất (thứ tự)

1. **Phase 0 critical fixes** (commit-hook matching + session-knowledge) — lane **high-risk** (đụng hooks/ + settings.json), full chain.
2. **Phase 1 post-merge workflow** — độc lập, giá trị/effort cao nhất trong nhóm mới; một file workflow + sửa Guardrails.
3. **Phase 3 substance denylist + test_verify_summary vào CI** — vá lỗ chung của cả hai repo; nhỏ, đo được ngay.
4. **Phase 2 manifest** — lớn hơn, đáng một PLAN.md riêng.
5. **Phase 4** — chỉ start khi ledger event-driven đã có ≥2 tuần data thật.
