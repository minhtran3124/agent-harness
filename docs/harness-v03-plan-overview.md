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

### Wave 5 — Vòng cải tiến khép kín
- **Gate vào wave:** chỉ start khi (a) ledger event-driven có ≥2 tuần row thật, (b) backlog hiện tại đã được triage (đang có 1 entry mồ côi 19 ngày — nếu không ai triage thì skip wave này, đúng cảnh báo "nghĩa địa" của research 06-09).
- **Quyết định (2026-07-03):** owner cam kết triage backlog — Wave 5 giữ trong lộ trình; điều kiện (a)/(b) vẫn phải thỏa trước khi start.

---

## 4. Thước đo thành công v0.3 (định nghĩa "xong")

1. **Zero record chờ người append** — không còn mandate "append X" nào trong docs mà thiếu event/checker đi kèm (grep-able).
2. Merge PR bất kỳ → trust-metrics + CHANGELOG có entry tự động trong ≤1 phút.
3. `ci-strict-gate` **không thể** pass bằng `| x | true | 0 | |` — có test pin chứng minh.
4. Hard-gate list tồn tại đúng **một** nơi máy đọc; 3 consumer trỏ về nó — có test pin.
5. `harness-audit` cho một con số + trend ≥3 tuần data JSONL.
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
| 0a | ✅ **merged** vào v2 (PR #31) — lib matcher + 4 hook rewired + bỏ `if`; 41 test; correctness+intent review (F1/F2 fixed) |
| 0b | ✅ PR #32 mở (CI xanh) — session-knowledge resolve root bằng git rev-parse (DR-2); regression test tại vị trí .claude/hooks/; correctness review SOUND |
| 0c | ✅ PR #33 mở (CI xanh) — 8 file doc-truth (specs/ tracked, test cmd, review chain, reviewer fallback, base branch, Việt→Anh, brainstorming↔worktree); intent review pass (phantom /code-review self-fixed) |
| 1 | ✅ PR #34 mở (CI xanh) — post-merge-maintenance.yml (open-PR) + bookkeeping.sh (11 tests) tự ghi ledger/CHANGELOG/VERSION; feature-intake bỏ mandate append tay; correctness (5 fix) + intent review pass. Live-test là merge KẾ TIẾP sau khi #34 vào v2 |
| 2 (verify-substance) | ✅ PR #38 mở (CI xanh) — trivial denylist (DR-6, pinned at gate), negative proof (DR-19a), honest stamp (19b), row-order rewrite (19c + review MEDIUM fix), placeholder sets aligned + cross-pinned (DR-18), lane/rollback exactness, test_verify_summary vào CI (DR-7). Merge #38 = live-test thật của Phase 1 bookkeeping |
| 2 | ✅ PR #35 mở (CI xanh) — harness-manifest.json nguồn canonical (8 detectable + 3 judgment gates + inventory); check_manifest.py (7 tests) enforce hook↔manifest + presence-scan trong CI; DR-4 fixed (feature-intake +public-contract); correctness SOUND (2 fix) + intent pass. Merge #35 = live-test đầu của Phase 1 bookkeeping |
| 3 | ⬜ |
| 4 | ⬜ |
| 5 | ⬜ (gated) |
| 6 | ⬜ |
