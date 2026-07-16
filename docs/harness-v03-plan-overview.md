# Harness v0.3 — Plan Overview: "Event-Sourced Trust"

- **Ngày:** 2026-07-03
- **Verdict đã chốt:** IMPROVE in-place, không rewrite. Đặt tên chu kỳ là **v0.3** (minor bump theo CHANGELOG rule sẵn có — đụng hooks/ + settings.json).
- **Nguồn (3 research):**
  1. `docs/research/2026-07-03-deep-review-harness-trustworthiness.md` — 2 critical, 9 high, 12 medium (ID: DR-*)
  2. `docs/research/2026-07-03-repository-harness-recheck-v2-proposal.md` — adoption audit + 5 phase v2 (ID: RC-*)
  3. `docs/research-repository-harness-ideas.md` (2026-06-09) — 16 IDEA gốc, verdict adapt/skip còn hiệu lực
- **Tiền lệ format:** `docs/harness-gap-closure-plan.md`

---

## 1. Mục tiêu & nguyên tắc

**Một câu:** mọi record mà harness mandate phải được ghi bởi **event máy** (CI/hook) hoặc bị **checker máy** chặn khi vắng — không record nào được phụ thuộc "nhớ append"; đồng thời vá các lỗ enforcement đã verify trong deep review.

Nguyên tắc thực thi (từ cả 3 research + decision 0007 của repository-harness):

1. **Sửa nền trước, đo lường sau** — không xây tầng đo trên hệ thống đang thủng (Phase 0 trước tất cả).
2. **Advisory trước, blocking sau** — gate mới ship ở chế độ WARN, flip strict khi đã chạy sạch ≥1 tuần.
3. **Deterministic cho tầng evolution** — script/CI đề xuất cải tiến, không để LLM tự sửa policy của chính nó.
4. **Chuỗi PR nhỏ tuần tự, không burst** — adoption audit chứng minh burst 06-14 chết ngay sau đó; mỗi wave một PR reviewable.
5. **Mỗi thay đổi hooks/ hoặc settings.json = Rule-4 high-blast** → lane **high-risk**, full chain, có Rollback.

---

## 2. Lộ trình — 6 wave / ~9 PR

| Wave | PR (slug đề xuất) | Lane | Nội dung | Findings đóng | Phụ thuộc |
|---|---|---|---|---|---|
| **0a** | `fix/hook-command-matching` | high-risk | Tokenize command matching trong `commit-quality-gate.sh`, `risk-corroboration.sh`, `branch-guard.sh`, `check-untracked-py.sh` (bắt `git … commit` sau `&&`/`;`/`\|`, `-C`/`-c`/`command`); bỏ field `"if"`/`statusMessage` giả trong settings.json; test bypass cases vào `tests/` | DR-1 (critical) | — |
| **0b** | `fix/session-knowledge-root` | high-risk | Resolve repo root bằng `git rev-parse --show-toplevel` như hook anh em; bỏ `exec 2>/dev/null`; test chạy từ `.claude/hooks/` | DR-2 (critical) | — |
| **0c** | `fix/skill-doc-truth` | normal | Sửa tiền đề sai trong `finishing-a-development-branch` (specs/ tracked, test command, remote name); thêm review-chain hoặc bỏ claim parity ở `executing-plans`; fallback cho quality-reviewer phantom; thống nhất base branch create-pr; dọn câu tiếng Việt sót; sửa xung đột brainstorming ↔ using-git-worktrees | DR-3, DR-8, DR-11, nhóm Low | — |
| **1** | `feat/post-merge-maintenance` | high-risk (đụng CI + quy trình ghi sổ) | GitHub Action `pull_request_target: closed` + `merged==true`: tự append row `trust-metrics.md`, prepend CHANGELOG, bump VERSION (minor khi diff đụng hooks/+settings.json), commit+tag idempotent. Sửa feature-intake Guardrails: bỏ mandate append tay. Fix/xóa metric `user_turns` + rotation Session End Log trong `state-breadcrumb.sh` | DR-12, DR-13, RC §4.1, IDEA-01/15 (hồi sinh) | 0a (gate phải kín trước khi tin record) |
| **2** | `fix/verify-substance` | normal | `verify_summary.py`: substance denylist (`true`, `:`, `echo`, `exit 0`, command không reference path trong diff → FAIL); fix em-dash duplicate + 3 semantics trap; **thêm `test_verify_summary.py` vào `run-tests.sh` (1 dòng)**; `check_lane_evidence.py`: rollback phải khác template, lane match exact; sandbox/timeout verify trên CI | DR-6, DR-7, DR-18, DR-19, RC §4.3 | — (song song Wave 1 được) |
| **3** | `feat/harness-manifest` | high-risk | `harness-manifest.yaml` (tracked): sections `skills` / `hooks` / `agents` / `hard_gates`. `scripts/check-manifest.py` probe theo kind + degrade ladder (Inactive/Degraded/Full), chạy CI, thay thế dần `lint-doc-truth.sh`. 3 consumer của hard-gate (`feature-intake` Step 3, `auto-correct-scope.md` Rule 4, `risk-corroboration.sh`) cùng đọc manifest → hết lệch 4 nguồn. Giải luôn xung đột dependency-bump (Rule 3 vs hook) bằng cách encode exception vào manifest | DR-4, DR-5 (một phần), RC §4.2, IDEA-09/10 (hoàn thiện) | 0c |
| **4** | `feat/entropy-trend` | normal | Nâng `harness-audit.sh` → 6 check promise-vs-evidence (plan active >30d im lặng · SUMMARY thiếu Verify · verify never-re-run · backlog open >14d · manifest Degraded · solutions stale) + **emit `audit-log.jsonl` mỗi CI run** → trend line thật. Wire vào harness-status | DR-13 (phần đo), RC §4.4, IDEA-04 (hoàn thiện) | 1, 3 |
| **5** | `feat/corrections-propose` | normal | `templates/CORRECTIONS.template.md` + `specs/<slug>/CORRECTIONS.md` (typed: correction/override/rework/approval); `scripts/propose.py` rule-based: group friction+corrections, count≥2 → backlog entry kèm `predicted_impact`; đóng entry bắt buộc `actual_outcome`, thiếu thì entropy audit đếm là drift (vòng tự police) | RC §4.5, IDEA-05/07/08 (hoàn thiện) | 4, và ledger có ≥2 tuần data thật |
| **6** | `chore/hygiene` | tiny | Xóa `settings copy.json`, `.claude copy/`, 3 dir `.harness-backup-*`; commit hoặc xóa REQ.md / PR_TEMPLATE.md; commit `docs/research/` | DR-21 | bất kỳ lúc nào |

> Wave 0a/0b/0c và Wave 2, Wave 6 độc lập nhau — chạy song song được. Wave 1 chờ 0a. Wave 3 chờ 0c. Wave 4 chờ 1+3. Wave 5 chờ 4 + data.

---

## 3. Phạm vi từng wave (scope / non-goals / risk chính)

### Wave 0 — Vá nền móng (DR critical + high)
- **Scope:** đúng các fix liệt kê, kèm regression test cho từng bypass form đã chứng minh.
- **Non-goals:** không refactor hook style, không thêm hook mới, không đụng break-glass design (dời sang backlog — cần thiết kế riêng file-based flag có TTL).
- **Risk:** sửa matching quá chặt → false-block lệnh git hợp lệ. Mitigation: test suite bypass + happy-path, ship qua `bash scripts/run-tests.sh` + CI 2 nền tảng.
- **Rollback:** `git revert` per-PR; hooks là script thuần, không state.

### Wave 1 — Bookkeeping theo event
- **Scope:** một workflow file + sửa Guardrails prose + fix state-breadcrumb.
- **Non-goals:** không tự release/publish gì ra ngoài repo; không đụng install/deploy.
- **Risk:** `pull_request_target` có quyền push — giới hạn step chỉ đọc metadata PR (`gh pr view`), không checkout code PR (học đúng failure mode đã biết của pattern này).
- **Quyết định (2026-07-03, đã chốt):** bot **mở PR bookkeeping** (`chore/bookkeeping-pr-<N>`) thay vì push thẳng main — không cần PAT/bypass branch protection; dùng `GITHUB_TOKEN` mặc định + auto-merge nếu bật. Trade-off chấp nhận: record trễ một nhịp merge thay vì tức thời.

### Wave 2 — Verify có substance
- **Scope:** siết checker + đưa test vào CI. Không đổi format SUMMARY.
- **Risk:** denylist chặn nhầm lệnh hợp lệ ngắn → cho phép allowlist per-repo trong manifest (Wave 3) sau.

### Wave 3 — Manifest một nguồn
- **Scope:** manifest + checker + trỏ 3 consumer về nó.
- **Non-goals:** KHÔNG registry sản phẩm kiểu ToolEntry/semver/arg-schema (verdict SKIP cũ giữ nguyên); không port context-scoring.
- **Risk:** hook bash parse YAML — giải bằng sinh `hard-gates.generated.sh` từ manifest lúc CI/pre-commit, hook source file sinh (deterministic, diffable).

### Wave 4 — Entropy có trend
- **Scope:** 6 check + JSONL + hiển thị trend. Trọng số để trong data (không hardcode), báo cả raw lẫn banded.
- **Non-goals:** không blocking, không cap-100 màu mè.
- **Bug phát hiện sau merge (2026-07-04):** `pull_request_target` luôn load workflow definition từ default branch thật của repo (`main`), bất kể `base` của PR — `main` đứng yên từ PR #36 (kém 107 commit so với `v2`), nên dòng `git add` mới (Task 2.2) chưa từng có hiệu lực: `bookkeeping.sh` tính + ghi dòng JSONL, nhưng step `git add` trong YAML cũ trên `main` không stage nó → PR bookkeeping #43 rỗng `audit-log.jsonl`. Fix: PR #44 (`ci/sync-post-merge-git-add`, merge thẳng vào `main`, cùng pattern PR #36) — sync 1 dòng, không đổi gì khác.
- **Finding phụ khi merge PR #44 (2026-07-04):** merge PR #44 vào `main` tự kích hoạt `post-merge-maintenance` cho chính PR #44 (workflow trigger có `branches: [v2, main]`) — chạy FAIL ngay ở bước đầu: `scripts/bookkeeping.sh: No such file or directory`, vì `main` chưa từng nhận `scripts/` của Wave 1+ (chỉ có file cũ tiền-v0.3 như `check_plan_format.py`). Đây là lỗi tiềm ẩn có sẵn, không phải do PR #44 gây ra — PR #44 là PR ĐẦU TIÊN merge vào `main` kể từ khi PR #36 đăng ký workflow này lên `main`, nên đường này chưa từng được exercise trước đó. Không có ghi dữ liệu sai/hỏng (crash ngay ở lệnh đầu, trước mọi thao tác git). **Fix ✅ PR #45** (merge thẳng `main`, cùng pattern #36/#44) — bỏ `main` khỏi `branches:` (`[v2, main]` → `[v2]`); file workflow vẫn nằm trên `main` (giữ registration, theo đúng lý do gốc của PR #36 — chỉ cần *tồn tại*, không cần nằm trong `branches:`), chỉ merge vào `v2` mới còn kích hoạt `bookkeeping.sh`.

### Wave 5 — Vòng cải tiến khép kín
- **Gate vào wave:** chỉ start khi (a) ledger event-driven có ≥2 tuần row thật, (b) backlog hiện tại đã được triage (đang có 1 entry mồ côi 19 ngày — nếu không ai triage thì skip wave này, đúng cảnh báo "nghĩa địa" của research 06-09).
- **Quyết định (2026-07-03):** owner cam kết triage backlog — Wave 5 giữ trong lộ trình; điều kiện (a)/(b) vẫn phải thỏa trước khi start.
- **Trạng thái gate (2026-07-04):** (a) CHƯA thỏa — ledger event-sourced mới chạy thật từ 2026-07-03, cần đợi đến ~2026-07-17. (b) ✅ đã triage — entry `pretooluse-hook-denies-combined-git-add-commit` đóng theo route docs-only (thêm rule vào `CLAUDE.md` Gotchas thay vì sửa `hooks/check-untracked-py.sh`, tránh full high-risk chain cho một friction thuần workflow-ordering); xem `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md`. Vẫn CHƯA start Wave 5 — chờ (a).

---

## 4. Thước đo thành công v0.3 (định nghĩa "xong")

1. **Zero record chờ người append** — không còn mandate "append X" nào trong docs mà thiếu event/checker đi kèm (grep-able).
2. Merge PR bất kỳ → trust-metrics + CHANGELOG có entry tự động trong ≤1 phút.
3. `ci-strict-gate` **không thể** pass bằng `| x | true | 0 | |` — có test pin chứng minh.
4. Hard-gate list tồn tại đúng **một** nơi máy đọc; 3 consumer trỏ về nó — có test pin.
5. `harness-audit` cho một con số + trend ≥3 tuần data JSONL. **CHƯA xong (2026-07-04):** cơ chế đã ship (Wave 4, PR #42) nhưng `audit-log.jsonl` mới nhận được dòng thật đầu tiên sau khi PR #44 (main/v2 sync fix) merge — cần ≥3 tuần dữ liệu tích lũy từ đó mới tính là "trend thật".
6. Các bypass form trong DR-1 đều bị chặn — có test pin từng form (`cd x && git commit`, `git -C`, …).
7. Mọi PR của v0.3 tự đi qua chính workflow nó xây (dogfood: lane khai đúng, SUMMARY có Verify thật, high-risk có Rollback).

## 5. Ngoài phạm vi v0.3 (tái khẳng định verdict cũ)

- Rust/SQLite substrate · context-read scorer · schema versioning/importer · AGENTS.md agnostic (chờ consumer thứ hai) · maturity matrix 6×11 · break-glass redesign (backlog, cần design riêng) · mở rộng branch-isolation sang Bash-write (backlog — cần cân nhắc false-positive trước).

## 6. Bước tiếp theo

1. Anh duyệt overview này (đặc biệt: thứ tự wave, điểm quyết định PAT ở Wave 1, gate vào Wave 5).
2. Chạy `/feature-intake` cho Wave 0a → SUMMARY (lane high-risk) → `/writing-plans` → PLAN.md chi tiết theo `rules/plan-format.md` → worktree → thực thi.
3. Mỗi wave lặp lại chu trình; overview này cập nhật cột trạng thái sau mỗi merge.

| Wave | Trạng thái |
|---|---|
| 0a | ✅ merged (PR #31) — lib matcher + 4 hook rewired + bỏ `if`; 41 test; reviews F1/F2 fixed |
| 0b | ✅ merged (PR #32) — session-knowledge resolve root bằng git rev-parse (DR-2); deployed-location regression test |
| 0c | ✅ merged (PR #33) — 8 file doc-truth; intent review pass (phantom /code-review self-fixed) |
| 1 | ✅ merged (PR #34) + **registration fix PR #36** (GitHub chỉ đăng ký pull_request_target từ default branch `main`) + backfill #31–#35 (PR #37) + repo setting "Actions may create PRs" bật. **Vòng full-auto verified 2026-07-04**: merge #40 → workflow tự mở #41 → merge → loop-guard skip ✓. VERSION tự bump tới 0.7.2 |
| 2 (verify-substance) | ✅ merged (PR #38 + auto-bookkeeping #39) — trivial denylist (DR-6, pinned at gate), negative proof (19a), honest stamp (19b), row-order rewrite (19c + review MEDIUM fix), placeholder sets cross-pinned (DR-18), lane/rollback exactness, test_verify_summary vào CI (DR-7) |
| 3 (manifest) | ✅ merged (PR #35) — harness-manifest.json canonical (8+3 gates + inventory); check_manifest.py enforce hook↔manifest + presence-scan trong CI; DR-4 fixed |
| 4 (entropy trend) | ✅ merged (PR #42) — `harness-audit.sh` 3→6 check (verify-never-rerun, backlog-stale, manifest-degraded) + `--root`/`--json` + 16-case test suite (đầu tiên cho script này); `bookkeeping.sh` ghi 1 dòng JSONL/PR merge vào `audit-log.jsonl` (tái dùng post-merge flow, không workflow mới); wired vào `harness-status.sh`. Correctness-review 2 vòng bắt + fix 2 bug thật (`set -u` unbound-array; `KeyError` chưa bắt trong except); 1 advisory (dirname/`--root` edge case) để lại có ghi chú. Intent-review bắt 1 drift ("mỗi CI run" → "mỗi merge") — đã hỏi và được xác nhận đúng. `/compound` ghi 2 doc mới + promote critical-patterns. **Follow-up ✅ merged (PR #44, thẳng vào `main`)** — sync dòng `git add` bị "mất tích" do `main` đứng yên 107 commit (xem §3 Wave 4); phát hiện thêm 1 lỗi tiềm ẩn (chưa fix, xem §3 Wave 4) khi merge PR #44 tự kích hoạt bookkeeping cho chính nó và crash vì `main` thiếu `scripts/bookkeeping.sh`. `audit-log.jsonl` vẫn CHƯA có dòng thật nào — chờ lần merge kế tiếp vào `v2` |
| 5 | ⬜ (gated: ≥2 tuần data + backlog được triage) |
| 6 | ✅ merged (PR #40 + auto #41) — 6 plan flip shipped (hết nhiễu blast-radius), research corpus committed, local junk (settings copy.json, .claude copy/, backups) đã xóa. REQ.md / PR_TEMPLATE.md đã commit (`1b95fc8`, ngoài luồng PR — chore trực tiếp trên `v2`) |
