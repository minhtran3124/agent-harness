# Deep Review — Harness Trustworthiness Audit

- **Date:** 2026-07-03
- **Scope:** hooks/ + settings.json · scripts/ + CI · skills/ + agents/ · rules/ + templates/ + specs/ + docs governance
- **Method:** 4 review agent song song, mỗi phát hiện được verify bằng cách đọc code hoặc chạy thực tế (không suy đoán). Các bypass ở mục Critical đã được chứng minh live.
- **Status:** findings only — chưa fix gì.

---

## Đánh giá tổng thể

Nền tảng của repo tốt hơn mức trung bình rõ rệt: merge logic của deploy/install có backup và test thật, CI chạy đúng những gì docs nói, benchmark review-chain có kết quả thật, và bảng Evidence Tiers trung thực. **Nhưng lớp "enforcement" — thứ tạo ra niềm tin — đang thủng ở đúng những chỗ quan trọng nhất**: mọi commit gate bypass được bằng một tiền tố lệnh, hook knowledge-base đã chết âm thầm ở vị trí deploy, và mọi cơ chế chỉ dựa vào prose (trust ledger, STATE.md, agent-memory decay) đều đã mục.

Repo tự chứng minh luận điểm của chính nó: *cái gì không được cơ giới hoá thì sẽ decay*.

---

## 🔴 Critical — cần fix ngay

### 1. Mọi commit gate bypass được bằng tiền tố lệnh

- **Vị trí:** `hooks/commit-quality-gate.sh:11`, `hooks/risk-corroboration.sh:26`, `hooks/branch-guard.sh:14`
- Cả 3 gate filter bằng `grep -qE '^git commit'` (neo đầu dòng). **Đã chứng minh live:** `cd /tmp && git commit -m x` và `git -C . commit` đi qua cả 3 gate với exit 0, không một dòng output.
- Các dạng bypass: `cd x && git commit` · `git -C dir commit` · `git -c k=v commit` · `command git commit` · `echo done; git commit`.
- Secrets scan, debug-artifact check, pytest gate, lane corroboration — tất cả chỉ cách một dấu `&&` là im lặng.
- **Kèm theo:** field `"if": "Bash(git *)"` trong settings.json **không tồn tại trong schema hooks của Claude Code** (schema chỉ có matcher/type/command/timeout) — nó bị silently ignore, nên cả 4 script chạy trên *mọi* Bash call và toàn bộ việc gating phụ thuộc vào chính cái self-filter bị hỏng nói trên. `statusMessage` cũng không phải field hợp lệ.
- `check-untracked-py.sh:9` dùng substring match nên sống sót qua `cd x &&` nhưng vẫn thua `git -C dir commit`.

### 2. `session-knowledge.sh` đã chết ở vị trí deploy

- **Vị trí:** `hooks/session-knowledge.sh:17-19`
- Hook resolve knowledge base bằng `$HOOK_DIR/../docs/solutions`, nhưng bản được đăng ký chạy từ `.claude/hooks/` → nó tìm `.claude/docs/solutions` (không tồn tại).
- **Đã chạy thử:** `bash .claude/hooks/session-knowledge.sh` emit rỗng; bản top-level emit đủ 5 entry INDEX.
- `exec 2>/dev/null` đảm bảo không ai phát hiện — mọi session khởi động **không có** knowledge base mà CLAUDE.md tuyên bố được load. Đây chính xác là lỗi `not_observed != absent` mà rules của repo cảnh báo.
- Mọi hook khác tránh lỗi này bằng `git -C "$SCRIPT_DIR" rev-parse --show-toplevel`; riêng hook này thì không.

---

## 🟠 High — làm sai lệch mô hình an toàn

### 3. `executing-plans` không có review gate nào

- README (`skills/README.md`) và CLAUDE.md nói executing-plans "same as subagent-driven-development" (two-stage review per task + correctness-review + intent-review).
- Thực tế `skills/executing-plans/SKILL.md`: Step 2 chạy task, Step 3 handoff thẳng đến finishing-a-development-branch. Không spec review, không quality review, không correctness, không intent.
- **Hệ quả:** plan nào chạy qua đường "parallel session" sẽ ship hoàn toàn không qua review trong khi harness tin là đã qua.

### 4. Hard-gate list lệch nhau giữa 4 nguồn

- `skills/feature-intake/SKILL.md` (Step 3, ~dòng 78–86): 6 gates — **thiếu** *public contract*, *removing existing functionality*, *session/transaction scope*.
- `.claude/rules/orchestration.md` (Escalation): 8 gates, có public contract.
- `rules/auto-correct-scope.md` Rule 4: thêm removing-functionality + session/transaction scope.
- `hooks/risk-corroboration.sh:80`: **block** cơ giới trên category `public-contract` (regex route-decorator).
- **Hệ quả:** intake phân lane `normal` hợp lệ cho một thay đổi route → commit hook chặn exit 2 → classifier và corroborator đánh nhau by design; đúng loại under-classification mà trust ledger sinh ra để bắt, nhưng do docs tự gây.
- **Cùng loại:** `risk-corroboration.sh:73` coi mọi thay đổi `package.json`/`pyproject.toml`/`requirements*.txt` là hard-gate `external-provider`, mâu thuẫn trực tiếp Rule 3 (cho phép auto-add dependency ở mọi lane) → mọi dependency bump lane normal đều bị block trừ khi re-classify high-risk.

### 5. Lane corroboration self-referential và fail-open

- **Vị trí:** `hooks/risk-corroboration.sh:103,109,112`
- Parse đòi dòng bắt đầu đúng `Lane:`; chính repo này có `specs/correctness-review-upgrade/SUMMARY.md:3` dùng `**Lane:** normal` → grep miss → không tìm thấy lane → warn-and-allow (fail-open) kể cả khi diff dính hard-gate.
- Fallback `ls -t specs/*/SUMMARY.md | head -1` chọn SUMMARY *được sửa gần nhất* → lane được corroborate có thể thuộc task khác.
- Block message chỉ cho agent cách tự unblock (tự ghi `Lane: high-risk`; không có human trong loop) → hook enforce **tính nhất quán**, không phải **an toàn**.

### 6. CI strict gate chứng minh "một lệnh đã chạy", không phải "bằng chứng"

- **Vị trí:** `scripts/ci-strict-gate.sh:38-62`
- PR đụng hard-gate path (`hooks/`, `settings.json`, `templates/`) pass được bằng cách ship một SUMMARY mới có `Lane: high-risk` + row `| x | \`true\` | 0 | |` — `verify_summary --check` chạy `true`, exit 0, gate OK.
- Rollback bằng template chưa sửa (`- \`git revert <sha>\``) được `check_lane_evidence.py:110-127` chấp nhận (**đã verify empirically** — zero errors): yêu cầu duy nhất của lane high-risk thoả mãn được bằng cách *không sửa gì*.
- **Side-effect:** CI thực thi shell tuỳ ý lấy từ SUMMARY.md do PR author viết (`verify_summary.py:112`, `shell=True`).

### 7. `test_verify_summary.py` không bao giờ được chạy trong CI

- **Vị trí:** `scripts/run-tests.sh:33` — `PYTESTS` liệt kê thiếu file này.
- **Đã verify:** suite báo 102 passed; chạy tay file bị bỏ sót cho thêm 19 test pass. Parser mà CI strict gate phụ thuộc là đúng script duy nhất không có coverage trong CI. Fix một dòng.

### 8. `finishing-a-development-branch` viết trên tiền đề sai

- 4 chỗ (dòng ~77, 90, 115, 141) nói "`specs/` is gitignored" — mâu thuẫn CLAUDE.md, plan-format.md, writing-plans, visual-planner (specs được track, transition `shipped` phải commit). Agent theo skill này sẽ để `status: shipped` uncommitted → đúng loại cross-machine drift mà skill cảnh báo.
- Step 1b hardcode `cd apps/api && python -m pytest` (repo khác — suite thật là `scripts/run-tests.sh`); Step 3 hardcode remote tên `github` (vỡ ở mọi clone dùng `origin`).

### 9. `agents/reviewer.md` — guarantee "structurally read-only" không còn đúng

- Frontmatter khai `tools: Glob, Grep, Read, Bash`, nhưng registry thực tế của session hiện tại resolve reviewer với cả `Write, Edit` (gần như chắc chắn do `memory: project` inject).
- Claim cốt lõi "review independence is enforced by the harness, not by instruction" hiện sai — reviewer có thể sửa file.

### 10. Branch-isolation "hard block" chỉ phủ 2 kênh ghi

- **Vị trí:** `.claude/settings.json` matcher `Write|Edit`.
- Mọi Bash write (`echo >`, `tee`, `sed -i`, `python -c`, `patch`, heredoc) và `NotebookEdit` đi qua tự do; các Bash-hook chỉ soi lệnh git.
- **Break-glass unreachable giữa session:** `BRANCH_ISOLATION_REASON`/`PROTECTED_PATH_REASON` đọc từ env của process Claude Code lúc launch — model không set được env cho một tool call. Đường duy nhất là ghi vào `settings.json` `"env"` → thành bypass **vĩnh viễn** với một dòng log stale. `RISK_CORROBORATION_STRICT`/`BLAST_RADIUS_STRICT` default off = fail-open có chủ đích, cùng ràng buộc launch-time.

### 11. Per-task quality review dispatch một agent không tồn tại

- `skills/subagent-driven-development/code-quality-reviewer-prompt.md` dispatch `Task tool (superpowers:code-reviewer)` với template `requesting-code-review/code-reviewer.md` — cả agent type lẫn template đều không tồn tại trong môi trường này (README tier nó documented-only).
- Gate bắt buộc ("Never skip reviews") không có fallback → controller hoặc lỗi hoặc tự improvise pass review.

---

## 🟡 Medium — decay & lifecycle

| # | Phát hiện | Vị trí / bằng chứng |
|---|---|---|
| 12 | **Trust ledger chết 3 tuần** — không cơ chế nào append cơ giới; row cuối 2026-06-14 (còn ghi "done (uncommitted)"), PRs #26–#30 ship 06-15→06-19 với 0 row. File sinh ra để "calibrate autonomy" stale ngay khi hết chú ý | `docs/harness-experimental/trust-metrics.md` |
| 13 | **STATE.md chưa bao giờ hoạt động đúng** — Active Spec luôn `(none)` dù có 19 spec dirs; `user_turns` luôn 0 vì `grep -c '"role": "user"'` không khớp format transcript; Session End Log append vô hạn (32 entries/8 ngày, 232/258 dòng). Agent resume đọc STATE.md không học được gì hơn `git log -1` | `specs/STATE.md`, `hooks/state-breadcrumb.sh:98-105` |
| 14 | **deploy-harness chỉ thêm, không xoá** — hook bị xoá/rename upstream vẫn nằm lại `.claude/` consumer, và registration cũ được classify "foreign" nên **được giữ qua merge** → dead hook chạy mãi, mỗi lần re-sync | `scripts/deploy-harness.sh:65-107` |
| 15 | **`python -m pytest` hardcode** — macOS stock không có binary `python` → exit 127 → `exit 2` → block *mọi* commit ở repo adopt có staged `app/` files (fail-closed vì lý do sai; `auto-test-on-change.sh:78-80` làm đúng fallback python3) | `hooks/commit-quality-gate.sh:153` |
| 16 | **Command-injection primitive** — `eval "$CMD"` với `$FILE_PATH` nội suy; path dạng `test_"; rm -rf x; ".py` thực thi shell tuỳ ý. Dormant hôm nay, nhưng là hook docs khuyên người khác wire lên | `hooks/auto-test-on-change.sh:107` |
| 17 | **blast-radius fallback sai plan** — không có plan `status: active` thì lấy PLAN.md *mới nhất* bất kể status → plan đã shipped tiếp tục sinh cảnh báo scope-creep (và block giả dưới STRICT=1); dòng 34 unquoted `$(ls -t …)` vỡ với path có space | `hooks/blast-radius-check.sh:34,37` |
| 18 | **Placeholder rules phân kỳ giữa 2 checker** — `verify_summary.py:33` có em-dash lặp trong set (size 3, một cái gần như chắc là ASCII `-` gõ nhầm); row command `-` được parse là thật và **được execute**. Comment của ci-strict-gate claim placeholder rules "stay in one place" — không đúng | `scripts/verify_summary.py:33` vs `check_lane_evidence.py:34` |
| 19 | **verify_summary semantics traps** — (a) row khai exit ≠ 0 trung thực vẫn FAIL kể cả khi `claimed == actual` (negative-proof không biểu diễn được); (b) write mode stamp `Verified:` cả khi checks FAILED; (c) `_rewrite_table` map theo tên check → tên trùng thì collide | `scripts/verify_summary.py:292,307-309,145` |
| 20 | **render_plan self-check pass trên output truncate** — fence ``` không đóng làm `md_to_html` nuốt đến EOF, section biến mất khỏi render nhưng self-check (non-empty, no `{{X}}`, slug, wave count) vẫn pass | `skills/visual-planner/render_plan.py:262-277,1269-1290` |
| 21 | **Hygiene mâu thuẫn chính mình** — `settings copy.json` (bản stale pre-branch-isolation-guard của file blast-radius cao nhất), `.claude copy/` (~20 file drift, giấu qua `.git/info/exclude` — teammate không nhìn thấy), 3 dir `.harness-backup-*` (06-09→06-11), REQ.md / PR_TEMPLATE.md / docs/research untracked nhiều tuần | git status, repo root |
| 22 | **agent-memory decay protocol là prose chết** — 0 entry sau ~1 tháng; không script nào parse `confirmed:/review-by:` hay downgrade confidence; phụ thuộc hoàn toàn vào agent tự nhớ, và chưa agent nào nhớ | `agent-memory/` |
| 23 | **feature-intake trích dẫn path derived** — cite `.claude/rules/...` và `.claude/hooks/*` (cây gitignored, regenerate bởi deploy-harness) làm high-blast list, trong khi CLAUDE.md và corroboration hook key trên `hooks/`/`settings.json` top-level → agent sửa source tree nhận tham chiếu path mâu thuẫn | `skills/feature-intake/SKILL.md` |

## 🟢 Low

- `check_lane_evidence.py:73` — lane match substring: `Lane: not-normal` resolve thành `normal`; `Reason: —`/`Reason: TBD` pass là "filled".
- `render_plan.py:229` — `[x](javascript:...)` render thành `<a href="javascript:...">` sống trong PLAN.html (quote breakout bị chặn bởi esc, scheme thì không).
- `render_plan.py:1257-1259` — sequential `template.replace`: prose chứa literal `{{TASKS}}` bị substitute nguyên block tasks; `{{UPPER}}` khác trong prose gây self-check fail giả.
- `run-tests.sh:12` — unquoted glob dưới `set -u`: `tests/scripts/` rỗng → pattern literal vào `bash -n` → fail giả.
- `check-untracked-py.sh:10` — `grep -v '/\.claude/'` không bao giờ khớp path repo-relative (không có leading slash) → exclusion chết; `git ls-files` chạy ở cwd session, không phải repo đích của commit.
- `create-pr` default base `dev` vs `finishing-a-development-branch` default `main` (repo này main là `main`) → PR body diff sai.
- `using-git-worktrees` claim "Called by: brainstorming (Phase 4) — REQUIRED" nhưng brainstorming cấm ("The ONLY skills you invoke after brainstorming are xia2 → writing-plans", dòng 72) — một trong hai sai.
- Câu tiếng Việt copy-paste sót trong `subagent-driven-development/SKILL.md:192` và `correctness-review/SKILL.md:22` — rationale load-bearing không đọc được với agent/user không cấu hình tiếng Việt.
- `executing-plans` Step 3 mô tả finishing "present options, execute choice" — stale (skill đó giờ unconditionally push + PR).
- "Never merges" là prose-only — không hook nào gate `gh pr merge`/`git merge` (tương phản branch-isolation là hook-enforced).
- `subagent-driven-development` (433 dòng, 2 DOT digraph) và `compound` (469 dòng) đẩy rủi ro instruction-following; digraph là nơi duy nhất spec full control flow.
- docs/solutions: cả 5 entry có `confirmed_at` ≥ 30 ngày tính đến 2026-07-03 → theo rule của chính repo, toàn bộ "potentially stale".
- state-breadcrumb: concurrent SessionEnd có thể interleave multi-`printf` block; idempotency chỉ per session_id.

---

## ✅ Những gì thực sự tốt (verified)

- `install-harness.sh` / `deploy-harness.sh`: backup trước merge, không clobber JSON invalid, không stage ở target root, giữ foreign keys/hooks — có test thật (`tests/scripts/settings-merge.test.sh`).
- `bash scripts/run-tests.sh` → **ALL GREEN** (102 passed, 1 skipped, + hook/script suites). `.github/workflows/harness-ci.yml` thật sự chạy run-tests trên ubuntu + macos và ci-strict-gate trên PR với base-ref fetch đúng.
- Registration audit: 11 hooks "wired ✅" trong CLAUDE.md khớp `.claude/settings.json` chính xác (event type + matcher); 2 dormant đúng là chưa đăng ký.
- Templates khớp field-by-field với `check_lane_evidence.py` (Lane/Confidence/Reason, Verify table header, Rollback) — không drift.
- Benchmark `benchmarks/review-chain/`: 5 fixture thật, 2 result file thật (06-12 baseline; 06-14 reviewer-agent: 5/5 catch, 0 FP, ~354k tokens), claim-discipline mẫu mực.
- Evidence Tiers table trung thực: tự khai documented-only cho mọi external skill/MCP; claim manually-verified duy nhất (commit `a2a4349`) resolve ra commit thật.
- Python checker tests là test thật (tmp-file round-trip, exit codes, timeouts), không tautology; checkers reject đúng raw template header, handle CRLF + bold-header.
- Spine routing (feature-intake → sdd → correctness-review → intent-review, thiết kế "ba oracle", `subagent_type: reviewer` dispatch, residual gates) được spec cụ thể, executable.
- `docs/solutions/INDEX.md` (5 entries) khớp chính xác 5 doc thật.

---

## Đề xuất ưu tiên (thứ tự thực thi)

1. **Fix command matching trong 3 commit hook** — tokenize/normalize lệnh (bắt `git … commit` ở bất kỳ segment nào sau `&&`/`;`/`|`, chấp nhận `-C`/`-c`/`command`), bỏ field `"if"` giả trong settings.json. Lỗ lớn nhất.
2. **Fix root resolution của `session-knowledge.sh`** theo pattern `git rev-parse --show-toplevel` như các hook anh em; bỏ `exec 2>/dev/null` để lỗi nhìn thấy được.
3. **Thống nhất hard-gate list về 1 nguồn máy-đọc-được** (YAML/JSON mà feature-intake, Rule 4, orchestration.md, risk-corroboration.sh cùng đọc). Giải luôn xung đột dependency-bump (Rule 3 vs hook line 73).
4. **Đưa review chain vào `executing-plans`** hoặc sửa docs thôi tuyên bố parity; sửa tiền đề sai + hardcode trong `finishing-a-development-branch`; sửa/fallback cho quality-reviewer dispatch không tồn tại; thống nhất base branch create-pr vs finishing.
5. **Siết evidence checks:** verify command phải tham chiếu file trong diff hoặc nằm trong allowlist (cấm `true`); rollback phải khác template; thêm `test_verify_summary.py` vào `run-tests.sh:33` (1 dòng); chạy verify command trong sandbox thay vì `shell=True` trên CI; unify placeholder sets về một module.
6. **Cơ giới hoá những gì đang là prose:** hook append trust-ledger row lúc PR merge; drift-check `hooks/` vs `.claude/hooks/` trong CI; deploy-harness học un-deploy (manifest-based); fix hoặc xoá metric `user_turns`; rotation cho Session End Log.
7. **Mở rộng branch-isolation coverage** sang Bash write + NotebookEdit; thiết kế lại break-glass để dùng được mid-session (vd. file-based flag có TTL thay vì env var).
8. **Dọn working tree:** xoá `settings copy.json`, `.claude copy/`, 3 backup dirs; commit hoặc xoá REQ.md / PR_TEMPLATE.md / docs/research.

> Lưu ý lane: nhóm 1, 2, 7 đụng `hooks/*` + `settings.json` = high-blast theo Rule 4 của chính repo → đi lane **high-risk** với PLAN + Rollback đầy đủ.
