# hook-surface-slim — Research brief (tiếng Việt)

Ngày: 2026-08-06 (ban đầu) · **Re-review: 2026-08-06 trên branch `simplify` @ `30dc501`**  
Độ sâu: Deep (intake high-risk; review trước + bench latency ×2)

> Bản dịch của `research-brief.md`. Khi lệch, bản tiếng Anh là canonical.

## 0. Delta re-review (`simplify` HEAD)

Tip branch đã merge tới superpowers-6 review pipeline. **Inventory wire hooks không đổi** (11 wired + 1 dormant). Thứ *đã* land ảnh hưởng ma sát:

| Đã ship trên `simplify` | Ảnh hưởng “quá nhiều hooks / stuck” |
|---|---|
| `simplify-gate-surface` — mode-as-data; `workflow-engine` + `weakening-validation` → **warn** | Ít block commit giả ở **meta-repo này** thôi |
| `fix-hooks-gate-lane-divergence` — `hooks/lib/lane.sh`; dedup scope-gate; blast dùng shared active-plan | Đúng hơn + bớt spam nudge; **không** giảm số process spawn |
| Fix install slim-skill-surface — untracked `.claude/**/*.py` không còn chặn consumer mới | Đã sửa 1 hard-stuck consumer (deny commit sau install) |
| SC coverage qua commit-quality `--plan-dir` | Gate commit **chặt hơn** khi stage SUMMARY+PLAN |
| risk-corroboration diff-size **warn** (gh-159) | Thêm noise advisory trên diff lớn tiny/normal |
| session-knowledge + active runs | SessionStart hơi nặng hơn |
| **Không phải hooks:** `require-claude-simplify-gate` + pipeline task-review Superpowers-6 | Stuck **ceremony** mới (finish/SDD/receipts) — cảm giác “gate” nhưng là skills/scripts |

**Vẫn đúng / vẫn mở (xác nhận lại trên HEAD này):**

1. `settings.json` vẫn **4 Bash PreToolUse** mọi Bash + **3 PostToolUse** mọi Edit.
2. Deploy vẫn **không ship** `harness-manifest.json` root → consumer risk vẫn **block mọi category**.
3. `auto-test-on-change.sh` vẫn dormant; commit-quality Check 2/2.5/3 vẫn dead weight `app/**` ở đây.
4. `blast-radius-check.sh` vẫn ~**127 ms**/edit với **0** active plan.

### Re-bench trên `simplify`

| Path | Giờ | Bench trước |
|---|---|---|
| Bash non-commit ×4 | **~62 ms** | ~118 ms |
| `git commit` ×4 | **~264 ms** | ~315 ms |
| Write\|Edit chain | **~184 ms** (blast ~127 ms) | ~245 ms |
| Light session (20e/40b/15p) | **~8 s** | ~12 s |
| Heavy (80/120/40) | **~28 s** | ~40 s |

Cấu trúc không đổi — thuế lớn vẫn multi-spawn Bash + blast scan + scope-gate mỗi prompt.

### Tách “stuck” cập nhật

| Triệu chứng | Nguyên nhân chính giờ | Hooks? |
|---|---|---|
| Chậm mỗi tool call | 4+3 process always-on | **có** |
| Không commit sau install mới | **Đã fix** | từng là hooks |
| Consumer chặt hơn meta-repo | thiếu manifest deploy → block-all | **có** |
| Feature cảm giác review vô tận | simplify-stage + task-review + receipts | **không** (skills) |

**Hệ quả:** cắt hooks → perf; parity consumer → Package B; “nặng trên simplify” chủ yếu là **review ceremony**, không phải số lượng hooks.

### Khuyến nghị mặc định vẫn **A+B**

A = dispatcher + blast fast-path + dọn dormant.  
B = consumer manifest/modes (fix install-py **chưa** đóng risk fail-closed).  
E (sau, ngoài hooks): scale simplify/task-review theo lane.

## 1. Inventory (nguồn sự thật: `settings.json` + `harness-manifest.json`)

| Hook | Event | Matcher | Quyết định | Wired |
|---|---|---|---|---|
| `check-untracked-py.sh` | PreToolUse | Bash | **block** commit/push nếu còn `.py` untracked | có |
| `commit-quality-gate.sh` | PreToolUse | Bash | **block** commit (secrets, escalations, lane evidence, app debug/tests) | có |
| `risk-corroboration.sh` | PreToolUse | Bash | **block/warn** commit nếu Lane khai báo thấp hơn hard gate | có |
| `branch-guard.sh` | PreToolUse | Bash | **warn** khi commit trên main/master | có |
| `branch-isolation-guard.sh` | PreToolUse | Write\|Edit | **deny** edit code trên shared branch | có |
| `ruff-on-edit.sh` | PostToolUse | Write\|Edit | auto-fix `.py`, không bao giờ block | có |
| `blast-radius-check.sh` | PostToolUse | Write\|Edit | warn ngoài scope so với PLAN active (strict opt-in) | có |
| `render-plan-on-write.sh` | PostToolUse | Write\|Edit | render PLAN.html chỉ khi đụng PLAN.md | có |
| `scope-gate.sh` | UserPromptSubmit | * | nhắc intake nếu intent implement mà chưa có plan | có |
| `session-knowledge.sh` | SessionStart | * | inject KB + active runs | có |
| `state-breadcrumb.sh` | SessionEnd | * | append STATE.md | có |
| `auto-test-on-change.sh` | — | — | dormant | **không** |

**Đã xóa:** `protected-path-guard.sh` (PR #133).  
**Đã nới:** `workflow-engine` + `weakening-validation` → warn (2026-07-23 / simplify-gate-surface).  
**Đã sửa:** resolve Lane thống nhất trong `hooks/lib/lane.sh` (F1 từ review 2026-07-29).

## 2. Wall-clock đo được (máy này, 2026-08-06)

| Path | Chi phí |
|---|---|
| Mọi Bash không-commit → 4 PreToolUse hooks | **~118 ms** (early-exit sau jq + matcher) |
| Mọi `git commit` → cùng 4 hooks chạy full | **~315 ms** (commit-quality ~136 ms, risk ~74 ms) |
| Mọi Write\|Edit → isolation + ruff + blast + render | **~245 ms** (riêng blast-radius ~132 ms dù 0 active plan) |
| Mọi UserPromptSubmit → scope-gate | **~155 ms** |
| SessionStart → session-knowledge | **~150 ms** |
| Session feature nhẹ (20 edit / 40 bash / 15 prompt) | **~12 s** pure hook tax |
| Session nặng (80 / 120 / 40) | **~40 s** |

Số subprocess trên commit path: commit-quality ~21 dòng git/python dưới `bash -x`; risk ~19.

**Kết luận “perf”:** không phải mỗi lần gọi mất vài giây, mà **nhân với mọi tool call**. Thuế always-on lớn nhất: (1) 4 process PreToolUse trên *mọi* Bash kể cả `ls`, (2) blast-radius trên *mọi* edit quét toàn bộ PLAN.md, (3) scope-gate trên *mọi* prompt.

## 3. Cái gì thật sự gây “stuck” (khác với chậm)

### A. Meta-repo này (harness-skills)

| Ma sát | Cơ chế | Block? |
|---|---|---|
| Phải branch trước mọi edit ngoài `specs/` | `branch-isolation-guard` | **có** deny |
| Commit cần lane evidence trong SUMMARY khi stage specs | commit-quality Check 1.6 | **có** |
| Lane khai báo thấp vs path high-blast/hooks | risk-corroboration | **có** |
| Gộp `git add && git commit` | check-untracked-py / matcher | **có** (gotcha đã document) |
| ESCALATIONS còn pending | commit-quality 1.5 | **có** |
| scope-gate / blast-radius / branch-guard / session KB | advisory | không |
| commit-quality app/ debug+pytest (Check 2/2.5/3) | chỉ `app/**/*.py` | **chết ở đây** (không có `app/`) |

Review lịch sử (2026-07-29): **zero** lần commit bị Lane-gate reject trong repo này sau khi nới; break-glass log vẫn trống.

### B. Consumer repo sau install (giả thuyết chính cho “stuck ở repo khác”)

`risk-corroboration.sh` ghi rõ:

> Consumer repos have no manifest at their root, so every category blocks there.

Deploy copy hooks + `settings.json` derived nhưng **không ship `harness-manifest.json`** vào root consumer. Hệ quả:

1. Cả 9 category detectable fallback về **block** (không còn warn-mode cho workflow-engine / weakening-validation).
2. Edit skills/rules/agents ở consumer (hoặc bất kỳ thứ khớp keyword scanner) + Lane dưới high-risk → **commit bị chặn**.
3. Các nới lỏng đã tune ở meta-repo **không chuyển sang** consumer.

Khớp báo cáo user tốt hơn giả thuyết “quá nhiều hooks” đơn thuần.

Ma sát consumer phụ:

- Cùng branch isolation lúc write (đúng thiết kế, nhưng bất ngờ nếu làm việc trên `main`).
- `check-untracked-py` với mọi `.py` untracked (đúng cho CI, ồn ở greenfield).
- `session-knowledge` / `scope-gate` inject token mỗi session/prompt (hơi chậm, không stuck).
- `commit-quality` Check 3 chạy pytest khi có `app/` — chi phí thật ở app repo (tốt), chết ở harness.

## 4. Prior art (đừng tranh lại mù quáng)

| Review | Kết luận còn đúng? |
|---|---|
| over-engineering 2026-07-16 | Có cho dead path `app/`, gộp commit gates, auto-test dormant; xóa branch-guard **sau đó bị bác** |
| hooks-gate-review 2026-07-29 | Có: tổng thể không over-block; giữ branch-guard; fix F1 (**xong** qua lane.sh); dedup scope-gate (**xong**) |
| simplify-gate-surface | Có: mode-as-data + 2 category warn đã ship |

## 5. Khuyến nghị cắt / slim (xếp theo ROI)

### Package A — rủi ro thấp, perf always-on cao (nên làm trước)

| Thay đổi | Vì sao | Rủi ro |
|---|---|---|
| **Gộp 4 Bash PreToolUse thành 1 dispatcher** (`hooks/pre-bash.sh` → source untracked / quality / risk / branch-guard) | 4 process → 1 trên mọi Bash; giữ đủ check | trung bình (wiring + tests) |
| **Fast-path matcher một lần** trong dispatcher trước heavy work | tránh 4× jq + 4× source lib | thấp |
| **blast-radius: cache active-plan hoặc skip khi không có `specs/*/PLAN.md` active** | vẫn ~132 ms quét; 0 active plan hôm nay vẫn trả ls/grep | thấp |
| **Xóa hoặc giữ dormant `auto-test-on-change.sh`** | 120 LOC chưa từng wire; hoặc chỉ wire opt-in | thấp nếu xóa |
| **Tách commit-quality Check 2/2.5/3 khỏi hook mặc định** → stack template / `REQUIRE_APP_GATES=1` | ~110 dòng không bao giờ cháy ở harness; vẫn hữu ích cho app consumer nếu opt-in | trung bình (đổi hành vi consumer nếu họ dựa pytest-at-commit mặc định) |

Kỳ vọng: Bash non-commit ~118 ms → ~30–40 ms; edit path −50–100 ms nếu blast fast-path tốt hơn.

### Package B — consumer “unstuck” (ROI sản phẩm cao nhất cho install-elsewhere)

| Thay đổi | Vì sao | Rủi ro |
|---|---|---|
| **Deploy `harness-manifest.json` cho consumer (hoặc embed modes trong hook)** cùng warn/block như meta-repo | chặn fail-closed block-all | high-blast / contract |
| **Hoặc: thiếu manifest → warn-not-block cho category không-security** (giữ block auth/authz/secrets/high-blast) | default an toàn hơn cho greenfield | cần design |
| **Document break-glass consumer** (`RISK_WARN_CATEGORIES`, settings.local env) trong install README | đã có nhưng vô hình | chỉ docs |
| **Optional “lite profile” settings** — chỉ commit gates, không scope-gate / session-knowledge / blast-radius | cho app repo muốn safety không ceremony | product fork |

### Package C — xóa / hạ cấp (chọn lọc; có evidence)

| Hook | Khuyến nghị | Đừng |
|---|---|---|
| `branch-guard.sh` | **GIỮ** (nudge duy nhất cho commit chỉ-specs trên main) | xóa (bị bác 2026-07-29) |
| `branch-isolation-guard.sh` | **GIỮ** (luật branch cấu trúc) | nới mà không có enforcement thay thế |
| `scope-gate.sh` | **GIỮ** (đã dedup); optional tắt trong lite | xóa — rẻ so với token cost khi routing sai |
| `blast-radius-check.sh` | giữ warn mặc định; tăng tốc; optional unwire trong lite | bật strict mặc định |
| `session-knowledge.sh` | cắt payload hoặc lazy-load; optional unwire trong lite | block session |
| `state-breadcrumb.sh` | giữ hoặc opt-in nếu consumer không dùng STATE.md | — |
| `render-plan-on-write.sh` | giữ (chỉ path PLAN.md) | — |
| `ruff-on-edit.sh` | giữ nếu project Python; no-op nếu không | — |
| 7 category risk block | **GIỮ** đến khi có metric FP mới | nới theo cảm tính |
| `workflow-engine` / `weakening-validation` | đã warn | siết lại |

### Package D — ngoài hooks nhưng cùng cảm giác “stuck”

Ceremony (skills/intake/plan/reviews) lớn hơn wall-clock hooks. Chỉ slim hooks **không** làm feature high-risk của harness cảm giác như “tiny”. Track riêng: scale review chain theo lane (đã ghi ở over-engineering review §5).

## 6. Không được gỡ (load-bearing)

- Secrets scan + untracked `.py` lúc commit  
- `branch-isolation-guard` deny lúc write  
- risk-corroboration cho hard gate thật (auth, data-loss, high-blast, …)  
- lane evidence Check 1.6 khi SUMMARY được stage  
- ESCALATIONS pending deny  

## 7. Quyết định đề xuất cho human

Chọn một:

1. **Chỉ A** — perf dispatcher + blast fast-path + xóa auto-test dormant (+ optional tách app checks)  
2. **A + B** — thêm fix consumer manifest/modes (trả lời tốt nhất cho “stuck ở repo khác”)  
3. **Lite profile product** — hai template settings: `full` (hiện tại) vs `lite` (chỉ commit safety)  
4. **Chỉ research** — không code

Khuyến nghị mặc định: **2 (A+B)**, kèm design note về chính sách missing-manifest trước khi code.
