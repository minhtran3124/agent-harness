# Package A + B — Phân tích chi tiết (design options)

Spec: `hook-surface-slim`  
Branch context: `simplify` @ ~30dc501  
Status: **analysis only** — chưa implement  
Canonical EN inventory: `research-brief.md` §0–§5

---

## 1. Mục tiêu kết hợp A+B

| Gói | Mục tiêu chính | Metric thành công |
|---|---|---|
| **A** | Giảm **always-on wall-clock** + bớt process spawn trên mọi tool call | Non-commit Bash p50 ≤ ~35ms; Edit chain −≥40ms khi không active plan; behavior block/warn **giữ nguyên** |
| **B** | Consumer sau install **không chặt hơn** meta-repo về risk modes; hết “mọi category block vì thiếu manifest” | Fresh install sandbox: commit path với Lane đúng không bị block chỉ vì thiếu manifest; modes warn/block **parity** với meta-repo (trừ override local) |

A và B **trực giao**: A = shape process; B = data/policy delivery. Làm chung một PR được nếu waves tách verify rõ; rủi ro review cao hơn → khuyến nghị **2 wave** (A rồi B) hoặc B-first nếu pain chính là consumer stuck.

---

## 2. Package A — chi tiết kỹ thuật

### 2.1 Vấn đề gốc

`settings.json` PreToolUse Bash đăng ký **4 command hooks riêng**:

```
check-untracked-py.sh
commit-quality-gate.sh
risk-corroboration.sh
branch-guard.sh
```

Mỗi hook, kể cả khi command là `ls`:

1. Spawn shell process mới  
2. `cat` stdin JSON  
3. `jq` parse  
4. `source lib/git-command.sh` (**cả 4 hooks** — check-untracked-py, commit-quality, risk-corroboration, branch-guard đều source)  
5. Early-exit nếu không phải `git commit`/`push`

Đo trên `simplify`: ~**62 ms** tổng cho non-commit (4 × ~15ms). Commit path ~**264 ms** (logic thật chồng lên).

Claude Code **không** share process giữa hooks cùng event — chỉ gộp ở phía harness (một `command` duy nhất).

### 2.2 A1 — Dispatcher PreToolUse Bash

#### Thiết kế đề xuất

```
settings.json:
  PreToolUse / Bash → hooks/pre-bash-dispatch.sh   # ONLY

hooks/pre-bash-dispatch.sh:
  INPUT=$(cat)
  CMD=$(jq ...)
  source lib/git-command.sh
  # Fast path: không phải commit/push → exit 0 ngay (~1 jq + 1 match)
  if ! hook_cmd_is_git_commit_or_push "$CMD"; then exit 0; fi

  # Commit path: chạy các check theo thứ tự hiện tại
  # Option 1 (an toàn): exec từng script với stdin replay
  # Option 2 (sạch hơn): refactor 4 script thành lib functions + thin CLI wrappers
```

#### Hai cách implement

| Cách | Mô tả | Ưu | Nhược |
|---|---|---|---|
| **A1-thin** | Dispatcher `printf '%s' "$INPUT" \| bash hooks/X.sh` lần lượt; giữ 4 file nguyên | Diff nhỏ; test cũ gần như reuse; fail-fast exit 2 giữ được | Vẫn 4 bash con trên **commit** path; non-commit chỉ 1 spawn → **thắng perf chính** |
| **A1-lib** | Tách body → `hooks/lib/{untracked,quality,risk,branch}.sh` functions; 4 file `.sh` trở thành thin wrappers cho CI/manual; dispatch gọi function | 1 process cả commit path; bớt duplicate source | Diff lớn; ~900 LOC test contract phải adapt; risk regression matcher/exit codes |

**Khuyến nghị:** **A1-thin trước** (wave A.1), A1-lib optional sau nếu commit path vẫn là bottleneck.

#### Thứ tự check (giữ nguyên semantics)

Hiện tại settings order:

1. untracked-py (commit **hoặc** push)  
2. commit-quality (commit only)  
3. risk-corroboration (commit only)  
4. branch-guard (commit only, warn)

Dispatch phải (⚠ contract deny-signal — 2 kênh **độc lập**):

Các sub-hook deny bằng **hai cơ chế khác nhau**, dispatcher phải xử lý cả hai:

| Sub-hook | Cơ chế deny | Exit code trên deny |
|---|---|---|
| `check-untracked-py` | **stdout JSON** `permissionDecision: "deny"` | **exit 0** (verified: script rơi xuống cuối sau khi in JSON) |
| `commit-quality`, `risk-corroboration` | stderr message + **exit 2** | exit 2 |
| `branch-guard` | stderr warn | exit 0 (không bao giờ block) |

Vì vậy contract **KHÔNG** được là "stop on first exit 2" đơn thuần — làm thế sẽ **nuốt mất deny của untracked-py** (nó exit 0) và commit lọt = hard block thành no-op. Contract đúng:

- **Relay stdout của MỌI sub-hook vô điều kiện** (bất kể exit code) — deny JSON của untracked-py phải luôn tới Claude. Nếu nhiều hook cùng in JSON, gom/forward theo thứ tự (deny đầu tiên thắng — Claude đọc `permissionDecision` từ stdout).
- **exit 2 là tín hiệu early-stop độc lập**: gặp exit 2 → dừng chuỗi ngay, propagate exit 2 (đã relay stdout của hook đó rồi).
- Push: chỉ untracked-py có hiệu lực (quality/risk/branch early-exit trên non-commit; untracked match push).
- Commit: chạy 1→2→3→4; branch-guard luôn exit 0 (chỉ warn).
- Stderr messages: forward nguyên.

#### Edge cases

| Case | Xử lý |
|---|---|
| Script con missing | Fail-closed exit 2 + message redeploy (giống risk/quality hiện tại) |
| `git add && git commit` | Matcher lib đã handle — không đổi |
| Tests gọi trực tiếp `hooks/X.sh` | Giữ entrypoint từng file → suite cũ chạy |
| `gate-integration.test.sh` | Cập nhật nếu assert 4 registrations; assert 1 dispatch + wrappers wired=false hoặc wrappers vẫn “callable” |
| Manifest `hooks[]` | Thêm `pre-bash-dispatch.sh` wired=true; 4 cũ: **wired=false** nếu chỉ còn library/CLI, **hoặc** wired=true nếu vẫn listed in settings (A1-thin: chỉ dispatch trong settings → 4 wired=false) |
| `lint-doc-truth` / CLAUDE.md table | Generate/update inventory |
| Deploy path rewrite | `derive_settings` đã rewrite `hooks/*.sh` → `.claude/hooks/...` — OK nếu chỉ đổi settings source |

#### Perf kỳ vọng A1-thin

| Path | Trước | Sau (ước lượng) |
|---|---|---|
| Non-commit Bash | ~62 ms × 4 spawns | ~15–25 ms × 1 spawn |
| Commit | ~264 ms | ~200–240 ms (vẫn 4 body; bớt 3× jq/source prologue) |

### 2.3 A2 — Blast-radius fast-path

#### Bottleneck

`hook_lib_find_active_plan` làm:

```bash
for p in $(ls -t "$repo"/specs/*/PLAN.md); do
  grep -qiE '^status:[[:space:]]*active' "$p" && echo && return
done
```

Với **hàng chục–gần trăm** spec dirs (repo này ~80+), mỗi Edit:

- `ls -t` glob lớn  
- Có thể grep nhiều file đến khi hết (0 active → quét **hết**)  
- Đo ~**127 ms** ngay cả khi 0 active plan  

#### Options

| Option | Ý tưởng | Ưu | Nhược |
|---|---|---|---|
| **A2a** | Marker file `specs/.active-plan` hoặc `runtime/active_plan` do SDD/writing-plans ghi khi `status: active`, xóa khi shipped | O(1) lookup | Cần discipline/skill write; stale marker = bug; thêm contract |
| **A2b** | Cache mtime: `/tmp/harness-active-plan-$repo_hash` TTL vài giây + invalidate nếu `specs/**/PLAN.md` mtime mới hơn | Nhanh, không đổi skills | Cache wrong across worktrees nếu hash kém; complexity |
| **A2c** | Early exit: nếu **không có** file khớp `grep -l '^status: active' specs/*/PLAN.md` — dùng một lần `grep -rl`/`rg --files-with-matches` có thể nhanh hơn vòng ls+grep từng file | Ít đổi semantics | Vẫn O(n) I/O; win phụ thuộc FS |
| **A2d** | Đảo order: bookkeeping skip **trước** (đã có); thêm skip nếu path không tồn tại `specs/` | rẻ | Không giúp khi có specs/ |
| **A2e** | `find specs -name PLAN.md -maxdepth 2` + dừng ở match đầu **không** sort mtime trừ khi >1 active | Tránh `ls -t` full sort | Multi-active hiếm; document “first found” |

**Khuyến nghị:** **A2c hoặc A2e** trong wave A (không phụ thuộc skill); A2a chỉ nếu muốn O(1) lâu dài (design fork riêng).

Semantics **giữ**: không active plan → silent exit 0; không fallback mtime plan cũ.

#### Perf kỳ vọng A2

Edit chain ~184 ms → ~**80–120 ms** nếu active-plan miss path rẻ (~10–30 ms).

### 2.4 A3 — Dormant `auto-test-on-change.sh`

| Option | Action |
|---|---|
| **Delete** | Xóa hook + test + manifest row + docs — −120 LOC, −114 test lines |
| **Keep dormant** | Status quo; clutter inventory |

**Khuyến nghị delete** nếu không có lịch wire trong 1 quý. Wire opt-in = product decision riêng (PostToolUse cost cao khi chạy pytest mỗi save).

### 2.5 A4 — Strip commit-quality Checks 2 / 2.5 / 3 (app/)

Hiện:

- Check 2: breakpoint/print trong `app/**/*.py` — block  
- Check 2.5: REQUIRE_VERIFY=1 + Verify table — block  
- Check 3: map app→tests + pytest — block  

Harness meta-repo **không có `app/`** → dead trên dogfood; consumer app repo thì **có giá trị**.

| Option | Hành vi |
|---|---|
| **A4-opt-in** | Chỉ chạy khi `REQUIRE_APP_GATES=1` hoặc `HARNESS_APP_ROOT=app` set trong settings env | An toàn cho consumer đang dựa default |
| **A4-detect** | Chạy nếu tồn tại dir `app/` ở repo root | Zero config cho app layout chuẩn; không chạy ở harness |
| **A4-move** | Chuyển body sang `templates/stacks/*` + docs “paste into hook” | Ít maintain central; dễ drift |

**Khuyến nghị: A4-opt-in** (`REQUIRE_APP_GATES=1`). Lý do đổi từ A4-detect:

- Check 2/3 vốn đã path-scope `app/**/*.py` → một `app/` không có Python staged (Next.js/Rails) **đã inert** hôm nay lẫn dưới A4-detect. Nên "zero config" của A4-detect gần như behavior-neutral — lợi ích thực chỉ là bỏ path chết cho harness.
- **False-positive A4-detect thêm vào:** repo giữ Python **không liên quan** trong thư mục tình cờ tên `app/` sẽ bị pytest-at-commit **không hề opt-in**, chỉ vì heuristic tên thư mục. Với lane **high-risk**, bật một gate chạy pytest theo suy đoán tên dir là không đáng; opt-in tường minh an toàn hơn.

**Không** đụng Check 1 secrets, 1.5 escalations, 1.6 lane evidence.

### 2.6 A — Scope / non-goals

**In:** dispatch, blast fast-path, delete dormant auto-test, app-gate detect/opt-in.  
**Out:** xóa branch-guard/isolation; nới 7 block risk categories; lite profile settings (Package C/product); simplify/task-review ceremony (Package E).

### 2.7 A — Rủi ro & mitigation

| Rủi ro | Mitigation |
|---|---|
| Dispatch nuốt stdout JSON deny (untracked-py exit 0 + JSON) | Contract §2.2: relay stdout vô điều kiện; **không** gate theo exit 2. Test: untracked deny vẫn ra `permissionDecision` |
| Exit code merge sai (warn vs block) | Contract tests per sub-check + integration commit path |
| Manifest/settings drift | `check_manifest.py` + lint-doc-truth |
| Deploy consumers giữ 4 hook cũ (orphan) | `deploy-harness` prune đã có cho hooks/ — verify old commands removed from settings merge |
| settings merge giữ **foreign** hooks trùng | derive_settings foreign filter by command path — retest merge |

### 2.8 A — Test plan

1. Toàn bộ `tests/hooks/*.test.sh` green (đặc biệt 4 bash + gate-integration + command-matching).  
2. New: `pre-bash-dispatch.test.sh` — non-commit exit 0 < budget; commit chains deny secrets/untracked; push only untracked.  
3. Blast: 0 active plan path benchmark hoặc assert không đọc >N PLAN files khi dùng A2e short-circuit.  
4. `bash scripts/run-tests.sh`.  
5. Manual: dogfood 20 Bash non-commit trong session — cảm giác snappier.

### 2.9 A — Effort ước lượng

| Wave | Việc | Effort |
|---|---|---|
| A.1 | A1-thin dispatcher + settings + manifest + docs | S–M (1 session) |
| A.2 | A2e/c blast + tests | S |
| A.3 | Delete auto-test + tests | XS |
| A.4 | app/ detect gate | S |
| **A total** | | **~1–2 focused days** incl. review |

---

## 3. Package B — chi tiết kỹ thuật

### 3.1 Vấn đề gốc

`risk-corroboration.sh`:

```bash
GATE_MODES=$(git show :harness-manifest.json | jq ...)
# missing/invalid → every category_mode() returns "block"
```

Comment chính thức:

> Consumer repos have no manifest at their root, so every category blocks there.

Deploy payload (`install-harness.sh` PAYLOAD + `deploy-harness` SYNCED_DIRS):

- skills, agents, hooks, rules, templates, runtime, settings.json, …  
- **Không** có `harness-manifest.json` ở **repo root** consumer  
- Hook resolve repo root via `git rev-parse` → tìm manifest **root**, không phải `.claude/`

Meta-repo đã warn:

- `workflow-engine`  
- `weakening-validation`  

Consumer: cả hai **block** → edit skills/rules hoặc diff trông giống “remove validation” + Lane &lt; high-risk → **stuck commit**. Đây là pain “install repo khác” còn lại sau fix untracked `.claude/**/*.py`.

### 3.2 B — Các phương án (design fork)

#### B1 — Deploy manifest ra **repo root** consumer

| | |
|---|---|
| **Cách** | `install-harness` / `deploy-harness` copy `harness-manifest.json` → `$TARGET/harness-manifest.json` (hoặc merge subset) |
| **Ưu** | Hook code gần như không đổi; `git show :harness-manifest.json` hoạt động nếu consumer commit file |
| **Nhược** | Ô nhiễm root consumer; file có skills/agents inventory **của harness** — nhiễu; consumer phải **stage/commit** manifest không thì `git show :` vẫn miss → vẫn block; conflict nếu consumer có manifest riêng |
| **Biến thể** | Chỉ deploy `hard_gates` slice: `harness-gate-modes.json` nhỏ |

#### B2 — Deploy manifest **vào `.claude/`** + hook đọc fallback chain

| | |
|---|---|
| **Cách** | Copy → `.claude/harness-manifest.json` (derived, gitignored cùng `.claude/`). Hook: (1) `git show :harness-manifest.json` (2) worktree root manifest (3) `$REPO/.claude/harness-manifest.json` hoặc cạnh hook `$(dirname)/../harness-manifest.json` |
| **Ưu** | Không đụng root tracked tree; re-sync mỗi deploy; parity modes với upstream harness |
| **Nhược** | **→ LOẠI (xem §3.3 blocker #160):** đọc `.claude/harness-manifest.json` phá **index-side purity** — `.claude` gitignored ở consumer, agent ghi được → nới gate ngoài cây commit. Đây là lớp TOCTOU critical `gate-config-must-read-index.md` đã đóng. Không dùng. |
| **Bảo mật** | Auth categories vẫn block; chỉ restore warn list từ upstream |

#### B3 — Missing manifest → **builtin default modes** trong hook

| | |
|---|---|
| **Cách** | Nếu không đọc được manifest: dùng default map hard-coded (copy 7 block + 2 warn giống upstream). Có manifest → manifest thắng |
| **Ưu** | Không phụ thuộc deploy path; consumer cũ tự “unstuck” sau upgrade hook only |
| **Nhược** | Modes **duplicate** (manifest + bash default) — drift risk; `check_manifest` phải pin default == manifest hoặc generate default từ manifest lúc build |
| **Mitigation** | Generate `hooks/lib/gate-modes.default.sh` từ manifest trong CI; hook sources generated file; drift = CI fail |

#### B4 — Missing manifest → warn-not-block cho non-security slugs

| | |
|---|---|
| **Cách** | Không có manifest: `workflow-engine`, `weakening-validation`, có thể `public-contract` → warn; auth/authz/data-loss/audit/external/high-blast → block |
| **Ưu** | An toàn hơn B3 full parity nếu default sai; greenfield dễ thở |
| **Nhược** | Vẫn dual policy; không đọc được “upstream vừa siết lại X” |

#### B5 — Docs only + RISK_WARN_CATEGORIES trong settings.local template

| | |
|---|---|
| **Cách** | Không đổi fail-closed; document break-glass |
| **Ưu** | XS effort |
| **Nhược** | **Không** giải stuck mặc định — user/agent phải biết knob |

### 3.3 B — Khuyến nghị thiết kế

**Chọn B3-only (generated defaults embed trong hook code).** ~~B-hybrid (B2+B3)~~ đã bị loại: xem “Index-side blocker” bên dưới — path đọc `.claude/harness-manifest.json` tái tạo đúng lỗ hổng `gate-config-must-read-index.md` (severity **critical**).

1. **Generated defaults:** CI sinh `hooks/lib/gate-modes.default.sh` từ `harness-manifest.json` (7 block + 2 warn). Hook source file này. Drift default ≠ manifest → CI fail (`scripts/check_manifest.py` mở rộng hoặc smoke test mode-set).
2. **Hook resolve order (chỉ 2 nguồn, cả hai index-safe):**
   a. `git show :harness-manifest.json` — nếu consumer **chủ động track** manifest (opt-in, index-side, an toàn theo #160).
   b. **Generated defaults embed** (B3) nếu (a) fail — đây là nguồn cho **mọi** consumer bình thường.
3. **KHÔNG** đọc bất kỳ file policy nào từ worktree/`.claude/` (on-disk, agent-writable). Sửa defaults = sửa hook = high-blast + index-checked → không có vector nới gate ngoài luồng.
4. **Không** auto-commit manifest vào root consumer (tránh B1 pollution) trừ opt-in docs.

#### Index-side blocker (PR #160 lesson — vì sao bỏ path `.claude`)

`docs/solutions/harness/gate-config-must-read-index.md` (critical): hook gating commit phải đọc **mọi** input quyết định allow/deny từ **index** (`git show :<path>`, fail-closed nếu vắng) — một lần đọc file policy phía worktree là **bypass**, vì agent sửa được file unstaged trước commit và nó không vào cây commit.

`.claude/` ở consumer là **gitignored → không bao giờ stage được → check index không bảo vệ nổi**. Nếu hook đọc mode từ `.claude/harness-manifest.json`, agent chỉ cần lật `mode: warn` để nới gate cho cây đang commit — đúng lớp TOCTOU mà #160 (commit `880eb15`) đã đóng. Các biện hộ “harness-owned derived / chỉ nới về parity” **không phải write-guard**: không gì ép file trên disk khớp upstream lúc commit.

→ **B3-only tránh hoàn toàn vector này** mà vẫn đạt mục tiêu unstuck (parity 2 warn / 7 block cho consumer), vì policy nằm trong hook code chứ không phải file agent ghi được. Nếu về sau muốn cho consumer track manifest riêng, chỉ dùng path (a) index-side — **không bao giờ** thêm lại path đọc `.claude`.

### 3.4 B — Ảnh hưởng consumer behavior (trước → sau)

| Scenario consumer | Trước | Sau B3 |
|---|---|---|
| Commit đổi `src/foo.ts`, Lane normal, no hard keywords | OK | OK |
| Commit đổi file match workflow-engine paths (nếu scanner path-based) + Lane normal | **BLOCK** | **WARN** (parity meta) |
| Commit auth code + Lane normal | BLOCK | BLOCK |
| Commit hooks/ trong consumer copy + Lane normal | BLOCK (high-blast) | BLOCK |
| Không có Lane, có signal | WARN (fail-open) | WARN |
| RISK_CORROBORATION_STRICT=1, no Lane | BLOCK | BLOCK |
| Old consumer chưa upgrade hook | block-all | block-all cho tới khi upgrade hook (embedded defaults theo hook, không cần re-deploy manifest) |

### 3.5 B — Scope / non-goals

**In:** mode resolution parity; deploy artifact; tests warn-mode trên fixture không root manifest.  
**Out:** lite profile (bỏ scope-gate/session); đổi detector keywords; nới auth; auto-classify Lane.

### 3.6 B — Rủi ro & mitigation

| Rủi ro | Severity | Mitigation |
|---|---|---|
| Fail-open quá rộng (mất block) | High | Contract tests: auth still block without root manifest; high-blast block |
| Drift default vs manifest | Med | Generate + CI pin (`check_gate_modes_smoke` mở rộng) |
| Consumer custom hard gates | Low | Root tracked manifest vẫn priority (a) |
| Generated defaults không ship (hook thiếu `gate-modes.default.sh`) | Med | fail-closed block + message redeploy; install sandbox test assert file tồn tại trong `hooks/lib/` |
| Doc/CLAUDE “manifest at root only” stale | Low | lint + research compound |

### 3.7 B — Test plan

1. Extend `tests/hooks/risk-corroboration.test.sh` / `warn-mode-smoke.test.sh`:  
   - temp repo **no** manifest anywhere (kể cả `.claude/`) → **embedded defaults** cho 2 warn / 7 block; workflow-engine commit passes with note  
   - auth keyword + Lane normal, no manifest → **exit 2** (embedded default vẫn block)  
   - high-blast (hooks/) + Lane normal, no manifest → exit 2  
   - **Bypass guard (regression #160):** ghi `.claude/harness-manifest.json` với mọi category = warn → gate **KHÔNG** được nới (hook không đọc worktree/`.claude` policy) → auth vẫn exit 2  
2. `tests/scripts/*.test.sh`: `hooks/lib/gate-modes.default.sh` được generate và mode-set == `harness-manifest.json hard_gates.detectable` (drift → fail).  
3. Meta-repo path unchanged: index manifest (`git show :`) still wins over embedded defaults.  
4. Full `run-tests.sh`.

### 3.8 B — Effort

| Wave | Việc | Effort |
|---|---|---|
| B.1 | Design freeze resolve order + generate defaults | S |
| B.2 | Hook resolve (index → embedded) + generated `gate-modes.default.sh` + tests | M (high-blast review chain) |
| B.3 | Docs install + compound solution entry | S |
| **B total** | | **~1–2 days** + high-risk ceremony |

---

## 4. A+B kết hợp — sequencing & dependency

```
         ┌─────────────┐
         │  Intake OK  │
         └──────┬──────┘
                ▼
         ┌─────────────┐
         │ Wave A.1    │  dispatcher thin (settings blast radius)
         │ Wave A.2-4  │  blast / delete dormant / app detect
         └──────┬──────┘
                ▼
         ┌─────────────┐
         │ Wave B.*    │  resolve (index→embedded) + gen defaults (high-blast, needs SUMMARY high-risk)
         └──────┬──────┘
                ▼
         correctness + intent + deploy sandbox
```

**Vì sao A trước B:** A ít đụng policy an ninh; dogfood perf ngay trên meta-repo; B cần design approve missing-manifest.  
**Vì sao B trước A nếu chỉ được 1 wave:** pain “stuck consumer” > pain 60ms/bash — chọn B-only trước.

**Không** gộp A1-lib + B3 một wave — blast radius review quá lớn.

### Shared files / conflict

| File | A | B |
|---|---|---|
| `settings.json` | yes | no (unless env) |
| `hooks/pre-bash-dispatch.sh` | create | — |
| `hooks/risk-corroboration.sh` | maybe call path only | **yes** resolve modes |
| `hooks/commit-quality-gate.sh` | A4 | no |
| `hooks/blast-radius-check.sh` / `lib/lane.sh` | A2 | no |
| `scripts/deploy-harness.sh` | prune verify | no copy manifest (B3: defaults ship trong `hooks/lib/` — deploy đã sync `hooks/`) |
| `hooks/lib/gate-modes.default.sh` | — | **create** (generated từ manifest, CI-pinned) |
| `harness-manifest.json` | hooks inventory | **source** để generate defaults (CI) |
| `tests/hooks/risk-*` | dispatch integration | **yes** |
| `tests/hooks/*quality*` | A4 | no |

Conflict thấp nếu B chỉ sửa đầu file risk (GATE_MODES resolve) và A chỉ bọc call.

---

## 5. Alternatives bị loại (nhắc lại)

| Alt | Lý do loại cho A+B |
|---|---|
| Xóa branch-guard | Review 2026-07-29 refuted |
| Loosen 7 block categories | Không có FP evidence mới |
| B5 docs-only | Không đạt goal unstuck |
| B1 root manifest full inventory | Ô nhiễm + inventory sai ngữ cảnh consumer |
| **B2 / B-hybrid đọc `.claude` manifest** | **Tái tạo TOCTOU #160** (critical): `.claude` gitignored ở consumer → agent ghi được → nới gate ngoài index. Dùng B3-only |
| A4-detect | False-positive: dir tình cờ tên `app/` → pytest-at-commit không opt-in; A4-opt-in an toàn cho high-risk lane |
| A1-lib ngay | Effort/risk cao; thin đủ ROI |

---

## 6. Decision checklist (human)

Trả lời trước khi `/writing-plans`:

1. **Sequence:** A→B (perf first) hay B→A (consumer first) hay A+B parallel worktrees?  
2. **A1:** thin (khuyến nghị) hay lib?  
3. **A2:** A2e short-circuit (khuyến nghị) hay marker file A2a?  
4. **A3:** delete auto-test hay keep dormant?  
5. **A4:** opt-in env `REQUIRE_APP_GATES=1` (khuyến nghị) / detect `app/` / skip A4?  
6. **B:** B3-only embedded defaults (khuyến nghị, index-safe) / chỉ path (a) index track / B4 softer? — **KHÔNG** dùng path đọc `.claude` (regression #160).  
7. **Ceremony:** có mở Package E (lane-scale simplify/task-review) trong cùng initiative không? (khuyến nghị **tách** spec)

---

## 7. Rollback

| Wave | Rollback |
|---|---|
| A | `git revert`; settings 4 hooks trở lại; deploy prune/resync consumers |
| B | revert hook resolve + xóa `gate-modes.default.sh`; consumers upgrade hook → behavior block-all cũ (documented) |

---

## 8. Tóm tắt một trang

**A** = bớt **spawn/tax** (dispatcher + blast miss-path + dọn dead), không nới security.  
**B** = consumer **cùng mode policy** với meta-repo qua **embedded defaults trong hook code** (B3-only, index-safe — không đọc file policy phía worktree/`.claude`), không bỏ hard gates thật.  
**Làm chung initiative, tách wave; default technical choices: A1-thin, A2e, A3-delete, A4-opt-in, B3-only.**  
**Contract bắt buộc trước khi code:** (1) dispatcher relay stdout vô điều kiện từ mọi sub-hook (không "stop on first exit 2"); (2) B chỉ đọc policy từ index (`git show :`) hoặc embedded defaults — không bao giờ từ `.claude/` (regression #160).  
**Không giải** cảm giác nặng do Superpowers-6 / simplify-stage — đó là track E.
