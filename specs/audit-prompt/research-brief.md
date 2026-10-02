# Prompt audit: project skills (2026-09-30)

Audit run with `/claude-api prompt-audit`, scoped to this project's own skills. No edits applied.

## Assumptions

- **Scope:** the project's own skills, read in `skills/` (the source). `.claude/skills/` is a derived copy that differs only in rewritten helper paths, plus a stripped maintainer section of `skills/README.md`. Not audited: plugin/MCP skills, `~/.claude`, `CLAUDE.md`, rules, agents.
- **Target model:** Sonnet 5.5 (the model running the session).
- **Not read:** the other `compound` subagent prompts and all `compound/templates/`; `xia2/references/research-brief-template.md`; the `finishing-a-development-branch` references; `visual-planner/references/review-sidecar.md`; the `xia2` and `compound` READMEs; the `tests/` fixture folders; the checkouts under `.worktrees/` and `.claude/worktrees/`.

## Summary

The skills are already lean. A 2026-07-29 review (`docs/research/2026-07-29-context-engineering-claude5-skill-review.md`) has already been through them, and the `HARD-GATE` blocks, blind-oracle rules and explicit Read steps are load-bearing, so they were left alone.

The most significant finding: several skills point at source-tree paths that the deploy step does not rewrite, so they break in a deployed consumer copy. The rest are two small wording fixes and a few low-confidence flags.

Findings per group: Group 1 (dated text) 2 medium, 3 low. Group 2 (config files) 1 medium, 3 low. Group 3 (tool descriptions) not applicable. Group 4 (request config) not applicable, since there is no request-building code.

## Findings, highest confidence first

### 1. Source-tree paths not rewritten on deploy — Medium — `flag`

- **Location:** `skills/feature-intake/SKILL.md:4,42`; `skills/finishing-a-development-branch/SKILL.md:51`; `skills/using-git-worktrees/SKILL.md:4,10,36`; `skills/subagent-driven-development/SKILL.md:53`
- **Evidence:** `runtime/run_state.py`, `skills/using-git-worktrees/scripts/detect-isolation.sh`, `bash scripts/deploy-harness.sh`, `skills/subagent-driven-development/scripts/task_brief.py`
- **Pattern:** Group 2, volatile specifics.
- **Why obsolete:** `rewrite_derived_paths` (`scripts/deploy-harness.sh:395-406`) rewrites only `scripts/<name>`, `harness-manifest.json` and `render_plan.py`. The deployed copies keep these four paths unchanged (`.claude/skills/using-git-worktrees/SKILL.md:10,36`), but the deployed tree only has `.claude/runtime/` and `.claude/skills/...`. The subagent-driven-development skill says so itself (`SKILL.md:23-24`). In a consumer repo the worktree `allowed-tools` patterns don't match, and run-state calls (`|| true` or best-effort) silently do nothing, so a run never reaches `ready_to_merge` (`finishing-a-development-branch/SKILL.md:53-56`).
- **Confidence:** Medium: repo-internal contradiction, not exercised in a real consumer install.
- **Action:** `flag`. Choose one fix: extend the rewrite table (touches `scripts/`, which CI gates), or make the skill text source-first like `resume_decision.py`. Recommended: extend the rewrite table, since one change fixes all four paths.

### 2. Trait claim in the implementer prompt — Medium — `rewrite`

- **Location:** `skills/subagent-driven-development/implementer-prompt.md:53-54`
- **Evidence:** "You reason best about code you can hold in context at once, and your edits are more reliable when files are focused."
- **Pattern:** 1a, trait claim.
- **Why obsolete:** It is a claim about the model, not an instruction. The bullets that follow carry the instruction.
- **Action:** `rewrite` (hunk H1).

### 3. "BY DEFAULT, not just when convenient" — Medium — `rewrite`

- **Location:** `skills/intent-review/intent-reviewer-prompt.md:94-95`
- **Evidence:** "Flag findings of this class BY DEFAULT, not just when convenient."
- **Pattern:** 1a, pressure/hedge.
- **Why obsolete:** Sonnet 5.5 follows the plain instruction literally; the emphasis adds nothing.
- **Action:** `rewrite` (hunk H2).

### 4. Stack-specific defect list in a stack-agnostic repo — Low — `flag`

- **Location:** `skills/correctness-review/prompts/angles/stack-defects.md:23-47`
- **Evidence:** FastAPI and DB classes (`Depends(get_current_user)`, `deleted_at IS NULL`, `get_db`, "AI and streaming paths").
- **Pattern:** 1c, example over-indexing.
- **Why obsolete:** This repo has no application stack, and the file itself says to derive the classes from `techstacks/`. The eval fixtures in `evals/skills/review-chain` may depend on this list (see `correctness-scorer-prompt.md:117-121`); not checked.
- **Action:** `flag`: re-baseline against the evals before trimming.

### 5. "Assume a bug exists" — Low — `flag`

- **Location:** `skills/correctness-review/prompts/shared.md:21-24`
- **Evidence:** "Assume this diff contains at least one real bug… trace one more execution path."
- **Pattern:** 1c, strategy coaching.
- **Why obsolete:** It asserts something that may be false, and it sits next to a legitimate "no defects found" ending. The scorer stage does filter false positives, and the high-recall design is deliberate.
- **Action:** `flag`.

### 6. Incident narrative in the scorer prompt — Low — `flag`

- **Location:** `skills/correctness-review/correctness-scorer-prompt.md:100-102,117-121`
- **Evidence:** "Case (2026-07-13, PR #51)…"; "on `evals/skills/review-chain` (2026-07-13)…"
- **Pattern:** Group 2, history narrative.
- **Why obsolete:** The rule stands without the incident ID. The 2026-07-29 review already chose to keep the anecdote in the prompt as calibration, so this is a preference, not a defect.
- **Action:** `flag`.

### 7. History in the guard-completeness angle — Low — `flag`

- **Location:** `skills/correctness-review/prompts/angles/guard-completeness.md:40-44`
- **Evidence:** "This repository shipped the same bug three times…"
- **Pattern:** Group 2, history narrative.
- **Why obsolete:** It also gives the reason for the angle, so it is context.
- **Action:** `flag`.

### 8. External skills that don't resolve here — Low — `flag`

- **Location:** `skills/README.md:141,143-145,165`
- **Evidence:** External skills `systematic-debugging`, `requesting-code-review`, `session-tracker`.
- **Pattern:** Group 2, volatile specifics.
- **Why obsolete:** None of the three is in this session's skill list. The README says the workflows degrade gracefully, and a tool outside the repo is not contradicted by being absent.
- **Action:** `flag`.

### 9. Redundant Read of an always-on rule — Low — `flag`

- **Location:** `skills/feature-intake/SKILL.md:17-18`
- **Evidence:** "Read … `rules/orchestration.md`"
- **Pattern:** Padding.
- **Why obsolete:** That rule already auto-loads every session. The Read costs 93 lines per intake and is harmless.
- **Action:** `flag`.

## Checked and holds

- Every path checked from the skills resolves in the source tree, including the six angle prompts, `review-config.json`, `detect-isolation.sh`, `task_brief.py`, `review_package.py`, `render_plan.py`, and the `compound` subagents and templates.
- The `visual-planner` flags `--summarize`, `--emit-files`, `--review`, `--file`, `--no-open`, `--port` and `--render` exist in the scripts.
- The scorer prompt's claim that no Python linter is wired holds: no `pyproject.toml` or `ruff.toml`, and `ruff` is absent from `.github` and `scripts/run-tests.sh`.
- The duplicated `model_stage` boilerplate in four prompts agrees across them; left as working redundancy.

## Proposed diff (against source `skills/`)

Grepping the repo (excluding `.claude/`, `.worktrees/`, `.git/`, `specs/`) for the three edited strings found only the prompt files themselves, so no tests or parsers depend on them. Redeploy after applying.

H1 (finding 2):

```diff
--- a/skills/subagent-driven-development/implementer-prompt.md
+++ b/skills/subagent-driven-development/implementer-prompt.md
@@ -51,4 +51,3 @@
     ## Code Organization
 
-    You reason best about code you can hold in context at once, and your edits are more
-    reliable when files are focused. Keep this in mind:
+    Keep files focused so edits stay reliable:
     - Follow the file structure defined in the plan
```

H2 (finding 3):

```diff
--- a/skills/intent-review/intent-reviewer-prompt.md
+++ b/skills/intent-review/intent-reviewer-prompt.md
@@ -93,5 +93,4 @@
       features, options, endpoints, abstractions, config knobs, or new public surface not
-      traceable to any intent clause. Flag findings of this class BY DEFAULT, not just when
-      convenient.) This `excess` verdict is a post-hoc check on the FINAL diff — distinct from
+      traceable to any intent clause. Report every finding of this class.) This `excess` verdict is a post-hoc check on the FINAL diff — distinct from
       the separate simplify pass, which edits an unmerged pre-ship diff where deletion is
```

Findings 1 and 4-9 have no hunk because each needs a decision or a measurement first.

---

# Kiểm tra prompt: CLAUDE.md, AGENTS.md, rules, agents (2026-09-30)

Phần mở rộng của `audit-report.vi.md` (chỉ gồm skills). Chưa áp dụng chỉnh sửa nào.

## Giả định

- **Phạm vi:** `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md` ở gốc repo; `rules/*.md` (9 file); `agents/*.md` (4 agent, `PROJECT.md`, `PROJECT.template.md`); và các điểm mà những file này mâu thuẫn với skills. Đọc ở bản gốc; `.claude/` là bản sinh ra.
- **Không có trong repo:** `commands/`, `output-styles/`, `CLAUDE.md` lồng trong thư mục con.
- **Không đọc:** `settings*.json`, `.mcp.json` (có thể chứa bí mật), nên bảng hook trong `CLAUDE.md` chưa được đối chiếu với `settings.json`. `agents/README.md` chưa đọc.
- **Ngoài phạm vi:** `~/.claude` (skill cấp user), skill của plugin, và các checkout trong `.worktrees/`, `.claude/worktrees/`.
- **Model mục tiêu:** Opus 5.5 (model của phiên hiện tại). Mỗi agent được xét theo model nó tự ghim: `coding` → `claude-opus-5-5`, `reviewer` và `task-reviewer` → `claude-opus-5`, `test-runner` → `claude-haiku-4-5-20251001`.

## Tóm tắt

Ba phát hiện đáng sửa nhất đều là thông tin đã cũ so với chính repo:

1. `agents/PROJECT.md` chỉ agent `coding` tới sai chỗ: quy ước code nằm ở `AGENTS.md`, không phải `rules/behavior.md`; phần test bỏ sót toàn bộ pytest; tín hiệu rủi ro của xia2 không còn nằm trong `SKILL.md`.
2. Hợp đồng trả kết quả của subagent bị nói hai kiểu: `rules/orchestration.md` yêu cầu 7 trường, còn prompt dispatch của implementer yêu cầu 4 trường và thiếu `Lane`, `Harness-Delta` (thứ mà `compound` đi tìm).
3. Bản deploy của `skills/README.md` nói hook đọc `.claude/harness-manifest.json`, trái với `CLAUDE.md:94`.

Số phát hiện: 3 mức cao, 8 mức trung bình, 7 mức thấp. Theo nhóm: Nhóm 1 (văn bản lỗi thời) 3 trung bình, 4 thấp. Nhóm 2 (file cấu hình) 3 cao, 5 trung bình, 3 thấp. Nhóm 3 không áp dụng. Nhóm 4 không áp dụng; riêng danh sách agent đã kiểm tra, không có agent trùng lặp.

## Các phát hiện, độ tin cậy cao trước

### C1. Vị trí tín hiệu rủi ro của xia2 đã cũ — Cao — `rewrite`

- **Vị trí:** `agents/PROJECT.md:7-8`; `agents/PROJECT.template.md:11-12,66`
- **Bằng chứng:** "they are built into `skills/xia2/SKILL.md`"; "carries them inside its own `SKILL.md`"
- **Mẫu:** Nhóm 2, chi tiết dễ đổi.
- **Vì sao:** `skills/xia2/SKILL.md:17,52-53` nay trỏ sang `rules/research-depth.md` và `references/depth-classifier.md`; `SKILL.md` không còn chứa danh sách tín hiệu.
- **Hành động:** `rewrite` (H3).

### C2. Bản deploy nói hook đọc `.claude/harness-manifest.json` — Cao — `rewrite`

- **Vị trí:** `skills/README.md:208` (bản deploy: `.claude/skills/README.md:208`)
- **Bằng chứng:** nguồn: "modes from the index `harness-manifest.json`"; sau deploy: "modes from the index `.claude/harness-manifest.json`"
- **Mẫu:** Nhóm 2, hai file chỉ dẫn mâu thuẫn.
- **Vì sao:** `rewrite_derived_paths` thêm tiền tố `.claude/` vào mọi `harness-manifest.json`. Kết quả trái với `CLAUDE.md:94` ("The hook **never** reads `.claude/harness-manifest.json`") và `rules/orchestration.md:25`.
- **Hành động:** `rewrite` câu nguồn để không còn tên file (H4).

### C3. Phần test trong PROJECT.md bỏ sót pytest — Cao — `rewrite`

- **Vị trí:** `agents/PROJECT.md:25-28`
- **Bằng chứng:** "Targeted-run flags: no flags; run a single suite directly"; "Markers / coverage: none — bash test suites…"
- **Mẫu:** Nhóm 2, chi tiết dễ đổi.
- **Vì sao:** `scripts/run-tests.sh:121` (`PYTESTS`) chạy 33 file pytest và `AGENTS.md:23,26` mô tả điều đó. `test-runner` đọc mục này trước, nên không biết cách chạy riêng một test Python.
- **Hành động:** `rewrite` (H5).

### C4. Quy ước code bị trỏ tới file không chứa chúng — Trung bình — `rewrite`

- **Vị trí:** `agents/PROJECT.md:15`
- **Bằng chứng:** "Code style / error handling / validation / logging: `rules/behavior.md` (single source of truth per CLAUDE.md)"
- **Mẫu:** Nhóm 2, mâu thuẫn giữa các file chỉ dẫn.
- **Vì sao:** `rules/behavior.md` chỉ có 5 quy tắc hành vi, không có style. Quy ước thật nằm ở `AGENTS.md:32` (thụt 2 dấu cách cho Bash, 4 cho Python, kebab-case). `agents/coding.md:21-22` lại cấm suy diễn quy ước chưa được nêu. `AGENTS.md:32` mới hơn (2026-07-21 so với 2026-07-17).
- **Hành động:** `rewrite` (H5). Kèm một cờ: `AGENTS.md:32` nói "Python follows standard `ruff`" nhưng repo không có cấu hình ruff nào (`correctness-scorer-prompt.md:72-74` cũng nói không có linter Python).

### C5. Hai hợp đồng trả kết quả khác nhau cho subagent — Trung bình — `rewrite` (chỉ đề xuất)

- **Vị trí:** `rules/orchestration.md:29-37`; `agents/coding.md:32-33`; `skills/subagent-driven-development/implementer-prompt.md:106-119`
- **Bằng chứng:** orchestration: "Every subagent… MUST include in its summary" 7 trường, gồm **Lane** và **Harness-Delta**. implementer-prompt: "return only `status`, commit SHAs, Verify result, and that report path", và định dạng báo cáo không có hai trường đó.
- **Mẫu:** Nhóm 2, mâu thuẫn giữa các file chỉ dẫn.
- **Vì sao:** Agent `coding` nhận cả hai chỉ dẫn cùng lúc. `compound` (`solution-extractor-prompt.md:89`) đi tìm `Harness-Delta: backlog` trong tóm tắt của subagent, nhưng implementer không bao giờ được yêu cầu ghi nó. Dòng Harness-Delta (2026-08-11) mới hơn định dạng báo cáo (2026-07-29).
- **Hành động:** thêm hai trường vào định dạng báo cáo của implementer (H6). Bạn cần xác nhận hướng này.

### C6. Không rõ scorer lấy model từ đâu — Trung bình — `flag`

- **Vị trí:** `skills/correctness-review/correctness-scorer-prompt.md:30-33,38`; `agents/reviewer.md:3`
- **Bằng chứng:** "Use the `model:` already declared in this stage's rendered `agents/` definition", với `subagent_type: reviewer`.
- **Mẫu:** Nhóm 2, mâu thuẫn.
- **Vì sao:** `adapters/runtime-entry-bindings.json:5` gán `correctness_scorer` → model của `coding` (`claude-opus-5-5`), nhưng file này không được deploy vào `.claude/`. Trong repo consumer, người điều phối chỉ thấy `reviewer.md` (`claude-opus-5`), nên finder và scorer chạy cùng model, mất tính đa dạng mà prompt yêu cầu.
- **Hành động:** `flag`. Cần quyết định: ghi rõ trong prompt "dùng `model:` của `agents/coding.md`", hoặc deploy bảng binding.

### C7. `python` thay vì `python3` — Trung bình — `rewrite`

- **Vị trí:** `rules/auto-correct-scope.md:38`; `skills/README.md:229`; `rules/plan-format.md:99-100` (ví dụ)
- **Bằng chứng:** "Run `python scripts/verify_summary.py --lane <slug>`"
- **Mẫu:** Nhóm 2, chi tiết dễ đổi.
- **Vì sao:** Mọi chỗ khác dùng `python3`, và `allowed-tools` của `feature-intake` chỉ cho phép `python3 …verify_summary.py *`, nên dạng `python` không khớp quyền.
- **Hành động:** `rewrite` (H7).

### C8. Tên thẻ XML cũ cho các trường của plan — Trung bình — `rewrite`

- **Vị trí:** `rules/orchestration.md:36,84`; `rules/wave-parallelism.md:18,43`; `rules/auto-correct-scope.md:50,57,81`; `CLAUDE.md:71`; `implementer-prompt.md:42,83,112`
- **Bằng chứng:** "task's `<verify>` command", "the `<action>` spec", "the active plan's `<files>` set"
- **Mẫu:** 1d, cách nói theo bản cũ.
- **Vì sao:** `rules/plan-format.md:182` nói XML là định dạng cũ chỉ để đọc; trường hiện hành là `Verify:` / `Action:` / `Files:`. Không test nào khớp các chuỗi này.
- **Hành động:** `rewrite` 11 chỗ (H8 là mẫu).

### C9. Tên model ghim trong rule luôn được nạp — Trung bình — `rewrite`

- **Vị trí:** `rules/behavior.md:5-6`
- **Bằng chứng:** "behaviors the Claude Opus 5.x guidance documents as departing from that default"
- **Mẫu:** Nhóm 2, tường thuật lịch sử và tên model ghim.
- **Vì sao:** Rule này nạp cho mọi agent, kể cả `test-runner` chạy Haiku 4.5. Quy tắc §4 và §5 tự đứng được; nguồn gốc không thêm gì cho model.
- **Hành động:** `rewrite` (H9).

### C10. Mô tả `test-runner` chứa hai đoạn hội thoại mẫu — Trung bình — `rewrite`

- **Vị trí:** `agents/test-runner.md:3`
- **Bằng chứng:** hai khối `<example>` với lượt `user:`/`assistant:` và "use the Task tool to launch the test-runner agent"
- **Mẫu:** Nhóm 2, liệt kê tình huống kích hoạt; Nhóm 3, ví dụ trong mô tả.
- **Vì sao:** Mô tả đi kèm mọi request. Ví dụ dùng `get_by_email`, "quota check" thuộc một stack ứng dụng mà repo này không có.
- **Hành động:** `rewrite` (H10). Kiểm tra `scripts/test_render_agent_definitions.py` trước khi áp dụng, vì file này có nhắc `test-runner`.

### C11. "Dùng code-review-graph trước Grep/Glob/Read" — Trung bình — `rewrite`

- **Vị trí:** `CLAUDE.md:99`
- **Bằng chứng:** "Use the `code-review-graph` MCP tools **before** Grep/Glob/Read for exploration… The graph auto-updates on file changes (via hooks)."
- **Mẫu:** 1a, "mặc định dùng [tool]".
- **Vì sao:** Opus 5.5 làm theo nguyên văn. Trong phiên này server không kết nối (không có tool `mcp__code-review-graph__*`), nên chỉ dẫn vô điều kiện thành ra trỏ vào tool không tồn tại. Hai điểm chưa kiểm chứng được: bảng hook ở `CLAUDE.md:69-73` không có hook nào cập nhật graph, và tên tool ở đây (`query_graph`) khác tên trong `skills/visual-planner/SKILL.md:4` (`query_graph_tool`).
- **Hành động:** `rewrite` thành có điều kiện (H11). Khối này có dấu `<!-- code-review-graph MCP tools -->`, có thể do trình cài của tool sinh ra và sẽ bị ghi đè.

### C12. Hai mục "không có tác dụng" trong terminology.md — Thấp — `flag`

- **Vị trí:** `rules/terminology.md:48-74`
- **Bằng chứng:** "§2 Modality — advisory, and not a compliance lever"; "§1… **Measured: no effect.**"
- **Vì sao:** File nạp mỗi lần đọc `PLAN.md`, `SUMMARY.md`, `research-brief.md`, nhưng chính nó nói chỉ §3 có tác dụng đo được. Số liệu đo là lý do, nên đây là gợi ý chuyển §1, §2 sang `specs/ste-terminology-evidence/DECISION.md`, không phải lỗi.

### C13. "ETA >30 min" làm ngưỡng viết plan — Thấp — `flag`

- **Vị trí:** `rules/plan-format.md:20`
- **Vì sao:** Ước lượng thời gian của người, agent không đo được. `rules/orchestration.md:55` và `skills/feature-intake/SKILL.md:54-56` chỉ nêu hai ngưỡng (>3 bước, >2 file).

### C14. Ví dụ theo stack ứng dụng trong repo không có stack — Thấp — `flag`

- **Vị trí:** `rules/auto-correct-scope.md:48,52,59-63,72`; `CLAUDE.md:89`
- **Bằng chứng:** "Wrong ORM/data-access query", "Missing `await`", "Migration revision ID collision"; gotcha về `app/**/*.py`
- **Vì sao:** Repo không có thư mục `app/`. Các dòng này phục vụ repo consumer, nên chỉ gắn cờ.

### C15. Câu chữ gắn với thời điểm — Thấp — `flag`

- **Vị trí:** `CLAUDE.md:38` ("which Phase 6 owns"); `CLAUDE.md:91` ("9 of the last 80 PRs would have blocked"); `rules/auto-correct-scope.md:38` ("once the back catalogue has drained"); `rules/terminology.md:91` ("v2.1.216")
- **Vì sao:** Sẽ sai dần theo thời gian và không ai kiểm lại. Phần lớn là lý do của một quyết định nên giữ, chỉ nên bỏ con số.

### C16. Hai rule luôn nạp chỉ để trỏ tới `techstacks/` rỗng — Thấp — `flag`

- **Vị trí:** `rules/architecture.md`, `rules/guidelines.md`
- **Vì sao:** "read `techstacks/*.md` before implementing", nhưng ở repo này `techstacks/` chỉ có README. Vô hại; file đã tự ghi chú ngoại lệ cho meta-repo.

### C17. `test-runner` có tool rộng hơn việc của nó — Thấp — `flag`

- **Vị trí:** `agents/test-runner.md:4` (nguồn: `agents/runtime-bindings.json`)
- **Bằng chứng:** `WebFetch, WebSearch, mcp__context7__resolve-library-id, mcp__context7__query-docs`
- **Vì sao:** Agent chỉ chạy test và báo cáo. Tên `mcp__context7__*` cũng không khớp tên tool context7 trong phiên này (`mcp__plugin_context7_context7__*`); tool thuộc phần cài ngoài repo nên chỉ gắn cờ.

### C18. Lệnh deploy trong AGENTS.md so với ghi nhớ của bạn — Thấp — `flag`

- **Vị trí:** `AGENTS.md:24`; `skills/using-git-worktrees/SKILL.md:36`
- **Vì sao:** Hai file bảo chạy `bash scripts/deploy-harness.sh` sau khi sửa nguồn. Ghi nhớ cấp user của bạn nói không đụng `.claude/` khi chưa được xác nhận. File ngoài dự án không phải lý do để sửa file trong dự án, nên không đề xuất chỉnh.

## Đã kiểm tra và vẫn đúng

- Danh sách rule ở `CLAUDE.md:7` khớp: 5 file luôn nạp, 4 file có `paths:`.
- Mọi đường dẫn `CLAUDE.md` và `AGENTS.md` nêu đều tồn tại: `docs/codex-alpha-install.md`, `scripts/codex_harness_doctor.py`, `tests/scripts/rule-loading-tiers.test.sh`, ba tài liệu `docs/solutions/harness/*`, `scripts/ci-strict-gate.sh`, `HARNESS.md`, `docs/harness-experimental/break-glass-log.md`, `templates/structure/specs-README.md`, `adapters/`, `evals/`.
- `_done_task_ids` có trong `render_plan.py`; `PYTESTS` có trong `scripts/run-tests.sh`.
- Frontmatter agent hợp lệ với model đã ghim; `test-runner` (Haiku 4.5) không đặt `effort`, đúng vì model đó không nhận.
- `reviewer` và `task-reviewer` không trùng lặp: khác bộ tool và mức effort.
- Các chỗ nhấn mạnh còn lại (`HARD-GATE`, "MUST write a `Lane:` line", "NEVER auto-apply", "Never fix") đều có lý do hoặc được hook thực thi, nên giữ.
- `CLAUDE.local.md` sạch.

## Diff đề xuất

Các hunk Nhóm 2 (H3–H7) chỉ là đề xuất, cần bạn xác nhận. Deploy lại sau khi áp dụng.

H3 (C1):

```diff
--- a/agents/PROJECT.md
+++ b/agents/PROJECT.md
@@ -7,2 +7,2 @@
-> Risk-classification signals are **not** here — they are built into `skills/xia2/SKILL.md` as
-> common cross-project vocabulary (xia2 is zero-config; it has no `PROJECT.md` sibling).
+> Risk-classification signals are **not** here — they live in `rules/research-depth.md` and
+> `skills/xia2/references/depth-classifier.md` (xia2 is zero-config; it has no `PROJECT.md` sibling).
--- a/agents/PROJECT.template.md
+++ b/agents/PROJECT.template.md
@@ -11,2 +11,2 @@
-> Risk-classification signals are **not** here — `skills/xia2/` is zero-config and carries them
-> inside its own `SKILL.md`. This file covers implementation + test execution only.
+> Risk-classification signals are **not** here — they live in `rules/research-depth.md` and
+> `skills/xia2/references/depth-classifier.md`. This file covers implementation + test execution only.
@@ -66 +66 @@
-- Kept separate from xia2's risk signals (which live in `skills/xia2/SKILL.md`). The agents must also work in a repo that does not use `xia2`.
+- Kept separate from xia2's risk signals (which live in `rules/research-depth.md`). The agents must also work in a repo that does not use `xia2`.
```

H4 (C2):

```diff
--- a/skills/README.md
+++ b/skills/README.md
@@ -208 +208 @@
-   signal with a lane below `high-risk` blocks (modes from the index `harness-manifest.json`)
+   signal with a lane below `high-risk` blocks (modes from the manifest in the git index, never a `.claude/` copy)
```

H5 (C3, C4):

```diff
--- a/agents/PROJECT.md
+++ b/agents/PROJECT.md
@@ -15 +15 @@
-- **Code style / error handling / validation / logging:** `rules/behavior.md` (single source of truth per CLAUDE.md)
+- **Code style / naming / testing conventions:** `AGENTS.md` → *Coding Style & Naming Conventions* and *Testing Guidelines*. Agent behavior rules: `rules/behavior.md`
@@ -26 +26 @@
-- **Targeted-run flags:** no flags; run a single suite directly, e.g. `bash tests/hooks/commit-gate.test.sh`
+- **Targeted-run flags:** shell: run one suite directly, e.g. `bash tests/hooks/commit-gate.test.sh`; Python: `python3 -m pytest <test file> -q`
@@ -28 +28 @@
-- **Markers / coverage:** none — bash test suites assert via `tests/lib.sh` helpers; no coverage gate
+- **Markers / coverage:** none — bash suites assert via `tests/lib.sh` helpers; Python tests are plain pytest (the list is `PYTESTS` in `scripts/run-tests.sh`); no coverage gate
```

H6 (C5):

```diff
--- a/skills/subagent-driven-development/implementer-prompt.md
+++ b/skills/subagent-driven-development/implementer-prompt.md
@@ -115,2 +115,4 @@
     - **deviations:** list of Rule 1–3 auto-fixes per `rules/auto-correct-scope.md`.
       Each entry: `{rule: 1|2|3, description, file, commit_sha}`. Empty list if none.
+    - **lane:** the intake lane this task ran under (`tiny | normal | high-risk`)
+    - **harness_delta:** workflow friction this task revealed — `fix-direct`, `backlog`, or `none`
```

H7 (C7):

```diff
--- a/rules/auto-correct-scope.md
+++ b/rules/auto-correct-scope.md
@@ -38 +38 @@
-… Run `python scripts/verify_summary.py --lane <slug>` (exit 1 = missing evidence). …
+… Run `python3 scripts/verify_summary.py --lane <slug>` (exit 1 = missing evidence). …
--- a/skills/README.md
+++ b/skills/README.md
@@ -229 +229 @@
-> `python scripts/verify_summary.py --lane <slug>`.
+> `python3 scripts/verify_summary.py --lane <slug>`.
```

Hai dòng ví dụ ở `rules/plan-format.md:99-100` đổi tương tự.

H8 (C8, mẫu; áp cùng kiểu cho 11 chỗ đã liệt kê):

```diff
--- a/rules/orchestration.md
+++ b/rules/orchestration.md
@@ -36 +36 @@
-- **Verify status** — pass/fail of task's `<verify>` command (with command output excerpt on fail)
+- **Verify status** — pass/fail of the task's `Verify` command (with command output excerpt on fail)
--- a/rules/auto-correct-scope.md
+++ b/rules/auto-correct-scope.md
@@ -50 +50 @@
-- Logic contradicting the `<action>` spec
+- Logic contradicting the task's `Action`
```

H9 (C9):

```diff
--- a/rules/behavior.md
+++ b/rules/behavior.md
@@ -5,2 +5,2 @@
-deliberately not restated here. §4 and §5 cover behaviors the Claude Opus 5.x guidance documents
-as departing from that default: scope drift, stopping at the easy part, and correction narration.
+deliberately not restated here. §4 and §5 cover scope drift, stopping at the easy part, and
+correction narration.
```

H10 (C10):

```diff
--- a/agents/test-runner.md
+++ b/agents/test-runner.md
@@ -3 +3 @@
-description: "Use this agent when unit tests have been modified or new tests have been written … <example>…</example> <example>…</example>"
+description: "Run the tests relevant to recently changed code and report the results. Use after implementing a feature, fixing a bug, or changing test files. It never edits code or tests."
```

H11 (C11):

```diff
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -99 +99 @@
-This project has a knowledge graph. Use the `code-review-graph` MCP tools **before** Grep/Glob/Read for exploration — faster, cheaper, and they give structural context (callers, dependents, test coverage) that file scanning cannot. Fall back to Grep/Glob/Read only when the graph doesn't cover what you need. The graph auto-updates on file changes (via hooks).
+This project has a knowledge graph. When the `code-review-graph` MCP server is connected, use it for structural questions (callers, dependents, test coverage, blast radius), which file scanning cannot answer. Use Grep/Glob/Read for everything else, and whenever the server is not connected.
```

C6 và C12–C18 không có hunk vì mỗi cái cần một quyết định của bạn.
